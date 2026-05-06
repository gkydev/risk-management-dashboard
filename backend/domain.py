from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Side = Literal["buy", "sell"]
OrderType = Literal["market"]
OrderStatus = Literal[
    "open",
    "partial",
    "filled",
    "cancelled",
    "partial_cancelled",
    "rejected",
]
LiquiditySide = Literal["bid", "ask"]


@dataclass(frozen=True)
class MarketConfig:
    market: str
    base_price: float
    spread_bps: float
    volatility_bps: float
    depth_levels: int = 5


@dataclass(frozen=True)
class ClientConfig:
    client_id: str
    display_name: str
    trade_chance_per_tick: float
    max_quantity: int


@dataclass(frozen=True)
class PriceLevel:
    price: float
    quantity: int


@dataclass(frozen=True)
class MarketQuote:
    market: str
    bid: float
    ask: float
    mid: float
    bid_depth: tuple[PriceLevel, ...]
    ask_depth: tuple[PriceLevel, ...]
    timestamp: float


@dataclass(frozen=True)
class OrderRequest:
    client_id: str
    market: str
    side: Side
    order_type: OrderType
    quantity: int
    requested_at: float


@dataclass
class Order:
    order_id: str
    client_id: str
    market: str
    side: Side
    order_type: OrderType
    quantity: int
    filled_quantity: int
    average_price: float | None
    status: OrderStatus
    bid: float
    ask: float
    created_at: float
    updated_at: float

    @property
    def remaining_quantity(self) -> int:
        return max(self.quantity - self.filled_quantity, 0)

    @property
    def fill_ratio(self) -> float:
        if self.quantity == 0:
            return 0.0
        return self.filled_quantity / self.quantity


@dataclass(frozen=True)
class Trade:
    trade_id: str
    order_id: str
    client_id: str
    market: str
    side: Side
    quantity: int
    price: float
    liquidity_side: LiquiditySide
    executed_at: float

    @property
    def book_quantity_delta(self) -> int:
        if self.side == "buy":
            return -self.quantity
        return self.quantity

    @property
    def cash_delta(self) -> float:
        if self.side == "buy":
            return self.price * self.quantity
        return -self.price * self.quantity
