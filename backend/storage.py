from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from backend.domain import (
    MarketQuote,
    Order,
    PriceLevel,
    Trade,
)


class SQLiteStore:
    def __init__(self, database_path: str | Path = ":memory:") -> None:
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.connection = sqlite3.connect(
            self.database_path,
            check_same_thread=False,
            isolation_level=None,
        )
        self.connection.row_factory = sqlite3.Row
        self._configure_connection()
        self._create_schema()

    def reset(self) -> None:
        with self.lock:
            self.connection.executescript(
                """
                DELETE FROM pnl_history;
                DELETE FROM client_positions;
                DELETE FROM positions;
                DELETE FROM trades;
                DELETE FROM orders;
                DELETE FROM quotes;
                DELETE FROM counters;
                """
            )

    def next_order_id(self) -> str:
        return f"ORD-{self._next_number('order'):06d}"

    def next_trade_id(self) -> str:
        return f"TRD-{self._next_number('trade'):06d}"

    def upsert_quote(self, quote: MarketQuote) -> None:
        with self.lock:
            self.connection.execute(
                """
                INSERT INTO quotes (
                    market, bid, ask, mid, bid_depth_json, ask_depth_json, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(market) DO UPDATE SET
                    bid = excluded.bid,
                    ask = excluded.ask,
                    mid = excluded.mid,
                    bid_depth_json = excluded.bid_depth_json,
                    ask_depth_json = excluded.ask_depth_json,
                    timestamp = excluded.timestamp
                """,
                (
                    quote.market,
                    quote.bid,
                    quote.ask,
                    quote.mid,
                    json.dumps([level.__dict__ for level in quote.bid_depth]),
                    json.dumps([level.__dict__ for level in quote.ask_depth]),
                    quote.timestamp,
                ),
            )

    def get_quote(self, market: str) -> MarketQuote | None:
        with self.lock:
            row = self.connection.execute(
                "SELECT * FROM quotes WHERE market = ?",
                (market,),
            ).fetchone()
        return self._quote_from_row(row) if row else None

    def list_quotes(self) -> list[MarketQuote]:
        with self.lock:
            rows = self.connection.execute("SELECT * FROM quotes ORDER BY market").fetchall()
        return [self._quote_from_row(row) for row in rows]

    def insert_order(self, order: Order) -> None:
        with self.lock:
            self.connection.execute(
                """
                INSERT INTO orders (
                    order_id, client_id, market, side, order_type, quantity,
                    filled_quantity, average_price, status, bid, ask, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order.order_id,
                    order.client_id,
                    order.market,
                    order.side,
                    order.order_type,
                    order.quantity,
                    order.filled_quantity,
                    order.average_price,
                    order.status,
                    order.bid,
                    order.ask,
                    order.created_at,
                    order.updated_at,
                ),
            )

    def update_order(self, order: Order) -> None:
        with self.lock:
            self.connection.execute(
                """
                UPDATE orders
                SET filled_quantity = ?, average_price = ?, status = ?, updated_at = ?
                WHERE order_id = ?
                """,
                (
                    order.filled_quantity,
                    order.average_price,
                    order.status,
                    order.updated_at,
                    order.order_id,
                ),
            )

    def insert_trade(self, trade: Trade, *, spread_capture: float) -> None:
        with self.lock:
            self.connection.execute(
                """
                INSERT INTO trades (
                    trade_id, order_id, client_id, market, side, quantity, price,
                    liquidity_side, book_quantity_delta, cash_delta, spread_capture,
                    executed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade.trade_id,
                    trade.order_id,
                    trade.client_id,
                    trade.market,
                    trade.side,
                    trade.quantity,
                    trade.price,
                    trade.liquidity_side,
                    trade.book_quantity_delta,
                    trade.cash_delta,
                    spread_capture,
                    trade.executed_at,
                ),
            )

    def apply_trade_to_positions(self, trade: Trade) -> None:
        with self.lock:
            self.connection.execute(
                """
                INSERT INTO positions (market, quantity, cash)
                VALUES (?, ?, ?)
                ON CONFLICT(market) DO UPDATE SET
                    quantity = quantity + excluded.quantity,
                    cash = cash + excluded.cash
                """,
                (trade.market, trade.book_quantity_delta, trade.cash_delta),
            )
            self.connection.execute(
                """
                INSERT INTO client_positions (client_id, market, quantity, cash)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(client_id, market) DO UPDATE SET
                    quantity = quantity + excluded.quantity,
                    cash = cash + excluded.cash
                """,
                (
                    trade.client_id,
                    trade.market,
                    trade.book_quantity_delta,
                    trade.cash_delta,
                ),
            )

    def append_pnl(self, *, timestamp: float, total_pnl: float) -> None:
        with self.lock:
            self.connection.execute(
                "INSERT INTO pnl_history (timestamp, total_pnl) VALUES (?, ?)",
                (timestamp, total_pnl),
            )
            self.connection.execute(
                """
                DELETE FROM pnl_history
                WHERE id NOT IN (
                    SELECT id FROM pnl_history ORDER BY timestamp DESC LIMIT 600
                )
                """
            )

    def recent_orders(self, *, limit: int) -> list[Order]:
        with self.lock:
            rows = self.connection.execute(
                "SELECT * FROM orders ORDER BY created_at DESC, order_id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._order_from_row(row) for row in rows]

    def recent_trades(self, *, limit: int) -> list[Trade]:
        with self.lock:
            rows = self.connection.execute(
                "SELECT * FROM trades ORDER BY executed_at DESC, trade_id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._trade_from_row(row) for row in rows]

    def pnl_history(self, *, limit: int) -> list[dict[str, float]]:
        with self.lock:
            rows = self.connection.execute(
                """
                SELECT timestamp, total_pnl
                FROM pnl_history
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {"timestamp": row["timestamp"], "total_pnl": row["total_pnl"]}
            for row in reversed(rows)
        ]

    def position_rows(self) -> list[sqlite3.Row]:
        with self.lock:
            return self.connection.execute(
                """
                SELECT p.market, p.quantity, p.cash, q.mid AS mark
                FROM positions p
                JOIN quotes q ON q.market = p.market
                ORDER BY p.market
                """
            ).fetchall()

    def pnl_by_client(self) -> dict[str, float]:
        with self.lock:
            rows = self.connection.execute(
                """
                SELECT cp.client_id, SUM(cp.cash + cp.quantity * q.mid) AS pnl
                FROM client_positions cp
                JOIN quotes q ON q.market = cp.market
                GROUP BY cp.client_id
                """
            ).fetchall()
        return {row["client_id"]: float(row["pnl"]) for row in rows}

    def monetization_by_client(self) -> dict[str, float]:
        with self.lock:
            rows = self.connection.execute(
                "SELECT client_id, SUM(spread_capture) AS total "
                "FROM trades GROUP BY client_id"
            ).fetchall()
        return {row["client_id"]: float(row["total"]) for row in rows}

    def notional_by_client(self) -> dict[str, float]:
        with self.lock:
            rows = self.connection.execute(
                "SELECT client_id, SUM(price * quantity) AS total "
                "FROM trades GROUP BY client_id"
            ).fetchall()
        return {row["client_id"]: float(row["total"]) for row in rows}

    def total_spread_capture(self) -> float:
        with self.lock:
            row = self.connection.execute(
                "SELECT COALESCE(SUM(spread_capture), 0) AS total FROM trades"
            ).fetchone()
        return float(row["total"])

    def count_orders(self) -> int:
        with self.lock:
            row = self.connection.execute(
                "SELECT COUNT(*) AS count FROM orders"
            ).fetchone()
        return int(row["count"])

    def count_trades(self) -> int:
        with self.lock:
            row = self.connection.execute(
                "SELECT COUNT(*) AS count FROM trades"
            ).fetchone()
        return int(row["count"])

    def _next_number(self, counter_name: str) -> int:
        with self.lock:
            self.connection.execute(
                "INSERT OR IGNORE INTO counters (name, next_value) VALUES (?, 1)",
                (counter_name,),
            )
            row = self.connection.execute(
                "SELECT next_value FROM counters WHERE name = ?",
                (counter_name,),
            ).fetchone()
            value = int(row["next_value"])
            self.connection.execute(
                "UPDATE counters SET next_value = ? WHERE name = ?",
                (value + 1, counter_name),
            )
            return value

    def _configure_connection(self) -> None:
        with self.lock:
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA synchronous=NORMAL")
            self.connection.execute("PRAGMA busy_timeout=5000")
            self.connection.execute("PRAGMA foreign_keys=ON")

    def _create_schema(self) -> None:
        with self.lock:
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS counters (
                    name TEXT PRIMARY KEY,
                    next_value INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS quotes (
                    market TEXT PRIMARY KEY,
                    bid REAL NOT NULL,
                    ask REAL NOT NULL,
                    mid REAL NOT NULL,
                    bid_depth_json TEXT NOT NULL,
                    ask_depth_json TEXT NOT NULL,
                    timestamp REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    market TEXT NOT NULL,
                    side TEXT NOT NULL,
                    order_type TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    filled_quantity INTEGER NOT NULL,
                    average_price REAL,
                    status TEXT NOT NULL,
                    bid REAL NOT NULL,
                    ask REAL NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS trades (
                    trade_id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL,
                    client_id TEXT NOT NULL,
                    market TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    liquidity_side TEXT NOT NULL,
                    book_quantity_delta INTEGER NOT NULL,
                    cash_delta REAL NOT NULL,
                    spread_capture REAL NOT NULL,
                    executed_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS positions (
                    market TEXT PRIMARY KEY,
                    quantity INTEGER NOT NULL DEFAULT 0,
                    cash REAL NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS client_positions (
                    client_id TEXT NOT NULL,
                    market TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 0,
                    cash REAL NOT NULL DEFAULT 0,
                    PRIMARY KEY (client_id, market)
                );

                CREATE TABLE IF NOT EXISTS pnl_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    total_pnl REAL NOT NULL
                );

                """
            )

    @staticmethod
    def _quote_from_row(row: sqlite3.Row) -> MarketQuote:
        return MarketQuote(
            market=row["market"],
            bid=row["bid"],
            ask=row["ask"],
            mid=row["mid"],
            bid_depth=tuple(
                PriceLevel(price=item["price"], quantity=item["quantity"])
                for item in json.loads(row["bid_depth_json"])
            ),
            ask_depth=tuple(
                PriceLevel(price=item["price"], quantity=item["quantity"])
                for item in json.loads(row["ask_depth_json"])
            ),
            timestamp=row["timestamp"],
        )

    @staticmethod
    def _order_from_row(row: sqlite3.Row) -> Order:
        return Order(
            order_id=row["order_id"],
            client_id=row["client_id"],
            market=row["market"],
            side=row["side"],  # type: ignore[arg-type]
            order_type=row["order_type"],  # type: ignore[arg-type]
            quantity=row["quantity"],
            filled_quantity=row["filled_quantity"],
            average_price=row["average_price"],
            status=row["status"],  # type: ignore[arg-type]
            bid=row["bid"],
            ask=row["ask"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _trade_from_row(row: sqlite3.Row) -> Trade:
        return Trade(
            trade_id=row["trade_id"],
            order_id=row["order_id"],
            client_id=row["client_id"],
            market=row["market"],
            side=row["side"],  # type: ignore[arg-type]
            quantity=row["quantity"],
            price=row["price"],
            liquidity_side=row["liquidity_side"],  # type: ignore[arg-type]
            executed_at=row["executed_at"],
        )
