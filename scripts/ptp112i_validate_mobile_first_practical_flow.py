from predixai.trader.strategy_engine import StrategyInput, MinimalStrategyEngine
from predixai.trader.confluence_engine import ConfluenceEngine
from predixai.mobile.signal_screen import build_mobile_signal_screen
from predixai.trader.paper_trade import build_paper_trade_from_mobile_signal


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    strategy_input = StrategyInput(
        asset="Cafeina Index",
        current_price=101.0,
        previous_price=100.0,
        recent_prices=[99.8, 100.4, 101.0],
    )

    strategy_decision = MinimalStrategyEngine().analyze(strategy_input)
    confluence_result = ConfluenceEngine(minimum_confidence=60.0).evaluate(strategy_decision)
    mobile_screen = build_mobile_signal_screen(confluence_result)

    mobile_data = mobile_screen.to_dict()

    assert_true("asset" in mobile_data, "mobile sem asset")
    assert_true("decision" in mobile_data, "mobile sem decision")
    assert_true("confidence" in mobile_data, "mobile sem confidence")
    assert_true("confluence_level" in mobile_data, "mobile sem confluence_level")
    assert_true("status" in mobile_data, "mobile sem status")

    session = build_paper_trade_from_mobile_signal(
        mobile_screen,
        session_id="PTP112I_SESSION",
        entry_value=5.0,
        initial_balance=100.0,
    )

    exported = session.to_dict()

    assert_true(exported["session_id"] == "PTP112I_SESSION", "session_id incorreto")
    assert_true(exported["initial_balance"] == 100.0, "initial_balance incorreto")
    assert_true("operations_count" in exported, "sem operations_count")

    if mobile_data["status"] == "APROVADO" and mobile_data["decision"] in ("ALTA", "BAIXA"):
        assert_true(exported["operations_count"] == 1, "operação simulada deveria ser aberta")
    else:
        assert_true(exported["operations_count"] == 0, "operação indevida aberta")

    blocked_terms = [
        "login", "senha", "password", "broker", "corretora",
        "saldo real", "ordem real", "click", "clique",
    ]

    blob = str(mobile_data).lower() + str(exported).lower()
    for term in blocked_terms:
        assert_true(term not in blob, f"termo proibido encontrado: {term}")

    print("PTP-112I.3 PASS")
    print("status:", mobile_data["status"])
    print("decision:", mobile_data["decision"])
    print("confidence:", mobile_data["confidence"])
    print("confluence_level:", mobile_data["confluence_level"])
    print("operations_count:", exported["operations_count"])


if __name__ == "__main__":
    main()
