from __future__ import annotations

from flask_cors import CORS
from flask_restx import Api
from flask_sock import Sock

cors = CORS()
rest_api = Api(
    version="0.1.0",
    title="Finalto Risk Dashboard API",
    description="Local API for simulated market data, client orders, trades, and risk analytics.",
    doc="/docs",
)
sock = Sock()
