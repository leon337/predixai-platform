"""Build structural pattern registries."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.visual.pattern import Patterns
from predixai.vision.visual.pattern_registry import PatternRegistry


class PatternRegistryBuilder:
    """Create a registry for detected structural patterns."""

    def build(self, patterns: Patterns) -> PatternRegistry:
        created_at = datetime.now().astimezone().isoformat()
        return PatternRegistry(
            id=f"pattern_registry:{patterns.source_market_structure_id}",
            source_market_structure_id=patterns.source_market_structure_id,
            source_market_scene_id=patterns.source_market_scene_id,
            source_visual_scene_id=patterns.source_visual_scene_id,
            source_frame=patterns.source_frame,
            created_at=created_at,
            patterns=patterns.patterns,
            version="1.0",
            enabled=True,
            profile_id="default",
            metadata={
                "pattern_count": patterns.count,
                "region_count": patterns.region_count,
                "entity_count": patterns.entity_count,
                "ai": False,
                "llm": False,
            },
        )
