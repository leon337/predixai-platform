"""Manual snapshot metadata."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class SnapshotMetadata:
    """Metadata produced by one manual screen snapshot."""

    session_id: str
    captured_at: str
    resolution_width: int
    resolution_height: int
    file_path: Path
    file_size_bytes: int
    image_format: str

    def to_dict(self) -> dict[str, object]:
        """Return a serializable representation."""
        return {
            "session_id": self.session_id,
            "captured_at": self.captured_at,
            "resolution": {
                "width": self.resolution_width,
                "height": self.resolution_height,
            },
            "file_path": str(self.file_path),
            "file_size_bytes": self.file_size_bytes,
            "image_format": self.image_format,
        }


@dataclass(frozen=True)
class WindowGeometry:
    """Immutable X11 client geometry."""

    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("authorized geometry dimensions must be positive")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "WindowGeometry":
        required = ("x", "y", "width", "height")
        missing = tuple(key for key in required if key not in value)
        if missing:
            raise ValueError(f"missing geometry fields: {','.join(missing)}")
        return cls(*(int(value[key]) for key in required))

    def to_dict(self) -> dict[str, int]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


@dataclass(frozen=True)
class AuthorizedWindowContract:
    """Exact source authorization supplied to controlled Linux capture."""

    window_id: str
    window_pid: int
    process_name: str
    title_pattern: str
    geometry: WindowGeometry
    display_server: str = "X11"
    require_foreground: bool = True

    REQUIRED_MAPPING_FIELDS = (
        "AUTHORIZED_WINDOW_ID",
        "AUTHORIZED_WINDOW_PID",
        "AUTHORIZED_PROCESS_NAME",
        "AUTHORIZED_TITLE_PATTERN",
        "AUTHORIZED_GEOMETRY",
    )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AuthorizedWindowContract":
        missing = tuple(key for key in cls.REQUIRED_MAPPING_FIELDS if key not in value)
        if missing:
            raise ValueError(f"missing contract fields: {','.join(missing)}")
        geometry = value["AUTHORIZED_GEOMETRY"]
        if not isinstance(geometry, Mapping):
            raise ValueError("AUTHORIZED_GEOMETRY must be a mapping")
        return cls(
            window_id=str(value["AUTHORIZED_WINDOW_ID"]),
            window_pid=int(value["AUTHORIZED_WINDOW_PID"]),
            process_name=str(value["AUTHORIZED_PROCESS_NAME"]),
            title_pattern=str(value["AUTHORIZED_TITLE_PATTERN"]),
            geometry=WindowGeometry.from_mapping(geometry),
            display_server=str(value.get("DISPLAY_SERVER", "X11")),
            require_foreground=bool(value.get("WINDOW_FOREGROUND_REQUIRED", True)),
        )


@dataclass(frozen=True)
class AuthorizedWindowObservation:
    """One immutable targeted observation of the authorized X11 client."""

    window_id: str
    window_pid: int
    process_name: str
    title: str
    geometry: WindowGeometry
    visible: bool
    minimized: bool
    foreground: bool

    @property
    def identity_hash(self) -> str:
        material = json.dumps(
            {
                "window_id": self.window_id,
                "window_pid": self.window_pid,
                "process_name": self.process_name,
                "title": self.title,
                "geometry": self.geometry.to_dict(),
                "visible": self.visible,
                "minimized": self.minimized,
                "foreground": self.foreground,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuthorizedCaptureResult:
    """Fail-closed capture result; pixel data is never represented or serialized."""

    capture_allowed: bool
    capture_published: bool
    xwd_executed: bool
    source_state: str
    fail_closed: bool
    reasons: tuple[str, ...] = ()
    width: int = 0
    height: int = 0
    pixel_format: str = "NONE"
    xwd_sha256: str = ""
    pixel_sha256: str = ""
    identity_hash_before: str = ""
    identity_hash_after: str = ""
    topology_hash_before: str = ""
    topology_hash_after: str = ""
    temporary_file_count_final: int = 0
    temporary_directory_removed: bool = True
    temp_path_inside_real_runtime: bool = False
    pixel_bytes: bytes | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.capture_published and not self.capture_allowed:
            raise ValueError("capture cannot be published when it is not allowed")
        if self.capture_published and self.pixel_bytes is None:
            raise ValueError("approved capture must contain in-memory pixels")
        if not self.capture_published and self.pixel_bytes is not None:
            raise ValueError("failed capture cannot retain pixel bytes")

    @property
    def invalid_reading_published(self) -> bool:
        return False

    @property
    def last_valid_reading_preserved(self) -> bool:
        return True

    def to_dict(self) -> dict[str, object]:
        """Return safe metadata only; pixel bytes and temporary paths are omitted."""
        return {
            "CAPTURE_ALLOWED": "YES" if self.capture_allowed else "NO",
            "CAPTURE_PUBLISHED": "YES" if self.capture_published else "NO",
            "XWD_EXECUTED": "YES" if self.xwd_executed else "NO",
            "PIXEL_BYTES_RETURNED": "YES" if self.pixel_bytes is not None else "NO",
            "INVALID_READING_PUBLISHED": "NO",
            "LAST_VALID_READING_PRESERVED": "YES",
            "SOURCE_STATE": self.source_state,
            "FAIL_CLOSED": "YES" if self.fail_closed else "NO",
            "REASONS": self.reasons,
            "WIDTH": self.width,
            "HEIGHT": self.height,
            "PIXEL_FORMAT": self.pixel_format,
            "XWD_SHA256": self.xwd_sha256,
            "PIXEL_SHA256": self.pixel_sha256,
            "IDENTITY_HASH_BEFORE": self.identity_hash_before,
            "IDENTITY_HASH_AFTER": self.identity_hash_after,
            "TOPOLOGY_HASH_BEFORE": self.topology_hash_before,
            "TOPOLOGY_HASH_AFTER": self.topology_hash_after,
            "TEMP_CAPTURE_FILE_COUNT_FINAL": self.temporary_file_count_final,
            "TEMP_DIRECTORY_REMOVED": (
                "YES" if self.temporary_directory_removed else "NO"
            ),
            "TEMP_PATH_INSIDE_REAL_RUNTIME": (
                "YES" if self.temp_path_inside_real_runtime else "NO"
            ),
        }
