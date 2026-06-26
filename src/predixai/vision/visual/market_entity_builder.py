"""Build structural market entities from market scenes."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.visual.market_entity import MarketEntities, MarketEntity
from predixai.vision.visual.market_scene import MarketScene


class MarketEntityBuilder:
    """Derive market entities from market scene elements deterministically."""

    def build(self, market_scene: MarketScene) -> MarketEntities:
        """Build market entities from market scene metadata."""
        created_at = datetime.now().astimezone().isoformat()
        labels_by_element = self._labels_by_element(market_scene)
        elements_by_id = {element.id: element for element in market_scene.market_elements.elements}
        entities = tuple(
            self._build_entity(
                market_scene,
                market_element,
                labels_by_element.get(market_element.source_semantic_element_id, ()),
                created_at,
            )
            for market_element in market_scene.market_elements.elements
        )
        return MarketEntities(
            source_market_scene_id=market_scene.id,
            source_visual_scene_id=market_scene.source_visual_scene_id,
            source_frame=market_scene.source_frame,
            created_at=created_at,
            entities=entities,
        )

    def _labels_by_element(
        self,
        market_scene: MarketScene,
    ) -> dict[str, tuple[str, ...]]:
        labels: dict[str, list[str]] = {}
        for label in market_scene.semantic_scene.label_mapping.labels:
            labels.setdefault(label.semantic_element_id, []).append(label.label)
        return {
            semantic_element_id: tuple(element_labels)
            for semantic_element_id, element_labels in labels.items()
        }

    def _build_entity(
        self,
        market_scene: MarketScene,
        market_element: object,
        labels: tuple[str, ...],
        created_at: str,
    ) -> MarketEntity:
        return MarketEntity(
            id=f"market_entity:{market_element.stable_key}",
            source_market_scene_id=market_scene.id,
            source_market_element_id=market_element.id,
            source_semantic_element_id=market_element.source_semantic_element_id,
            source_object_id=market_element.source_object_id,
            stable_key=market_element.stable_key,
            entity_type=market_element.market_type,
            region_id=market_element.region_id,
            region_name=market_element.region_name,
            text=market_element.text,
            labels=labels,
            x=market_element.x,
            y=market_element.y,
            width=market_element.width,
            height=market_element.height,
            confidence=market_element.confidence,
            created_at=created_at,
            metadata={
                "source_market_type": market_element.market_type,
                "structural_only": True,
                "value_interpreted": False,
                "operation_interpreted": False,
                "ai": False,
                "llm": False,
            },
        )
