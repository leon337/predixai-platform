"""Validate pattern analysis metadata."""

from __future__ import annotations

from dataclasses import dataclass, field

from predixai.vision.visual.pattern_analysis import PatternAnalysis


@dataclass(frozen=True)
class PatternAnalysisValidation:
    valid: bool
    issues: tuple[str, ...]
    pattern_count: int
    classification_count: int
    context_count: int
    created_at: str
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "issues": list(self.issues),
            "pattern_count": self.pattern_count,
            "classification_count": self.classification_count,
            "context_count": self.context_count,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


class PatternAnalysisValidator:
    def validate(self, analysis: PatternAnalysis) -> PatternAnalysisValidation:
        issues: list[str] = []
        if analysis.pattern_count == 0:
            issues.append("No patterns available for analysis.")
        if analysis.classification_count == 0:
            issues.append("No classifications available.")
        if analysis.context_count == 0:
            issues.append("No contexts available.")
        return PatternAnalysisValidation(
            valid=not issues,
            issues=tuple(issues),
            pattern_count=analysis.pattern_count,
            classification_count=analysis.classification_count,
            context_count=analysis.context_count,
            created_at=analysis.created_at,
            metadata={
                "source_pattern_scene_id": analysis.source_pattern_scene_id,
                "ai": False,
                "llm": False,
                "decision_making": False,
            },
        )
