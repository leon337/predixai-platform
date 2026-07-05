from predixai.mobile.simulated_bank import SimulatedBankEngine


def assert_equal(label, value, expected):
    if value != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {value}")


def assert_true(label, condition):
    if not condition:
        raise AssertionError(label)


def validate_win_loss_draw():
    engine = SimulatedBankEngine(
        initial_bank=100.0,
        entry_value=10.0,
        stop_loss=30.0,
        take_profit=30.0,
        max_losses=3,
        payout=0.80,
    )

    engine.apply_result("WIN")
    snap = engine.snapshot()
    assert_equal("saldo apos WIN", snap["current_bank"], 108.0)
    assert_equal("wins", snap["wins"], 1)

    engine.apply_result("LOSS")
    snap = engine.snapshot()
    assert_equal("saldo apos LOSS", snap["current_bank"], 98.0)
    assert_equal("losses", snap["losses"], 1)

    engine.apply_result("DRAW")
    snap = engine.snapshot()
    assert_equal("saldo apos DRAW", snap["current_bank"], 98.0)
    assert_equal("draws", snap["draws"], 1)
    assert_equal("operacoes", snap["operations"], 3)
    assert_equal("taxa de acerto", snap["accuracy_rate"], 50.0)


def validate_stop_loss():
    engine = SimulatedBankEngine(100.0, 10.0, 20.0, 50.0, 5)
    engine.apply_result("LOSS")
    engine.apply_result("LOSS")
    snap = engine.snapshot()
    assert_equal("status stop loss", snap["status"], "stop_loss")
    assert_true("sessao bloqueada por stop loss", not snap["can_continue"])


def validate_take_profit():
    engine = SimulatedBankEngine(100.0, 10.0, 50.0, 16.0, 5, payout=0.80)
    engine.apply_result("WIN")
    engine.apply_result("WIN")
    snap = engine.snapshot()
    assert_equal("status take profit", snap["status"], "take_profit")
    assert_true("sessao bloqueada por take profit", not snap["can_continue"])


def validate_max_losses():
    engine = SimulatedBankEngine(100.0, 5.0, 50.0, 50.0, 2)
    engine.apply_result("LOSS")
    engine.apply_result("LOSS")
    snap = engine.snapshot()
    assert_equal("status max losses", snap["status"], "max_losses")
    assert_true("sessao bloqueada por max losses", not snap["can_continue"])


def validate_security_source():
    source = open("src/predixai/mobile/simulated_bank.py", "r", encoding="utf-8").read().lower()
    blocked = [
        "send_order",
        "buy(",
        "sell(",
        "click(",
        "deposit",
        "withdraw",
        "password",
        "real_balance",
    ]
    found = [term for term in blocked if term in source]
    if found:
        raise AssertionError(f"termos bloqueados encontrados: {found}")


def main():
    validate_win_loss_draw()
    validate_stop_loss()
    validate_take_profit()
    validate_max_losses()
    validate_security_source()
    print("PASS: PTP-112D Motor de Banca Simulada validado em Modo 1")


if __name__ == "__main__":
    main()
