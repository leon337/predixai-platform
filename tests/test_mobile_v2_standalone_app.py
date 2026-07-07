from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from predixai.mobile_v2.app import create_mobile_v2_app  # noqa: E402
from predixai.mobile_v2.state_store import RuntimeStateStore  # noqa: E402


class MobileV2StandaloneAppTests(unittest.TestCase):
    def make_app(self, tmpdir: str):
        base = Path(tmpdir)
        store = RuntimeStateStore(
            state_path=base / "mobile_v2_state.json",
            lock_path=base / "mobile_v2_state.lock",
        )
        return create_mobile_v2_app(store=store), store

    def test_index_exposes_standalone_metadata(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app, _ = self.make_app(tmpdir)
            client = app.test_client()

            response = client.get("/")
            self.assertEqual(response.status_code, 200)

            data = response.get_json()
            self.assertTrue(data["ok"])
            self.assertTrue(data["standalone"])
            self.assertFalse(data["legacy_mobile_server"])
            self.assertFalse(data["observer_real_started"])
            self.assertTrue(data["safety"]["simulation_only"])
            self.assertFalse(data["safety"]["orders_enabled"])

    def test_health_endpoint(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app, _ = self.make_app(tmpdir)
            response = app.test_client().get("/health")

            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data["ok"])
            self.assertTrue(data["mobile_v2"])
            self.assertTrue(data["standalone"])

    def test_mobile_v2_routes_are_available(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app, store = self.make_app(tmpdir)
            client = app.test_client()

            state_response = client.get("/state/current")
            self.assertEqual(state_response.status_code, 200)
            self.assertFalse(store.state_path.exists())

            start_response = client.post("/observer/start")
            self.assertEqual(start_response.status_code, 200)
            start_data = start_response.get_json()
            self.assertTrue(start_data["simulated_control_only"])
            self.assertFalse(start_data["reader_process_started"])
            self.assertTrue(store.state_path.exists())

            stop_response = client.post("/observer/stop")
            self.assertEqual(stop_response.status_code, 200)
            stop_data = stop_response.get_json()
            self.assertTrue(stop_data["simulated_control_only"])
            self.assertFalse(stop_data["reader_process_stopped"])
            self.assertEqual(stop_data["state"]["observer"]["status"], "OFF")


if __name__ == "__main__":
    unittest.main()
