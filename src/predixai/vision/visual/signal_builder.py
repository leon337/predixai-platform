"""Build structural signals."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.visual.intelligence_snapshot import IntelligenceSnapshot
from predixai.vision.visual.signal import Signal, Signals


class SignalBuilder:
    def build(self, intelligence_snapshot: IntelligenceSnapshot) -> Signals:
        created_at = datetime.now().astimezone().isoformat()
        signals = tuple(
            self._build_signal(intelligence_snapshot, created_at)
            for _ in range(1)
        )
        return Signals(
            source_intelligence_snapshot_id=intelligence_snapshot.id,
            source_market_structure_id=intelligence_snapshot.source_market_structure_id,
            source_pattern_analysis_id=intelligence_snapshot.source_pattern_analysis_id,
            source_market_scene_id=intelligence_snapshot.source_market_scene_id,
            source_visual_scene_id=intelligence_snapshot.source_visual_scene_id,
            source_frame=intelligence_snapshot.source_frame,
            created_at=created_at,
            signals=signals,
        )

    def _build_signal(self, intelligence_snapshot: IntelligenceSnapshot, created_at: str) -> Signal:
        return Signal(
            id=f"signal:{intelligence_snapshot.source_pattern_analysis_id}",
            source_intelligence_snapshot_id=intelligence_snapshot.id,
            source_market_structure_id=intelligence_snapshot.source_market_structure_id,
            source_pattern_analysis_id=intelligence_snapshot.source_pattern_analysis_id,
            source_market_scene_id=intelligence_snapshot.source_market_scene_id,
            source_visual_scene_id=intelligence_snapshot.source_visual_scene_id,
            source_frame=intelligence_snapshot.source_frame,
            created_at=created_at,
            signal_type="STRUCTURAL_SIGNAL",
            description="Deterministic structural signal derived from intelligence snapshot without execution.",
            strength=1.0,
            intelligence_snapshot=intelligence_snapshot,
            metadata={"ai": False, "llm": False, "decision_making": False},
        )
