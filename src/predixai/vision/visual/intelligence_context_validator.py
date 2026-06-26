"""Validate intelligence context metadata."""

from __future__ import annotations

from dataclasses import dataclass, field

from predixai.vision.visual.intelligence_context import IntelligenceContext


@dataclass(frozen=True)
class IntelligenceContextValidation:
    valid: bool
    issues: tuple[str, ...]
    analysis_count: int
    entity_count: int
    created_at: str
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "issues": list(self.issues),
            "analysis_count": self.analysis_count,
            "entity_count": self.entity_count,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


class IntelligenceContextValidator:
    def validate(self, context: IntelligenceContext) -> IntelligenceContextValidation:
        issues: list[str] = []
        if context.analysis_count <= 0:
            issues.append("Pattern analysis is required.")
        if context.entity_count <= 0:
            issues.append("Market entities are required.")
        return IntelligenceContextValidation(
            valid=not issues,
            issues=tuple(issues),
            analysis_count=context.analysis_count,
            entity_count=context.entity_count,
            created_at=context.created_at,
            metadata={
                "source_pattern_analysis_id": context.source_pattern_analysis_id,
                "ai": False,
                "llm": False,
                "decision_making": False,
            },
        )
