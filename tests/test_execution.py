from __future__ import annotations

import unittest

from backend.domain import (
    ClientConfig,
    MarketConfig,
    MarketQuote,
    OrderRequest,
    PriceLevel,
)
from backend.storage import SQLiteStore
from backend.mock.client_orders import ClientOrderSimulator
from backend.mock.execution import ExecutionService


class ExecutionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore(":memory:")
        self.execution = ExecutionService(self.store)
        self.store.upsert_quote(
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

    def test_client_sell_market_order_creates_multiple_trades(self) -> None:
        order, trades = self.execution.execute_market_order(
            OrderRequest(
                client_id="client-001",
                market="GBPUSD",
                side="sell",
                order_type="market",
                quantity=2_500_000,
                requested_at=2.0,
            )
        )

        self.assertEqual(order.status, "filled")
        self.assertEqual(order.filled_quantity, 2_500_000)
        self.assertAlmostEqual(order.average_price or 0, 1.0638)
        self.assertEqual([trade.quantity for trade in trades], [2_000_000, 500_000])
        self.assertEqual([trade.price for trade in trades], [1.064, 1.063])
        self.assertEqual({trade.order_id for trade in trades}, {order.order_id})
        position = self.store.position_rows()[0]
        self.assertEqual(position["quantity"], 2_500_000)
        self.assertAlmostEqual(position["cash"], -2_659_500)

    def test_client_buy_market_order_reduces_finalto_position(self) -> None:
        order, trades = self.execution.execute_market_order(
            OrderRequest(
                client_id="client-001",
                market="GBPUSD",
                side="buy",
                order_type="market",
                quantity=1_500_000,
                requested_at=2.0,
            )
        )

        self.assertEqual(order.status, "filled")
        self.assertEqual([trade.liquidity_side for trade in trades], ["ask", "ask"])
        position = self.store.position_rows()[0]
        self.assertEqual(position["quantity"], -1_500_000)
        self.assertAlmostEqual(position["cash"], 1_598_000)

    def test_market_order_can_be_partially_filled_and_cancelled(self) -> None:
        order, trades = self.execution.execute_market_order(
            OrderRequest(
                client_id="client-001",
                market="GBPUSD",
                side="sell",
                order_type="market",
                quantity=3_500_000,
                requested_at=2.0,
            )
        )

        self.assertEqual(order.status, "partial_cancelled")
        self.assertEqual(order.filled_quantity, 3_000_000)
        self.assertEqual(order.remaining_quantity, 500_000)
        self.assertEqual(sum(trade.quantity for trade in trades), 3_000_000)


class ClientOrderSimulatorTests(unittest.TestCase):
    def test_simulator_only_generates_order_requests(self) -> None:
        simulator = ClientOrderSimulator(
            clients=[ClientConfig("client-001", "Test Client", 1.0, 100_000)],
            markets=[MarketConfig("GBPUSD", 1.0635, 1.0, 1.0)],
            seed=1,
        )

        requests = simulator.generate_order_requests(10.0)

        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].client_id, "client-001")
        self.assertEqual(requests[0].market, "GBPUSD")
        self.assertEqual(requests[0].order_type, "market")
        self.assertEqual(requests[0].requested_at, 10.0)


if __name__ == "__main__":
    unittest.main()
