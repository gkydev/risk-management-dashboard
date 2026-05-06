from __future__ import annotations

import time

from backend.config import DEFAULT_CLIENTS, DEFAULT_MARKETS
from backend.storage import SQLiteStore
from backend.web.serialization import quote_payload, trade_payload

PNL_HISTORY_SAMPLE_SECONDS = 1.0


class DashboardQueryService:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store
        # Throttles pnl_history DB writes to one per PNL_HISTORY_SAMPLE_SECONDS.
        # Safe because there is one DashboardQueryService per backend process.
        self._last_pnl_history_at = 0.0

    def config_payload(self) -> dict[str, object]:
        return {
            "timestamp": time.time(),
            "markets": [market.__dict__ for market in DEFAULT_MARKETS],
            "clients": [client.__dict__ for client in DEFAULT_CLIENTS],
            "cadence": {
                "market_data_seconds": 0.25,
                "mock_order_source_seconds": 0.25,
            },
        }

    def live_payload(self) -> dict[str, object]:
        # Side effect: samples total PnL into pnl_history so refreshes and new
        # tabs see the same recent curve. Throttled by _append_pnl_history.
        timestamp = time.time()
        positions = self.positions_payload()
        summary = self.summary_payload(positions)
        self._append_pnl_history(
            timestamp=timestamp,
            total_pnl=float(summary["total_pnl"]),
        )
        return {
            "timestamp": timestamp,
            "prices": [quote_payload(quote) for quote in self.store.list_quotes()],
            "recent_trades": [
                trade_payload(trade) for trade in self.store.recent_trades(limit=10)
            ],
            "positions": positions,
            "summary": summary,
        }

    def recent_trades_payload(self, *, limit: int = 30) -> dict[str, object]:
        limit = self._bounded_limit(limit)
        return {
            "timestamp": time.time(),
            "limit": limit,
            "trades": [
                trade_payload(trade) for trade in self.store.recent_trades(limit=limit)
            ],
        }

    def pnl_history_payload(self, *, limit: int = 300) -> dict[str, object]:
        limit = self._bounded_limit(limit, max_limit=600)
        return {
            "timestamp": time.time(),
            "limit": limit,
            "points": self.store.pnl_history(limit=limit),
        }

    def positions_payload(self) -> list[dict[str, object]]:
        return [
            {
                "market": row["market"],
                "quantity": row["quantity"],
                "cash": round(row["cash"], 2),
                "mark": row["mark"],
                "market_value": round(row["quantity"] * row["mark"], 2),
                "pnl": round(row["cash"] + row["quantity"] * row["mark"], 2),
            }
            for row in self.store.position_rows()
        ]

    def summary_payload(
        self, positions: list[dict[str, object]] | None = None
    ) -> dict[str, object]:
        # PnL: cash + qty * mark per market, summed across the book.
        # Monetization: half-spread captured at fill, summed across trades.
        # Client yield (bps): monetization / total notional.
        # The two SUMs below are full-table; fine at MVP scale, but at prod
        # scale replace with incremental counters or a streaming aggregator.
        positions = positions if positions is not None else self.positions_payload()
        total_pnl = sum(float(position["pnl"]) for position in positions)
        gross_exposure = sum(float(abs(position["market_value"])) for position in positions)
        monetization_total = sum(self.store.monetization_by_client().values())
        notional_total = sum(self.store.notional_by_client().values())
        client_yield_bps = (
            monetization_total / notional_total * 10_000 if notional_total else 0.0
        )
        return {
            "total_pnl": round(total_pnl, 2),
            "gross_exposure": round(gross_exposure, 2),
            "monetization": round(monetization_total, 2),
            "client_yield_bps": round(client_yield_bps, 4),
            "trade_count": self.store.count_trades(),
        }

    def _append_pnl_history(self, *, timestamp: float, total_pnl: float) -> None:
        if timestamp - self._last_pnl_history_at < PNL_HISTORY_SAMPLE_SECONDS:
            return
        self.store.append_pnl(timestamp=timestamp, total_pnl=total_pnl)
        self._last_pnl_history_at = timestamp

    @staticmethod
    def _bounded_limit(limit: int, *, max_limit: int = 100) -> int:
        return max(1, min(limit, max_limit))
