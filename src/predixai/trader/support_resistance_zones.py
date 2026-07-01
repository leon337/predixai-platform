"""Support and resistance zone foundation for PredixAI Trader V1.

Observer-only market memory layer.
No broker clicks, no orders, no real-account execution.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from predixai.trader.data_store import TraderDataStore


@dataclass(frozen=True)
class SupportResistanceZoneResult:
    zone_id: int | None
    session_id: int
    asset: str
    timeframe: str
    zone_type: str
    lower_price: float
    upper_price: float
    mid_price: float
    touch_count: int
    strength_score: float
    last_touch_at: str | None
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "zone_id": self.zone_id,
            "session_id": self.session_id,
            "asset": self.asset,
            "timeframe": self.timeframe,
            "zone_type": self.zone_type,
            "lower_price": self.lower_price,
            "upper_price": self.upper_price,
            "mid_price": self.mid_price,
            "touch_count": self.touch_count,
            "strength_score": self.strength_score,
            "last_touch_at": self.last_touch_at,
            "status": self.status,
        }


class SupportResistanceZoneDetector:
    """Detect price clusters as observer support/resistance zones."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.store = TraderDataStore() if db_path is None else TraderDataStore(db_path)

    def detect_for_session(
        self,
        *,
        session_id: int,
        tolerance_percent: float = 0.25,
        min_touches: int = 2,
        persist: bool = True,
    ) -> tuple[SupportResistanceZoneResult, ...]:
        self.store.initialize()

        with self.store._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, captured_at, asset, timeframe, price
                FROM market_ticks
                WHERE session_id = ? AND price IS NOT NULL
                ORDER BY price ASC, captured_at ASC, id ASC
                """,
                (session_id,),
            ).fetchall()

            if not rows:
                return ()

            latest_row = connection.execute(
                """
                SELECT asset, timeframe, price
                FROM market_ticks
                WHERE session_id = ? AND price IS NOT NULL
                ORDER BY captured_at DESC, id DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()

            latest_price = float(latest_row[2]) if latest_row else float(rows[-1][4])
            clusters = _cluster_prices(rows, tolerance_percent)
            results: list[SupportResistanceZoneResult] = []

            for cluster in clusters:
                touch_count = len(cluster["prices"])
                if touch_count < min_touches:
                    continue

                lower_price = round(min(cluster["prices"]), 6)
                upper_price = round(max(cluster["prices"]), 6)
                mid_price = round(sum(cluster["prices"]) / touch_count, 6)
                zone_type = "support" if mid_price <= latest_price else "resistance"
                strength_score = _strength_score(touch_count, latest_price, mid_price)
                last_touch_at = max(cluster["timestamps"]) if cluster["timestamps"] else None

                zone_id: int | None = None
                if persist:
                    cursor = connection.execute(
                        """
                        INSERT INTO support_resistance_zones (
                            session_id, asset, timeframe, zone_type,
                            lower_price, upper_price, mid_price,
                            touch_count, strength_score, last_touch_at, source_json
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            session_id,
                            str(cluster["asset"]),
                            str(cluster["timeframe"]),
                            zone_type,
                            lower_price,
                            upper_price,
                            mid_price,
                            touch_count,
                            strength_score,
                            last_touch_at,
                            json.dumps(
                                {
                                    "tolerance_percent": tolerance_percent,
                                    "min_touches": min_touches,
                                    "latest_price": latest_price,
                                    "source": "SupportResistanceZoneDetector",
                                },
                                ensure_ascii=False,
                            ),
                        ),
                    )
                    zone_id = int(cursor.lastrowid)

                results.append(
                    SupportResistanceZoneResult(
                        zone_id=zone_id,
                        session_id=session_id,
                        asset=str(cluster["asset"]),
                        timeframe=str(cluster["timeframe"]),
                        zone_type=zone_type,
                        lower_price=lower_price,
                        upper_price=upper_price,
                        mid_price=mid_price,
                        touch_count=touch_count,
                        strength_score=strength_score,
                        last_touch_at=last_touch_at,
                        status="SUPPORT_RESISTANCE_ZONE_DETECTED",
                    )
                )

            if persist:
                connection.commit()

        return tuple(results)

    def list_zones(
        self,
        *,
        session_id: int,
        limit: int = 20,
    ) -> tuple[dict[str, Any], ...]:
        self.store.initialize()
        with self.store._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, session_id, asset, timeframe, zone_type,
                       lower_price, upper_price, mid_price, touch_count,
                       strength_score, last_touch_at, source_json, created_at
                FROM support_resistance_zones
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, max(1, int(limit))),
            ).fetchall()

        return tuple(
            {
                "id": int(row[0]),
                "session_id": int(row[1]),
                "asset": row[2],
                "timeframe": row[3],
                "zone_type": row[4],
                "lower_price": row[5],
                "upper_price": row[6],
                "mid_price": row[7],
                "touch_count": int(row[8]),
                "strength_score": row[9],
                "last_touch_at": row[10],
                "source": json.loads(row[11] or "{}"),
                "created_at": row[12],
            }
            for row in rows
        )


def _cluster_prices(rows: list[Any], tolerance_percent: float) -> list[dict[str, Any]]:
    clusters: list[dict[str, Any]] = []
    tolerance_percent = max(0.01, float(tolerance_percent))

    for row in rows:
        captured_at = str(row[1])
        asset = str(row[2])
        timeframe = str(row[3])
        price = float(row[4])

        matched = False
        for cluster in clusters:
            tolerance = max(abs(float(cluster["mid_price"])) * tolerance_percent / 100.0, 0.000001)
            if abs(price - float(cluster["mid_price"])) <= tolerance:
                cluster["prices"].append(price)
                cluster["timestamps"].append(captured_at)
                cluster["mid_price"] = sum(cluster["prices"]) / len(cluster["prices"])
                matched = True
                break

        if not matched:
            clusters.append(
                {
                    "asset": asset,
                    "timeframe": timeframe,
                    "prices": [price],
                    "timestamps": [captured_at],
                    "mid_price": price,
                }
            )

    return clusters


def _strength_score(touch_count: int, latest_price: float, mid_price: float) -> float:
    distance = abs(latest_price - mid_price)
    distance_penalty = min(30.0, distance)
    score = min(100.0, touch_count * 18.0 + 20.0 - distance_penalty)
    return round(max(0.0, score), 2)
