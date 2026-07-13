"""Controlled, simulation-only Observer runtime for PredixAI Mobile V2."""

from __future__ import annotations

import copy
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, Optional

from .state_store import RuntimeStateStore


APPLICATION_ID = "MOBILE_V2"
OFF = "OFF"
STARTING = "STARTING"
ON_WAITING_SOURCE = "ON_WAITING_SOURCE"
ON_SIMULATED = "ON_SIMULATED"
PAUSED = "PAUSED"
ERROR = "ERROR"


class DeterministicSimulatedSource:
    """Return a deterministic, local sequence without external I/O."""

    DEFAULT_SEQUENCE = (
        {"asset": "SIM-EURUSD", "price": 1.10001},
        {"asset": "SIM-EURUSD", "price": 1.10002},
        {"asset": "SIM-EURUSD", "price": 1.10003},
        {"asset": "SIM-EURUSD", "price": 1.10004},
    )

    def __init__(self, sequence: Optional[Iterable[Dict[str, Any]]] = None) -> None:
        values = tuple(copy.deepcopy(tuple(sequence or self.DEFAULT_SEQUENCE)))
        if not values:
            raise ValueError("deterministic simulated source requires a sequence")
        self._sequence = values
        self._index = 0
        self._lock = threading.Lock()

    def next_reading(self, cycle: int) -> Dict[str, Any]:
        with self._lock:
            value = copy.deepcopy(self._sequence[self._index % len(self._sequence)])
            self._index += 1
        value["cycle"] = cycle
        value["source"] = "deterministic_simulation"
        return value


