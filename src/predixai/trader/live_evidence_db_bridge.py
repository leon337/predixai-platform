"""Bridge live evidence JSON files into the PredixAI Trader SQLite store.

V1 scope: observer memory only.
No broker clicks, no orders, no real-account execution.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from predixai.trader.data_store import TraderDataStore
from predixai.trader.market_session_recorder import MarketSessionRecorder


@dataclass(frozen=True)
class LiveEvidenceIngestResult:
    session_id: int
    tick_id: int
    evidence_record_id: int
    evidence_path: str
    asset: str
    timeframe: str
    price: float | None
    quality_score: float
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "tick_id": self.tick_id,
            "evidence_record_id": self.evidence_record_id,
            "evidence_path": self.evidence_path,
            "asset": self.asset,
            "timeframe": self.timeframe,
            "price": self.price,
            "quality_score": self.quality_score,
            "status": self.status,
        }


class LiveEvidenceDBBridge:
    """Persist live evidence packages into the Trader data store."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.store = TraderDataStore() if db_path is None else TraderDataStore(db_path)
        self.recorder = MarketSessionRecorder(db_path)

    def ingest_evidence_file(
        self,
        *,
        evidence_path: str | Path,
        session_id: int | None = None,
        asset: str = "UNKNOWN",
        timeframe: str = "M1",
    ) -> LiveEvidenceIngestResult:
        self.store.initialize()
        clean_path = Path(evidence_path)
        if not clean_path.exists():
            raise FileNotFoundError(f"Evidence file not found: {clean_path}")

        payload = json.loads(clean_path.read_text(encoding="utf-8-sig"))

        effective_asset = _first_text(
            payload.get("asset"),
            _nested_get(payload, ("session", "asset")),
            _nested_get(payload, ("metadata", "asset")),
            asset,
        )
        effective_timeframe = _first_text(
            payload.get("timeframe"),
            _nested_get(payload, ("candle_snapshot", "timeframe")),
            _nested_get(payload, ("session", "timeframe")),
            _nested_get(payload, ("metadata", "timeframe")),
            timeframe,
        )

        if session_id is None:
            session = self.recorder.start_session(
                asset=effective_asset,
                timeframe=effective_timeframe,
                mode="observer",
                notes=f"auto-created by LiveEvidenceDBBridge for {clean_path.name}",
            )
            session_id = session.id
        else:
            existing = self.recorder.get_session(int(session_id))
            if existing is None:
                raise ValueError(f"Session not found: {session_id}")

        captured_at = _first_text(
            payload.get("captured_at"),
            payload.get("created_at"),
            payload.get("generated_at"),
            _nested_get(payload, ("candle_snapshot", "captured_at")),
            _nested_get(payload, ("candle_snapshot", "created_at")),
            _utc_now(),
        )

        price = _extract_price(payload)
        direction = _extract_direction(payload)
        quality_score = _quality_score(payload, price)

        tick_id = self.store.record_tick(
            session_id=int(session_id),
            asset=effective_asset,
            timeframe=effective_timeframe,
            captured_at=captured_at,
            price=price,
            direction=direction,
            raw_fields=_compact_raw_fields(payload),
            evidence_path=str(clean_path),
            quality_score=quality_score,
        )

        evidence_record_id = self._record_evidence(
            session_id=int(session_id),
            tick_id=tick_id,
            evidence_path=str(clean_path),
            payload=payload,
        )

        return LiveEvidenceIngestResult(
            session_id=int(session_id),
            tick_id=tick_id,
            evidence_record_id=evidence_record_id,
            evidence_path=str(clean_path),
            asset=effective_asset,
            timeframe=effective_timeframe,
            price=price,
            quality_score=quality_score,
            status="LIVE_EVIDENCE_DB_INGESTED",
        )

    def ingest_latest_evidence(
        self,
        *,
        evidence_dir: str | Path = Path("data") / "live_evidence",
        session_id: int | None = None,
        asset: str = "UNKNOWN",
        timeframe: str = "M1",
    ) -> LiveEvidenceIngestResult:
        directory = Path(evidence_dir)
        if not directory.exists():
            raise FileNotFoundError(f"Evidence directory not found: {directory}")

        files = sorted(
            (path for path in directory.rglob("*.json") if path.is_file()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not files:
            raise FileNotFoundError(f"No JSON evidence files found in: {directory}")

        return self.ingest_evidence_file(
            evidence_path=files[0],
            session_id=session_id,
            asset=asset,
            timeframe=timeframe,
        )

    def _record_evidence(
        self,
        *,
        session_id: int,
        tick_id: int,
        evidence_path: str,
        payload: dict[str, Any],
    ) -> int:
        with self.store._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO evidence_records (
                    session_id, tick_id, evidence_path, evidence_type, payload_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    tick_id,
                    evidence_path,
                    "live_evidence",
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)


def _extract_price(payload: dict[str, Any]) -> float | None:
    direct_candidates = (
        payload.get("price"),
        _nested_get(payload, ("candle_statistics", "close")),
        _nested_get(payload, ("candle_statistics", "last")),
        _nested_get(payload, ("candle_statistics", "average")),
        _nested_get(payload, ("live_candle_benchmark", "average")),
    )
    for candidate in direct_candidates:
        parsed = _parse_number(candidate)
        if parsed is not None:
            return parsed

    field_values = _nested_get(payload, ("candle_snapshot", "field_values"))
    if isinstance(field_values, list):
        for item in field_values:
            if not isinstance(item, dict):
                continue
            name = str(item.get("field_name") or item.get("name") or "").lower()
            if "price" not in name and "preco" not in name and "cotacao" not in name:
                continue
            for key in ("value", "raw_value", "text", "normalized_value"):
                parsed = _parse_number(item.get(key))
                if parsed is not None:
                    return parsed

    return None


def _extract_direction(payload: dict[str, Any]) -> str | None:
    candidates = (
        payload.get("direction"),
        _nested_get(payload, ("candle_statistics", "direction")),
        _nested_get(payload, ("candle_snapshot", "direction")),
    )
    for candidate in candidates:
        if candidate is not None and str(candidate).strip():
            return str(candidate).strip()
    return None


def _quality_score(payload: dict[str, Any], price: float | None) -> float:
    score = 25.0

    if price is not None:
        score += 35.0

    if payload.get("candle_snapshot"):
        score += 15.0

    if payload.get("candle_statistics"):
        score += 15.0

    unknown_fields = _nested_get(payload, ("candle_snapshot", "unknown_fields"))
    if isinstance(unknown_fields, list):
        score -= min(20.0, float(len(unknown_fields)) * 5.0)

    field_values = _nested_get(payload, ("candle_snapshot", "field_values"))
    if isinstance(field_values, list) and field_values:
        score += 10.0

    return max(0.0, min(100.0, round(score, 2)))


def _compact_raw_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "asset": payload.get("asset"),
        "timeframe": payload.get("timeframe"),
        "candle_snapshot": payload.get("candle_snapshot"),
        "candle_statistics": payload.get("candle_statistics"),
        "live_candle_benchmark": payload.get("live_candle_benchmark"),
        "live_validation_benchmark": payload.get("live_validation_benchmark"),
    }


def _nested_get(payload: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _first_text(*values: Any) -> str:
    for value in values:
        if value is not None and str(value).strip():
            return str(value).strip()
    return "UNKNOWN"


def _parse_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    match = re.search(r"[-+]?\d+(?:[.,]\d+)?", text.replace(" ", ""))
    if not match:
        return None

    normalized = match.group(0).replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
