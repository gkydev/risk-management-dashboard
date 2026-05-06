# Finalto Risk Dashboard MVP

MVP risk-management dashboard for simulated client trading activity and book metrics.

The application simulates streamed market prices, client market orders, generated
trades, positions, PnL, monetization, and client yield. The React dashboard consumes
bounded REST snapshots plus a live WebSocket feed.

The backend is split by responsibility:

- `app.py` is only the Flask application factory.
- `web/` owns RESTX resources, Flask extensions, serialization, and WebSocket routes.
- `storage.py` owns local SQLite persistence.
- `mock/` owns local fake market data, client order generation, and mock execution.
- `web/queries.py` calculates dashboard metrics from SQLite for API requests.
- `domain.py` and `config.py` contain shared trading types and static configuration.

The Flask API and mock feed do not share Python objects. Their only shared boundary
is the SQLite database file.

## Quick Start

There are two supported ways to run the application locally:

1. Docker Compose, which is the recommended and easiest option.
2. Manual local development with `uv` for the backend and `npm` for the frontend.

Docker Compose starts the backend API, mock feed, and frontend with one command:

```bash
docker compose up --build
```

Then open `http://127.0.0.1:3000`.

Compose starts:

- `backend`: Flask RESTX API and WebSocket server on container port `8000`.
- `mock-feed`: mock market data, client order, and execution generator.
- `frontend`: React dashboard built and served by nginx on host port `3000`.

The frontend proxies `/api` and `/ws` to the backend container, so the browser only
needs the frontend URL. To stop the stack, press `Ctrl+C`, then run:

```bash
docker compose down
```

To start a heavier 10x client-flow simulation:

```bash
MOCK_ORDER_SCALE=10 docker compose up --build
```

On Windows PowerShell:

```powershell
$env:MOCK_ORDER_SCALE = "10"
docker compose up --build
```

Useful URLs after startup:

- Dashboard: `http://127.0.0.1:3000`
- API health: `http://127.0.0.1:3000/api/health`
- API docs: `http://127.0.0.1:3000/docs`

## Local Development

Use this path if you want to run the backend, mock feed, and frontend directly
instead of Docker. It uses three terminals.

### 1. Backend API

From the repository root:

Python dependencies are managed with `uv`.

```bash
uv sync
uv run python -m backend
```

The Flask backend listens on `http://127.0.0.1:8000` by default.

### 2. Mock Feed

In a second terminal from the repository root:

```bash
uv run python -m backend.mock.feed
```

By default, mock client orders are generated every `1.5` seconds with an order
scale of `1`. `MOCK_ORDER_SCALE` multiplies the client order generation attempts
per interval. For example, `10` creates roughly ten times the normal client flow
without changing the market data cadence.

To run a 10x client-flow simulation:

```bash
MOCK_ORDER_SCALE=10 uv run python -m backend.mock.feed
```

To make the mock flow calmer or faster, set `MOCK_ORDER_INTERVAL_SECONDS` before
starting the feed:

```bash
MOCK_ORDER_INTERVAL_SECONDS=3 uv run python -m backend.mock.feed
```

On Windows PowerShell:

```powershell
$env:MOCK_ORDER_SCALE = "10"
$env:MOCK_ORDER_INTERVAL_SECONDS = "3"
uv run python -m backend.mock.feed
```

### 3. Frontend

In a third terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server listens on `http://127.0.0.1:5173` by default.

Optional frontend environment values can be copied from `frontend/.env.example`:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_WS_URL=ws://127.0.0.1:8000/ws/live
```

Then open `http://127.0.0.1:5173`.

Useful endpoints:

- `GET /api/health`
- `GET /api/config`
- `GET /api/trades/recent?limit=30`
- `GET /api/pnl/history?limit=300`
- `POST /api/reset`
- `WS /ws/live`

Flask-RESTX API documentation is available at `http://127.0.0.1:8000/docs`.

## Prerequisites

For Docker run:

- Docker Desktop or Docker Engine with Compose support.

For local development without Docker:

- Python `3.11` or newer.
- `uv` for Python dependency management.
- Node.js `20.19.0` or newer. This repository includes `.nvmrc`, so `nvm use`
  selects the expected Node version when using nvm.

No `requirements.txt` is used. Python dependencies are installed with `uv sync`.

## Behavior and Assumptions

- Prices come from `mock/market_data.py`, which publishes bid, ask, and visible
  depth per market.
- Each configured client periodically submits a market order. The execution
  layer walks the depth book, so one client order can produce one or more
  trades depending on how much liquidity it consumes.
- Sign convention is from the client's perspective: a client buy leaves Finalto
  short; a client sell leaves Finalto long.
- Positions are netted per market. "Open Positions" in the UI means markets
  where Finalto has non-zero net quantity — not open client orders.
- Market orders are immediate-or-cancel: anything not filled against current
  depth is cancelled rather than left working. The dashboard surfaces the
  resulting trades in `Latest Trades`; orders themselves are persisted as
  audit data only.

## Metrics

- PnL: `cash + quantity * current_mid` per market, summed across the book.
- Gross exposure: `sum(abs(quantity * current_mid))`.
- Monetization: spread capture at execution time, calculated from the difference
  between the fill price and the quote mid.
- Client yield: total monetization divided by total traded notional, expressed in
  basis points.
- PnL curve: the backend samples total PnL once per second from the live summary
  and persists up to ten minutes of points in SQLite. The frontend keeps the most
  recent minute at full resolution and down-samples older points into 10-second
  buckets, so the chart starts drawing immediately, stays detailed for the recent
  window, and bounds browser memory on long sessions. Refreshes and additional
  tabs replay the persisted curve through REST, so they all show the same history.

The scope is intentionally kept to a 3-4 hour MVP. A full margin engine,
deposits/withdrawals, realized PnL lots, hedging, and external liquidity routing
are outside that timebox, so the implementation focuses on the core book
management flow: prices, client trades, positions, PnL, monetization, and live
dashboard updates.

## Scaling Notes

- WebSocket live payloads use a short in-process TTL cache so many connected
  dashboards can reuse one DB-backed payload instead of each connection querying
  SQLite independently.
- The frontend keeps bounded recent rows and chart points to avoid unbounded memory
  growth during long-running sessions.
- SQLite is acceptable for this local MVP and supports the backend and mock feed as
  separate processes through WAL mode. For production scale, replace it with a
  server database and move live fan-out to a broker such as Redis pub/sub or
  RabbitMQ.
- The current single `/ws/live` channel is deliberately simple. If payload volume
  grows, split it into topics such as prices, trades, positions, and alerts so
  clients subscribe only to the data they render.

## Verification

```bash
uv run pytest
```

```bash
cd frontend
npm run build
```

The current tests validate the core order/trade lifecycle and Finalto book sign
conventions.

## Runtime Configuration

The main environment variables are:

- `DATABASE_PATH`: SQLite database file path. Defaults to `./risk_dashboard.db`
  locally and `/data/risk_dashboard.db` in Docker.
- `HOST`: backend bind host. Defaults to `127.0.0.1` locally and `0.0.0.0` in
  Docker.
- `PORT`: backend port. Defaults to `8000`.
- `MOCK_ORDER_SCALE`: multiplies generated client order attempts per interval.
  Defaults to `1`.
- `MOCK_ORDER_INTERVAL_SECONDS`: seconds between generated client-order batches.
  Defaults to `1.5`.
- `LIVE_PAYLOAD_CACHE_SECONDS`: in-process WebSocket payload cache TTL. Defaults
  to `0.5` in Docker Compose.
- `FRONTEND_PORT`: Docker host port for the nginx frontend. Defaults to `3000`.

Example Docker override:

```bash
FRONTEND_PORT=5173 MOCK_ORDER_SCALE=10 MOCK_ORDER_INTERVAL_SECONDS=3 docker compose up --build
```

PowerShell equivalent:

```powershell
$env:FRONTEND_PORT = "5173"
$env:MOCK_ORDER_SCALE = "10"
$env:MOCK_ORDER_INTERVAL_SECONDS = "3"
docker compose up --build
```
