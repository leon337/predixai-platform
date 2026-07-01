"""Triple Rebound observer for PredixAI Trader V1.

Observer-only layer that combines:
- latest market price
- support/resistance zone context
- Triple RSI snapshot

No broker clicks, no orders, no real-account execution.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from predixai.trader.data_store import TraderDataStore


@dataclass(frozen=True)
class TripleReboundObservationResult:
    observation_id: int | None
    session_id: int
    tick_id: int | None
    asset: str
    timeframe: str
    latest_price: float | None
    zone_id: int | None
    zone_type: str | None
    zone_mid_price: float | None
    distance_to_zone_percent: float | None
    rsi_snapshot_id: int | None
    rsi_short: float | None
    rsi_medium: float | None
    rsi_long: float | None
    confidence_score: float
    observation_label: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "session_id": self.session_id,
            "tick_id": self.tick_id,
            "asset": self.asset,
            "timeframe": self.timeframe,
            "latest_price": self.latest_price,
            "zone_id": self.zone_id,
            "zone_type": self.zone_type,
            "zone_mid_price": self.zone_mid_price,
            "distance_to_zone_percent": self.distance_to_zone_percent,
            "rsi_snapshot_id": self.rsi_snapshot_id,
            "rsi_short": self.rsi_short,
            "rsi_medium": self.rsi_medium,
            "rsi_long": self.rsi_long,
            "confidence_score": self.confidence_score,
            "observation_label": self.observation_label,
            "status": self.status,
        }


class TripleReboundObserver:
    """Observe Triple Rebound context without producing operational signals."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.store = TraderDataStore() if db_path is None else TraderDataStore(db_path)

    def observe_for_session(
        self,
        *,
        session_id: int,
        max_zone_distance_percent: float = 0.35,
        min_zone_strength: float = 50.0,
        persist: bool = True,
    ) -> TripleReboundObservationResult:
        self.store.initialize()

        with self.store._connect() as connection:
            _ensure_observation_table(connection)

            latest_tick = _fetch_latest_tick(connection, session_id)
            latest_rsi = _fetch_latest_rsi(connection, session_id)
            zones = _fetch_zones(connection, session_id, min_zone_strength)

            if latest_tick is None:
                return TripleReboundObservationResult(
                    observation_id=None,
                    session_id=session_id,
                    tick_id=None,
                    asset="UNKNOWN",
                    timeframe="UNKNOWN",
                    latest_price=None,
                    zone_id=None,
                    zone_type=None,
                    zone_mid_price=None,
                    distance_to_zone_percent=None,
                    rsi_snapshot_id=None,
                    rsi_short=None,
                    rsi_medium=None,
                    rsi_long=None,
                    confidence_score=0.0,
                    observation_label="NO_PRICE_DATA",
                    status="TRIPLE_REBOUND_NO_PRICE_DATA",
                )

            tick_id = int(latest_tick["id"])
            asset = str(latest_tick["asset"])
            timeframe = str(latest_tick["timeframe"])
            latest_price = float(latest_tick["price"])

            nearest_zone = _nearest_zone(latest_price, zones)
            latest_rsi = latest_rsi or {}

            rsi_snapshot_id = int(latest_rsi["id"]) if latest_rsi.get("id") is not None else None
            rsi_short = _as_float(latest_rsi.get("rsi_short"))
            rsi_medium = _as_float(latest_rsi.get("rsi_medium"))
            rsi_long = _as_float(latest_rsi.get("rsi_long"))

            zone_id: int | None = None
            zone_type: str | None = None
            zone_mid_price: float | None = None
            distance_percent: float | None = None

            if nearest_zone is not None:
                zone_id = int(nearest_zone["id"])
                zone_type = str(nearest_zone["zone_type"])
                zone_mid_price = float(nearest_zone["mid_price"])
                distance_percent = _distance_percent(latest_price, zone_mid_price)

            observation_label, status = _classify_observation(
                zone_type=zone_type,
                distance_percent=distance_percent,
                max_zone_distance_percent=max_zone_distance_percent,
                rsi_short=rsi_short,
                rsi_medium=rsi_medium,
                rsi_long=rsi_long,
            )

            confidence_score = _confidence_score(
                zone=nearest_zone,
                distance_percent=distance_percent,
                max_zone_distance_percent=max_zone_distance_percent,
                rsi_short=rsi_short,
                rsi_medium=rsi_medium,
                rsi_long=rsi_long,
            )

            result = TripleReboundObservationResult(
                observation_id=None,
                session_id=session_id,
                tick_id=tick_id,
                asset=asset,
                timeframe=timeframe,
                latest_price=latest_price,
                zone_id=zone_id,
                zone_type=zone_type,
                zone_mid_price=zone_mid_price,
                distance_to_zone_percent=distance_percent,
                rsi_snapshot_id=rsi_snapshot_id,
                rsi_short=rsi_short,
                rsi_medium=rsi_medium,
                rsi_long=rsi_long,
                confidence_score=confidence_score,
                observation_label=observation_label,
                status=status,
            )

            observation_id: int | None = None
            if persist:
                observation_id = _insert_observation(connection, result)
                connection.commit()

        return TripleReboundObservationResult(
            observation_id=observation_id,
            session_id=result.session_id,
            tick_id=result.tick_id,
            asset=result.asset,
            timeframe=result.timeframe,
            latest_price=result.latest_price,
            zone_id=result.zone_id,
            zone_type=result.zone_type,
            zone_mid_price=result.zone_mid_price,
            distance_to_zone_percent=result.distance_to_zone_percent,
            rsi_snapshot_id=result.rsi_snapshot_id,
            rsi_short=result.rsi_short,
            rsi_medium=result.rsi_medium,
            rsi_long=result.rsi_long,
            confidence_score=result.confidence_score,
            observation_label=result.observation_label,
            status=result.status,
        )

    def list_observations(
        self,
        *,
        session_id: int,
        limit: int = 20,
    ) -> tuple[dict[str, Any], ...]:
        self.store.initialize()
        with self.store._connect() as connection:
            _ensure_observation_table(connection)
            rows = connection.execute(
                """
                SELECT *
                FROM triple_rebound_observations
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, max(1, int(limit))),
            ).fetchall()
            columns = [
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(triple_rebound_observations)"
                ).fetchall()
            ]

        observations: list[dict[str, Any]] = []
        for row in rows:
            item = dict(zip(columns, row))
            source_raw = item.get("source_json") or item.get("payload_json") or "{}"
            try:
                source = json.loads(source_raw)
            except Exception:
                source = {"raw": source_raw}

            observations.append(
                {
                    "id": item.get("id"),
                    "session_id": item.get("session_id"),
                    "tick_id": item.get("tick_id"),
                    "asset": item.get("asset"),
                    "timeframe": item.get("timeframe"),
                    "zone_id": item.get("zone_id"),
                    "zone_type": item.get("zone_type"),
                    "rsi_snapshot_id": item.get("rsi_snapshot_id"),
                    "latest_price": item.get("latest_price"),
                    "zone_mid_price": item.get("zone_mid_price"),
                    "distance_to_zone_percent": item.get("distance_to_zone_percent"),
                    "rsi_short": item.get("rsi_short"),
                    "rsi_medium": item.get("rsi_medium"),
                    "rsi_long": item.get("rsi_long"),
                    "observation_label": item.get("observation_label") or item.get("label"),
                    "confidence_score": item.get("confidence_score"),
                    "source": source,
                    "created_at": item.get("created_at") or item.get("observed_at"),
                }
            )

        return tuple(observations)


def _ensure_observation_table(connection: Any) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS triple_rebound_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            tick_id INTEGER,
            asset TEXT,
            timeframe TEXT,
            zone_id INTEGER,
            zone_type TEXT,
            rsi_snapshot_id INTEGER,
            latest_price REAL,
            zone_mid_price REAL,
            distance_to_zone_percent REAL,
            rsi_short REAL,
            rsi_medium REAL,
            rsi_long REAL,
            observation_label TEXT,
            confidence_score REAL,
            source_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    existing = {
        row[1]
        for row in connection.execute("PRAGMA table_info(triple_rebound_observations)").fetchall()
    }
    required = {
        "session_id": "INTEGER",
        "tick_id": "INTEGER",
        "asset": "TEXT",
        "timeframe": "TEXT",
        "zone_id": "INTEGER",
        "zone_type": "TEXT",
        "rsi_snapshot_id": "INTEGER",
        "latest_price": "REAL",
        "zone_mid_price": "REAL",
        "distance_to_zone_percent": "REAL",
        "rsi_short": "REAL",
        "rsi_medium": "REAL",
        "rsi_long": "REAL",
        "observation_label": "TEXT",
        "confidence_score": "REAL",
        "source_json": "TEXT",
        "created_at": "TEXT",
    }
    for column, column_type in required.items():
        if column not in existing:
            connection.execute(
                f"ALTER TABLE triple_rebound_observations ADD COLUMN {column} {column_type}"
            )


def _fetch_latest_tick(connection: Any, session_id: int) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT id, asset, timeframe, price
        FROM market_ticks
        WHERE session_id = ? AND price IS NOT NULL
        ORDER BY captured_at DESC, id DESC
        LIMIT 1
        """,
        (session_id,),
    ).fetchone()
    if row is None:
        return None
    return {"id": row[0], "asset": row[1], "timeframe": row[2], "price": row[3]}


