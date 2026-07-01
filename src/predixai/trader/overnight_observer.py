"""Overnight Observer for PredixAI Trader V1.

Supervised long-session observer.
No broker clicks, no orders, no real-account execution.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from predixai.trader.data_store import TraderDataStore
from predixai.trader.market_session_recorder import MarketSessionRecorder
from predixai.trader.support_resistance_zones import SupportResistanceZoneDetector
from predixai.trader.triple_rebound_observer import TripleReboundObserver
from predixai.trader.triple_rsi_observer import TripleRSIObserver


DEFAULT_REPORT_DIR = Path("data") / "runtime" / "overnight_observer"


@dataclass(frozen=True)
class OvernightCycleResult:
    cycle_index: int
    session_id: int
    tick_id: int | None
    latest_price: float | None
    rsi_status: str | None
    zones_detected: int
    rebound_status: str | None
    rebound_label: str | None
    confidence_score: float | None
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_index": self.cycle_index,
            "session_id": self.session_id,
            "tick_id": self.tick_id,
            "latest_price": self.latest_price,
            "rsi_status": self.rsi_status,
            "zones_detected": self.zones_detected,
            "rebound_status": self.rebound_status,
            "rebound_label": self.rebound_label,
            "confidence_score": self.confidence_score,
            "status": self.status,
        }


@dataclass(frozen=True)
class OvernightRunResult:
    session_id: int
    asset: str
    timeframe: str
    cycle_count: int
    started_at: str
    ended_at: str
    report_path: str
    latest_cycle: dict[str, Any] | None
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "asset": self.asset,
            "timeframe": self.timeframe,
            "cycle_count": self.cycle_count,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "report_path": self.report_path,
            "latest_cycle": self.latest_cycle,
            "status": self.status,
        }


class OvernightObserver:
    """Run supervised observer cycles for long market sessions."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.store = TraderDataStore() if db_path is None else TraderDataStore(db_path)
        self.sessions = MarketSessionRecorder(db_path)
        self.rsi = TripleRSIObserver(db_path)
        self.zones = SupportResistanceZoneDetector(db_path)
        self.rebound = TripleReboundObserver(db_path)

    def run(
        self,
        *,
        asset: str,
        timeframe: str = "M1",
        cycles: int = 30,
        sleep_seconds: float = 0.0,
        synthetic: bool = False,
        close_session: bool = False,
        report_dir: str | Path = DEFAULT_REPORT_DIR,
    ) -> OvernightRunResult:
        self.store.initialize()
        started_at = _utc_now()
        clean_cycles = max(1, int(cycles))
        clean_sleep = max(0.0, float(sleep_seconds))

        session = self.sessions.start_session(
            asset=asset,
            timeframe=timeframe,
            mode="observer",
            notes=(
                "PTP-103 Overnight Observer session. "
                "Observer-only. No broker clicks, no orders, no real-account execution."
            ),
        )

        cycle_results: list[OvernightCycleResult] = []
        synthetic_prices = _synthetic_prices(clean_cycles)

        for index in range(clean_cycles):
            tick_id: int | None = None
            latest_price: float | None = None

            if synthetic:
                latest_price = float(synthetic_prices[index])
                tick_id = self.store.record_tick(
                    session_id=session.id,
                    asset=asset,
                    timeframe=timeframe,
                    captured_at=_utc_now(),
                    price=latest_price,
                    direction="observer",
                    raw_fields={
                        "source": "PTP-103 OvernightObserver synthetic validation",
                        "cycle_index": index + 1,
                    },
                    evidence_path=None,
                    quality_score=100.0,
                )

            rsi_result = self.rsi.calculate_for_session(session_id=session.id, persist=True)
            zone_results = self.zones.detect_for_session(session_id=session.id, persist=True)
            rebound_result = self.rebound.observe_for_session(session_id=session.id, persist=True)

            cycle_results.append(
                OvernightCycleResult(
                    cycle_index=index + 1,
                    session_id=session.id,
                    tick_id=tick_id,
                    latest_price=latest_price,
                    rsi_status=rsi_result.status,
                    zones_detected=len(zone_results),
                    rebound_status=rebound_result.status,
                    rebound_label=rebound_result.observation_label,
                    confidence_score=rebound_result.confidence_score,
                    status="OVERNIGHT_OBSERVER_CYCLE_COMPLETED",
                )
            )

            if clean_sleep > 0 and index < clean_cycles - 1:
                time.sleep(clean_sleep)

        if close_session:
            self.sessions.close_session(session_id=session.id, status="completed")

        ended_at = _utc_now()
        report_path = self._write_report(
            report_dir=report_dir,
            session_id=session.id,
            asset=asset,
            timeframe=timeframe,
            started_at=started_at,
            ended_at=ended_at,
            cycles=cycle_results,
        )

        latest_cycle = cycle_results[-1].to_dict() if cycle_results else None

        return OvernightRunResult(
            session_id=session.id,
            asset=asset,
            timeframe=timeframe,
            cycle_count=len(cycle_results),
            started_at=started_at,
            ended_at=ended_at,
            report_path=str(report_path),
            latest_cycle=latest_cycle,
            status="OVERNIGHT_OBSERVER_COMPLETED",
        )

    def _write_report(
        self,
        *,
        report_dir: str | Path,
        session_id: int,
        asset: str,
        timeframe: str,
        started_at: str,
        ended_at: str,
        cycles: list[OvernightCycleResult],
    ) -> Path:
        directory = Path(report_dir)
        directory.mkdir(parents=True, exist_ok=True)
        report_path = directory / f"overnight_session_{session_id}_{_compact_timestamp()}.json"

        payload = {
            "session_id": session_id,
            "asset": asset,
            "timeframe": timeframe,
            "started_at": started_at,
            "ended_at": ended_at,
            "cycle_count": len(cycles),
            "execution_scope": "observer_only",
            "guardrails": {
                "broker_clicks_enabled": False,
                "orders_enabled": False,
                "real_account_enabled": False,
                "broker_automation_enabled": False,
                "decision_making_enabled": False,
            },
            "cycles": [cycle.to_dict() for cycle in cycles],
        }

        report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report_path


def _synthetic_prices(cycles: int) -> list[float]:
    base = [
        100.00, 100.05, 100.10, 100.03, 100.15,
        100.20, 100.08, 100.18, 100.25, 100.30,
        100.12, 100.22, 100.35, 100.40, 100.18,
        100.28, 100.38, 100.45, 100.20, 100.30,
        100.42, 100.50, 100.25, 100.35, 100.48,
        100.55, 100.30, 100.40, 100.52, 100.60,
    ]
    if cycles <= len(base):
        return base[:cycles]

    prices = list(base)
    while len(prices) < cycles:
        prices.append(round(prices[-1] + 0.05, 6))
    return prices


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _compact_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