class ObserverRuntimeController:
    """Own exactly one non-daemon Observer thread for one Flask application."""

    def __init__(
        self,
        store: RuntimeStateStore,
        *,
        source: Optional[Any] = None,
        interval: float = 1.0,
        clock: Optional[Callable[[], Any]] = None,
        event_factory: Callable[[], threading.Event] = threading.Event,
        thread_factory: Callable[..., threading.Thread] = threading.Thread,
        join_timeout: float = 2.0,
    ) -> None:
        if interval < 0:
            raise ValueError("observer interval must be non-negative")
        if join_timeout <= 0:
            raise ValueError("observer join timeout must be positive")
        self.store = store
        self.source = source or DeterministicSimulatedSource()
        self.interval = interval
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.join_timeout = join_timeout
        self._event_factory = event_factory
        self._thread_factory = thread_factory
        self._command_lock = threading.RLock()
        self._stop_event = event_factory()
        self._resume_event = event_factory()
        self._thread: Optional[threading.Thread] = None
        self._observer_state = OFF

    @property
    def thread(self) -> Optional[threading.Thread]:
        with self._command_lock:
            return self._thread

    @property
    def thread_alive(self) -> bool:
        with self._command_lock:
            return bool(self._thread and self._thread.is_alive())

    @property
    def active_thread_count(self) -> int:
        return 1 if self.thread_alive else 0

    def _now_iso(self) -> str:
        value = self.clock()
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.isoformat()
        return str(value)

    def _persist(
        self,
        observer_state: str,
        *,
        reading: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        clear_current_reading: bool = False,
    ) -> Dict[str, Any]:
        now = self._now_iso()

        def mutate(state: Dict[str, Any]) -> Dict[str, Any]:
            observer = state["observer"]
            state["observer_state"] = observer_state
            state["observer_updated_at"] = now
            state["observer_error"] = error
            observer["status"] = observer_state
            observer["running"] = observer_state in {
                STARTING,
                ON_WAITING_SOURCE,
                ON_SIMULATED,
                PAUSED,
            }
            observer["pid"] = None
            observer["last_error"] = error
            if observer_state == STARTING:
                observer["started_at"] = now
                observer["stopped_at"] = None
                state["status"] = "observer_starting"
            elif observer_state == ON_WAITING_SOURCE:
                state["status"] = "observer_waiting_source"
                state["reading"]["status"] = "waiting_source"
                state["reading"]["source"] = "deterministic_simulation"
            elif observer_state == ON_SIMULATED:
                state["status"] = "observer_simulated"
            elif observer_state == PAUSED:
                state["status"] = "observer_paused"
            elif observer_state == ERROR:
                state["status"] = "observer_error"
            elif observer_state == OFF:
                state["status"] = "idle"
                observer["stopped_at"] = now

            if reading is not None:
                normalized_reading = copy.deepcopy(reading)
                normalized_reading["captured_at"] = now
                normalized_reading["status"] = "simulated_reading"
                normalized_reading["source"] = "deterministic_simulation"
                state["observer_cycle"] = int(normalized_reading["cycle"])
                state["observer_last_reading"] = copy.deepcopy(normalized_reading)
                state["reading"].update(normalized_reading)
            if clear_current_reading:
                state["reading"].update(
                    {
                        "status": "no_active_reading",
                        "asset": None,
                        "price": None,
                        "captured_at": None,
                        "source": "none",
                    }
                )
                state["signal"].update(
                    {
                        "status": "aguardando_leitura",
                        "direction": "NEUTRO",
                        "confidence": None,
                    }
                )
            return state

        persisted = self.store.update_state(mutate)
        self._observer_state = observer_state
        return persisted

    def _result(
        self,
        *,
        changed: bool,
        error: Optional[str] = None,
        state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        current = state or self.store.read_state()
        return {
            "application_id": APPLICATION_ID,
            "observer_state": current["observer_state"],
            "observer_cycle": current["observer_cycle"],
            "changed": changed,
            "error": error,
            "state": current,
        }

    def start(self) -> Dict[str, Any]:
        with self._command_lock:
            if self._thread is not None and self._thread.is_alive():
                return self._result(changed=False)
            if self._observer_state == ERROR:
                return self._result(
                    changed=False,
                    error="observer em ERROR; execute stop antes de reiniciar",
                )
            self._stop_event = self._event_factory()
            self._resume_event = self._event_factory()
            self._resume_event.set()
            state = self._persist(STARTING)
            thread = self._thread_factory(
                target=self._run,
                name=f"predixai-mobile-v2-observer-{id(self)}",
                daemon=False,
            )
            self._thread = thread
            thread.start()
            return self._result(changed=True, state=state)

    def pause(self) -> Dict[str, Any]:
        with self._command_lock:
            if self._observer_state == PAUSED:
                return self._result(changed=False)
            if self._observer_state != ON_SIMULATED:
                return self._result(
                    changed=False,
                    error=f"pause exige ON_SIMULATED; estado atual={self._observer_state}",
                )
            self._resume_event.clear()
            return self._result(changed=True, state=self._persist(PAUSED))

    def resume(self) -> Dict[str, Any]:
        with self._command_lock:
            if self._observer_state != PAUSED:
                return self._result(
                    changed=False,
                    error=f"resume exige PAUSED; estado atual={self._observer_state}",
                )
            state = self._persist(ON_SIMULATED)
            self._resume_event.set()
            return self._result(changed=True, state=state)

    def stop(self) -> Dict[str, Any]:
        with self._command_lock:
            thread = self._thread
            if self._observer_state == OFF and not (thread and thread.is_alive()):
                return self._result(changed=False)
            self._stop_event.set()
            self._resume_event.set()

        if thread is not None and thread.is_alive():
            thread.join(timeout=self.join_timeout)

        with self._command_lock:
            if thread is not None and thread.is_alive():
                state = self._persist(
                    ERROR,
                    error="observer thread não encerrou dentro do timeout controlado",
                )
                return self._result(
                    changed=False,
                    error=state["observer_error"],
                    state=state,
                )
            self._thread = None
            state = self._persist(OFF, clear_current_reading=True)
            return self._result(changed=True, state=state)

    def _run(self) -> None:
        try:
            with self._command_lock:
                if self._stop_event.is_set():
                    return
                self._persist(ON_WAITING_SOURCE)

            while not self._stop_event.is_set():
                self._resume_event.wait()
                if self._stop_event.is_set():
                    break

                with self._command_lock:
                    next_cycle = self.store.read_state()["observer_cycle"] + 1

                try:
                    reading = self.source.next_reading(next_cycle)
                except Exception as exc:
                    message = f"simulated source failure: {type(exc).__name__}: {exc}"
                    with self._command_lock:
                        self._persist(ERROR, error=message)
                    return

                with self._command_lock:
                    if self._stop_event.is_set():
                        break
                    if self._observer_state == PAUSED:
                        continue
                    self._persist(ON_SIMULATED, reading=reading)

                if self._stop_event.wait(self.interval):
                    break
        except Exception as exc:
            message = f"observer runtime failure: {type(exc).__name__}: {exc}"
            with self._command_lock:
                self._persist(ERROR, error=message)


__all__ = [
    "APPLICATION_ID",
    "DeterministicSimulatedSource",
    "ERROR",
    "OFF",
    "ON_SIMULATED",
    "ON_WAITING_SOURCE",
    "ObserverRuntimeController",
    "PAUSED",
    "STARTING",
]
