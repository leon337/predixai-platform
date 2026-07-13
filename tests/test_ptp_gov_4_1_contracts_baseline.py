from __future__ import annotations

import fcntl
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from predixai.mobile_v2.app import create_mobile_v2_app  # noqa: E402
from predixai.mobile_v2.state_store import (  # noqa: E402
    RuntimeStateLockTimeout,
    RuntimeStateStore,
    RuntimeStateValidationError,
    create_default_state,
)


EXPECTED_ROUTES = {
    ("GET", "/"),
    ("GET", "/health"),
    ("GET", "/session/setup"),
    ("POST", "/session/create"),
    ("GET", "/mobile"),
    ("GET", "/state/current"),
    ("POST", "/observer/start"),
    ("POST", "/observer/stop"),
}


class CurrentCharacterizationTests(unittest.TestCase):
    """Freeze only behavior that exists at the audited commit."""

    def make_store(self, tmpdir: str) -> RuntimeStateStore:
        base = Path(tmpdir)
        return RuntimeStateStore(
            state_path=base / "mobile_v2_state.json",
            lock_path=base / "mobile_v2_state.json.lock",
        )

    def make_app(self, tmpdir: str):
        store = self.make_store(tmpdir)
        app = create_mobile_v2_app(store=store)
        app.config.update(TESTING=True)
        return app, store

    def test_canonical_application_port_matrix(self) -> None:
        runner = (ROOT / "scripts" / "run_mobile_v2_server.py").read_text(
            encoding="utf-8"
        )
        legacy = (ROOT / "scripts" / "predixai_trader_mobile_server.py").read_text(
            encoding="utf-8"
        )
        dashboard = (
            ROOT / "src" / "predixai" / "dashboard" / "dashboard_server.py"
        ).read_text(encoding="utf-8")
        self.assertIn('PREDIXAI_MOBILE_V2_PORT", "5001"', runner)
        self.assertIn("DEFAULT_PORT = 8766", legacy)
        self.assertIn("port: int = 8765", dashboard)

    def test_mobile_v2_route_set_and_methods(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            app, _ = self.make_app(tmpdir)
            actual = {
                (method, rule.rule)
                for rule in app.url_map.iter_rules()
                if rule.rule != "/static/<path:filename>"
                for method in rule.methods
                if method not in {"HEAD", "OPTIONS"}
            }
            self.assertEqual(actual, EXPECTED_ROUTES)

    def test_health_current_identity_characterization(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            app, _ = self.make_app(tmpdir)
            response = app.test_client().get("/health")
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertIs(payload["mobile_v2"], True)
            self.assertIs(payload["standalone"], True)
            self.assertIs(payload["simulation_only"], True)

    def test_index_http_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            app, _ = self.make_app(tmpdir)
            response = app.test_client().get("/")
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertEqual(payload["app"], "PredixAI Trader Mobile V2")
            self.assertIs(payload["safety"]["simulation_only"], True)
            self.assertIs(payload["safety"]["orders_enabled"], False)
            self.assertIs(payload["safety"]["real_money_enabled"], False)
            self.assertIs(payload["safety"]["auto_click_enabled"], False)
            self.assertIs(payload["safety"]["broker_login_enabled"], False)

    def test_session_setup_http_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            app, _ = self.make_app(tmpdir)
            response = app.test_client().get("/session/setup")
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"<!", response.data[:100].lower())

    def test_session_create_simulation_safety_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            app, store = self.make_app(tmpdir)
            response = app.test_client().post(
                "/session/create",
                json={"initial_bank": "100", "entry_value": "5"},
            )
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertIs(payload["simulated_contract_only"], True)
            self.assertIs(payload["real_money"], False)
            persisted = store.read_state()
            self.assertIs(persisted["session"]["simulation_only"], True)
            self.assertIs(persisted["session"]["orders_enabled"], False)

    def test_mobile_screen_http_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            app, store = self.make_app(tmpdir)
            response = app.test_client().get("/mobile")
            self.assertEqual(response.status_code, 200)
            self.assertFalse(store.state_path.exists())

    def test_state_current_http_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            app, _ = self.make_app(tmpdir)
            response = app.test_client().get("/state/current")
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertEqual(payload["state"]["schema_version"], "mobile_v2_state_v1")
            self.assertIs(payload["runtime_persisted"], False)

    def test_observer_start_http_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            app, _ = self.make_app(tmpdir)
            response = app.test_client().post("/observer/start")
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertIs(payload["simulated_control_only"], True)
            self.assertIs(payload["reader_process_started"], False)

    def test_observer_stop_http_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            app, _ = self.make_app(tmpdir)
            response = app.test_client().post("/observer/stop")
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertIs(payload["simulated_control_only"], True)
            self.assertIs(payload["reader_process_stopped"], False)

    def test_runtime_schema_version_contract(self) -> None:
        state = create_default_state()
        self.assertEqual(state["schema_version"], "mobile_v2_state_v1")
        state["schema_version"] = "unknown"
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.make_store(tmpdir)
            with self.assertRaises(RuntimeStateValidationError):
                store.write_state(state)

    def test_runtime_atomic_write_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.make_store(tmpdir)
            state = create_default_state()
            state["status"] = "atomic_characterization"
            stored = store.write_state(state)
            self.assertEqual(stored["status"], "atomic_characterization")
            with store.state_path.open("r", encoding="utf-8") as handle:
                self.assertEqual(json.load(handle)["status"], "atomic_characterization")
            self.assertEqual(list(Path(tmpdir).glob("*.tmp")), [])

    def test_runtime_thread_lock_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.make_store(tmpdir)
            barrier = threading.Barrier(2)
            failures = []

            def worker(value: int) -> None:
                try:
                    barrier.wait(timeout=2)
                    state = create_default_state()
                    state["session"]["initial_bank"] = float(value)
                    store.write_state(state)
                except Exception as exc:  # pragma: no cover - assertion below
                    failures.append(exc)

            threads = [threading.Thread(target=worker, args=(value,)) for value in (1, 2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)
            self.assertEqual(failures, [])
            self.assertTrue(all(not thread.is_alive() for thread in threads))
            with store.state_path.open("r", encoding="utf-8") as handle:
                self.assertIn(json.load(handle)["session"]["initial_bank"], {1.0, 2.0})

    def test_runtime_process_lock_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            gate = base / "start.gate"
            state_path = base / "mobile_v2_state.json"
            lock_path = base / "mobile_v2_state.json.lock"
            worker = (
                "import sys,time; from pathlib import Path; "
                "from predixai.mobile_v2.state_store import RuntimeStateStore,create_default_state; "
                "gate=Path(sys.argv[1]); value=float(sys.argv[2]); "
                "store=RuntimeStateStore(state_path=sys.argv[3],lock_path=sys.argv[4]); "
                "\nwhile not gate.exists(): time.sleep(0.01)\n"
                "state=create_default_state(); state['session']['initial_bank']=value; "
                "store.write_state(state)"
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = str(SRC)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            processes = [
                subprocess.Popen(
                    [sys.executable, "-c", worker, str(gate), str(value), str(state_path), str(lock_path)],
                    cwd=tmpdir,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for value in (1, 2)
            ]
            gate.touch()
            results = [process.communicate(timeout=10) for process in processes]
            self.assertEqual([process.returncode for process in processes], [0, 0], results)
            with state_path.open("r", encoding="utf-8") as handle:
                self.assertIn(json.load(handle)["session"]["initial_bank"], {1.0, 2.0})

    def test_runtime_lock_timeout_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.make_store(tmpdir)
            store.lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_file = store.lock_path.open("a+", encoding="utf-8")
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaises(RuntimeStateLockTimeout):
                    store.read_state(lock_timeout=0.05)
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_file.close()

    def test_runtime_corrupted_json_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.make_store(tmpdir)
            store.state_path.parent.mkdir(parents=True, exist_ok=True)
            store.state_path.write_text("{invalid-json", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                store.read_state()

    def test_runtime_restart_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            first = self.make_store(tmpdir)
            state = create_default_state()
            state["status"] = "restart_characterization"
            first.write_state(state)
            second = self.make_store(tmpdir)
            self.assertEqual(second.read_state()["status"], "restart_characterization")

    def test_runtime_git_tracking_is_prohibited(self) -> None:
        tracked = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "--error-unmatch", "data/runtime/probe.json"],
            capture_output=True,
            text=True,
            check=False,
        )
        ignored = subprocess.run(
            ["git", "-C", str(ROOT), "check-ignore", "data/runtime/probe.json"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(tracked.returncode, 0)
        self.assertEqual(ignored.returncode, 0)

    def test_canonical_package_import_from_clean_working_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env = os.environ.copy()
            env["PYTHONPATH"] = str(SRC)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import predixai; print(predixai.__file__)",
                ],
                cwd=tmpdir,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(result.stdout.strip()).resolve(), (SRC / "predixai" / "__init__.py").resolve())

    def test_mobile_v2_does_not_import_legacy_server(self) -> None:
        combined = "\n".join(
            (ROOT / relative).read_text(encoding="utf-8")
            for relative in (
                "src/predixai/mobile_v2/app.py",
                "src/predixai/mobile_v2/routes.py",
                "src/predixai/mobile_v2/state_store.py",
            )
        )
        self.assertNotIn("predixai_trader_mobile_server", combined)
        self.assertNotIn("create_mobile_app", combined)

    def test_protected_files_match_preflight_hashes(self) -> None:
        expected = {
            "src/predixai/mobile_v2/app.py": "59579f1294ce7f7fce02954b39b8a7b8684cff1f639e7bd91dea2f81ce82da78",
            "src/predixai/mobile_v2/routes.py": "5047be027d814609e51ea24fdcf662e74e453e50aad717609cda868b76135e79",
            "src/predixai/mobile_v2/state_store.py": "61e7260fdb783fc836494b5d40a77f16f4802504d72ce7d16d376fabb5b0e848",
            "scripts/run_mobile_v2_server.py": "64e64c64b6df3f3459ee4d841476f96154dc8c31af9ba4c30f8b8f97ec3a601e",
            "predixai/__init__.py": "b41cddb5318762695136eaffadd852df49d60a0097be005d28084ab003df8cb2",
            "src/predixai/__init__.py": "e92a8ed7faa347c099e41c68fa49637029579f5a5631347691662cc5cc85c3d3",
            ".gitignore": "a5b8a6c59c3387e78cfab797ec0c16c19b68206d962c50c92e50b8f4f40ceea9",
            "scripts/predixai_trader_mobile_server.py": "af5436d71011873a51eac082b67c96789dcd27f660ffedaa8f444fba5b1d812d",
        }
        actual = {
            relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            for relative in expected
        }
        self.assertEqual(actual, expected)
        self.assertFalse((ROOT / "pyproject.toml").exists())


class ExpectedContractGapProofs(unittest.TestCase):
    """Visible expected failures for approved contracts not present at the base commit."""

    def make_app(self, tmpdir: str):
        base = Path(tmpdir)
        store = RuntimeStateStore(
            state_path=base / "mobile_v2_state.json",
            lock_path=base / "mobile_v2_state.json.lock",
        )
        app = create_mobile_v2_app(store=store)
        app.config.update(TESTING=True)
        return app

    @unittest.expectedFailure
    def test_gap_health_requires_application_id_mobile_v2(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = self.make_app(tmpdir).test_client().get("/health").get_json()
            self.assertEqual(payload.get("application_id"), "MOBILE_V2")

    @unittest.expectedFailure
    def test_gap_entrypoint_requires_port_application_identity_check(self) -> None:
        source = (ROOT / "scripts" / "run_mobile_v2_server.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("application_id", source)
        self.assertIn("port_application_identity_check", source)

    @unittest.expectedFailure
    def test_gap_runtime_store_requires_explicit_backup_recovery(self) -> None:
        source = (
            ROOT / "src" / "predixai" / "mobile_v2" / "state_store.py"
        ).read_text(encoding="utf-8")
        self.assertIn("backup", source.lower())
        self.assertIn("recover", source.lower())


if __name__ == "__main__":
    unittest.main()
