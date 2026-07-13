"""Capture Engine foundation bootstrap."""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from predixai.capture.capture_session import CaptureSession
from predixai.capture.capture_snapshot import (
    LinuxXwdWindowSnapshot,
    ManualScreenSnapshot,
)
from predixai.capture.capture_storage import CaptureStorage
from predixai.capture.capture_validator import CaptureValidator
from predixai.capture.snapshot_metadata import (
    AuthorizedCaptureResult,
    AuthorizedWindowContract,
    AuthorizedWindowObservation,
    SnapshotMetadata,
    WindowGeometry,
)
from predixai.capture.x11_display_topology import X11DisplayTopologyInspector
from predixai.core.config import AppConfig


@dataclass(frozen=True)
class CaptureEngineStatus:
    """Capture Engine bootstrap status."""

    enabled: bool
    session: CaptureSession
    storage: CaptureStorage


class _StopAuthorizedCapture(Exception):
    """Internal control flow after a fail-closed result has been built."""


class CaptureEngine:
    """Initializes screenshot capture infrastructure without capturing."""

    def __init__(
        self,
        config: AppConfig,
        *,
        window_detector: Any = None,
        linux_snapshot: LinuxXwdWindowSnapshot | None = None,
        topology_inspector: X11DisplayTopologyInspector | None = None,
        temporary_directory_factory: Any = tempfile.TemporaryDirectory,
    ) -> None:
        self.config = config
        self.validator = CaptureValidator()
        self.snapshot = ManualScreenSnapshot()
        if window_detector is None:
            # Lazy import preserves the existing capture/live package initialization order.
            from predixai.live.broker_window_detector import BrokerWindowDetector

            window_detector = BrokerWindowDetector()
        self.window_detector = window_detector
        self.linux_snapshot = linux_snapshot or LinuxXwdWindowSnapshot()
        self.topology_inspector = topology_inspector or X11DisplayTopologyInspector()
        self._temporary_directory_factory = temporary_directory_factory

    def bootstrap(self) -> CaptureEngineStatus:
        """Validate capture configuration and create a unique session."""
        storage = CaptureStorage.from_config(self.config)
        validation = self.validator.validate(storage)
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))

        return CaptureEngineStatus(
            enabled=bool(self.config.capture["enabled"]),
            session=CaptureSession(),
            storage=storage,
        )

    def capture_manual_snapshot(
        self,
        status: CaptureEngineStatus | None = None,
    ) -> SnapshotMetadata:
        """Capture one manual snapshot using an existing capture session."""
        active_status = status or self.bootstrap()
        captured_at = datetime.now().astimezone()
        output_path = active_status.storage.build_snapshot_path(captured_at)
        result = self.snapshot.capture(
            output_path=output_path,
            compression=active_status.storage.compression,
        )

        return SnapshotMetadata(
            session_id=active_status.session.session_id,
            captured_at=captured_at.isoformat(),
            resolution_width=result.width,
            resolution_height=result.height,
            file_path=output_path,
            file_size_bytes=result.file_size_bytes,
            image_format=active_status.storage.image_format,
        )

    def capture_authorized_linux_window(
        self,
        contract: AuthorizedWindowContract | Mapping[str, Any],
    ) -> AuthorizedCaptureResult:
        """Capture one authorized X11 client and publish only after post-validation."""
        try:
            authorization = (
                contract
                if isinstance(contract, AuthorizedWindowContract)
                else AuthorizedWindowContract.from_mapping(contract)
            )
            self._validate_contract(authorization)
        except Exception as exc:
            return self._failed_capture(f"CONTRACT_INVALID:{type(exc).__name__}")

        temporary = None
        temporary_root: Path | None = None
        result = self._failed_capture("CAPTURE_NOT_STARTED")
        xwd_executed = False
        identity_before = ""
        topology_before_hash = ""
        try:
            first = self._observe(authorization.window_id)
            topology_before = self.topology_inspector.read_snapshot()
            second = self._observe(authorization.window_id)
            identity_before = second.identity_hash
            topology_before_hash = topology_before.topology_hash
            reasons = self._gate_reasons(authorization, second)
            if first.identity_hash != second.identity_hash:
                reasons.append("PRECHECK_IDENTITY_NOT_STABLE")
            if not topology_before.gate_pass:
                reasons.append("PRECHECK_TOPOLOGY_NOT_AUTHORIZED")
            if reasons:
                result = self._failed_capture(
                    *reasons,
                    identity_hash_before=identity_before,
                    topology_hash_before=topology_before_hash,
                )
                raise _StopAuthorizedCapture

            temporary = self._temporary_directory_factory(
                prefix="predixai-authorized-xwd-"
            )
            temporary_root = Path(temporary.name).absolute()
            self._validate_temporary_root(temporary_root)
            output_path = temporary_root / "authorized-client.xwd"
            xwd_executed = True
            snapshot = self.linux_snapshot.capture(
                window_id=authorization.window_id,
                output_path=output_path,
                expected_width=authorization.geometry.width,
                expected_height=authorization.geometry.height,
            )

            after = self._observe(authorization.window_id)
            topology_after = self.topology_inspector.read_snapshot()
            post_reasons = self._gate_reasons(authorization, after)
            if after.identity_hash != identity_before:
                post_reasons.append("POSTCHECK_IDENTITY_CHANGED")
            if topology_after.topology_hash != topology_before_hash:
                post_reasons.append("POSTCHECK_TOPOLOGY_CHANGED")
            if not topology_after.gate_pass:
                post_reasons.append("POSTCHECK_TOPOLOGY_NOT_AUTHORIZED")
            if post_reasons:
                snapshot = None
                result = self._failed_capture(
                    *post_reasons,
                    xwd_executed=True,
                    identity_hash_before=identity_before,
                    identity_hash_after=after.identity_hash,
                    topology_hash_before=topology_before_hash,
                    topology_hash_after=topology_after.topology_hash,
                )
                raise _StopAuthorizedCapture

            result = AuthorizedCaptureResult(
                capture_allowed=True,
                capture_published=True,
                xwd_executed=True,
                source_state="SOURCE_CONFIRMED",
                fail_closed=False,
                width=snapshot.width,
                height=snapshot.height,
                pixel_format=snapshot.pixel_format,
                xwd_sha256=snapshot.xwd_sha256,
                pixel_sha256=snapshot.pixel_sha256,
                identity_hash_before=identity_before,
                identity_hash_after=after.identity_hash,
                topology_hash_before=topology_before_hash,
                topology_hash_after=topology_after.topology_hash,
                pixel_bytes=snapshot.pixel_bytes,
            )
        except _StopAuthorizedCapture:
            pass
        except Exception as exc:
            result = self._failed_capture(
                f"CAPTURE_ERROR:{type(exc).__name__}",
                xwd_executed=xwd_executed,
                identity_hash_before=identity_before,
                topology_hash_before=topology_before_hash,
            )
        finally:
            if temporary is not None:
                temporary.cleanup()
            removed = temporary_root is None or not temporary_root.exists()
            final_count = (
                0
                if temporary_root is None or not temporary_root.exists()
                else sum(1 for item in temporary_root.rglob("*") if item.is_file())
            )
            result = replace(
                result,
                temporary_file_count_final=final_count,
                temporary_directory_removed=removed,
            )
        return result

    @staticmethod
    def _validate_contract(contract: AuthorizedWindowContract) -> None:
        normalized = LinuxXwdWindowSnapshot.normalize_window_id(contract.window_id)
        if not normalized or normalized != contract.window_id.lower():
            raise ValueError("AUTHORIZED_WINDOW_ID must be canonical hexadecimal")
        if contract.window_pid <= 0 or not contract.process_name.strip():
            raise ValueError("authorized PID and process name are required")
        if contract.display_server.upper() != "X11":
            raise ValueError("controlled Linux capture requires X11")
        if not contract.title_pattern:
            raise ValueError("authorized title pattern is required")
        re.compile(contract.title_pattern)

    def _observe(self, window_id: str) -> AuthorizedWindowObservation:
        state = self.window_detector.inspect_explicit_linux_window(window_id)
        metadata = state.metadata
        if not metadata.get("detected"):
            raise RuntimeError("authorized X11 window was not detected")
        return AuthorizedWindowObservation(
            window_id=str(metadata.get("window_id") or ""),
            window_pid=int(metadata.get("window_pid") or 0),
            process_name=str(metadata.get("process_name") or ""),
            title=state.title,
            geometry=WindowGeometry(
                x=state.left,
                y=state.top,
                width=state.resolution_width,
                height=state.resolution_height,
            ),
            visible=bool(metadata.get("window_visible")),
            minimized=bool(metadata.get("window_minimized")),
            foreground=state.foreground,
        )

    @staticmethod
    def _gate_reasons(
        contract: AuthorizedWindowContract,
        observed: AuthorizedWindowObservation,
    ) -> list[str]:
        reasons: list[str] = []
        expected_id = LinuxXwdWindowSnapshot.normalize_window_id(contract.window_id)
        if observed.window_id != expected_id:
            reasons.append("AUTHORIZED_WINDOW_ID_MISMATCH")
        if observed.window_pid != contract.window_pid:
            reasons.append("AUTHORIZED_WINDOW_PID_MISMATCH")
        if observed.process_name != contract.process_name:
            reasons.append("AUTHORIZED_PROCESS_NAME_MISMATCH")
        if re.fullmatch(contract.title_pattern, observed.title) is None:
            reasons.append("AUTHORIZED_TITLE_MISMATCH")
        if observed.geometry != contract.geometry:
            reasons.append("AUTHORIZED_GEOMETRY_MISMATCH")
        if not observed.visible:
            reasons.append("WINDOW_NOT_VISIBLE")
        if observed.minimized:
            reasons.append("WINDOW_MINIMIZED")
        if contract.require_foreground and not observed.foreground:
            reasons.append("WINDOW_NOT_FOREGROUND")
        return reasons

    def _validate_temporary_root(self, path: Path) -> None:
        metadata = path.lstat()
        if not path.is_dir() or path.is_symlink():
            raise RuntimeError("temporary capture root is not a real directory")
        if metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
            raise RuntimeError("temporary capture root ownership or permissions are unsafe")
        real_runtime = self.config.resolve_project_path("data/runtime").resolve()
        try:
            path.relative_to(real_runtime)
        except ValueError:
            return
        raise RuntimeError("temporary capture path is inside real runtime")

    @staticmethod
    def _failed_capture(
        *reasons: str,
        xwd_executed: bool = False,
        identity_hash_before: str = "",
        identity_hash_after: str = "",
        topology_hash_before: str = "",
        topology_hash_after: str = "",
    ) -> AuthorizedCaptureResult:
        clean_reasons = tuple(reason for reason in reasons if reason)
        return AuthorizedCaptureResult(
            capture_allowed=False,
            capture_published=False,
            xwd_executed=xwd_executed,
            source_state="WAITING_SOURCE_OR_SOURCE_NOT_CONFIRMED",
            fail_closed=True,
            reasons=clean_reasons,
            identity_hash_before=identity_hash_before,
            identity_hash_after=identity_hash_after,
            topology_hash_before=topology_hash_before,
            topology_hash_after=topology_hash_after,
            pixel_bytes=None,
        )
