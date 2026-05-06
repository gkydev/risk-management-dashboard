from __future__ import annotations

import unittest

from backend.domain import Order, Trade


class DomainTests(unittest.TestCase):
    def test_order_remaining_quantity_and_fill_ratio(self) -> None:
        order = Order(
            order_id="ORD-000001",
            client_id="client-001",
            market="GBPUSD",
            side="sell",
            order_type="market",
            quantity=2_500_000,
            filled_quantity=1_000_000,
            average_price=1.064,
            status="partial",
            bid=1.064,
            ask=1.065,
            created_at=1.0,
            updated_at=2.0,
        )

        self.assertEqual(order.remaining_quantity, 1_500_000)
        self.assertEqual(order.fill_ratio, 0.4)

    def test_trade_sign_convention_is_client_perspective(self) -> None:
        buy_trade = Trade(
            trade_id="TRD-000001",
            order_id="ORD-000001",
            client_id="client-001",
            market="GBPUSD",
            side="buy",
            quantity=1_000_000,
            price=1.065,
            liquidity_side="ask",
            executed_at=1.0,
        )
        sell_trade = Trade(
            trade_id="TRD-000002",
            order_id="ORD-000002",
            client_id="client-001",
            market="GBPUSD",
            side="sell",
            quantity=1_000_000,
            price=1.064,
            liquidity_side="bid",
            executed_at=1.0,
        )

        self.assertEqual(buy_trade.book_quantity_delta, -1_000_000)
        self.assertEqual(buy_trade.cash_delta, 1_065_000)
        self.assertEqual(sell_trade.book_quantity_delta, 1_000_000)
        self.assertEqual(sell_trade.cash_delta, -1_064_000)


if __name__ == "__main__":
    unittest.main()
