"""Deterministic pattern classification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from predixai.vision.visual.pattern_scene import PatternScene


@dataclass(frozen=True)
class PatternClassification:
    pattern_id: str
    classification: str
    rule: str
    confidence: float
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "pattern_id": self.pattern_id,
            "classification": self.classification,
            "rule": self.rule,
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
        }


class PatternClassifier:
    def classify(self, pattern_scene: PatternScene) -> tuple[PatternClassification, ...]:
        classifications: list[PatternClassification] = []
        for pattern in pattern_scene.patterns.patterns:
            label = self._classify_pattern(pattern.pattern_type)
            classifications.append(
                PatternClassification(
                    pattern_id=pattern.id,
                    classification=label,
                    rule="structural_type_rule",
                    confidence=1.0,
                    metadata={
                        "region_id": pattern.region_id,
                        "ai": False,
                        "llm": False,
                    },
                )
            )
        return tuple(classifications)

    def _classify_pattern(self, pattern_type: str) -> str:
        if "PRICE" in pattern_type:
            return "PRICE_PATTERN"
        if "TIME" in pattern_type:
            return "TIME_PATTERN"
        return "STRUCTURAL_PATTERN"
