"""Build structural patterns from market structures."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.visual.market_structure import MarketStructure
from predixai.vision.visual.pattern import Pattern, Patterns


class PatternBuilder:
    """Derive deterministic patterns from market structure metadata."""

    def build(self, market_structure: MarketStructure) -> Patterns:
        """Build structural patterns from the market structure."""
        created_at = datetime.now().astimezone().isoformat()
        patterns = tuple(
            self._build_pattern(market_structure, entity, created_at)
            for entity in market_structure.market_entities.entities
        )
        return Patterns(
            source_market_structure_id=market_structure.id,
            source_market_scene_id=market_structure.source_market_scene_id,
            source_visual_scene_id=market_structure.market_scene.source_visual_scene_id,
            source_frame=market_structure.source_frame,
            created_at=created_at,
            patterns=patterns,
        )

    def _build_pattern(
        self,
        market_structure: MarketStructure,
        entity: object,
        created_at: str,
    ) -> Pattern:
        pattern_type = f"{getattr(entity, 'entity_type', 'STRUCTURAL')}_PATTERN"
        name = getattr(entity, "region_name", "Pattern")
        description = (
            "Deterministic structural pattern derived from market structure "
            "metadata without AI or decision-making."
        )
        confidence = float(getattr(entity, "confidence", 0.0))
        return Pattern(
            id=f"pattern:{getattr(entity, 'stable_key', market_structure.frame_sha256)}",
            source_market_structure_id=market_structure.id,
            source_market_scene_id=market_structure.source_market_scene_id,
            source_visual_scene_id=market_structure.market_scene.source_visual_scene_id,
            source_frame=market_structure.source_frame,
            stable_key=str(getattr(entity, "stable_key", market_structure.frame_sha256)),
            pattern_type=pattern_type,
            name=name,
            description=description,
            region_id=str(getattr(entity, "region_id", "FULL_SCREEN")),
            region_name=str(getattr(entity, "region_name", "Full Screen")),
            x=int(getattr(entity, "x", 0)),
            y=int(getattr(entity, "y", 0)),
            width=int(getattr(entity, "width", 0)),
            height=int(getattr(entity, "height", 0)),
            confidence=confidence,
            entity_ids=(str(getattr(entity, "id", "")),),
            created_at=created_at,
            metadata={
                "source_market_type": getattr(entity, "entity_type", "STRUCTURAL"),
                "structural_only": True,
                "ai": False,
                "llm": False,
                "decision_making": False,
            },
        )
