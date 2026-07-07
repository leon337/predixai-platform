# PTP113C75_SQLITE_SHARED_RESILIENCE_START
"""
Camada compartilhada de resiliência SQLite para PredixAI Trader.

Objetivo:
- Aplicar timeout maior em todos os processos Python relevantes.
- Ativar WAL quando possível.
- Reduzir falhas "database is locked" entre mobile server e reader.
- Ser idempotente e segura em modo simulado.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

_MARKER = "_predixai_ptp113c75_sqlite_resilience_installed"
_ORIGINAL = "_predixai_ptp113c75_original_connect"


def _is_file_database(database: Any) -> bool:
    if database is None:
        return False
    value = str(database)
    if not value or value == ":memory:":
        return False
    if value.startswith("file::memory:"):
        return False
    return True


def _configure_connection(conn: sqlite3.Connection, database: Any) -> sqlite3.Connection:
    try:
        conn.execute("PRAGMA busy_timeout=30000")
    except Exception:
        pass

    if _is_file_database(database):
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except Exception:
            pass

        try:
            conn.execute("PRAGMA synchronous=NORMAL")
        except Exception:
            pass

        try:
            conn.execute("PRAGMA temp_store=MEMORY")
        except Exception:
            pass

    return conn


def install_sqlite_resilience() -> bool:
    if getattr(sqlite3, _MARKER, False):
        return True

    original_connect = getattr(sqlite3, _ORIGINAL, sqlite3.connect)
    setattr(sqlite3, _ORIGINAL, original_connect)

    def resilient_connect(database: Any, *args: Any, **kwargs: Any) -> sqlite3.Connection:
        current_timeout = kwargs.get("timeout")
        if current_timeout is None or float(current_timeout) < 30:
            kwargs["timeout"] = 30

        attempts = 6
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                conn = original_connect(database, *args, **kwargs)
                return _configure_connection(conn, database)
            except sqlite3.OperationalError as exc:
                last_error = exc
                if "locked" not in str(exc).lower():
                    raise
                time.sleep(min(0.25 * attempt, 2.0))

        if last_error:
            raise last_error

        conn = original_connect(database, *args, **kwargs)
        return _configure_connection(conn, database)

    sqlite3.connect = resilient_connect  # type: ignore[assignment]
    setattr(sqlite3, _MARKER, True)
    return True
# PTP113C75_SQLITE_SHARED_RESILIENCE_END
