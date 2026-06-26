"""Build screen object registries."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256

from predixai.vision.visual.screen_element import ScreenElement, ScreenElements
from predixai.vision.visual.screen_object import ScreenObject, ScreenObjectRegistry
from predixai.vision.visual.visual_snapshot import VisualSnapshot


class ScreenObjectRegistryBuilder:
    """Register screen objects from deterministic screen elements."""

    def build(
        self,
        visual_snapshot: VisualSnapshot,
        screen_elements: ScreenElements,
    ) -> ScreenObjectRegistry:
        """Build one registry of screen objects."""
        created_at = datetime.now().astimezone().isoformat()
        objects = tuple(
            self._build_object(visual_snapshot, created_at, element)
            for element in screen_elements.elements
        )
        return ScreenObjectRegistry(
            id=f"screen_object_registry:{visual_snapshot.frame_sha256}",
            source_snapshot_id=visual_snapshot.id,
            source_frame=visual_snapshot.source_frame,
            created_at=created_at,
            objects=objects,
        )

    def _build_object(
        self,
        visual_snapshot: VisualSnapshot,
        created_at: str,
        element: ScreenElement,
    ) -> ScreenObject:
        stable_key = self._stable_key(element)
        return ScreenObject(
            id=f"screen_object:{stable_key}",
            stable_key=stable_key,
            element_id=element.id,
            object_type=element.element_type,
            x=element.x,
            y=element.y,
            width=element.width,
            height=element.height,
            first_seen_snapshot_id=visual_snapshot.id,
            last_seen_snapshot_id=visual_snapshot.id,
            observation_count=1,
            created_at=created_at,
            metadata={
                "source_region_id": element.source_region_id,
                "source_region_name": element.source_region_name,
                "source": element.source,
                "text_signature": self._text_signature(element.text),
                "reuse_prepared": True,
                "ai_classification": False,
            },
        )

    def _stable_key(self, element: ScreenElement) -> str:
        raw_key = "|".join(
            (
                element.element_type,
                element.source_region_id,
                str(element.x),
                str(element.y),
                str(element.width),
                str(element.height),
            )
        )
        return sha256(raw_key.encode("utf-8")).hexdigest()[:16]

    def _text_signature(self, text: str) -> str:
        return sha256(text.encode("utf-8")).hexdigest()[:16]
