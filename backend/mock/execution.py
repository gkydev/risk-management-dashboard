from __future__ import annotations

import logging

from backend.domain import (
    MarketQuote,
    Order,
    OrderRequest,
    PriceLevel,
    Trade,
)
from backend.storage import SQLiteStore

logger = logging.getLogger(__name__)


class ExecutionService:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def execute_market_order(self, request: OrderRequest) -> tuple[Order, list[Trade]]:
        quote = self.store.get_quote(request.market)
        if quote is None:
            raise ValueError(f"No quote available for market: {request.market}")

        order = Order(
            order_id=self.store.next_order_id(),
            client_id=request.client_id,
            market=request.market,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            filled_quantity=0,
            average_price=None,
            status="open",
            bid=quote.bid,
            ask=quote.ask,
            created_at=request.requested_at,
            updated_at=request.requested_at,
        )
        self.store.insert_order(order)

        trades = self._execute_against_quote(order, quote)
        self.store.update_order(order)
        logger.info(
            "mock execution: order_id=%s client=%s %s %s qty=%s status=%s fills=%d avg=%s",
            order.order_id,
            order.client_id,
            order.market,
            order.side,
            order.quantity,
            order.status,
            len(trades),
            order.average_price,
        )
        return order, trades

    def _execute_against_quote(
        self, order: Order, quote: MarketQuote
    ) -> list[Trade]:
        liquidity_side = "ask" if order.side == "buy" else "bid"
        active_depth = quote.ask_depth if liquidity_side == "ask" else quote.bid_depth
        updated_depth: list[PriceLevel] = []
        trades: list[Trade] = []
        remaining = order.quantity

        for level in active_depth:
            if remaining > 0:
                fill_quantity = min(remaining, level.quantity)
                remaining -= fill_quantity
                if fill_quantity > 0:
                    trade = Trade(
                        trade_id=self.store.next_trade_id(),
                        order_id=order.order_id,
                        client_id=order.client_id,
                        market=order.market,
                        side=order.side,
                        quantity=fill_quantity,
                        price=level.price,
                        liquidity_side=liquidity_side,
                        executed_at=order.created_at,
                    )
                    self._persist_trade(trade, reference_mid=quote.mid)
                    trades.append(trade)
                level_remaining = level.quantity - fill_quantity
                if level_remaining > 0:
                    updated_depth.append(PriceLevel(level.price, level_remaining))
            else:
                updated_depth.append(level)

        filled_quantity = sum(trade.quantity for trade in trades)
        order.filled_quantity = filled_quantity
        order.average_price = (
            sum(trade.quantity * trade.price for trade in trades) / filled_quantity
            if filled_quantity
            else None
        )
        order.updated_at = order.created_at
        # Mock IOC semantics: anything not filled against current depth is
        # cancelled rather than left working. A real venue would leave the
        # remainder open; the dashboard's risk view doesn't model that.
        if filled_quantity == order.quantity:
            order.status = "filled"
        elif filled_quantity > 0:
            order.status = "partial_cancelled"
        else:
            order.status = "rejected"

        self._replace_consumed_depth(quote, liquidity_side, tuple(updated_depth))
        return trades

    def _persist_trade(self, trade: Trade, *, reference_mid: float) -> None:
        # Spread capture = how much we earned vs. mid at the moment of fill.
        # Client buys lift the ask (price > mid) and client sells hit the bid
        # (price < mid), so both branches yield a positive number on normal
        # flow. Negative would mean we filled the client through mid.
        if trade.side == "buy":
            spread_capture = (trade.price - reference_mid) * trade.quantity
        else:
            spread_capture = (reference_mid - trade.price) * trade.quantity
        self.store.insert_trade(trade, spread_capture=spread_capture)
        self.store.apply_trade_to_positions(trade)

    def _replace_consumed_depth(
        self,
        quote: MarketQuote,
        liquidity_side: str,
        updated_depth: tuple[PriceLevel, ...],
    ) -> None:
        bid_depth = updated_depth if liquidity_side == "bid" else quote.bid_depth
        ask_depth = updated_depth if liquidity_side == "ask" else quote.ask_depth
        bid = bid_depth[0].price if bid_depth else quote.bid
        ask = ask_depth[0].price if ask_depth else quote.ask
        mid = round((bid + ask) / 2, 5)
        self.store.upsert_quote(
            MarketQuote(
                market=quote.market,
                bid=bid,
                ask=ask,
                mid=mid,
                bid_depth=bid_depth,
                ask_depth=ask_depth,
                timestamp=quote.timestamp,
            )
        )
