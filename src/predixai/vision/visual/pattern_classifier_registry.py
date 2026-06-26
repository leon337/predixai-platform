"""Registry for deterministic pattern classifications."""

from __future__ import annotations

from dataclasses import dataclass

from predixai.vision.visual.pattern_classifier import PatternClassification


@dataclass(frozen=True)
class PatternClassifierRegistry:
    classifications: tuple[PatternClassification, ...]

    @property
    def count(self) -> int:
        return len(self.classifications)

    def to_dict(self) -> dict[str, object]:
        return {
            "count": self.count,
            "classifications": [item.to_dict() for item in self.classifications],
        }
