"""
logger.py — logs every trade decision and execution to SQLite.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger(__name__)


def _get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    """Create the transactions table if it does not exist."""
    with _get_conn(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT    NOT NULL,
                symbol    TEXT    NOT NULL,
                action    TEXT    NOT NULL,
                quantity  REAL,
                price     REAL,
                reasoning TEXT,
                status    TEXT,
                pnl       REAL
            )
            """
        )
        conn.commit()
    log.info("Database initialised at %s", db_path)


def log_transaction(
    db_path: str,
    symbol: str,
    action: str,
    quantity: Optional[float],
    price: Optional[float],
    reasoning: str,
    status: str,
    pnl: Optional[float] = None,
    timestamp: Optional[str] = None,
) -> int:
    """Insert a transaction row and return its row id."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()

    with _get_conn(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO transactions
                (timestamp, symbol, action, quantity, price, reasoning, status, pnl)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (timestamp, symbol, action, quantity, price, reasoning, status, pnl),
        )
        conn.commit()
        row_id = cursor.lastrowid

    log.info(
        "Logged transaction id=%s: %s %s qty=%.4f price=%.2f status=%s",
        row_id, action, symbol, quantity or 0, price or 0, status,
    )
    return row_id  # type: ignore[return-value]


def get_transactions(
    db_path: str,
    symbol: Optional[str] = None,
    limit: int = 500,
) -> list[dict]:
    """Return transactions as a list of dicts (newest first)."""
    with _get_conn(db_path) as conn:
        if symbol:
            rows = conn.execute(
                "SELECT * FROM transactions WHERE symbol = ? ORDER BY id DESC LIMIT ?",
                (symbol, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM transactions ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


def count_today_trades(db_path: str) -> int:
    """Count trades executed today (UTC) with status EXECUTED or DRY_RUN."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with _get_conn(db_path) as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS n FROM transactions
            WHERE timestamp LIKE ?
              AND action IN ('BUY', 'SELL')
              AND status IN ('EXECUTED', 'DRY_RUN')
            """,
            (f"{today}%",),
        ).fetchone()
    return int(row["n"]) if row else 0
