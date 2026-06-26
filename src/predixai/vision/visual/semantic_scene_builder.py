"""Build deterministic semantic scenes."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.visual.semantic_element import SemanticElements
from predixai.vision.visual.semantic_label import SemanticLabelMapping
from predixai.vision.visual.semantic_scene import SemanticScene
from predixai.vision.visual.visual_scene import VisualScene


class SemanticSceneBuilder:
    """Consolidate visual scene, semantic elements and labels."""

    def build(
        self,
        visual_scene: VisualScene,
        semantic_elements: SemanticElements,
        label_mapping: SemanticLabelMapping,
    ) -> SemanticScene:
        """Build one semantic scene without interpreting decisions."""
        created_at = datetime.now().astimezone().isoformat()
        return SemanticScene(
            id=f"semantic_scene:{visual_scene.frame_sha256}",
            source_scene_id=visual_scene.id,
            source_frame=visual_scene.source_frame,
            frame_sha256=visual_scene.frame_sha256,
            created_at=created_at,
            visual_scene=visual_scene,
            semantic_elements=semantic_elements,
            label_mapping=label_mapping,
            metadata={
                "entity_count": semantic_elements.count,
                "label_count": label_mapping.count,
                "region_count": semantic_elements.region_count,
                "deterministic": True,
                "ai": False,
                "llm": False,
                "decision_making": False,
            },
        )
