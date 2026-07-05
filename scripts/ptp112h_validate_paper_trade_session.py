from predixai.trader.paper_trade import (
    PaperTradeSession,
    build_paper_trade_from_mobile_signal,
)


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    approved_signal = {
        "asset": "Cafeina Index",
        "decision": "ALTA",
        "confidence": 80,
        "status": "APROVADO",
    }

    session = build_paper_trade_from_mobile_signal(
        approved_signal,
        session_id="PTP112H_TEST",
        entry_value=5.0,
        initial_balance=100.0,
    )

    assert_true(session.session_id == "PTP112H_TEST", "session_id incorreto")
    assert_true(session.operations_count == 1, "operação simulada não foi criada")

    op = session.operations[0]
    assert_true(op.asset == "Cafeina Index", "asset incorreto")
    assert_true(op.direction == "ALTA", "direção incorreta")
    assert_true(op.status == "PENDING", "status inicial incorreto")
    assert_true(op.source == "MOBILE_SIMULATED_SESSION", "source incorreto")

    session.close_operation(op.operation_id, "WIN", 4.0)
    assert_true(session.current_balance == 104.0, "saldo simulado incorreto após WIN")

    rejected_signal = {
        "asset": "Cafeina Index",
        "decision": "BAIXA",
        "confidence": 40,
        "status": "REJEITADO",
    }

    rejected_session = build_paper_trade_from_mobile_signal(
        rejected_signal,
        session_id="PTP112H_REJECTED",
    )

    assert_true(rejected_session.operations_count == 0, "sinal rejeitado não deveria abrir operação")

    wait_signal = {
        "asset": "Cafeina Index",
        "decision": "AGUARDAR",
        "confidence": 0,
        "status": "AGUARDAR",
    }

    wait_session = build_paper_trade_from_mobile_signal(
        wait_signal,
        session_id="PTP112H_WAIT",
    )

    assert_true(wait_session.operations_count == 0, "AGUARDAR não deveria abrir operação")

    raw = PaperTradeSession(session_id="RAW_TEST")
    try:
        raw.open_operation("Cafeina Index", "AGUARDAR", 80, 5)
        raise AssertionError("AGUARDAR abriu operação indevidamente")
    except ValueError:
        pass

    print("PTP-112H MODO 1 VALIDATION: PASS")


if __name__ == "__main__":
    main()
