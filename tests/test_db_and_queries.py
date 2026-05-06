from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.storage import SQLiteStore
from backend.domain import MarketQuote, OrderRequest, PriceLevel
from backend.mock.execution import ExecutionService
from backend.web.queries import DashboardQueryService


def seed_gbpusd_quote(store: SQLiteStore) -> None:
    store.upsert_quote(
        MarketQuote(
            market="GBPUSD",
            bid=1.064,
            ask=1.065,
            mid=1.0645,
            bid_depth=(
                PriceLevel(price=1.064, quantity=2_000_000),
                PriceLevel(price=1.063, quantity=1_000_000),
            ),
            ask_depth=(
                PriceLevel(price=1.065, quantity=1_000_000),
                PriceLevel(price=1.066, quantity=1_000_000),
            ),
            timestamp=1.0,
        )
    )


class DatabaseAndQueryTests(unittest.TestCase):
    def test_two_sqlite_connections_share_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "risk.db"
            writer = SQLiteStore(database_path)
            reader = SQLiteStore(database_path)

            seed_gbpusd_quote(writer)

            quote = reader.get_quote("GBPUSD")
            self.assertIsNotNone(quote)
            self.assertEqual(quote.market, "GBPUSD")
            self.assertEqual(quote.bid, 1.064)

    def test_dashboard_queries_calculate_summary_from_db(self) -> None:
        store = SQLiteStore(":memory:")
        seed_gbpusd_quote(store)
        ExecutionService(store).execute_market_order(
            OrderRequest(
                client_id="client-001",
                market="GBPUSD",
                side="sell",
                order_type="market",
                quantity=2_500_000,
                requested_at=2.0,
            )
        )

        payload = DashboardQueryService(store).summary_payload()

        self.assertEqual(payload["total_pnl"], 500.0)
        self.assertEqual(payload["gross_exposure"], 2_660_000.0)
        self.assertEqual(payload["monetization"], 1750.0)
        self.assertEqual(payload["client_yield_bps"], 6.5802)
        self.assertEqual(payload["trade_count"], 2)

    def test_recent_trade_query_is_separate_from_summary(self) -> None:
        store = SQLiteStore(":memory:")
        seed_gbpusd_quote(store)
        ExecutionService(store).execute_market_order(
            OrderRequest(
                client_id="client-001",
                market="GBPUSD",
                side="sell",
                order_type="market",
                quantity=2_500_000,
                requested_at=2.0,
            )
        )

        payload = DashboardQueryService(store).recent_trades_payload(limit=30)

        self.assertEqual(payload["limit"], 30)
        self.assertEqual(len(payload["trades"]), 2)

    def test_live_payload_records_backend_pnl_history(self) -> None:
        store = SQLiteStore(":memory:")
        seed_gbpusd_quote(store)
        ExecutionService(store).execute_market_order(
            OrderRequest(
                client_id="client-001",
                market="GBPUSD",
                side="sell",
                order_type="market",
                quantity=2_500_000,
                requested_at=2.0,
            )
        )

        queries = DashboardQueryService(store)
        live_payload = queries.live_payload()
        history_payload = queries.pnl_history_payload(limit=10)

        self.assertEqual(history_payload["limit"], 10)
        self.assertEqual(len(history_payload["points"]), 1)
        self.assertEqual(
            history_payload["points"][0]["total_pnl"],
            live_payload["summary"]["total_pnl"],
        )


if __name__ == "__main__":
    unittest.main()
