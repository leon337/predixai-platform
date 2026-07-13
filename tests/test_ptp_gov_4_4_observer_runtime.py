from __future__ import annotations

import copy
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from predixai.mobile_v2.app import create_mobile_v2_app  # noqa: E402
from predixai.mobile_v2.observer_runtime import (  # noqa: E402
    DeterministicSimulatedSource,
    ObserverRuntimeController,
)
from predixai.mobile_v2.state_store import (  # noqa: E402
    RuntimeStateStore,
    create_default_state,
    validate_state,
)


class StepClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 7, 13, 18, 0, tzinfo=timezone.utc)
        self.lock = threading.Lock()

    def __call__(self) -> datetime:
        with self.lock:
            current = self.value
            self.value += timedelta(seconds=1)
            return current


class FailingSource:
    def next_reading(self, cycle: int):
        raise RuntimeError("falha determinística de teste")


class CountingSource:
    def __init__(self) -> None:
        self.calls = 0
        self.lock = threading.Lock()

    def next_reading(self, cycle: int):
        with self.lock:
            self.calls += 1
        return {"asset": "SIM-COUNT", "price": float(cycle), "cycle": cycle}


class GatedSource:
    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()

    def next_reading(self, cycle: int):
        self.entered.set()
        if not self.release.wait(1.0):
            raise RuntimeError("gate timeout")
        return {"asset": "SIM-GATED", "price": 1.0, "cycle": cycle}


