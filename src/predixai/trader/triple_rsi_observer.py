"""Triple RSI observer for PredixAI Trader V1.

Observer-only indicator layer for market memory.
No broker clicks, no orders, no real-account execution.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from predixai.trader.data_store import TraderDataStore


@dataclass(frozen=True)
class TripleRSIResult:
    session_id: int
    tick_id: int | None
    asset: str
    timeframe: str
    rsi_short: float | None
    rsi_medium: float | None
    rsi_long: float | None
    short_period: int
    medium_period: int
    long_period: int
    price_count: int
    indicator_snapshot_id: int | None
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "tick_id": self.tick_id,
            "asset": self.asset,
            "timeframe": self.timeframe,
            "rsi_short": self.rsi_short,
            "rsi_medium": self.rsi_medium,
            "rsi_long": self.rsi_long,
            "short_period": self.short_period,
            "medium_period": self.medium_period,
            "long_period": self.long_period,
            "price_count": self.price_count,
            "indicator_snapshot_id": self.indicator_snapshot_id,
            "status": self.status,
        }


class TripleRSIObserver:
    """Calculate and persist RSI 7/14/21 snapshots from stored market ticks."""

    DEFAULT_PERIODS = (7, 14, 21)

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.store = TraderDataStore() if db_path is None else TraderDataStore(db_path)

    def calculate_for_session(
        self,
        *,
        session_id: int,
        short_period: int = 7,
        medium_period: int = 14,
        long_period: int = 21,
        persist: bool = True,
    ) -> TripleRSIResult:
        self.store.initialize()

        with self.store._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, asset, timeframe, price
                FROM market_ticks
                WHERE session_id = ? AND price IS NOT NULL
                ORDER BY captured_at ASC, id ASC
                """,
                (session_id,),
            ).fetchall()

            if not rows:
                return TripleRSIResult(
                    session_id=session_id,
                    tick_id=None,
                    asset="UNKNOWN",
                    timeframe="UNKNOWN",
                    rsi_short=None,
                    rsi_medium=None,
                    rsi_long=None,
                    short_period=short_period,
                    medium_period=medium_period,
                    long_period=long_period,
                    price_count=0,
                    indicator_snapshot_id=None,
                    status="TRIPLE_RSI_NO_PRICE_DATA",
                )

            latest = rows[-1]
            tick_id = int(latest[0])
            asset = str(latest[1])
            timeframe = str(latest[2])
            prices = [float(row[3]) for row in rows]

            rsi_short = _calculate_rsi(prices, short_period)
            rsi_medium = _calculate_rsi(prices, medium_period)
            rsi_long = _calculate_rsi(prices, long_period)

            status = (
                "TRIPLE_RSI_READY"
                if rsi_short is not None and rsi_medium is not None and rsi_long is not None
                else "TRIPLE_RSI_INSUFFICIENT_DATA"
            )

            indicator_snapshot_id: int | None = None
            if persist:
                cursor = connection.execute(
                    """
                    INSERT INTO indicator_snapshots (
                        session_id, tick_id, asset, timeframe,
                        rsi_short, rsi_medium, rsi_long, config_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        tick_id,
                        asset,
                        timeframe,
                        rsi_short,
                        rsi_medium,
                        rsi_long,
                        json.dumps(
                            {
                                "short_period": short_period,
                                "medium_period": medium_period,
                                "long_period": long_period,
                                "price_count": len(prices),
                                "status": status,
                            },
                            ensure_ascii=False,
                        ),
                    ),
                )
                connection.commit()
                indicator_snapshot_id = int(cursor.lastrowid)

        return TripleRSIResult(
            session_id=session_id,
            tick_id=tick_id,
            asset=asset,
            timeframe=timeframe,
            rsi_short=rsi_short,
            rsi_medium=rsi_medium,
            rsi_long=rsi_long,
            short_period=short_period,
            medium_period=medium_period,
            long_period=long_period,
            price_count=len(prices),
            indicator_snapshot_id=indicator_snapshot_id,
            status=status,
        )

    def list_snapshots(
        self,
        *,
        session_id: int,
        limit: int = 10,
    ) -> tuple[dict[str, Any], ...]:
        self.store.initialize()
        with self.store._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, session_id, tick_id, asset, timeframe,
                       rsi_short, rsi_medium, rsi_long, config_json, created_at
                FROM indicator_snapshots
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
                "tick_id": int(row[2]) if row[2] is not None else None,
                "asset": row[3],
                "timeframe": row[4],
                "rsi_short": row[5],
                "rsi_medium": row[6],
                "rsi_long": row[7],
                "config": json.loads(row[8] or "{}"),
                "created_at": row[9],
            }
            for row in rows
        )


def _calculate_rsi(prices: list[float], period: int) -> float | None:
    if period <= 0 or len(prices) <= period:
        return None

    deltas = [prices[index] - prices[index - 1] for index in range(1, len(prices))]
    recent = deltas[-period:]

    gains = [delta if delta > 0 else 0.0 for delta in recent]
    losses = [-delta if delta < 0 else 0.0 for delta in recent]

    average_gain = sum(gains) / period
    average_loss = sum(losses) / period

    if average_gain == 0 and average_loss == 0:
        return 50.0

    if average_loss == 0:
        return 100.0

    relative_strength = average_gain / average_loss
    return round(100.0 - (100.0 / (1.0 + relative_strength)), 2)
