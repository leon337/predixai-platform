"""Semantic labels created by deterministic rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SemanticLabel:
    """One deterministic semantic label assigned to an element."""

    id: str
    semantic_element_id: str
    label: str
    category: str
    rule: str
    confidence: float
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "id": self.id,
            "semantic_element_id": self.semantic_element_id,
            "label": self.label,
            "category": self.category,
            "rule": self.rule,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class SemanticLabelMapping:
    """Result of deterministic label mapping for semantic elements."""

    source_scene_id: str
    created_at: str
    labels: tuple[SemanticLabel, ...]

    @property
    def count(self) -> int:
        """Return the number of mapped labels."""
        return len(self.labels)

    @property
    def unique_label_count(self) -> int:
        """Return the number of unique label names."""
        return len({label.label for label in self.labels})

    def labels_for_element(self, semantic_element_id: str) -> tuple[SemanticLabel, ...]:
        """Return labels assigned to a semantic element."""
        return tuple(
            label
            for label in self.labels
            if label.semantic_element_id == semantic_element_id
        )

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "source_scene_id": self.source_scene_id,
            "created_at": self.created_at,
            "count": self.count,
            "unique_label_count": self.unique_label_count,
            "labels": [label.to_dict() for label in self.labels],
        }
