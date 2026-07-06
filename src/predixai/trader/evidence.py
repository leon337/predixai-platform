import os
import sqlite3
from typing import Optional


class EvidenceDB:
    def __init__(self, db_path: Optional[str] = None):
        base = db_path or os.path.join("data", "predixai_trader_evidence.db")
        os.makedirs(os.path.dirname(base), exist_ok=True)
        self.conn = sqlite3.connect(base)
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()
        cur.executescript(
            """
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT,
            config TEXT
        );
        CREATE TABLE IF NOT EXISTS session_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS strategy_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            profile_json TEXT
        );
        CREATE TABLE IF NOT EXISTS raw_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            payload TEXT
        );
        CREATE TABLE IF NOT EXISTS market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            asset TEXT,
            price REAL
        );
        CREATE TABLE IF NOT EXISTS signal_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            candidate_json TEXT
        );
        CREATE TABLE IF NOT EXISTS risk_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            decision_json TEXT
        );
        CREATE TABLE IF NOT EXISTS recovery_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            plan_json TEXT
        );
        CREATE TABLE IF NOT EXISTS paper_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            trade_json TEXT
        );
        CREATE TABLE IF NOT EXISTS trade_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            note TEXT
        );
        CREATE TABLE IF NOT EXISTS broker_access_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            event TEXT
        );
        CREATE TABLE IF NOT EXISTS system_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            event TEXT
        );
        """
        )
        self.conn.commit()

    def insert(self, table: str, payload: dict):
        cur = self.conn.cursor()
        cur.execute(f"INSERT INTO {table} (ts, {self._payload_column(table)}) VALUES (datetime('now'), ?)", (str(payload),))
        self.conn.commit()
        return cur.lastrowid

    def _payload_column(self, table: str) -> str:
        mapping = {
            "sessions": "config",
            "session_configs": "value",
            "strategy_profiles": "profile_json",
            "raw_observations": "payload",
            "market_data": "price",
            "signal_candidates": "candidate_json",
            "risk_decisions": "decision_json",
            "recovery_plans": "plan_json",
            "paper_trades": "trade_json",
            "trade_journal": "note",
            "broker_access_events": "event",
            "system_events": "event",
        }
        return mapping.get(table, "payload")

    def close(self):
        self.conn.close()
