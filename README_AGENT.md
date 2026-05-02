# AI Trading Agent — Setup & Usage Guide

This document explains how to set up and run the AI trading agent that extends
the Portfolio R Shiny Dashboard.

---

## Architecture

```
R Shiny Dashboard (app.R)
       │
       └── httr2 HTTP calls
             │
             ▼
       FastAPI Server (api/main.py)  :8000
             │
             ├── GET /transactions
             ├── GET /transactions/{symbol}
             ├── POST /agent/run
             ├── GET /agent/status
             └── GET /portfolio
                   │
                   ▼
         TradingAgent (trading_agent/)
               ├── market_data.py  ← yfinance (OHLCV + RSI/MACD/MA)
               ├── strategy.py     ← MA crossover + RSI filter
               ├── broker.py       ← Alpaca paper trading
               └── logger.py       ← SQLite (trading_agent.db)
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| R      | 4.3+   |

---

## Step 1 — Alpaca Paper Trading Account

1. Create a free account at <https://alpaca.markets/>.
2. Navigate to **Paper Trading** → **API Keys** and generate a key pair.
3. Keys look like: `PK...` (key) and a longer secret string.

> ⚠️ **Never use Live Trading keys here.** The agent is configured for paper
> trading only (`https://paper-api.alpaca.markets`).

---

## Step 2 — Environment Variables

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
ALPACA_API_KEY=PKxxxxxxxxxxxxxxxx
ALPACA_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ALPACA_BASE_URL=https://paper-api.alpaca.markets

DB_PATH=trading_agent.db
WATCH_SYMBOLS=AAPL,MSFT,GOOGL,AMZN,NVDA

API_HOST=0.0.0.0
API_PORT=8000

MAX_POSITION_PCT=0.10   # max 10 % of portfolio per position
MAX_DAILY_TRADES=3      # max trades per day
```

> If you don't have Alpaca keys yet, leave them blank — the agent will run in
> **dry-run mode** (simulated orders, no real/paper money used).

---

## Step 3 — Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 4 — Start the FastAPI Server

```bash
python -m api.main
```

The API will be available at <http://localhost:8000>.
Interactive docs (Swagger UI) at <http://localhost:8000/docs>.

---

## Step 5 — Install R Dependencies

```r
install.packages(c("shiny", "DT", "ggplot2", "plotly", "httr2", "scales"))
```

---

## Step 6 — Launch the Shiny Dashboard

```r
shiny::runApp("app.R", port = 3838)
```

Open <http://localhost:3838> in your browser.

---

## Step 7 (Optional) — Run the Scheduler

The scheduler triggers the agent automatically every 30 minutes during US
market hours (9:30 AM – 4:00 PM ET, weekdays).

```bash
python scheduler.py
```

Run this in a separate terminal (or as a background process/service).

---

## Trading Strategy

The default strategy is a **Moving Average Crossover** with an RSI filter:

| Signal | Condition |
|--------|-----------|
| **BUY** | 50-day SMA crosses *above* 200-day SMA (golden cross) AND RSI < 70 |
| **SELL** | 50-day SMA crosses *below* 200-day SMA (death cross) AND RSI > 30 |
| **HOLD** | No crossover, or filtered by RSI |

---

## Agent Guardrails

- **Max 10 % of portfolio per position** — prevents concentration risk.
- **Max 3 trades per day** — limits over-trading.
- **Paper trading only** — Alpaca paper endpoint is hard-coded as the default.
- **Dry-run mode** — if no Alpaca credentials are configured, all orders are
  simulated locally and logged to SQLite with status `DRY_RUN`.

---

## File Structure

```
trading_agent/
  __init__.py     — package init
  config.py       — env var loading
  market_data.py  — yfinance OHLCV + indicators
  strategy.py     — MA crossover + RSI filter
  broker.py       — Alpaca paper trading wrapper
  logger.py       — SQLite transaction logging
  agent.py        — orchestrator

api/
  __init__.py
  main.py         — FastAPI app
  models.py       — Pydantic models

R/
  agent_api.R     — httr2 helpers for R Shiny ↔ FastAPI

app.R             — R Shiny dashboard (Portfolio + AI Agent tabs)
scheduler.py      — APScheduler for automatic market-hours runs
requirements.txt  — Python dependencies
.env.example      — environment variable template
README_AGENT.md   — this file
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/transactions` | All trade history (newest first) |
| GET | `/transactions/{symbol}` | Trades for a specific symbol |
| POST | `/agent/run` | Trigger the agent now |
| GET | `/agent/status` | Last run time + portfolio summary |
| GET | `/portfolio` | Current open positions |

Full interactive docs: <http://localhost:8000/docs>

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "API Offline" badge in dashboard | Start the FastAPI server (`python -m api.main`) |
| No transactions appearing | Click "Run Agent Now" — first run needs ≥200 days of data |
| `alpaca_trade_api` import error | Run `pip install alpaca-trade-api` |
| Alpaca 403 errors | Check your API key/secret in `.env` and verify paper-trading is selected |
| yfinance rate limit | Add a short sleep between symbols or reduce `WATCH_SYMBOLS` |
