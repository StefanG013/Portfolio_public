"""
strategy.py — rule-based trading strategy.

Default strategy: Moving Average Crossover (Golden/Death Cross).

  BUY  signal: 50-day SMA crosses *above* the 200-day SMA (golden cross).
  SELL signal: 50-day SMA crosses *below* the 200-day SMA (death cross).
  HOLD otherwise.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

import pandas as pd

logger = logging.getLogger(__name__)

Action = Literal["BUY", "SELL", "HOLD"]


@dataclass
class Signal:
    action: Action
    symbol: str
    reasoning: str
    confidence: float = 1.0  # 0–1 scale (reserved for future ML extension)


def moving_average_crossover(df: pd.DataFrame, symbol: str) -> Signal:
    """Evaluate the MA-crossover strategy on *df* for *symbol*.

    Requires columns ``sma_50`` and ``sma_200`` to be present (added by
    :func:`trading_agent.market_data.add_indicators`).

    The golden-cross / death-cross is detected by comparing today's relative
    position of the two MAs against yesterday's position.
    """
    required = {"sma_50", "sma_200"}
    if not required.issubset(df.columns):
        return Signal(
            action="HOLD",
            symbol=symbol,
            reasoning="Insufficient data: SMA columns missing",
        )

    valid = df.dropna(subset=["sma_50", "sma_200"])
    if len(valid) < 2:
        return Signal(
            action="HOLD",
            symbol=symbol,
            reasoning="Not enough rows after dropping NaN indicators",
        )

    prev = valid.iloc[-2]
    curr = valid.iloc[-1]

    prev_above = prev["sma_50"] > prev["sma_200"]
    curr_above = curr["sma_50"] > curr["sma_200"]

    curr_price = float(curr["Close"])
    curr_sma50 = float(curr["sma_50"])
    curr_sma200 = float(curr["sma_200"])

    if not prev_above and curr_above:
        reasoning = (
            f"Golden cross: SMA50 ({curr_sma50:.2f}) crossed above "
            f"SMA200 ({curr_sma200:.2f}). Current price: {curr_price:.2f}."
        )
        return Signal(action="BUY", symbol=symbol, reasoning=reasoning)

    if prev_above and not curr_above:
        reasoning = (
            f"Death cross: SMA50 ({curr_sma50:.2f}) crossed below "
            f"SMA200 ({curr_sma200:.2f}). Current price: {curr_price:.2f}."
        )
        return Signal(action="SELL", symbol=symbol, reasoning=reasoning)

    trend = "above" if curr_above else "below"
    reasoning = (
        f"No crossover. SMA50 ({curr_sma50:.2f}) is {trend} "
        f"SMA200 ({curr_sma200:.2f}). Current price: {curr_price:.2f}."
    )
    return Signal(action="HOLD", symbol=symbol, reasoning=reasoning)


def rsi_filter(df: pd.DataFrame, signal: Signal) -> Signal:
    """Optionally suppress a BUY/SELL signal when RSI is in extreme territory.

    * Suppresses BUY when RSI >= 70  (overbought).
    * Suppresses SELL when RSI <= 30 (oversold / potential reversal).
    """
    if "rsi" not in df.columns or signal.action == "HOLD":
        return signal

    latest_rsi = df["rsi"].dropna()
    if latest_rsi.empty:
        return signal

    rsi_val = float(latest_rsi.iloc[-1])

    if signal.action == "BUY" and rsi_val >= 70:
        return Signal(
            action="HOLD",
            symbol=signal.symbol,
            reasoning=(
                f"{signal.reasoning} — BUY suppressed by RSI filter "
                f"(RSI={rsi_val:.1f} >= 70, overbought)."
            ),
        )

    if signal.action == "SELL" and rsi_val <= 30:
        return Signal(
            action="HOLD",
            symbol=signal.symbol,
            reasoning=(
                f"{signal.reasoning} — SELL suppressed by RSI filter "
                f"(RSI={rsi_val:.1f} <= 30, oversold)."
            ),
        )

    return signal


def evaluate(df: pd.DataFrame, symbol: str) -> Signal:
    """Run the full strategy pipeline: MA crossover → RSI filter."""
    signal = moving_average_crossover(df, symbol)
    signal = rsi_filter(df, signal)
    logger.info("[%s] Strategy decision: %s — %s", symbol, signal.action, signal.reasoning)
    return signal