class PtpGov44ObserverRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controllers: list[ObserverRuntimeController] = []

    def tearDown(self) -> None:
        for controller in self.controllers:
            controller.stop()
            self.assertFalse(controller.thread_alive)

    def wait_for(self, predicate, timeout: float = 1.0) -> bool:
        gate = threading.Event()
        for _ in range(max(1, int(timeout / 0.005))):
            if predicate():
                return True
            gate.wait(0.005)
        return bool(predicate())

    def make_store(self, tmpdir: str) -> RuntimeStateStore:
        base = Path(tmpdir)
        return RuntimeStateStore(
            state_path=base / "mobile_v2_state.json",
            lock_path=base / "mobile_v2_state.lock",
            backup_path=base / "mobile_v2_state.backup",
        )

    def make_controller(
        self,
        tmpdir: str,
        *,
        source=None,
        interval: float = 0.01,
    ) -> tuple[ObserverRuntimeController, RuntimeStateStore]:
        store = self.make_store(tmpdir)
        controller = ObserverRuntimeController(
            store,
            source=source or CountingSource(),
            interval=interval,
            clock=StepClock(),
            join_timeout=1.0,
        )
        self.controllers.append(controller)
        return controller, store

    def test_one_controller_per_application_without_module_global(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            app_one = create_mobile_v2_app(
                store=self.make_store(first), observer_interval=0.01
            )
            app_two = create_mobile_v2_app(
                store=self.make_store(second), observer_interval=0.01
            )
            one = app_one.extensions["observer_runtime"]
            two = app_two.extensions["observer_runtime"]
            self.controllers.extend((one, two))
            self.assertIsNot(one, two)
            self.assertIs(app_one.extensions["observer_runtime"], one)

    def test_start_is_idempotent_and_prevents_duplicate_thread(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            controller, store = self.make_controller(tmpdir)
            first = controller.start()
            first_thread = controller.thread
            second = controller.start()
            self.assertTrue(first["changed"])
            self.assertFalse(second["changed"])
            self.assertIs(first_thread, controller.thread)
            self.assertEqual(controller.active_thread_count, 1)
            self.assertTrue(
                self.wait_for(lambda: store.read_state()["observer_cycle"] >= 1)
            )

    def test_state_transition_chain_reaches_waiting_and_simulated(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = GatedSource()
            controller, store = self.make_controller(tmpdir, source=source)
            started = controller.start()
            self.assertEqual(started["observer_state"], "STARTING")
            self.assertTrue(source.entered.wait(1.0))
            self.assertEqual(store.read_state()["observer_state"], "ON_WAITING_SOURCE")
            source.release.set()
            self.assertTrue(
                self.wait_for(
                    lambda: store.read_state()["observer_state"] == "ON_SIMULATED"
                )
            )

    def test_deterministic_sequence_and_cycle_updates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = DeterministicSimulatedSource(
                (
                    {"asset": "SIM-A", "price": 10.0},
                    {"asset": "SIM-B", "price": 20.0},
                )
            )
            controller, store = self.make_controller(tmpdir, source=source)
            controller.start()
            self.assertTrue(
                self.wait_for(lambda: store.read_state()["observer_cycle"] >= 2)
            )
            controller.pause()
            state = store.read_state()
            expected_asset = "SIM-A" if state["observer_cycle"] % 2 else "SIM-B"
            expected_price = 10.0 if expected_asset == "SIM-A" else 20.0
            self.assertEqual(state["observer_last_reading"]["asset"], expected_asset)
            self.assertEqual(state["observer_last_reading"]["price"], expected_price)
            self.assertEqual(state["observer_state"], "PAUSED")

    def test_pause_preserves_reading_and_cycle_without_busy_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = CountingSource()
            controller, store = self.make_controller(tmpdir, source=source)
            controller.start()
            self.assertTrue(
                self.wait_for(lambda: store.read_state()["observer_cycle"] >= 1)
            )
            paused = controller.pause()
            self.assertTrue(paused["changed"])
            before = copy.deepcopy(store.read_state())
            threading.Event().wait(0.05)
            after = store.read_state()
            self.assertEqual(after["observer_state"], "PAUSED")
            self.assertEqual(after["observer_cycle"], before["observer_cycle"])
            self.assertEqual(
                after["observer_last_reading"], before["observer_last_reading"]
            )
            self.assertFalse(controller.pause()["changed"])

    def test_resume_advances_after_pause(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            controller, store = self.make_controller(tmpdir)
            controller.start()
            self.assertTrue(
                self.wait_for(lambda: store.read_state()["observer_cycle"] >= 1)
            )
            controller.pause()
            paused_cycle = store.read_state()["observer_cycle"]
            resumed = controller.resume()
            self.assertTrue(resumed["changed"])
            self.assertTrue(
                self.wait_for(
                    lambda: store.read_state()["observer_cycle"] > paused_cycle
                )
            )

    def test_resume_outside_paused_is_controlled_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            controller, _ = self.make_controller(tmpdir)
            result = controller.resume()
            self.assertFalse(result["changed"])
            self.assertIn("resume exige PAUSED", result["error"])
            self.assertEqual(result["observer_state"], "OFF")

    def test_stop_is_idempotent_and_joins_owned_thread(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            controller, store = self.make_controller(tmpdir)
            controller.start()
            self.assertTrue(self.wait_for(lambda: controller.thread_alive))
            first = controller.stop()
            second = controller.stop()
            self.assertTrue(first["changed"])
            self.assertFalse(second["changed"])
            self.assertFalse(controller.thread_alive)
            self.assertEqual(controller.active_thread_count, 0)
            self.assertEqual(store.read_state()["observer_state"], "OFF")

    def test_restart_after_stop_uses_new_owned_thread(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            controller, store = self.make_controller(tmpdir)
            controller.start()
            first_thread = controller.thread
            self.assertTrue(
                self.wait_for(lambda: store.read_state()["observer_cycle"] >= 1)
            )
            controller.stop()
            controller.start()
            second_thread = controller.thread
            self.assertIsNot(first_thread, second_thread)
            self.assertTrue(
                self.wait_for(lambda: store.read_state()["observer_state"] == "ON_SIMULATED")
            )

    def test_source_exception_persists_controlled_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            controller, store = self.make_controller(tmpdir, source=FailingSource())
            controller.start()
            self.assertTrue(
                self.wait_for(lambda: store.read_state()["observer_state"] == "ERROR")
            )
            state = store.read_state()
            self.assertIn("falha determinística de teste", state["observer_error"])
            self.assertIsInstance(state["observer_updated_at"], str)
            self.assertFalse(controller.thread_alive)
            self.assertIsNotNone(controller.start()["error"])
            self.assertEqual(controller.stop()["observer_state"], "OFF")

    def test_concurrent_start_has_one_changed_result_and_one_thread(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            controller, _ = self.make_controller(tmpdir)
            barrier = threading.Barrier(6)
            results = []
            failures = []

            def worker() -> None:
                try:
                    barrier.wait(timeout=1)
                    results.append(controller.start())
                except Exception as exc:  # pragma: no cover
                    failures.append(exc)

            threads = [threading.Thread(target=worker) for _ in range(6)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=2)
            self.assertEqual(failures, [])
            self.assertEqual(sum(bool(result["changed"]) for result in results), 1)
            self.assertEqual(controller.active_thread_count, 1)

    def test_runtime_paths_remain_inside_temporary_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            controller, store = self.make_controller(tmpdir)
            controller.start()
            self.assertTrue(
                self.wait_for(lambda: store.read_state()["observer_cycle"] >= 1)
            )
            root = Path(tmpdir).resolve()
            for path in (store.state_path, store.lock_path, store.backup_path):
                path.resolve().relative_to(root)
            self.assertNotEqual(
                store.state_path.resolve(),
                (ROOT / "data" / "runtime" / "mobile_v2_state.json").resolve(),
            )

    def test_http_contracts_and_application_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.make_store(tmpdir)
            app = create_mobile_v2_app(
                store=store,
                observer_source=CountingSource(),
                observer_interval=0.01,
                observer_clock=StepClock(),
            )
            controller = app.extensions["observer_runtime"]
            self.controllers.append(controller)
            client = app.test_client()
            invalid_resume = client.post("/observer/resume")
            self.assertEqual(invalid_resume.status_code, 409)
            self.assertIsNotNone(invalid_resume.get_json()["error"])

            start = client.post("/observer/start")
            self.assertEqual(start.status_code, 200)
            self.assertEqual(start.get_json()["application_id"], "MOBILE_V2")
            self.assertTrue(
                self.wait_for(lambda: store.read_state()["observer_cycle"] >= 1)
            )
            pause = client.post("/observer/pause")
            self.assertEqual(pause.status_code, 200)
            self.assertEqual(pause.get_json()["observer_state"], "PAUSED")
            resume = client.post("/observer/resume")
            self.assertEqual(resume.status_code, 200)
            stop = client.post("/observer/stop")
            self.assertEqual(stop.status_code, 200)
            for payload in (
                start.get_json(),
                pause.get_json(),
                resume.get_json(),
                stop.get_json(),
            ):
                self.assertEqual(payload["application_id"], "MOBILE_V2")
                self.assertIn("observer_state", payload)
                self.assertIn("observer_cycle", payload)
                self.assertIn("changed", payload)
                self.assertIn("error", payload)

    def test_mobile_page_reflects_state_fields_and_single_polling_timer(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_mobile_v2_app(store=self.make_store(tmpdir))
            self.controllers.append(app.extensions["observer_runtime"])
            html = app.test_client().get("/mobile").get_data(as_text=True)
            for field in (
                "observerStatus",
                "observerCycle",
                "observerLastReading",
                "observerUpdatedAt",
                "observerError",
            ):
                self.assertIn(f'id="{field}"', html)
            self.assertEqual(html.count("window.setInterval(loadState, 5000)"), 1)
            self.assertIn("window.predixaiMobileV2PollingTimer", html)

    def test_previous_schema_is_migrated_explicitly_without_version_change(self) -> None:
        state = create_default_state()
        for field in (
            "observer_state",
            "observer_cycle",
            "observer_updated_at",
            "observer_last_reading",
            "observer_error",
        ):
            state.pop(field)
        state["observer"]["status"] = "ON_WAITING_SOURCE"
        migrated = validate_state(state)
        self.assertEqual(migrated["schema_version"], "mobile_v2_state_v1")
        self.assertEqual(migrated["observer_state"], "ON_WAITING_SOURCE")
        self.assertEqual(migrated["observer_cycle"], 0)
        self.assertIsNone(migrated["observer_last_reading"])
        self.assertIsNone(migrated["observer_error"])


if __name__ == "__main__":
    unittest.main()
