"""PredixAI Trader SQLite data store foundation.

V1 scope: observer only.
No broker clicks, no orders, no real-account execution.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
DEFAULT_DB_PATH = Path("data") / "predixai_trader.sqlite3"


@dataclass(frozen=True)
class TraderDataStoreStatus:
    db_path: str
    exists: bool
    schema_version: int | None
    tables: tuple[str, ...]
    ok: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "db_path": self.db_path,
            "exists": self.exists,
            "schema_version": self.schema_version,
            "tables": list(self.tables),
            "ok": self.ok,
        }


class TraderDataStore:
    """SQLite foundation for PredixAI Trader observer memory."""

    REQUIRED_TABLES = (
        "schema_metadata",
        "market_sessions",
        "market_ticks",
        "market_candles",
        "evidence_records",
        "indicator_snapshots",
        "support_resistance_zones",
        "triple_rebound_observations",
    )

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def initialize(self) -> TraderDataStoreStatus:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            self._create_schema(connection)
            self._set_schema_version(connection)
            connection.commit()
        return self.status()

    def status(self) -> TraderDataStoreStatus:
        exists = self.db_path.exists()
        if not exists:
            return TraderDataStoreStatus(
                db_path=str(self.db_path),
                exists=False,
                schema_version=None,
                tables=(),
                ok=False,
            )

        with self._connect() as connection:
            tables = self._list_tables(connection)
            schema_version = self._get_schema_version(connection)

        ok = (
            schema_version == SCHEMA_VERSION
            and all(table in tables for table in self.REQUIRED_TABLES)
        )

        return TraderDataStoreStatus(
            db_path=str(self.db_path),
            exists=True,
            schema_version=schema_version,
            tables=tables,
            ok=ok,
        )

    def create_market_session(
        self,
        *,
        asset: str,
        timeframe: str,
        mode: str = "observer",
        notes: str = "",
    ) -> int:
        now = _utc_now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO market_sessions (
                    asset, timeframe, mode, status, started_at, notes
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (asset, timeframe, mode, "running", now, notes),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def record_tick(
        self,
        *,
        session_id: int,
        asset: str,
        timeframe: str,
        captured_at: str | None = None,
        price: float | None = None,
        direction: str | None = None,
        raw_fields: dict[str, Any] | None = None,
        evidence_path: str | None = None,
        quality_score: float | None = None,
    ) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO market_ticks (
                    session_id, captured_at, asset, timeframe, price, direction,
                    raw_fields_json, evidence_path, quality_score
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    captured_at or _utc_now(),
                    asset,
                    timeframe,
                    price,
                    direction,
                    json.dumps(raw_fields or {}, ensure_ascii=False),
                    evidence_path,
                    quality_score,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _create_schema(self, connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS market_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                mode TEXT NOT NULL DEFAULT 'observer',
                status TEXT NOT NULL DEFAULT 'running',
                started_at TEXT NOT NULL,
                ended_at TEXT,
                notes TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS market_ticks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                captured_at TEXT NOT NULL,
                asset TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                price REAL,
                direction TEXT,
                raw_fields_json TEXT NOT NULL DEFAULT '{}',
                evidence_path TEXT,
                quality_score REAL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES market_sessions(id)
            );

            CREATE TABLE IF NOT EXISTS market_candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                candle_time TEXT NOT NULL,
                asset TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                sample_count INTEGER NOT NULL DEFAULT 0,
                volatility REAL,
                direction TEXT,
                source_snapshot_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES market_sessions(id)
            );

            CREATE TABLE IF NOT EXISTS evidence_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                tick_id INTEGER,
                evidence_path TEXT NOT NULL,
                evidence_type TEXT NOT NULL DEFAULT 'live_evidence',
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES market_sessions(id),
                FOREIGN KEY(tick_id) REFERENCES market_ticks(id)
            );

            CREATE TABLE IF NOT EXISTS indicator_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                tick_id INTEGER,
                asset TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                rsi_short REAL,
                rsi_medium REAL,
                rsi_long REAL,
                config_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES market_sessions(id),
                FOREIGN KEY(tick_id) REFERENCES market_ticks(id)
            );

            CREATE TABLE IF NOT EXISTS support_resistance_zones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                asset TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                zone_type TEXT NOT NULL,
                lower_price REAL NOT NULL,
                upper_price REAL NOT NULL,
                mid_price REAL,
                touch_count INTEGER NOT NULL DEFAULT 0,
                strength_score REAL,
                last_touch_at TEXT,
                source_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES market_sessions(id)
            );

            CREATE TABLE IF NOT EXISTS triple_rebound_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                zone_id INTEGER,
                candle_id INTEGER,
                asset TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                touch_index INTEGER NOT NULL,
                observation_status TEXT NOT NULL DEFAULT 'observed',
                confidence REAL,
                rsi_context_json TEXT NOT NULL DEFAULT '{}',
                context_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES market_sessions(id),
                FOREIGN KEY(zone_id) REFERENCES support_resistance_zones(id),
                FOREIGN KEY(candle_id) REFERENCES market_candles(id)
            );

            CREATE INDEX IF NOT EXISTS idx_market_sessions_asset_timeframe
                ON market_sessions(asset, timeframe);

            CREATE INDEX IF NOT EXISTS idx_market_ticks_session_time
                ON market_ticks(session_id, captured_at);

            CREATE INDEX IF NOT EXISTS idx_market_candles_session_time
                ON market_candles(session_id, candle_time);

            CREATE INDEX IF NOT EXISTS idx_indicator_snapshots_session_tick
                ON indicator_snapshots(session_id, tick_id);

            CREATE INDEX IF NOT EXISTS idx_zones_session_type
                ON support_resistance_zones(session_id, zone_type);

            CREATE INDEX IF NOT EXISTS idx_triple_rebound_session
                ON triple_rebound_observations(session_id, touch_index);
            """
        )

    def _set_schema_version(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            INSERT INTO schema_metadata(key, value, updated_at)
            VALUES('schema_version', ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value=excluded.value,
                updated_at=excluded.updated_at
            """,
            (str(SCHEMA_VERSION), _utc_now()),
        )

    def _get_schema_version(self, connection: sqlite3.Connection) -> int | None:
        row = connection.execute(
            "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
        ).fetchone()
        if row is None:
            return None
        try:
            return int(row[0])
        except (TypeError, ValueError):
            return None

    def _list_tables(self, connection: sqlite3.Connection) -> tuple[str, ...]:
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()
        return tuple(str(row[0]) for row in rows)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def initialize_default_store() -> TraderDataStoreStatus:
    return TraderDataStore().initialize()


def default_store_status() -> TraderDataStoreStatus:
    return TraderDataStore().status()
