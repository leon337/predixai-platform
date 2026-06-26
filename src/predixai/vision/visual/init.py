"""Visual intelligence foundation entrypoint."""

from predixai.vision.visual.ocr_parser import OCRParsedText, OCRParser
from predixai.vision.visual.ocr_text_block import OCRTextBlock
from predixai.vision.visual.region_text import RegionText
from predixai.vision.visual.region_text_mapper import (
    RegionTextMapper,
    RegionTextMapping,
)
from predixai.vision.visual.structured_ocr_builder import StructuredOCRBuilder
from predixai.vision.visual.structured_ocr_result import StructuredOCRResult
from predixai.vision.visual.visual_benchmark import (
    VisualBenchmark,
    VisualBenchmarkResult,
    VisualBenchmarkRun,
)
from predixai.vision.visual.visual_snapshot import VisualSnapshot
from predixai.vision.visual.visual_snapshot_builder import VisualSnapshotBuilder

__all__ = [
    "OCRParsedText",
    "OCRParser",
    "OCRTextBlock",
    "RegionText",
    "RegionTextMapper",
    "RegionTextMapping",
    "StructuredOCRBuilder",
    "StructuredOCRResult",
    "VisualBenchmark",
    "VisualBenchmarkResult",
    "VisualBenchmarkRun",
    "VisualSnapshot",
    "VisualSnapshotBuilder",
]