def _fetch_latest_rsi(connection: Any, session_id: int) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT id, rsi_short, rsi_medium, rsi_long
        FROM indicator_snapshots
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (session_id,),
    ).fetchone()
    if row is None:
        return None
    return {"id": row[0], "rsi_short": row[1], "rsi_medium": row[2], "rsi_long": row[3]}


def _fetch_zones(
    connection: Any,
    session_id: int,
    min_zone_strength: float,
) -> tuple[dict[str, Any], ...]:
    rows = connection.execute(
        """
        SELECT id, zone_type, mid_price, lower_price, upper_price,
               touch_count, strength_score
        FROM support_resistance_zones
        WHERE session_id = ? AND strength_score >= ?
        ORDER BY strength_score DESC, touch_count DESC, id DESC
        """,
        (session_id, min_zone_strength),
    ).fetchall()

    return tuple(
        {
            "id": row[0],
            "zone_type": row[1],
            "mid_price": row[2],
            "lower_price": row[3],
            "upper_price": row[4],
            "touch_count": row[5],
            "strength_score": row[6],
        }
        for row in rows
    )


def _nearest_zone(
    latest_price: float,
    zones: tuple[dict[str, Any], ...],
) -> dict[str, Any] | None:
    if not zones:
        return None
    return min(zones, key=lambda zone: abs(latest_price - float(zone["mid_price"])))


