"""Build unified visual scenes."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.visual.screen_element import ScreenElements
from predixai.vision.visual.screen_layout import ScreenLayout
from predixai.vision.visual.screen_object import ScreenObjectRegistry
from predixai.vision.visual.visual_scene import VisualScene
from predixai.vision.visual.visual_snapshot import VisualSnapshot


class VisualSceneBuilder:
    """Create a unified screen scene without interpretation."""

    def build(
        self,
        visual_snapshot: VisualSnapshot,
        screen_elements: ScreenElements,
        screen_layout: ScreenLayout,
        object_registry: ScreenObjectRegistry,
    ) -> VisualScene:
        """Build one visual scene from existing structured metadata."""
        created_at = datetime.now().astimezone().isoformat()
        return VisualScene(
            id=f"visual_scene:{visual_snapshot.frame_sha256}",
            source_snapshot_id=visual_snapshot.id,
            source_frame=visual_snapshot.source_frame,
            frame_sha256=visual_snapshot.frame_sha256,
            created_at=created_at,
            visual_snapshot=visual_snapshot,
            layout=screen_layout,
            object_registry=object_registry,
            metadata={
                "element_count": screen_elements.count,
                "layout_node_count": screen_layout.node_count,
                "object_count": object_registry.count,
                "region_count": visual_snapshot.structured_ocr.total_regions,
                "semantic_interpretation": False,
                "decision_making": False,
                "ai": False,
            },
        )
