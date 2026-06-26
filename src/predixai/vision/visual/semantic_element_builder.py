"""Build semantic elements from visual scenes."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.visual.semantic_element import (
    SemanticElement,
    SemanticElements,
)
from predixai.vision.visual.visual_scene import VisualScene


class SemanticElementBuilder:
    """Derive semantic elements from screen objects and visual scene data."""

    def build(self, visual_scene: VisualScene) -> SemanticElements:
        """Build semantic elements without AI or LLM classification."""
        created_at = datetime.now().astimezone().isoformat()
        regions_by_id = {
            region.region_id: region
            for region in visual_scene.visual_snapshot.structured_ocr.regions
        }
        elements = tuple(
            self._build_element(visual_scene, created_at, screen_object, regions_by_id)
            for screen_object in visual_scene.object_registry.objects
        )
        return SemanticElements(
            source_scene_id=visual_scene.id,
            source_frame=visual_scene.source_frame,
            created_at=created_at,
            elements=elements,
        )

    def _build_element(
        self,
        visual_scene: VisualScene,
        created_at: str,
        screen_object: object,
        regions_by_id: dict[str, object],
    ) -> SemanticElement:
        region_id = str(screen_object.metadata.get("source_region_id", ""))
        region = regions_by_id.get(region_id)
        text = region.text if region is not None else ""
        confidence = region.confidence if region is not None else 0.0
        region_name = (
            region.region_name
            if region is not None
            else str(screen_object.metadata.get("source_region_name", ""))
        )
        return SemanticElement(
            id=f"semantic_element:{screen_object.stable_key}",
            source_scene_id=visual_scene.id,
            source_object_id=screen_object.id,
            source_element_id=screen_object.element_id,
            stable_key=screen_object.stable_key,
            semantic_type="INTERFACE_OBJECT",
            region_id=region_id,
            region_name=region_name,
            text=text,
            x=screen_object.x,
            y=screen_object.y,
            width=screen_object.width,
            height=screen_object.height,
            confidence=confidence,
            created_at=created_at,
            metadata={
                "source_object_type": screen_object.object_type,
                "source_object_stable_key": screen_object.stable_key,
                "source_scene_id": visual_scene.id,
                "source_frame_sha256": visual_scene.frame_sha256,
                "ai": False,
                "llm": False,
            },
        )
