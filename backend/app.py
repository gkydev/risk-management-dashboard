from __future__ import annotations

import os

from flask import Flask

from backend.storage import SQLiteStore
from backend.web.api import create_api_namespace
from backend.web.extensions import cors, rest_api, sock
from backend.web.queries import DashboardQueryService
from backend.web.websocket import register_websocket_routes


def create_app() -> Flask:
    app = Flask(__name__)

    cors.init_app(app)
    rest_api.init_app(app)
    sock.init_app(app)

    store = SQLiteStore(os.getenv("DATABASE_PATH", "./risk_dashboard.db"))
    queries = DashboardQueryService(store)

    rest_api.add_namespace(create_api_namespace(store, queries))
    register_websocket_routes(queries)
    return app
