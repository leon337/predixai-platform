"""Build market interface elements from semantic scenes."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.visual.market_element import MarketElement, MarketElements
from predixai.vision.visual.semantic_scene import SemanticScene


class MarketElementBuilder:
    """Derive structural market elements without operational interpretation."""

    _ASSET_TOKENS = ("ativo", "asset", "par", "symbol", "otc")
    _PRICE_TOKENS = ("preco", "price", "valor", "cotacao", "quote")
    _TIME_TOKENS = ("tempo", "time", "hora", "timer", "expiracao")

    def build(self, semantic_scene: SemanticScene) -> MarketElements:
        """Build market elements from semantic entities deterministically."""
        created_at = datetime.now().astimezone().isoformat()
        labels_by_element = self._labels_by_element(semantic_scene)
        elements = tuple(
            self._build_element(
                semantic_scene,
                semantic_element,
                labels_by_element.get(semantic_element.id, ()),
                created_at,
            )
            for semantic_element in semantic_scene.semantic_elements.elements
        )
        return MarketElements(
            source_semantic_scene_id=semantic_scene.id,
            source_visual_scene_id=semantic_scene.source_scene_id,
            source_frame=semantic_scene.source_frame,
            created_at=created_at,
            elements=elements,
        )

    def _labels_by_element(
        self,
        semantic_scene: SemanticScene,
    ) -> dict[str, tuple[str, ...]]:
        labels: dict[str, list[str]] = {}
        for label in semantic_scene.label_mapping.labels:
            labels.setdefault(label.semantic_element_id, []).append(label.label)
        return {
            semantic_element_id: tuple(element_labels)
            for semantic_element_id, element_labels in labels.items()
        }

    def _build_element(
        self,
        semantic_scene: SemanticScene,
        semantic_element: object,
        labels: tuple[str, ...],
        created_at: str,
    ) -> MarketElement:
        market_type = self._market_type_for(semantic_element)
        return MarketElement(
            id=f"market_element:{semantic_element.stable_key}",
            source_semantic_scene_id=semantic_scene.id,
            source_semantic_element_id=semantic_element.id,
            source_object_id=semantic_element.source_object_id,
            stable_key=semantic_element.stable_key,
            market_type=market_type,
            region_id=semantic_element.region_id,
            region_name=semantic_element.region_name,
            text=semantic_element.text,
            labels=labels,
            x=semantic_element.x,
            y=semantic_element.y,
            width=semantic_element.width,
            height=semantic_element.height,
            confidence=semantic_element.confidence,
            created_at=created_at,
            metadata={
                "source_semantic_type": semantic_element.semantic_type,
                "structural_only": True,
                "value_interpreted": False,
                "operation_interpreted": False,
                "ai": False,
                "llm": False,
            },
        )

    def _market_type_for(self, semantic_element: object) -> str:
        text = semantic_element.text.casefold()
        region_id = semantic_element.region_id.casefold()
        region_name = semantic_element.region_name.casefold()
        haystack = f"{text} {region_id} {region_name}"
        if self._has_token(haystack, self._PRICE_TOKENS):
            return "PRICE_REGION_CANDIDATE"
        if self._has_token(haystack, self._TIME_TOKENS):
            return "TIME_REGION_CANDIDATE"
        if self._has_token(haystack, self._ASSET_TOKENS):
            return "ASSET_REGION_CANDIDATE"
        return "MARKET_REGION_CANDIDATE"

    def _has_token(self, haystack: str, tokens: tuple[str, ...]) -> bool:
        return any(token in haystack for token in tokens)