def _distance_percent(latest_price: float, zone_mid_price: float) -> float:
    if zone_mid_price == 0:
        return 0.0
    return round(abs(latest_price - zone_mid_price) / abs(zone_mid_price) * 100.0, 4)


def _classify_observation(
    *,
    zone_type: str | None,
    distance_percent: float | None,
    max_zone_distance_percent: float,
    rsi_short: float | None,
    rsi_medium: float | None,
    rsi_long: float | None,
) -> tuple[str, str]:
    if zone_type is None or distance_percent is None:
        return "NO_ZONE_CONTEXT", "TRIPLE_REBOUND_NO_ZONE_CONTEXT"

    near_zone = distance_percent <= max_zone_distance_percent
    has_triple_rsi = rsi_short is not None and rsi_medium is not None and rsi_long is not None

    if not near_zone:
        return "AWAY_FROM_ZONE", "TRIPLE_REBOUND_AWAY_FROM_ZONE"

    if not has_triple_rsi:
        return "NEAR_ZONE_WITHOUT_TRIPLE_RSI", "TRIPLE_REBOUND_INCOMPLETE_CONTEXT"

    if zone_type == "support":
        return "SUPPORT_REBOUND_CONTEXT", "TRIPLE_REBOUND_CONTEXT_OBSERVED"

    if zone_type == "resistance":
        return "RESISTANCE_REJECTION_CONTEXT", "TRIPLE_REBOUND_CONTEXT_OBSERVED"

    return "ZONE_CONTEXT_OBSERVED", "TRIPLE_REBOUND_CONTEXT_OBSERVED"


