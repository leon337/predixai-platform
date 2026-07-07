from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from flask import Flask
except Exception:  # pragma: no cover
    Flask = None

from predixai.mobile_v2.routes import register_mobile_v2_routes  # noqa: E402
from predixai.mobile_v2.state_store import (  # noqa: E402
    RuntimeStateStore,
    create_default_state,
)


@unittest.skipIf(Flask is None, "Flask não disponível")
class MobileV2RoutesTests(unittest.TestCase):
    def make_app_and_store(self, tmpdir: str):
        app = Flask(__name__)
        base = Path(tmpdir)
        store = RuntimeStateStore(
            state_path=base / "mobile_v2_state.json",
            lock_path=base / "mobile_v2_state.lock",
        )
        info = register_mobile_v2_routes(app, store=store)
        return app, store, info

    def test_register_routes_and_get_default_state(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app, store, info = self.make_app_and_store(tmpdir)

            self.assertEqual(len(info["added"]), 3)
            client = app.test_client()
            response = client.get("/state/current")

            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data["ok"])
            self.assertTrue(data["mobile_v2"])
            self.assertFalse(data["runtime_persisted"])
            self.assertEqual(data["state"]["status"], "idle")
            self.assertIsNone(data["state"]["reading"]["age_seconds"])
            self.assertFalse(store.state_path.exists())

    def test_observer_start_is_control_only(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app, store, _ = self.make_app_and_store(tmpdir)
            response = app.test_client().post("/observer/start")

            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data["simulated_control_only"])
            self.assertFalse(data["reader_process_started"])
            self.assertEqual(data["state"]["observer"]["status"], "ON_WAITING_SOURCE")
            self.assertFalse(data["state"]["observer"]["running"])
            self.assertTrue(store.state_path.exists())

    def test_observer_stop_sets_off_without_real_kill(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app, _, _ = self.make_app_and_store(tmpdir)
            client = app.test_client()

            client.post("/observer/start")
            response = client.post("/observer/stop")

            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data["simulated_control_only"])
            self.assertFalse(data["reader_process_stopped"])
            self.assertEqual(data["state"]["observer"]["status"], "OFF")
            self.assertEqual(data["state"]["signal"]["status"], "aguardando_leitura")

    def test_age_seconds_is_not_persisted(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app, store, _ = self.make_app_and_store(tmpdir)
            state = create_default_state()
            state["reading"]["captured_at"] = "2026-07-07T10:00:00+00:00"
            state["reading"]["status"] = "reading"
            state["reading"]["asset"] = "TEST"
            store.write_state(state)

            response = app.test_client().get("/state/current")
            self.assertEqual(response.status_code, 200)

            data = response.get_json()
            self.assertIn("age_seconds", data["state"]["reading"])

            with store.state_path.open("r", encoding="utf-8") as handle:
                persisted = json.load(handle)

            self.assertNotIn("age_seconds", persisted["reading"])

    def test_registration_is_idempotent(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app, store, first = self.make_app_and_store(tmpdir)
            second = register_mobile_v2_routes(app, store=store)

            self.assertEqual(len(first["added"]), 3)
            self.assertEqual(len(second["added"]), 0)
            self.assertEqual(len(second["skipped"]), 3)


if __name__ == "__main__":
    unittest.main()
