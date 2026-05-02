"""
agent.py — orchestrates the trading agent loop.

For each watched symbol:
  1. Fetch market data + indicators.
  2. Run the strategy to get a BUY / SELL / HOLD signal.
  3. Apply guardrails (max daily trades, max position size).
  4. Execute via the broker.
  5. Log the result to SQLite.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from . import config
from .broker import AlpacaBroker, OrderResult
from .logger import count_today_trades, init_db, log_transaction
from .market_data import get_latest_price, get_market_data_with_indicators
from .strategy import Signal, evaluate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger(__name__)


class TradingAgent:
    """Stateful trading agent that manages its own broker and DB connection."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        symbols: Optional[list[str]] = None,
    ) -> None:
        self.db_path = db_path or config.DB_PATH
        self.symbols = symbols or config.WATCH_SYMBOLS
        self.broker = AlpacaBroker(
            api_key=config.ALPACA_API_KEY,
            secret_key=config.ALPACA_SECRET_KEY,
            base_url=config.ALPACA_BASE_URL,
        )
        self.last_run: Optional[str] = None
        init_db(self.db_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> list[dict]:
        """Analyse all watched symbols and execute trades where appropriate.

        Returns a list of result dicts — one per symbol.
        """
        self.last_run = datetime.now(timezone.utc).isoformat()
        log.info("Agent run started at %s for symbols: %s", self.last_run, self.symbols)

        daily_trades = count_today_trades(self.db_path)
        results = []

        for symbol in self.symbols:
            result = self._process_symbol(symbol, daily_trades)
            results.append(result)
            if result.get("action") in ("BUY", "SELL") and result.get("status") in (
                "EXECUTED",
                "DRY_RUN",
            ):
                daily_trades += 1

        log.info("Agent run complete. %d symbols processed.", len(results))
        return results

    def get_status(self) -> dict:
        """Return a summary of the agent's current state."""
        account = self.broker.get_account()
        return {
            "last_run": self.last_run,
            "symbols_watched": self.symbols,
            "portfolio_value": account.get("portfolio_value"),
            "cash": account.get("cash"),
            "dry_run": self.broker._dry_run,
        }

    def get_portfolio(self) -> list[dict]:
        """Return current open positions."""
        return self.broker.get_positions()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process_symbol(self, symbol: str, daily_trades: int) -> dict:
        log.info("Processing %s (daily trades so far: %d)", symbol, daily_trades)

        # 1. Fetch market data
        df = get_market_data_with_indicators(symbol)
        if df.empty:
            self._log_skipped(symbol, "No market data available")
            return {
                "symbol": symbol,
                "action": "HOLD",
                "status": "SKIPPED",
                "reasoning": "No market data available",
            }

        # 2. Strategy signal
        signal: Signal = evaluate(df, symbol)

        if signal.action == "HOLD":
            self._log_skipped(symbol, signal.reasoning)
            return {
                "symbol": symbol,
                "action": "HOLD",
                "status": "SKIPPED",
                "reasoning": signal.reasoning,
            }

        # 3. Guardrails
        if daily_trades >= config.MAX_DAILY_TRADES:
            reason = (
                f"{signal.reasoning} — trade skipped: daily limit "
                f"({config.MAX_DAILY_TRADES}) reached."
            )
            self._log_skipped(symbol, reason)
            return {
                "symbol": symbol,
                "action": signal.action,
                "status": "SKIPPED",
                "reasoning": reason,
            }

        # 4. Get current price
        price = get_latest_price(symbol)
        if price is None:
            self._log_skipped(symbol, "Could not fetch current price")
            return {
                "symbol": symbol,
                "action": signal.action,
                "status": "SKIPPED",
                "reasoning": "Could not fetch current price",
            }

        # 5. Execute via broker
        if signal.action == "BUY":
            order: OrderResult = self.broker.place_buy_order(
                symbol, price, config.MAX_POSITION_PCT
            )
        else:
            order = self.broker.place_sell_order(
                symbol, price, config.MAX_POSITION_PCT
            )

        # 6. Log
        log_transaction(
            db_path=self.db_path,
            symbol=symbol,
            action=signal.action,
            quantity=order.quantity,
            price=order.price,
            reasoning=signal.reasoning,
            status=order.status,
        )

        return {
            "symbol": symbol,
            "action": signal.action,
            "status": order.status,
            "quantity": order.quantity,
            "price": order.price,
            "reasoning": signal.reasoning,
            "order_id": order.order_id,
        }

    def _log_skipped(self, symbol: str, reasoning: str) -> None:
        log_transaction(
            db_path=self.db_path,
            symbol=symbol,
            action="HOLD",
            quantity=None,
            price=None,
            reasoning=reasoning,
            status="SKIPPED",
        )


# Allow running the agent directly: `python -m trading_agent.agent`
if __name__ == "__main__":
    agent = TradingAgent()
    results = agent.run()
    for r in results:
        print(r)
