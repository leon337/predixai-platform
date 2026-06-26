"""Validate structural patterns."""

from __future__ import annotations

from dataclasses import dataclass, field

from predixai.vision.visual.pattern import Patterns


@dataclass(frozen=True)
class PatternValidation:
    """Validation result for structural patterns."""

    valid: bool
    issues: tuple[str, ...]
    pattern_count: int
    entity_count: int
    region_count: int
    created_at: str
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "issues": list(self.issues),
            "pattern_count": self.pattern_count,
            "entity_count": self.entity_count,
            "region_count": self.region_count,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


class PatternValidator:
    """Validate patterns using structural rules only."""

    def validate(self, patterns: Patterns) -> PatternValidation:
        """Validate structural pattern metadata."""
        issues: list[str] = []
        pattern_ids: set[str] = set()
        entity_ids: set[str] = set()
        region_ids: set[str] = set()

        if patterns.count == 0:
            issues.append("No patterns were detected.")

        for pattern in patterns.patterns:
            if not pattern.id:
                issues.append("Pattern identifier is missing.")
            if pattern.id in pattern_ids:
                issues.append(f"Duplicate pattern identifier: {pattern.id}")
            pattern_ids.add(pattern.id)
            if pattern.width <= 0 or pattern.height <= 0:
                issues.append(f"Pattern has invalid size: {pattern.id}")
            if pattern.x < 0 or pattern.y < 0:
                issues.append(f"Pattern has invalid coordinates: {pattern.id}")
            region_ids.add(pattern.region_id)
            entity_ids.update(pattern.entity_ids)

        valid = not issues
        return PatternValidation(
            valid=valid,
            issues=tuple(issues),
            pattern_count=patterns.count,
            entity_count=len(entity_ids),
            region_count=len(region_ids),
            created_at=patterns.created_at,
            metadata={
                "source_market_structure_id": patterns.source_market_structure_id,
                "source_market_scene_id": patterns.source_market_scene_id,
                "ai": False,
                "llm": False,
                "decision_making": False,
            },
        )
