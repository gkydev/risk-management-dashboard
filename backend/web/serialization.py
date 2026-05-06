from __future__ import annotations

from backend.domain import MarketQuote, PriceLevel, Trade


def price_level_payload(level: PriceLevel) -> dict[str, float | int]:
    return {"price": level.price, "quantity": level.quantity}


def quote_payload(quote: MarketQuote) -> dict[str, object]:
    return {
        "market": quote.market,
        "bid": quote.bid,
        "ask": quote.ask,
        "mid": quote.mid,
        "bid_depth": [price_level_payload(level) for level in quote.bid_depth],
        "ask_depth": [price_level_payload(level) for level in quote.ask_depth],
        "timestamp": quote.timestamp,
    }


def trade_payload(trade: Trade) -> dict[str, object]:
    return {
        "trade_id": trade.trade_id,
        "order_id": trade.order_id,
        "client_id": trade.client_id,
        "market": trade.market,
        "side": trade.side,
        "quantity": trade.quantity,
        "price": trade.price,
        "liquidity_side": trade.liquidity_side,
        "book_quantity_delta": trade.book_quantity_delta,
        "cash_delta": round(trade.cash_delta, 2),
        "executed_at": trade.executed_at,
    }
