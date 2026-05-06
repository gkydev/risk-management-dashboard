from __future__ import annotations

import logging
import random

from backend.domain import MarketConfig, MarketQuote, PriceLevel
from backend.storage import SQLiteStore

logger = logging.getLogger(__name__)


class MarketDataService:
    MIN_SPREAD_MULTIPLIER = 0.65
    MAX_SPREAD_MULTIPLIER = 1.45

    def __init__(
        self,
        store: SQLiteStore,
        markets: list[MarketConfig],
        *,
        seed: int = 11,
    ) -> None:
        self.store = store
        self.markets = markets
        self.random = random.Random(seed)
        self.prices = {market.market: market.base_price for market in markets}

    def initialize(self, now: float) -> None:
        for market in self.markets:
            self.store.upsert_quote(self._build_quote(market, market.base_price, now))
        logger.info("mock market data seeded (%d markets)", len(self.markets))

    def update_once(self, now: float) -> list[MarketQuote]:
        quotes = []
        for market in self.markets:
            current_mid = self.prices[market.market]
            shock = self.random.gauss(0, market.volatility_bps / 10_000)
            next_mid = max(current_mid * (1 + shock), 0.0001)
            quote = self._build_quote(market, next_mid, now)
            self.prices[market.market] = quote.mid
            self.store.upsert_quote(quote)
            quotes.append(quote)
        logger.debug(
            "quotes tick: %s",
            ", ".join(f"{q.market} mid={q.mid}" for q in quotes),
        )
        return quotes

    def _build_quote(self, market: MarketConfig, mid: float, now: float) -> MarketQuote:
        pip = self._pip_size(market.market)
        precision = self._price_precision(market.market)
        spread_bps = self._floating_spread_bps(market)
        # 20_000 = 10_000 (bps -> fraction) * 2 (full spread -> half spread).
        # Floored at one pip so the bid/ask never collapse to the same price.
        half_spread = max(mid * spread_bps / 20_000, pip)
        bid = round(mid - half_spread, precision)
        ask = round(mid + half_spread, precision)
        bid_depth = tuple(
            PriceLevel(
                price=round(bid - level * pip, precision),
                quantity=self.random.randint(5, 35) * 100_000,
            )
            for level in range(market.depth_levels)
        )
        ask_depth = tuple(
            PriceLevel(
                price=round(ask + level * pip, precision),
                quantity=self.random.randint(5, 35) * 100_000,
            )
            for level in range(market.depth_levels)
        )
        return MarketQuote(
            market=market.market,
            bid=bid,
            ask=ask,
            mid=round(mid, precision),
            bid_depth=bid_depth,
            ask_depth=ask_depth,
            timestamp=now,
        )

    @staticmethod
    def _pip_size(market: str) -> float:
        if market.endswith("JPY"):
            return 0.01
        if market in {"BTCUSD", "XAUUSD"}:
            return 0.1
        return 0.0001

    @staticmethod
    def _price_precision(market: str) -> int:
        if market.endswith("JPY") or market in {"BTCUSD", "XAUUSD"}:
            return 2
        return 5

    def _floating_spread_bps(self, market: MarketConfig) -> float:
        multiplier = self.random.uniform(
            self.MIN_SPREAD_MULTIPLIER,
            self.MAX_SPREAD_MULTIPLIER,
        )
        return max(market.spread_bps * multiplier, 0.01)
