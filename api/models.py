"""
models.py — Pydantic response models for the FastAPI layer.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel


class Transaction(BaseModel):
    id: int
    timestamp: str
    symbol: str
    action: str
    quantity: Optional[float] = None
    price: Optional[float] = None
    reasoning: Optional[str] = None
    status: Optional[str] = None
    pnl: Optional[float] = None


class AgentRunResult(BaseModel):
    symbol: str
    action: str
    status: str
    reasoning: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    order_id: Optional[str] = None


class AgentStatus(BaseModel):
    last_run: Optional[str]
    symbols_watched: list[str]
    portfolio_value: Optional[float]
    cash: Optional[float]
    dry_run: bool


class Position(BaseModel):
    symbol: str
    qty: float
    avg_entry_price: float
    current_price: float
    market_value: float
    unrealized_pl: float
    unrealized_plpc: float
