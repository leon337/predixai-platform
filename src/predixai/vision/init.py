"""Vision Engine foundation entrypoint."""

from predixai.vision.frame import Frame
from predixai.vision.image_buffer import ImageBuffer
from predixai.vision.image_loader import ImageLoader
from predixai.vision.regions import (
    ProfileBindingLoader,
    Region,
    RegionManager,
    RegionProfileBinding,
    RegionRegistry,
    ScreenProfileBinding,
)
from predixai.vision.roi import RegionOfInterest
from predixai.vision.roi_crop import ROICrop
from predixai.vision.roi_crop_engine import ROICropEngine
from predixai.vision.roi_crop_exporter import ROICropExporter
from predixai.vision.roi_crop_storage import ROICropExport, ROICropStorage
from predixai.vision.roi_manager import ROIManager
from predixai.vision.roi_registry import ROIRegistry
from predixai.vision.vision_engine import VisionEngine
from predixai.vision.visual import (
    OCRParsedText,
    OCRParser,
    OCRTextBlock,
    RegionText,
    RegionTextMapper,
    RegionTextMapping,
    StructuredOCRBuilder,
    StructuredOCRResult,
    VisualBenchmark,
    VisualBenchmarkResult,
    VisualBenchmarkRun,
    VisualSnapshot,
    VisualSnapshotBuilder,
)

__all__ = [
    "Frame",
    "ImageBuffer",
    "ImageLoader",
    "ProfileBindingLoader",
    "Region",
    "RegionManager",
    "RegionProfileBinding",
    "RegionRegistry",
    "ScreenProfileBinding",
    "RegionOfInterest",
    "ROICrop",
    "ROICropEngine",
    "ROICropExport",
    "ROICropExporter",
    "ROICropStorage",
    "ROIManager",
    "ROIRegistry",
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
    "VisionEngine",
]
