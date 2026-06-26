"""Map parsed OCR text to logical screen regions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from predixai.vision.regions import RegionRegistry
from predixai.vision.roi_crop_storage import ROICropExport
from predixai.vision.visual.ocr_parser import OCRParsedText
from predixai.vision.visual.region_text import RegionText


@dataclass(frozen=True)
class RegionTextMapping:
    """Result of associating parsed OCR text with screen regions."""

    mapped_at: str
    texts: tuple[RegionText, ...]

    @property
    def count(self) -> int:
        """Return the number of mapped region texts."""
        return len(self.texts)

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "mapped_at": self.mapped_at,
            "count": self.count,
            "texts": [region_text.to_dict() for region_text in self.texts],
        }


class RegionTextMapper:
    """Associate parsed OCR payloads with their logical screen regions."""

    def map_texts(
        self,
        parsed_texts: tuple[OCRParsedText, ...],
        region_registry: RegionRegistry,
        roi_exports: tuple[ROICropExport, ...],
    ) -> RegionTextMapping:
        """Map each OCR text payload to the corresponding region."""
        mapped_at = datetime.now().astimezone().isoformat()
        regions_by_id = {region.id: region for region in region_registry.regions}
        exports_by_path = {
            str(roi_export.output_path): roi_export
            for roi_export in roi_exports
        }

        region_texts: list[RegionText] = []
        for parsed_text in parsed_texts:
            roi_export = exports_by_path.get(parsed_text.source_image_path)
            if roi_export is None:
                continue

            region = regions_by_id.get(roi_export.roi_id)
            if region is None:
                continue

            region_texts.append(
                RegionText(
                    id=f"{region.id}:{parsed_text.source_image_sha256}",
                    region_id=region.id,
                    region_name=region.name,
                    description=region.description,
                    x=region.x,
                    y=region.y,
                    width=region.width,
                    height=region.height,
                    text=self._join_blocks(parsed_text),
                    confidence=parsed_text.confidence,
                    source_image_sha256=parsed_text.source_image_sha256,
                    source_image_path=parsed_text.source_image_path,
                    mapped_at=mapped_at,
                    blocks=parsed_text.blocks,
                    metadata={
                        "roi_id": roi_export.roi_id,
                        "roi_name": roi_export.roi_name,
                        "profile_id": region_registry.profile_id,
                        "registry_version": region_registry.version,
                    },
                )
            )

        return RegionTextMapping(
            mapped_at=mapped_at,
            texts=tuple(region_texts),
        )

    def _join_blocks(self, parsed_text: OCRParsedText) -> str:
        if parsed_text.blocks:
            return " ".join(block.text for block in parsed_text.blocks)
        return parsed_text.raw_text
