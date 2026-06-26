"""Text associated with one logical screen region."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from predixai.vision.visual.ocr_text_block import OCRTextBlock


@dataclass(frozen=True)
class RegionText:
    """Structured OCR text mapped to a logical screen region."""

    id: str
    region_id: str
    region_name: str
    description: str
    x: int
    y: int
    width: int
    height: int
    text: str
    confidence: float
    source_image_sha256: str
    source_image_path: str
    mapped_at: str
    blocks: tuple[OCRTextBlock, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def block_count(self) -> int:
        """Return the number of OCR blocks mapped to this region."""
        return len(self.blocks)

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "id": self.id,
            "region_id": self.region_id,
            "region_name": self.region_name,
            "description": self.description,
            "position": {
                "x": self.x,
                "y": self.y,
                "width": self.width,
                "height": self.height,
            },
            "text": self.text,
            "confidence": self.confidence,
            "source_image_sha256": self.source_image_sha256,
            "source_image_path": self.source_image_path,
            "mapped_at": self.mapped_at,
            "block_count": self.block_count,
            "blocks": [block.to_dict() for block in self.blocks],
            "metadata": dict(self.metadata),
        }
