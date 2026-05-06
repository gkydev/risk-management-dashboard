from __future__ import annotations

import logging
import os
import queue
import threading
import time
from collections.abc import Callable

from backend.config import DEFAULT_CLIENTS, DEFAULT_MARKETS
from backend.storage import SQLiteStore
from backend.domain import ClientConfig, MarketConfig, OrderRequest
from backend.mock.client_orders import ClientOrderSimulator
from backend.mock.execution import ExecutionService
from backend.mock.market_data import MarketDataService

logger = logging.getLogger(__name__)
DEFAULT_MOCK_ORDER_SCALE = 1
DEFAULT_MOCK_ORDER_INTERVAL_SECONDS = 1.5


class MockFeedRunner:
    def __init__(
        self,
        *,
        store: SQLiteStore,
        markets: list[MarketConfig] | None = None,
        clients: list[ClientConfig] | None = None,
        mock_order_scale: int = 1,
        mock_order_interval_seconds: float = DEFAULT_MOCK_ORDER_INTERVAL_SECONDS,
    ) -> None:
        self.store = store
        self.markets = markets or DEFAULT_MARKETS
        self.clients = clients or DEFAULT_CLIENTS
        self.mock_order_scale = max(mock_order_scale, 1)
        self.mock_order_interval_seconds = max(mock_order_interval_seconds, 0.1)
        self.market_data = MarketDataService(store, self.markets)
        self.client_orders = ClientOrderSimulator(self.clients, self.markets)
        self.execution = ExecutionService(store)
        # Bounded so a stalled execution thread can't grow memory without limit;
        # 5_000 is roughly ten minutes of orders at the default cadence.
        self.order_queue: queue.Queue[OrderRequest] = queue.Queue(maxsize=5_000)
        self.stop_event = threading.Event()
        self.threads: list[threading.Thread] = []

    def start(self) -> None:
        if self.threads:
            return
        logger.info(
            "starting mock feed (markets=%s, clients=%s, order_scale=%s, order_interval_seconds=%s)",
            [m.market for m in self.markets],
            [c.client_id for c in self.clients],
            self.mock_order_scale,
            self.mock_order_interval_seconds,
        )
        self.market_data.initialize(time.time())
        self._start_thread("mock-market-data", self._market_data_loop)
        self._start_thread("mock-client-orders", self._client_order_loop)
        self._start_thread("mock-execution", self._execution_loop)

    def stop(self) -> None:
        logger.info("stopping mock feed")
        self.stop_event.set()
        for thread in self.threads:
            thread.join(timeout=2)

    def run_forever(self) -> None:
        self.start()
        try:
            while not self.stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("mock feed interrupted (KeyboardInterrupt)")
            self.stop()

    def _start_thread(self, name: str, target: Callable[[], None]) -> None:
        thread = threading.Thread(target=target, name=name, daemon=True)
        thread.start()
        self.threads.append(thread)

    def _market_data_loop(self) -> None:
        while not self.stop_event.is_set():
            self.market_data.update_once(time.time())
            self.stop_event.wait(0.25)

    def _client_order_loop(self) -> None:
        while not self.stop_event.is_set():
            requests = self.client_orders.generate_order_requests(
                time.time(),
                scale=self.mock_order_scale,
            )
            for request in requests:
                try:
                    self.order_queue.put_nowait(request)
                except queue.Full:
                    logger.warning(
                        "order queue full (max=%s); dropping remaining batch",
                        self.order_queue.maxsize,
                    )
                    break
            self.stop_event.wait(self.mock_order_interval_seconds)

    def _execution_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                request = self.order_queue.get(timeout=0.25)
            except queue.Empty:
                continue
            try:
                self.execution.execute_market_order(request)
            except ValueError as err:
                logger.warning("execution skipped: %s", err)
            except Exception:
                logger.exception("execution failed")
            finally:
                self.order_queue.task_done()


def _configure_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    if not logging.root.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s [%(threadName)s] %(message)s",
        )
    else:
        logging.getLogger().setLevel(level)


def _float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError:
        logger.warning("%s must be a float; using default %s", name, default)
        return default


def _int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        logger.warning("%s must be an int; using default %s", name, default)
        return default


def main() -> None:
    _configure_logging()
    db_path = os.getenv("DATABASE_PATH", "./risk_dashboard.db")
    mock_order_scale = _int_env("MOCK_ORDER_SCALE", DEFAULT_MOCK_ORDER_SCALE)
    mock_order_interval_seconds = _float_env(
        "MOCK_ORDER_INTERVAL_SECONDS",
        DEFAULT_MOCK_ORDER_INTERVAL_SECONDS,
    )
    logger.info("mock feed database path: %s", db_path)
    store = SQLiteStore(db_path)
    MockFeedRunner(
        store=store,
        mock_order_scale=mock_order_scale,
        mock_order_interval_seconds=mock_order_interval_seconds,
    ).run_forever()


if __name__ == "__main__":
    main()
