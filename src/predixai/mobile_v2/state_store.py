"""Runtime state store for PredixAI Trader Mobile V2.

Rules:
- The runtime JSON file is operational data and must not be versioned.
- The initial state is produced by create_default_state().
- Writes are protected by a Linux fcntl lock.
- Writes use temp file + JSON validation + atomic rename.
"""

from __future__ import annotations

import copy
import fcntl
import json
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, Optional


class RuntimeStateValidationError(ValueError):
    """Raised when a runtime state payload is structurally invalid."""


class RuntimeStateLockTimeout(TimeoutError):
    """Raised when the state lock cannot be acquired in time."""


StateDict = Dict[str, Any]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_root() -> Path:
    # src/predixai/mobile_v2/state_store.py -> repo root
    return Path(__file__).resolve().parents[3]


def create_default_state() -> StateDict:
    """Create the canonical initial Mobile V2 runtime state.

    This function replaces committing data/runtime/mobile_v2_state.json.
    Runtime files are created only at execution time.
    """
    now = _utc_now_iso()
    return {
        "schema_version": "mobile_v2_state_v1",
        "status": "idle",
        "updated_at": now,
        "observer": {
            "status": "OFF",
            "running": False,
            "pid": None,
            "last_error": None,
            "started_at": None,
            "stopped_at": None,
        },
        "reading": {
            "status": "no_active_reading",
            "asset": None,
            "price": None,
            "captured_at": None,
            "source": "none",
        },
        "session": {
            "status": "not_created",
            "simulation_only": True,
            "orders_enabled": False,
            "real_money_enabled": False,
            "auto_click_enabled": False,
            "broker_login_enabled": False,
            "credentials_allowed": False,
        },
        "signal": {
            "status": "aguardando_leitura",
            "direction": "NEUTRO",
            "confidence": None,
            "reason": None,
            "strategy": None,
        },
        "operation": {
            "status": "none",
            "operation_id": None,
            "result": None,
        },
        "history": {
            "count": 0,
            "last_event_id": None,
        },
    }


_REQUIRED_TOP_LEVEL = {
    "schema_version",
    "status",
    "updated_at",
    "observer",
    "reading",
    "session",
    "signal",
    "operation",
    "history",
}


def validate_state(state: StateDict) -> StateDict:
    """Validate and return a deep copy of the state."""
    if not isinstance(state, dict):
        raise RuntimeStateValidationError("state must be a dict")

    missing = sorted(_REQUIRED_TOP_LEVEL.difference(state.keys()))
    if missing:
        raise RuntimeStateValidationError(f"missing top-level fields: {missing}")

    if state.get("schema_version") != "mobile_v2_state_v1":
        raise RuntimeStateValidationError("invalid schema_version")

    for key in ("observer", "reading", "session", "signal", "operation", "history"):
        if not isinstance(state.get(key), dict):
            raise RuntimeStateValidationError(f"{key} must be a dict")

    session = state["session"]
    required_safety = {
        "simulation_only": True,
        "orders_enabled": False,
        "real_money_enabled": False,
        "auto_click_enabled": False,
        "broker_login_enabled": False,
        "credentials_allowed": False,
    }
    for key, expected in required_safety.items():
        if session.get(key) is not expected:
            raise RuntimeStateValidationError(
                f"safety field {key} must be {expected!r}"
            )

    return copy.deepcopy(state)


class RuntimeStateStore:
    """Small atomic JSON state store with Linux file locking."""

    def __init__(
        self,
        state_path: Optional[Path | str] = None,
        lock_path: Optional[Path | str] = None,
    ) -> None:
        default_state_path = _repo_root() / "data" / "runtime" / "mobile_v2_state.json"
        self.state_path = Path(state_path) if state_path else default_state_path
        self.lock_path = Path(lock_path) if lock_path else self.state_path.with_suffix(
            self.state_path.suffix + ".lock"
        )

    @contextmanager
    def _exclusive_lock(self, timeout: float = 5.0) -> Iterator[None]:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = self.lock_path.open("a+", encoding="utf-8")
        started = time.monotonic()

        try:
            while True:
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError as exc:
                    if time.monotonic() - started >= timeout:
                        raise RuntimeStateLockTimeout(
                            f"could not acquire state lock within {timeout:.2f}s"
                        ) from exc
                    time.sleep(0.02)

            yield
        finally:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            finally:
                lock_file.close()

    def read_state(self, *, lock_timeout: float = 5.0) -> StateDict:
        """Read the runtime state or return a default state when no file exists."""
        with self._exclusive_lock(timeout=lock_timeout):
            if not self.state_path.exists():
                return create_default_state()

            with self.state_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)

            return validate_state(data)

    def write_state(self, state: StateDict, *, lock_timeout: float = 5.0) -> StateDict:
        """Write state atomically under lock."""
        validated = validate_state(state)
        validated["updated_at"] = _utc_now_iso()

        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        with self._exclusive_lock(timeout=lock_timeout):
            return self._write_unlocked(validated)

    def update_state(
        self,
        mutator: Callable[[StateDict], StateDict],
        *,
        lock_timeout: float = 5.0,
    ) -> StateDict:
        """Read, mutate and write state while holding one lock."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        with self._exclusive_lock(timeout=lock_timeout):
            if self.state_path.exists():
                with self.state_path.open("r", encoding="utf-8") as handle:
                    current = validate_state(json.load(handle))
            else:
                current = create_default_state()

            next_state = mutator(copy.deepcopy(current))
            validated = validate_state(next_state)
            validated["updated_at"] = _utc_now_iso()
            return self._write_unlocked(validated)

    def _write_unlocked(self, state: StateDict) -> StateDict:
        tmp_name = (
            f".{self.state_path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
        )
        tmp_path = self.state_path.with_name(tmp_name)

        try:
            with tmp_path.open("w", encoding="utf-8") as handle:
                json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())

            with tmp_path.open("r", encoding="utf-8") as handle:
                validate_state(json.load(handle))

            os.replace(tmp_path, self.state_path)
            return copy.deepcopy(state)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
