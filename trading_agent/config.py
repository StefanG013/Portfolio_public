"""
config.py — loads environment variables and central configuration for the trading agent.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Alpaca paper trading credentials
# ---------------------------------------------------------------------------
ALPACA_API_KEY: str = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY: str = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL: str = os.getenv(
    "ALPACA_BASE_URL", "https://paper-api.alpaca.markets"
)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DB_PATH: str = os.getenv("DB_PATH", "trading_agent.db")

# ---------------------------------------------------------------------------
# Symbols the agent watches
# ---------------------------------------------------------------------------
_raw_symbols = os.getenv("WATCH_SYMBOLS", "AAPL,MSFT,GOOGL,AMZN,NVDA")
WATCH_SYMBOLS: list[str] = [s.strip() for s in _raw_symbols.split(",") if s.strip()]

# ---------------------------------------------------------------------------
# FastAPI server
# ---------------------------------------------------------------------------
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))

# ---------------------------------------------------------------------------
# Agent guardrails
# ---------------------------------------------------------------------------
MAX_POSITION_PCT: float = float(os.getenv("MAX_POSITION_PCT", "0.10"))
MAX_DAILY_TRADES: int = int(os.getenv("MAX_DAILY_TRADES", "3"))
