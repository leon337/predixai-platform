#!/usr/bin/env python3
"""
Validação mínima da PTP-112A — Mobile Session Contract v1.1.
Não inicia robô, não envia ordem, não faz clique e não usa dinheiro real.
"""

from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from predixai.trader.mobile_session_contract import (
    build_mobile_session_contract,
    mark_contract_blocked,
    save_mobile_session_contract,
    validate_mobile_session_contract,
)


def assert_valid_default_contract() -> None:
    contract = build_mobile_session_contract()
    ok, errors = validate_mobile_session_contract(contract)

    assert ok, errors
    assert contract["session"]["status"] == "CREATED"
    assert contract["security"]["executor_blocked"] is True
    assert contract["security"]["orders_enabled"] is False
    assert contract["security"]["real_money_enabled"] is False
    assert contract["operation"]["paper_trade_enabled"] is True


def assert_security_is_server_enforced() -> None:
    malicious_mobile_payload = {
        "security": {
            "orders_enabled": True,
            "real_money_enabled": True,
            "auto_click_enabled": True,
            "broker_login_enabled": True,
            "credentials_allowed": True,
        }
    }

    contract = build_mobile_session_contract(malicious_mobile_payload)
    ok, errors = validate_mobile_session_contract(contract)

    assert ok, errors
    assert contract["security"]["orders_enabled"] is False
    assert contract["security"]["real_money_enabled"] is False
    assert contract["security"]["auto_click_enabled"] is False
    assert contract["security"]["broker_login_enabled"] is False
    assert contract["security"]["credentials_allowed"] is False


def assert_future_strategy_is_blocked() -> None:
    contract = build_mobile_session_contract(
        {
            "strategy": {
                "strategy_mode": "COMBINED_AI",
                "strategy_stack": ["COMBINED_AI"],
            }
        }
    )

    ok, errors = validate_mobile_session_contract(contract)

    assert not ok
    assert any("estratégia futura bloqueada" in error for error in errors)


def assert_invalid_bankroll_is_rejected() -> None:
    contract = build_mobile_session_contract(
        {
            "bankroll": {
                "initial_bankroll": 100.0,
                "current_bankroll": 100.0,
                "initial_entry": 50.0,
                "current_entry": 50.0,
            },
            "risk": {
                "risk_profile": "CONSERVATIVE",
            },
        }
    )

    ok, errors = validate_mobile_session_contract(contract)

    assert not ok
    assert any("CONSERVATIVE" in error for error in errors)


def assert_blocked_status_helper() -> None:
    contract = build_mobile_session_contract()
    blocked = mark_contract_blocked(
        contract,
        reason="INVALID_CONTRACT",
        validation_error="Teste controlado PTP-112A",
    )

    assert blocked["session"]["status"] == "BLOCKED"
    assert blocked["safety_audit"]["blocked_reason"] == "INVALID_CONTRACT"
    assert blocked["security"]["orders_enabled"] is False


def save_example_contract() -> None:
    contract = build_mobile_session_contract(
        {
            "strategy": {
                "strategy_mode": "PRICE_ACTION",
                "strategy_stack": ["PRICE_ACTION", "SUPPORT_RESISTANCE"],
                "min_confidence": 70,
            },
            "bankroll": {
                "initial_bankroll": 100.0,
                "current_bankroll": 100.0,
                "initial_entry": 5.0,
                "current_entry": 5.0,
            },
            "risk": {
                "risk_profile": "CONSERVATIVE",
                "stop_loss": 20.0,
                "take_profit": 20.0,
                "payout_min": 80,
            },
        }
    )

    ok, errors = validate_mobile_session_contract(contract)
    assert ok, errors

    example_path = REPO / "data" / "runtime" / "mobile_session_contract_v1_1_example.json"
    save_mobile_session_contract(contract, example_path)
    print(f"[OK] Exemplo salvo em: {example_path}")


def main() -> None:
    assert_valid_default_contract()
    assert_security_is_server_enforced()
    assert_future_strategy_is_blocked()
    assert_invalid_bankroll_is_rejected()
    assert_blocked_status_helper()
    save_example_contract()

    print("[OK] PTP-112A Mobile Session Contract validado com sucesso.")


if __name__ == "__main__":
    main()
