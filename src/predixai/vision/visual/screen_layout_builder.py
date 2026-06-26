"""Build structured screen layouts."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.visual.screen_element import ScreenElements
from predixai.vision.visual.screen_layout import ScreenLayout, ScreenLayoutNode
from predixai.vision.visual.visual_snapshot import VisualSnapshot


class ScreenLayoutBuilder:
    """Create a deterministic layout tree from screen elements."""

    def build(
        self,
        visual_snapshot: VisualSnapshot,
        screen_elements: ScreenElements,
    ) -> ScreenLayout:
        """Build one layout tree preserving positions and hierarchy."""
        created_at = datetime.now().astimezone().isoformat()
        root_id = f"layout_node:{visual_snapshot.frame_sha256}:root"
        child_nodes = tuple(
            self._build_element_node(root_id, element)
            for element in sorted(
                screen_elements.elements,
                key=lambda item: (item.y, item.x, item.id),
            )
        )
        root_node = ScreenLayoutNode(
            id=root_id,
            parent_id="",
            node_type="SCREEN",
            element_id="",
            x=0,
            y=0,
            width=visual_snapshot.width,
            height=visual_snapshot.height,
            children=tuple(node.id for node in child_nodes),
            metadata={
                "source_snapshot_id": visual_snapshot.id,
                "source_frame": visual_snapshot.source_frame,
            },
        )
        return ScreenLayout(
            id=f"screen_layout:{visual_snapshot.frame_sha256}",
            source_snapshot_id=visual_snapshot.id,
            source_frame=visual_snapshot.source_frame,
            created_at=created_at,
            root_id=root_id,
            nodes=(root_node, *child_nodes),
            metadata={
                "element_count": screen_elements.count,
                "hierarchy": "root_screen_with_positioned_children",
                "structured_ocr_compatible": True,
            },
        )

    def _build_element_node(
        self,
        root_id: str,
        element: object,
    ) -> ScreenLayoutNode:
        return ScreenLayoutNode(
            id=f"layout_node:{element.id}",
            parent_id=root_id,
            node_type="ELEMENT",
            element_id=element.id,
            x=element.x,
            y=element.y,
            width=element.width,
            height=element.height,
            metadata={
                "element_type": element.element_type,
                "source_region_id": element.source_region_id,
            },
        )
