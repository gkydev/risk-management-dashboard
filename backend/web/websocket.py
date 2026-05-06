from __future__ import annotations

import json
import logging
import os
import time

from backend.utils import TTLCache
from backend.web.extensions import sock
from backend.web.queries import DashboardQueryService

logger = logging.getLogger(__name__)
LIVE_PAYLOAD_CACHE_SECONDS = 0.3
LIVE_PAYLOAD_PUSH_SECONDS = 0.3


def _live_payload_cache_seconds() -> float:
    raw_value = os.getenv("LIVE_PAYLOAD_CACHE_SECONDS")
    if raw_value is None:
        return LIVE_PAYLOAD_CACHE_SECONDS
    try:
        return max(float(raw_value), 0.01)
    except ValueError:
        logger.warning(
            "LIVE_PAYLOAD_CACHE_SECONDS must be a float; using default %s",
            LIVE_PAYLOAD_CACHE_SECONDS,
        )
        return LIVE_PAYLOAD_CACHE_SECONDS


live_payload_cache = TTLCache[str](ttl_seconds=_live_payload_cache_seconds())

# Streaming model:
# The dashboard uses a single /ws/live channel that pushes a full state snapshot
# every 300 ms. Simple, stateless, fine at this scale.
#
# For real production load I'd swap the WS loop for a pub/sub event-driven model
# (Redis or RabbitMQ between the feed and the WS gateway, per-topic channels,
# push-on-change instead of poll-and-snapshot). Doing that here would be
# overengineering for an MVP — another broker, another container, another thing
# that can break. The current setup still scales horizontally
# WS is stateless, SQLite is the only shared boundary.

def register_websocket_routes(queries: DashboardQueryService) -> None:
    @sock.route("/ws/live")
    def live(ws):
        try:
            while True:
                payload_json = live_payload_cache.get_or_set(
                    lambda: json.dumps(queries.live_payload())
                )
                ws.send(payload_json)
                time.sleep(LIVE_PAYLOAD_PUSH_SECONDS)
        except Exception:
            logger.debug("live websocket disconnected", exc_info=True)
            return None


def clear_live_payload_cache() -> None:
    live_payload_cache.clear()
