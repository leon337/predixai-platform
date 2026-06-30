"""Live evidence package foundation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


def _to_json_value(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _to_json_value(value.to_dict())
    if isinstance(value, dict):
        return {str(key): _to_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json_value(item) for item in value]
    return value


@dataclass(frozen=True)
class LiveEvidencePackage:
    evidence_id: str
    created_at: str
    source: str
    session_id: str
    capture_count: int
    field_count: int
    unknown_fields: tuple[str, ...]
    candle_snapshot: Any
    candle_statistics: Any
    live_candle_benchmark: Any
    live_validation_benchmark: Any
    guardrails: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "evidence_id": self.evidence_id,
            "created_at": self.created_at,
            "source": self.source,
            "session_id": self.session_id,
            "capture_count": self.capture_count,
            "field_count": self.field_count,
            "unknown_fields": list(self.unknown_fields),
            "candle_snapshot": _to_json_value(self.candle_snapshot),
            "candle_statistics": _to_json_value(self.candle_statistics),
            "live_candle_benchmark": _to_json_value(self.live_candle_benchmark),
            "live_validation_benchmark": _to_json_value(
                self.live_validation_benchmark
            ),
            "guardrails": dict(self.guardrails),
        }


class LiveEvidencePackageWriter:
    """Write observer-only live evidence packages as JSON."""

    guardrails = {
        "clicks_enabled": False,
        "orders_enabled": False,
        "broker_automation_enabled": False,
        "decision_making_enabled": False,
        "real_account_enabled": False,
        "strategy_changed": False,
    }

    def __init__(self, output_directory: Path) -> None:
        self.output_directory = output_directory

    def build(
        self,
        *,
        source: str,
        session_id: str,
        capture_count: int,
        field_count: int,
        unknown_fields: tuple[str, ...],
        candle_snapshot: Any,
        candle_statistics: Any,
        live_candle_benchmark: Any,
        live_validation_benchmark: Any,
    ) -> LiveEvidencePackage:
        created_at = datetime.now().astimezone().isoformat()
        evidence_id = f"live_evidence_{self._timestamp()}_{self._safe_id(session_id)}"
        return LiveEvidencePackage(
            evidence_id=evidence_id,
            created_at=created_at,
            source=source,
            session_id=session_id,
            capture_count=capture_count,
            field_count=field_count,
            unknown_fields=unknown_fields,
            candle_snapshot=candle_snapshot,
            candle_statistics=candle_statistics,
            live_candle_benchmark=live_candle_benchmark,
            live_validation_benchmark=live_validation_benchmark,
            guardrails=dict(self.guardrails),
        )

    def write(self, package: LiveEvidencePackage) -> Path:
        self.output_directory.mkdir(parents=True, exist_ok=True)
        output_path = self.output_directory / f"{package.evidence_id}.json"
        output_path.write_text(
            json.dumps(package.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output_path

    @staticmethod
    def _timestamp() -> str:
        return datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")

    @staticmethod
    def _safe_id(value: str) -> str:
        safe_value = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
        return safe_value or "unknown_session"
