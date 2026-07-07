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


class MobileV2HtmlScreensTests(unittest.TestCase):
    def make_app(self, tmpdir: str):
        base = Path(tmpdir)
        store = RuntimeStateStore(
            state_path=base / "mobile_v2_state.json",
            lock_path=base / "mobile_v2_state.lock",
        )
        return create_mobile_v2_app(store=store), store

    def test_session_setup_screen_loads(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app, _ = self.make_app(tmpdir)
            response = app.test_client().get("/session/setup")

            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)

            self.assertIn("PredixAI Mobile V2 — Tela 1", html)
            self.assertIn("Criar contrato simulado", html)
            self.assertIn("simulation_only=true", html)

    def test_mobile_screen_loads_with_placeholders(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app, _ = self.make_app(tmpdir)
            response = app.test_client().get("/mobile")

            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)

            self.assertIn("PredixAI Mobile V2 — Tela 2", html)
            self.assertIn("Sinal atual — placeholder", html)
            self.assertIn("Histórico — placeholder futuro", html)
            self.assertIn("Não existe geração de sinal", html)

    def test_session_create_sets_simulated_contract_only(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app, store = self.make_app(tmpdir)

            response = app.test_client().post(
                "/session/create",
                json={
                    "initial_bank": "100,00",
                    "entry_value": "5,00",
                    "profit_goal": "10,00",
                    "recovery_mode": "sem_recuperacao",
                    "asset_label": "Aguardando leitura",
                },
            )

            self.assertEqual(response.status_code, 200)
            data = response.get_json()

            self.assertTrue(data["ok"])
            self.assertTrue(data["simulated_contract_only"])
            self.assertFalse(data["signal_generation"])
            self.assertFalse(data["history_recording"])
            self.assertFalse(data["operation_result"])
            self.assertFalse(data["real_money"])

            state = store.read_state()
            self.assertEqual(state["session"]["status"], "configured")
            self.assertEqual(state["session"]["contract"]["initial_bank"], 100.0)
            self.assertTrue(state["session"]["simulation_only"])
            self.assertFalse(state["session"]["orders_enabled"])

    def test_mobile_screen_does_not_create_runtime_file(self) -> None:
        with TemporaryDirectory() as tmpdir:
            app, store = self.make_app(tmpdir)
            app.test_client().get("/mobile")

            self.assertFalse(store.state_path.exists())


if __name__ == "__main__":
    unittest.main()
