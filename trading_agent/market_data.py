"""
market_data.py — fetches OHLCV data and computes technical indicators.

Uses yfinance as the primary data source so no API key is required for
historical data (Alpaca market-data endpoints need a paid subscription for
most real-time feeds).
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator

logger = logging.getLogger(__name__)


def fetch_ohlcv(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """Download OHLCV data for *symbol* from Yahoo Finance.

    Parameters
    ----------
    symbol:   Ticker symbol (e.g. "AAPL").
    period:   Lookback window accepted by yfinance (e.g. "1y", "6mo").
    interval: Bar interval accepted by yfinance (e.g. "1d", "1h").

    Returns
    -------
    DataFrame with columns: Open, High, Low, Close, Volume (index = Date).
    Returns an empty DataFrame on failure.
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            logger.warning("No data returned for %s", symbol)
            return pd.DataFrame()
        df.index = pd.to_datetime(df.index)
        return df[["Open", "High", "Low", "Close", "Volume"]]
    except Exception as exc:
        logger.error("Error fetching data for %s: %s", symbol, exc)
        return pd.DataFrame()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute RSI, MACD, 50-day MA and 200-day MA and append them as columns.

    Parameters
    ----------
    df: OHLCV DataFrame as returned by :func:`fetch_ohlcv`.

    Returns
    -------
    The same DataFrame with extra indicator columns added in-place.
    """
    if df.empty or len(df) < 26:
        return df

    close = df["Close"]

    # RSI (14-period)
    df["rsi"] = RSIIndicator(close=close, window=14).rsi()

    # MACD (12, 26, 9)
    macd_obj = MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
    df["macd"] = macd_obj.macd()
    df["macd_signal"] = macd_obj.macd_signal()
    df["macd_diff"] = macd_obj.macd_diff()

    # Moving averages
    if len(df) >= 50:
        df["sma_50"] = SMAIndicator(close=close, window=50).sma_indicator()
    if len(df) >= 200:
        df["sma_200"] = SMAIndicator(close=close, window=200).sma_indicator()

    return df


def get_latest_price(symbol: str) -> Optional[float]:
    """Return the most recent closing price for *symbol*, or None on failure."""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="2d", interval="1d")
        if data.empty:
            return None
        return float(data["Close"].iloc[-1])
    except Exception as exc:
        logger.error("Error fetching latest price for %s: %s", symbol, exc)
        return None


def get_market_data_with_indicators(
    symbol: str, period: str = "1y"
) -> pd.DataFrame:
    """Convenience wrapper: fetch OHLCV + add all indicators."""
    df = fetch_ohlcv(symbol, period=period)
    return add_indicators(df)