def _confidence_score(
    *,
    zone: dict[str, Any] | None,
    distance_percent: float | None,
    max_zone_distance_percent: float,
    rsi_short: float | None,
    rsi_medium: float | None,
    rsi_long: float | None,
) -> float:
    if zone is None or distance_percent is None:
        return 0.0

    zone_strength = min(100.0, float(zone.get("strength_score") or 0.0))
    distance_component = max(
        0.0,
        100.0 - (distance_percent / max(max_zone_distance_percent, 0.0001) * 100.0),
    )

    rsi_values = [value for value in (rsi_short, rsi_medium, rsi_long) if value is not None]
    rsi_component = 0.0
    if len(rsi_values) == 3:
        rsi_component = 75.0
        spread = max(rsi_values) - min(rsi_values)
        if spread <= 15.0:
            rsi_component += 15.0
        if all(0.0 <= value <= 100.0 for value in rsi_values):
            rsi_component += 10.0

    score = (zone_strength * 0.45) + (distance_component * 0.35) + (rsi_component * 0.20)
    return round(max(0.0, min(100.0, score)), 2)


def _insert_observation(connection: Any, result: TripleReboundObservationResult) -> int:
    payload = result.to_dict()
    now = _utc_now()
    source_json = {
        "source": "TripleReboundObserver",
        "execution_scope": "observer_only",
        "no_broker_clicks": True,
        "no_orders": True,
        "no_real_account": True,
        "observation": payload,
    }

    values: dict[str, Any] = {
        "session_id": result.session_id,
        "tick_id": result.tick_id,
        "asset": result.asset,
        "timeframe": result.timeframe,
        "zone_id": result.zone_id,
        "zone_type": result.zone_type,
        "rsi_snapshot_id": result.rsi_snapshot_id,
        "latest_price": result.latest_price,
        "zone_mid_price": result.zone_mid_price,
        "distance_to_zone_percent": result.distance_to_zone_percent,
        "rsi_short": result.rsi_short,
        "rsi_medium": result.rsi_medium,
        "rsi_long": result.rsi_long,
        "observation_label": result.observation_label,
        "label": result.observation_label,
        "status": result.status,
        "confidence_score": result.confidence_score,
        "source_json": json.dumps(source_json, ensure_ascii=False),
        "payload_json": json.dumps(source_json, ensure_ascii=False),
        "result_json": json.dumps(source_json, ensure_ascii=False),
        "touch_index": 1,
        "created_at": now,
        "observed_at": now,
        "captured_at": now,
    }

    table_info = connection.execute("PRAGMA table_info(triple_rebound_observations)").fetchall()
    final_values: dict[str, Any] = {}

    for column in table_info:
        name = column[1]
        column_type = str(column[2] or "").upper()
        not_null = bool(column[3])
        default_value = column[4]
        primary_key = bool(column[5])

        if primary_key and name == "id":
            continue

        if name in values:
            final_values[name] = values[name]
            continue

        if not_null and default_value is None:
            final_values[name] = _fallback_required_value(
                name=name,
                column_type=column_type,
                result=result,
                source_json=source_json,
                now=now,
            )

    columns = list(final_values.keys())
    placeholders = ", ".join("?" for _ in columns)
    column_sql = ", ".join(columns)

    cursor = connection.execute(
        f"INSERT INTO triple_rebound_observations ({column_sql}) VALUES ({placeholders})",
        tuple(final_values[column] for column in columns),
    )
    return int(cursor.lastrowid)


def _fallback_required_value(
    *,
    name: str,
    column_type: str,
    result: TripleReboundObservationResult,
    source_json: dict[str, Any],
    now: str,
) -> Any:
    lowered = name.lower()

    if "json" in lowered or "payload" in lowered or "source" in lowered:
        return json.dumps(source_json, ensure_ascii=False)

    if "status" in lowered:
        return result.status

    if "label" in lowered:
        return result.observation_label

    if "type" in lowered:
        return result.zone_type or "unknown"

    if "asset" in lowered:
        return result.asset

    if "timeframe" in lowered:
        return result.timeframe

    if "index" in lowered or "count" in lowered:
        return 1

    if "time" in lowered or lowered.endswith("_at"):
        return now

    if "price" in lowered:
        return result.latest_price or 0.0

    if "score" in lowered or "rsi" in lowered or "percent" in lowered:
        return 0.0

    if "INT" in column_type:
        return 0

    if "REAL" in column_type or "FLOAT" in column_type or "DOUBLE" in column_type:
        return 0.0

    return "unknown"


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
