"""Market session recorder for PredixAI Trader V1.

Observer-only session control.
No broker clicks, no orders, no real-account execution.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from predixai.trader.data_store import TraderDataStore


@dataclass(frozen=True)
class MarketSessionSummary:
    id: int
    asset: str
    timeframe: str
    mode: str
    status: str
    started_at: str
    ended_at: str | None
    notes: str
    tick_count: int
    candle_count: int
    evidence_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "asset": self.asset,
            "timeframe": self.timeframe,
            "mode": self.mode,
            "status": self.status,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "notes": self.notes,
            "tick_count": self.tick_count,
            "candle_count": self.candle_count,
            "evidence_count": self.evidence_count,
        }


class MarketSessionRecorder:
    """Create, list, inspect and close observer market sessions."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.store = TraderDataStore() if db_path is None else TraderDataStore(db_path)

    def start_session(
        self,
        *,
        asset: str,
        timeframe: str,
        mode: str = "observer",
        notes: str = "",
    ) -> MarketSessionSummary:
        self.store.initialize()
        session_id = self.store.create_market_session(
            asset=asset.strip(),
            timeframe=timeframe.strip(),
            mode=mode.strip() or "observer",
            notes=notes.strip(),
        )
        session = self.get_session(session_id)
        if session is None:
            raise RuntimeError(f"Unable to load created session: {session_id}")
        return session

    def get_session(self, session_id: int) -> MarketSessionSummary | None:
        self.store.initialize()
        with self.store._connect() as connection:
            row = connection.execute(
                """
                SELECT id, asset, timeframe, mode, status, started_at, ended_at, notes
                FROM market_sessions
                WHERE id = ?
                """,
                (session_id,),
            ).fetchone()
            if row is None:
                return None
            return self._build_summary(connection, row)

    def list_sessions(self, *, limit: int = 10) -> tuple[MarketSessionSummary, ...]:
        self.store.initialize()
        with self.store._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, asset, timeframe, mode, status, started_at, ended_at, notes
                FROM market_sessions
                ORDER BY id DESC
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()
            return tuple(self._build_summary(connection, row) for row in rows)

    def close_session(
        self,
        *,
        session_id: int,
        status: str = "completed",
    ) -> MarketSessionSummary:
        self.store.initialize()
        clean_status = status.strip() or "completed"
        with self.store._connect() as connection:
            existing = connection.execute(
                "SELECT id FROM market_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if existing is None:
                raise ValueError(f"Session not found: {session_id}")

            connection.execute(
                """
                UPDATE market_sessions
                SET status = ?, ended_at = ?
                WHERE id = ?
                """,
                (clean_status, _utc_now(), session_id),
            )
            connection.commit()

        session = self.get_session(session_id)
        if session is None:
            raise RuntimeError(f"Unable to load closed session: {session_id}")
        return session

    def _build_summary(
        self,
        connection: sqlite3.Connection,
        row: sqlite3.Row | tuple[Any, ...],
    ) -> MarketSessionSummary:
        session_id = int(row[0])
        tick_count = _count(connection, "market_ticks", session_id)
        candle_count = _count(connection, "market_candles", session_id)
        evidence_count = _count(connection, "evidence_records", session_id)

        return MarketSessionSummary(
            id=session_id,
            asset=str(row[1]),
            timeframe=str(row[2]),
            mode=str(row[3]),
            status=str(row[4]),
            started_at=str(row[5]),
            ended_at=row[6],
            notes=str(row[7] or ""),
            tick_count=tick_count,
            candle_count=candle_count,
            evidence_count=evidence_count,
        )


def _count(connection: sqlite3.Connection, table: str, session_id: int) -> int:
    row = connection.execute(
        f"SELECT COUNT(*) FROM {table} WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return int(row[0]) if row else 0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
