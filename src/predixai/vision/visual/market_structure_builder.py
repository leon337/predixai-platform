"""Build the unified market structure."""

from __future__ import annotations

from datetime import datetime

from predixai.vision.visual.market_entity import MarketEntities
from predixai.vision.visual.market_entity_registry import MarketEntityRegistry
from predixai.vision.visual.market_scene import MarketScene
from predixai.vision.visual.market_structure import MarketStructure
from predixai.vision.visual.visual_snapshot import VisualSnapshot


class MarketStructureBuilder:
    """Consolidate visual, OCR and market metadata into one structure."""

    def build(
        self,
        visual_snapshot: VisualSnapshot,
        market_scene: MarketScene,
        market_entities: MarketEntities,
        entity_registry: MarketEntityRegistry,
        ocr_result: object,
    ) -> MarketStructure:
        """Build the market structure without interpretation."""
        created_at = datetime.now().astimezone().isoformat()
        return MarketStructure(
            id=f"market_structure:{market_scene.frame_sha256}",
            source_visual_snapshot_id=visual_snapshot.id,
            source_market_scene_id=market_scene.id,
            source_frame=market_scene.source_frame,
            frame_sha256=market_scene.frame_sha256,
            created_at=created_at,
            visual_snapshot=visual_snapshot,
            market_scene=market_scene,
            market_entities=market_entities,
            entity_registry=entity_registry,
            ocr_result=ocr_result,
            metadata={
                "structural_only": True,
                "pattern_recognition": False,
                "decision_making": False,
                "ai": False,
                "llm": False,
            },
        )
