"""
main.py — FastAPI application exposing the trading agent over HTTP.

Endpoints
---------
GET  /transactions            — all trade history (newest first)
GET  /transactions/{symbol}   — trade history filtered by symbol
POST /agent/run               — trigger the agent analysis loop
GET  /agent/status            — agent last-run time + portfolio summary
GET  /portfolio               — current Alpaca paper positions
"""

from __future__ import annotations

import sys
import os

# Allow running directly from the project root:  python -m api.main
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.models import AgentRunResult, AgentStatus, Position, Transaction
from trading_agent.agent import TradingAgent
from trading_agent import config
from trading_agent.logger import get_transactions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger(__name__)

app = FastAPI(
    title="AI Trading Agent API",
    description="REST interface for the AI trading agent that powers the Portfolio dashboard.",
    version="1.0.0",
)

# Allow the R Shiny app (running on any localhost port) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Single shared agent instance (lazy-initialised on first request).
_agent: TradingAgent | None = None


def _get_agent() -> TradingAgent:
    global _agent
    if _agent is None:
        _agent = TradingAgent()
    return _agent


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


@app.get("/transactions", response_model=list[Transaction], tags=["transactions"])
def list_transactions(limit: int = 200):
    """Return all trade history from SQLite, newest first."""
    rows = get_transactions(config.DB_PATH, limit=limit)
    return rows


@app.get(
    "/transactions/{symbol}", response_model=list[Transaction], tags=["transactions"]
)
def list_transactions_by_symbol(symbol: str, limit: int = 200):
    """Return trade history filtered by ticker symbol."""
    rows = get_transactions(config.DB_PATH, symbol=symbol.upper(), limit=limit)
    if not rows:
        raise HTTPException(status_code=404, detail=f"No transactions found for {symbol}")
    return rows


# ---------------------------------------------------------------------------
# Agent control
# ---------------------------------------------------------------------------


@app.post("/agent/run", response_model=list[AgentRunResult], tags=["agent"])
def run_agent():
    """Trigger the agent to analyse all watched symbols and execute trades."""
    agent = _get_agent()
    results = agent.run()
    return results


@app.get("/agent/status", response_model=AgentStatus, tags=["agent"])
def agent_status():
    """Return the agent's last run time, watched symbols, and portfolio summary."""
    agent = _get_agent()
    return agent.get_status()


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------


@app.get("/portfolio", response_model=list[Position], tags=["portfolio"])
def get_portfolio():
    """Return current open positions from the Alpaca paper account."""
    agent = _get_agent()
    positions = agent.get_portfolio()
    return positions


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=False,
    )
