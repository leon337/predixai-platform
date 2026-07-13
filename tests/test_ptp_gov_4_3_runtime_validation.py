from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "ptp_gov_4_3_validate_mobile_v2_runtime.py"
SPEC = importlib.util.spec_from_file_location("ptp_gov_4_3_validator", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("não foi possível carregar o validador da PTP-GOV.4.3")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class PtpGov43RuntimeValidatorTests(unittest.TestCase):
    def test_all_injected_runtime_paths_must_be_inside_one_temp_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.assertTrue(
                VALIDATOR._validate_runtime_paths(
                    directory,
                    directory / "state.json",
                    directory / "state.lock",
                    directory / "state.backup",
                )
            )
            self.assertFalse(
                VALIDATOR._validate_runtime_paths(
                    directory,
                    directory / "state.json",
                    directory / "state.lock",
                    ROOT / "data" / "runtime" / "forbidden.backup",
                )
            )

    def test_duplicate_runtime_paths_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            state = directory / "state.json"
            self.assertFalse(
                VALIDATOR._validate_runtime_paths(
                    directory, state, state, directory / "state.backup"
                )
            )

    def test_port_status_mapping_is_complete_and_exact(self) -> None:
        expected = {
            VALIDATOR.ENTRYPOINT.PORT_FREE: "PORT_5001_FREE",
            VALIDATOR.ENTRYPOINT.PORT_OCCUPIED_BY_MOBILE_V2: "PORT_5001_MOBILE_V2_EXTERNAL",
            VALIDATOR.ENTRYPOINT.PORT_OCCUPIED_BY_OTHER_APPLICATION: "PORT_5001_OTHER_APPLICATION",
            VALIDATOR.ENTRYPOINT.HEALTH_TIMEOUT: "PORT_5001_TIMEOUT",
            VALIDATOR.ENTRYPOINT.HEALTH_INVALID_RESPONSE: "PORT_5001_INVALID_RESPONSE",
        }
        self.assertEqual(VALIDATOR.PORT_CLASSIFICATION, expected)

    def test_port_classification_delegates_to_canonical_identity_check(self) -> None:
        with mock.patch.object(
            VALIDATOR.ENTRYPOINT,
            "port_application_identity_check",
            return_value=VALIDATOR.ENTRYPOINT.PORT_FREE,
        ) as identity_check:
            self.assertEqual(
                VALIDATOR._classify_port(),
                (VALIDATOR.ENTRYPOINT.PORT_FREE, "PORT_5001_FREE"),
            )
        identity_check.assert_called_once_with("127.0.0.1", 5001, timeout=0.5)

    def test_local_request_contract_is_fixed_to_loopback_port_5001(self) -> None:
        with mock.patch.object(VALIDATOR, "HOST", "192.0.2.1"):
            with self.assertRaisesRegex(ValueError, "somente 127.0.0.1:5001"):
                VALIDATOR._local_request("GET", "/health")

    def test_hash_tree_is_stable_and_detects_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            item = directory / "state.json"
            item.write_text("one", encoding="utf-8")
            first = VALIDATOR._hash_tree(directory)
            self.assertEqual(first, VALIDATOR._hash_tree(directory))
            item.write_text("two", encoding="utf-8")
            self.assertNotEqual(first, VALIDATOR._hash_tree(directory))


if __name__ == "__main__":
    unittest.main()
