from __future__ import annotations

from flask import request
from flask_restx import Namespace, Resource

from backend.storage import SQLiteStore
from backend.web.queries import DashboardQueryService
from backend.web.websocket import clear_live_payload_cache


def create_api_namespace(
    store: SQLiteStore,
    queries: DashboardQueryService,
) -> Namespace:
    api_namespace = Namespace("api", path="/api", description="Dashboard API")

    @api_namespace.route("/health")
    class HealthResource(Resource):
        def get(self):
            return {"status": "ok"}, 200

    @api_namespace.route("/config")
    class ConfigResource(Resource):
        def get(self):
            return queries.config_payload()

    @api_namespace.route("/trades/recent")
    class RecentTradesResource(Resource):
        def get(self):
            return queries.recent_trades_payload(limit=_request_limit(default=10))

    @api_namespace.route("/pnl/history")
    class PnlHistoryResource(Resource):
        def get(self):
            return queries.pnl_history_payload(limit=_request_limit(default=300))

    @api_namespace.route("/reset")
    class ResetResource(Resource):
        def post(self):
            store.reset()
            clear_live_payload_cache()
            return {"status": "reset"}

    return api_namespace


def _request_limit(default: int = 30) -> int:
    raw_limit = request.args.get("limit", default)
    try:
        return int(raw_limit)
    except (TypeError, ValueError):
        return default
