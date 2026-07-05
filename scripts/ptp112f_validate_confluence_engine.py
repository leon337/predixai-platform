from predixai.trader.confluence_engine import ConfluenceEngine


def assert_equal(name, actual, expected):
    if actual != expected:
        raise AssertionError(f"{name}: esperado {expected}, recebido {actual}")


def main():
    engine = ConfluenceEngine(minimum_confidence=60.0)

    approved = engine.evaluate({
        "decision": "ALTA",
        "confidence": 75.0,
        "asset": "Cafeina Index",
    })
    assert_equal("aprovado.status", approved.status, "APROVADO")
    assert approved.reason
    assert approved.to_dict()["status"] == "APROVADO"

    rejected = engine.evaluate({
        "decision": "BAIXA",
        "confidence": 45.0,
        "asset": "Cafeina Index",
    })
    assert_equal("rejected.status", rejected.status, "REJEITADO")

    waiting = engine.evaluate({
        "decision": "AGUARDAR",
        "confidence": 20.0,
        "asset": "Cafeina Index",
    })
    assert_equal("waiting.status", waiting.status, "AGUARDAR")

    invalid_cases = [
        {},
        {"decision": "COMPRA", "confidence": 70, "asset": "Cafeina Index"},
        {"decision": "ALTA", "confidence": -1, "asset": "Cafeina Index"},
        {"decision": "ALTA", "confidence": 96, "asset": "Cafeina Index"},
        {"decision": "ALTA", "confidence": 70, "asset": ""},
    ]

    for case in invalid_cases:
        try:
            engine.evaluate(case)
        except ValueError:
            pass
        else:
            raise AssertionError(f"caso inválido aceito indevidamente: {case}")

    blocked_terms = [
        "send_order",
        "buy(",
        "sell(",
        "click(",
        "deposit",
        "withdraw",
        "password",
        "real_balance",
        "login",
    ]

    source = open("src/predixai/trader/confluence_engine.py", "r", encoding="utf-8").read()
    for term in blocked_terms:
        if term in source:
            raise AssertionError(f"termo bloqueado encontrado: {term}")

    print("PASS: PTP-112F Confluence Engine validado em Modo 1.")


if __name__ == "__main__":
    main()
