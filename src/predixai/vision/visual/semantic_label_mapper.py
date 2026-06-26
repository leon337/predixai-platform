"""Map deterministic semantic labels to semantic elements."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.visual.semantic_element import (
    SemanticElement,
    SemanticElements,
)
from predixai.vision.visual.semantic_label import (
    SemanticLabel,
    SemanticLabelMapping,
)


class SemanticLabelMapper:
    """Assign labels using simple deterministic rules only."""

    def map_labels(self, semantic_elements: SemanticElements) -> SemanticLabelMapping:
        """Map labels without AI, LLMs or probabilistic classification."""
        created_at = datetime.now().astimezone().isoformat()
        labels: list[SemanticLabel] = []
        for element in semantic_elements.elements:
            labels.extend(self._labels_for_element(element, created_at))

        return SemanticLabelMapping(
            source_scene_id=semantic_elements.source_scene_id,
            created_at=created_at,
            labels=tuple(labels),
        )

    def _labels_for_element(
        self,
        element: SemanticElement,
        created_at: str,
    ) -> tuple[SemanticLabel, ...]:
        rules: list[tuple[str, str, str]] = [
            (
                "INTERFACE_OBJECT",
                "ENTITY",
                "semantic_type_equals_interface_object",
            )
        ]
        if element.region_id == "FULL_SCREEN":
            rules.append(("FULL_SCREEN_REGION", "REGION", "region_id_full_screen"))
        if element.text.strip():
            rules.append(("TEXT_CONTENT_PRESENT", "TEXT", "text_is_not_empty"))

        normalized_text = element.text.casefold()
        if "predixai" in normalized_text:
            rules.append(("PREDIXAI_TEXT_PRESENT", "TEXT_PATTERN", "text_has_predixai"))
        if any(token in normalized_text for token in ("arquivo", "editar", "exibir")):
            rules.append(("MENU_TEXT_PRESENT", "TEXT_PATTERN", "text_has_menu_token"))

        return tuple(
            SemanticLabel(
                id=f"semantic_label:{element.stable_key}:{label}",
                semantic_element_id=element.id,
                label=label,
                category=category,
                rule=rule,
                confidence=1.0,
                created_at=created_at,
                metadata={
                    "region_id": element.region_id,
                    "source_object_id": element.source_object_id,
                    "deterministic": True,
                    "ai": False,
                    "llm": False,
                },
            )
            for label, category, rule in rules
        )
