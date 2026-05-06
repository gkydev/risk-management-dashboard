from __future__ import annotations

import logging
import random

from backend.domain import (
    ClientConfig,
    MarketConfig,
    OrderRequest,
    Side,
)

logger = logging.getLogger(__name__)


class ClientOrderSimulator:
    def __init__(
        self,
        clients: list[ClientConfig],
        markets: list[MarketConfig],
        *,
        seed: int = 7,
    ) -> None:
        self.clients = clients
        self.markets = markets
        self.random = random.Random(seed)

    def generate_order_requests(self, now: float, *, scale: int = 1) -> list[OrderRequest]:
        requests: list[OrderRequest] = []
        scale = max(1, scale)
        for _ in range(scale):
            for client in self.clients:
                if self.random.random() < client.trade_chance_per_tick:
                    requests.append(self._request_for_client(client, now))
        if requests:
            logger.debug("generated %d mock client order(s)", len(requests))
        return requests

    def _request_for_client(self, client: ClientConfig, now: float) -> OrderRequest:
        side: Side = self.random.choice(["buy", "sell"])
        quantity_step = 50_000
        max_steps = max(1, client.max_quantity // quantity_step)
        return OrderRequest(
            client_id=client.client_id,
            market=self.random.choice(self.markets).market,
            side=side,
            order_type="market",
            quantity=self.random.randint(1, max_steps) * quantity_step,
            requested_at=now,
        )
