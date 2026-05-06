from __future__ import annotations

from backend.domain import ClientConfig, MarketConfig

DEFAULT_MARKETS = [
    MarketConfig("EURUSD", 1.0875, 1.4, 2.2),
    MarketConfig("GBPUSD", 1.2680, 1.8, 2.5),
    MarketConfig("USDJPY", 154.25, 1.6, 2.0),
    MarketConfig("AUDUSD", 0.6612, 1.7, 2.4),
    MarketConfig("XAUUSD", 2310.0, 3.2, 4.0),
    MarketConfig("BTCUSD", 64200.0, 8.0, 12.0),
]

DEFAULT_CLIENTS = [
    ClientConfig("client-001", "Client A", 0.20, 700_000),
    ClientConfig("client-002", "Client B", 0.16, 500_000),
    ClientConfig("client-003", "Client C", 0.18, 350_000),
    ClientConfig("client-004", "Client D", 0.12, 250_000),
    ClientConfig("client-005", "Client E", 0.14, 450_000),
    ClientConfig("client-006", "Client F", 0.15, 400_000),
]
