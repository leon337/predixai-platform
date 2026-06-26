"""Build semantic registries."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256

from predixai.vision.visual.semantic_element import SemanticElement
from predixai.vision.visual.semantic_registry import SemanticEntity, SemanticRegistry
from predixai.vision.visual.semantic_scene import SemanticScene


class SemanticRegistryBuilder:
    """Register semantic entities for future reuse between captures."""

    def build(self, semantic_scene: SemanticScene) -> SemanticRegistry:
        """Build one registry from a semantic scene."""
        created_at = datetime.now().astimezone().isoformat()
        entities = tuple(
            self._build_entity(semantic_scene, created_at, element)
            for element in semantic_scene.semantic_elements.elements
        )
        return SemanticRegistry(
            id=f"semantic_registry:{semantic_scene.frame_sha256}",
            source_scene_id=semantic_scene.id,
            source_frame=semantic_scene.source_frame,
            created_at=created_at,
            entities=entities,
        )

    def _build_entity(
        self,
        semantic_scene: SemanticScene,
        created_at: str,
        element: SemanticElement,
    ) -> SemanticEntity:
        labels = tuple(
            label.label
            for label in semantic_scene.label_mapping.labels_for_element(element.id)
        )
        stable_key = self._stable_key(element, labels)
        return SemanticEntity(
            id=f"semantic_entity:{stable_key}",
            stable_key=stable_key,
            semantic_element_id=element.id,
            source_object_id=element.source_object_id,
            region_id=element.region_id,
            semantic_type=element.semantic_type,
            labels=labels,
            first_seen_scene_id=semantic_scene.id,
            last_seen_scene_id=semantic_scene.id,
            observation_count=1,
            created_at=created_at,
            metadata={
                "source_scene_id": semantic_scene.source_scene_id,
                "source_frame": semantic_scene.source_frame,
                "deterministic": True,
                "ai": False,
                "llm": False,
            },
        )

    def _stable_key(
        self,
        element: SemanticElement,
        labels: tuple[str, ...],
    ) -> str:
        raw_key = "|".join(
            (
                element.semantic_type,
                element.region_id,
                element.stable_key,
                ",".join(sorted(labels)),
            )
        )
        return sha256(raw_key.encode("utf-8")).hexdigest()[:16]
