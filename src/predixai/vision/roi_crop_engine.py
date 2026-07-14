"""ROI Crop Engine foundation."""

from __future__ import annotations

from datetime import datetime
import hashlib
from io import BytesIO

from PIL import Image, ImageOps

from predixai.vision.image_buffer import ImageBuffer
from predixai.vision.roi import RegionOfInterest
from predixai.vision.roi_crop import RGB24Crop, ROICrop
from predixai.vision.roi_crop_validator import ROICropValidator
from predixai.vision.roi_registry import ROIRegistry


class ROICropEngine:
    """Create ROI crop metadata without extracting image content."""

    def __init__(self) -> None:
        self.validator = ROICropValidator()

    def create_crop(
        self,
        roi: RegionOfInterest,
        image_buffer: ImageBuffer,
    ) -> ROICrop:
        """Create one ROI crop metadata object from validated coordinates."""
        validation = self.validator.validate(roi, image_buffer)
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))

        return ROICrop(
            roi_id=roi.id,
            roi_name=roi.name,
            x=roi.x,
            y=roi.y,
            width=roi.width,
            height=roi.height,
            source_frame=image_buffer.filename,
            created_at=datetime.now().astimezone().isoformat(),
        )

    def create_crops(
        self,
        registry: ROIRegistry,
        image_buffer: ImageBuffer,
    ) -> tuple[ROICrop, ...]:
        """Create ROI crop metadata for all registered ROIs."""
        return tuple(
            self.create_crop(roi, image_buffer)
            for roi in registry.rois
        )

    def crop_rgb24(
        self,
        *,
        roi: RegionOfInterest,
        pixel_bytes: bytes,
        image_width: int,
        image_height: int,
    ) -> RGB24Crop:
        """Extract one strict RGB24 crop without paths or silent clamping."""
        validation = self.validator.validate_dimensions(
            roi=roi,
            image_width=image_width,
            image_height=image_height,
        )
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))
        expected_size = image_width * image_height * 3
        if len(pixel_bytes) != expected_size:
            raise ValueError("RGB24 source byte count contradicts its dimensions")
        source_stride = image_width * 3
        target = bytearray(roi.width * roi.height * 3)
        target_index = 0
        for row in range(roi.y, roi.y + roi.height):
            start = row * source_stride + roi.x * 3
            end = start + roi.width * 3
            row_bytes = pixel_bytes[start:end]
            target[target_index:target_index + len(row_bytes)] = row_bytes
            target_index += len(row_bytes)
        result = bytes(target)
        return RGB24Crop(
            roi_id=roi.id,
            x=roi.x,
            y=roi.y,
            width=roi.width,
            height=roi.height,
            sha256=hashlib.sha256(result).hexdigest(),
            pixel_bytes=result,
        )

    @staticmethod
    def preprocess_png(
        crop: RGB24Crop,
        *,
        scale: int = 3,
        threshold: int | None = None,
    ) -> bytes:
        """Build deterministic grayscale PNG bytes for a temporary OCR input."""
        if scale < 1 or scale > 6:
            raise ValueError("preprocessing scale must be between 1 and 6")
        if threshold is not None and not 0 <= threshold <= 255:
            raise ValueError("preprocessing threshold must be between 0 and 255")
        image = Image.frombytes("RGB", (crop.width, crop.height), crop.pixel_bytes)
        image = image.resize(
            (crop.width * scale, crop.height * scale),
            Image.Resampling.NEAREST,
        )
        image = ImageOps.autocontrast(ImageOps.grayscale(image))
        if threshold is not None:
            image = image.point(lambda value: 255 if value >= threshold else 0)
        output = BytesIO()
        image.save(output, format="PNG", optimize=False, compress_level=6)
        return output.getvalue()
