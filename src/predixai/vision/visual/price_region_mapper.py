"""Map structural price regions without reading price values."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from predixai.vision.visual.market_element import MarketElement, MarketElements


@dataclass(frozen=True)
class PriceRegion:
    """A region structurally associated with price metadata."""

    id: str
    market_element_id: str
    region_id: str
    region_name: str
    x: int
    y: int
    width: int
    height: int
    mapped_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "id": self.id,
            "market_element_id": self.market_element_id,
            "region_id": self.region_id,
            "region_name": self.region_name,
            "position": {
                "x": self.x,
                "y": self.y,
                "width": self.width,
                "height": self.height,
            },
            "mapped_at": self.mapped_at,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class PriceRegionMapping:
    """Collection of structural price regions."""

    source_semantic_scene_id: str
    created_at: str
    regions: tuple[PriceRegion, ...]

    @property
    def count(self) -> int:
        """Return the number of price regions."""
        return len(self.regions)

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "source_semantic_scene_id": self.source_semantic_scene_id,
            "created_at": self.created_at,
            "count": self.count,
            "regions": [region.to_dict() for region in self.regions],
        }


class PriceRegionMapper:
    """Map price regions using deterministic metadata rules only."""

    _PRICE_TOKENS = ("preco", "price", "valor", "cotacao", "quote")

    def map_regions(self, market_elements: MarketElements) -> PriceRegionMapping:
        """Map structural price regions without parsing values."""
        created_at = datetime.now().astimezone().isoformat()
        regions = tuple(
            self._to_price_region(element, created_at)
            for element in market_elements.elements
            if self._is_price_candidate(element)
        )
        return PriceRegionMapping(
            source_semantic_scene_id=market_elements.source_semantic_scene_id,
            created_at=created_at,
            regions=regions,
        )

    def _is_price_candidate(self, element: MarketElement) -> bool:
        if element.market_type == "PRICE_REGION_CANDIDATE":
            return True
        haystack = f"{element.region_id} {element.region_name} {element.text}".casefold()
        return any(token in haystack for token in self._PRICE_TOKENS)

    def _to_price_region(
        self,
        element: MarketElement,
        mapped_at: str,
    ) -> PriceRegion:
        return PriceRegion(
            id=f"price_region:{element.stable_key}",
            market_element_id=element.id,
            region_id=element.region_id,
            region_name=element.region_name,
            x=element.x,
            y=element.y,
            width=element.width,
            height=element.height,
            mapped_at=mapped_at,
            metadata={
                "source_market_type": element.market_type,
                "value_interpreted": False,
                "operation_interpreted": False,
                "deterministic": True,
                "ai": False,
                "llm": False,
            },
        )
