from __future__ import annotations

import fcntl
import json
import sys
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from predixai.mobile_v2.state_store import (  # noqa: E402
    RuntimeStateLockTimeout,
    RuntimeStateStore,
    create_default_state,
)


class RuntimeStateStoreTests(unittest.TestCase):
    def make_store(self, tmpdir: str) -> RuntimeStateStore:
        base = Path(tmpdir)
        return RuntimeStateStore(
            state_path=base / "mobile_v2_state.json",
            lock_path=base / "mobile_v2_state.lock",
        )

    def test_create_default_state_has_required_safety_locks(self) -> None:
        state = create_default_state()

        self.assertEqual(state["schema_version"], "mobile_v2_state_v1")
        self.assertTrue(state["session"]["simulation_only"])
        self.assertFalse(state["session"]["orders_enabled"])
        self.assertFalse(state["session"]["real_money_enabled"])
        self.assertFalse(state["session"]["auto_click_enabled"])
        self.assertFalse(state["session"]["broker_login_enabled"])
        self.assertFalse(state["session"]["credentials_allowed"])
        self.assertEqual(state["observer_state"], "OFF")
        self.assertEqual(state["observer_cycle"], 0)
        self.assertIsNone(state["observer_last_reading"])
        self.assertIsNone(state["observer_error"])
        self.assertIsInstance(state["observer_updated_at"], str)

    def test_write_and_read_state_sequential(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store = self.make_store(tmpdir)
            state = create_default_state()
            state["status"] = "test_sequential"

            written = store.write_state(state)
            read_back = store.read_state()

            self.assertEqual(written["status"], "test_sequential")
            self.assertEqual(read_back["status"], "test_sequential")
            self.assertTrue(store.state_path.exists())

    def test_write_creates_valid_json_atomically(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store = self.make_store(tmpdir)
            state = create_default_state()
            state["observer"]["status"] = "OFF"

            store.write_state(state)

            with store.state_path.open("r", encoding="utf-8") as handle:
                loaded = json.load(handle)

            self.assertEqual(loaded["schema_version"], "mobile_v2_state_v1")
            self.assertEqual(loaded["observer"]["status"], "OFF")
            self.assertFalse(list(Path(tmpdir).glob("*.tmp")))

    def test_concurrent_writes_respect_lock_and_keep_json_valid(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store = self.make_store(tmpdir)
            barrier = threading.Barrier(2)
            errors = []

            def worker(worker_id: int) -> None:
                try:
                    state = create_default_state()
                    state["status"] = f"worker_{worker_id}"
                    barrier.wait(timeout=2)
                    store.write_state(state, lock_timeout=2.0)
                except Exception as exc:  # pragma: no cover - surfaced by assertion
                    errors.append(exc)

            threads = [
                threading.Thread(target=worker, args=(1,)),
                threading.Thread(target=worker, args=(2,)),
            ]

            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)

            self.assertEqual(errors, [])

            with store.state_path.open("r", encoding="utf-8") as handle:
                loaded = json.load(handle)

            self.assertIn(loaded["status"], {"worker_1", "worker_2"})
            self.assertEqual(loaded["schema_version"], "mobile_v2_state_v1")

    def test_lock_timeout_is_controlled_failure(self) -> None:
        with TemporaryDirectory() as tmpdir:
            store = self.make_store(tmpdir)
            store.lock_path.parent.mkdir(parents=True, exist_ok=True)

            lock_file = store.lock_path.open("a+", encoding="utf-8")
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

                with self.assertRaises(RuntimeStateLockTimeout):
                    store.write_state(create_default_state(), lock_timeout=0.05)
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_file.close()


if __name__ == "__main__":
    unittest.main()
