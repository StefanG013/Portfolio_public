"""
broker.py — thin wrapper around the Alpaca paper trading REST API.

Uses alpaca-trade-api when credentials are available; otherwise operates in
*dry-run* mode so that the rest of the agent can be exercised without real
(or paper) credentials.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class OrderResult:
    order_id: str
    symbol: str
    action: str          # "BUY" | "SELL"
    quantity: float
    price: float
    status: str          # "EXECUTED" | "FAILED" | "DRY_RUN"
    error: Optional[str] = None


class AlpacaBroker:
    """Wrapper for Alpaca paper trading.

    If *api_key* / *secret_key* are empty strings the broker runs in dry-run
    mode — all orders are simulated and logged but never sent to Alpaca.
    """

    def __init__(self, api_key: str, secret_key: str, base_url: str) -> None:
        self._dry_run = not (api_key and secret_key)
        self._api = None

        if not self._dry_run:
            try:
                import alpaca_trade_api as tradeapi  # type: ignore

                self._api = tradeapi.REST(
                    key_id=api_key,
                    secret_key=secret_key,
                    base_url=base_url,
                    api_version="v2",
                )
                logger.info("Alpaca broker initialised (paper trading: %s)", base_url)
            except Exception as exc:
                logger.warning("Failed to initialise Alpaca client: %s. Using dry-run mode.", exc)
                self._dry_run = True
        else:
            logger.info("Alpaca credentials not set — broker running in dry-run mode.")

    # ------------------------------------------------------------------
    # Portfolio queries
    # ------------------------------------------------------------------

    def get_account(self) -> dict:
        """Return account info dict (equity, cash, buying_power, …)."""
        if self._dry_run or self._api is None:
            return {
                "equity": 100_000.0,
                "cash": 100_000.0,
                "buying_power": 100_000.0,
                "portfolio_value": 100_000.0,
                "status": "DRY_RUN",
            }
        try:
            acct = self._api.get_account()
            return {
                "equity": float(acct.equity),
                "cash": float(acct.cash),
                "buying_power": float(acct.buying_power),
                "portfolio_value": float(acct.portfolio_value),
                "status": acct.status,
            }
        except Exception as exc:
            logger.error("get_account error: %s", exc)
            return {}

    def get_positions(self) -> list[dict]:
        """Return list of current open positions."""
        if self._dry_run or self._api is None:
            return []
        try:
            positions = self._api.list_positions()
            return [
                {
                    "symbol": p.symbol,
                    "qty": float(p.qty),
                    "avg_entry_price": float(p.avg_entry_price),
                    "current_price": float(p.current_price),
                    "market_value": float(p.market_value),
                    "unrealized_pl": float(p.unrealized_pl),
                    "unrealized_plpc": float(p.unrealized_plpc),
                }
                for p in positions
            ]
        except Exception as exc:
            logger.error("get_positions error: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Order execution
    # ------------------------------------------------------------------

    def _calc_quantity(
        self, symbol: str, price: float, max_position_pct: float
    ) -> float:
        """Calculate safe order quantity based on portfolio guardrail."""
        acct = self.get_account()
        portfolio_value = acct.get("portfolio_value", 0.0)
        if portfolio_value <= 0 or price <= 0:
            return 0.0
        max_dollars = portfolio_value * max_position_pct
        return max(1.0, round(max_dollars / price, 4))

    def place_buy_order(
        self,
        symbol: str,
        price: float,
        max_position_pct: float = 0.10,
    ) -> OrderResult:
        """Place a market buy order for *symbol*."""
        qty = self._calc_quantity(symbol, price, max_position_pct)
        if qty <= 0:
            return OrderResult(
                order_id="",
                symbol=symbol,
                action="BUY",
                quantity=0,
                price=price,
                status="FAILED",
                error="Could not determine quantity",
            )

        if self._dry_run or self._api is None:
            logger.info("[DRY-RUN] BUY %s x %s @ ~%.2f", qty, symbol, price)
            return OrderResult(
                order_id=f"dry-run-buy-{symbol}",
                symbol=symbol,
                action="BUY",
                quantity=qty,
                price=price,
                status="DRY_RUN",
            )

        try:
            order = self._api.submit_order(
                symbol=symbol,
                qty=qty,
                side="buy",
                type="market",
                time_in_force="day",
            )
            return OrderResult(
                order_id=str(order.id),
                symbol=symbol,
                action="BUY",
                quantity=qty,
                price=price,
                status="EXECUTED",
            )
        except Exception as exc:
            logger.error("BUY order failed for %s: %s", symbol, exc)
            return OrderResult(
                order_id="",
                symbol=symbol,
                action="BUY",
                quantity=qty,
                price=price,
                status="FAILED",
                error=str(exc),
            )

    def place_sell_order(
        self,
        symbol: str,
        price: float,
        max_position_pct: float = 0.10,
    ) -> OrderResult:
        """Place a market sell order for *symbol* (closes existing position)."""
        if self._dry_run or self._api is None:
            logger.info("[DRY-RUN] SELL %s @ ~%.2f", symbol, price)
            return OrderResult(
                order_id=f"dry-run-sell-{symbol}",
                symbol=symbol,
                action="SELL",
                quantity=1.0,
                price=price,
                status="DRY_RUN",
            )

        try:
            # Sell entire existing position
            position = None
            try:
                position = self._api.get_position(symbol)
            except Exception:
                pass

            qty = float(position.qty) if position else self._calc_quantity(
                symbol, price, max_position_pct
            )

            order = self._api.submit_order(
                symbol=symbol,
                qty=qty,
                side="sell",
                type="market",
                time_in_force="day",
            )
            return OrderResult(
                order_id=str(order.id),
                symbol=symbol,
                action="SELL",
                quantity=qty,
                price=price,
                status="EXECUTED",
            )
        except Exception as exc:
            logger.error("SELL order failed for %s: %s", symbol, exc)
            return OrderResult(
                order_id="",
                symbol=symbol,
                action="SELL",
                quantity=0,
                price=price,
                status="FAILED",
                error=str(exc),
            )
