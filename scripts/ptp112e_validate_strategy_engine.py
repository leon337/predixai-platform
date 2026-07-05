from predixai.trader.strategy_engine import (
    ALTA,
    BAIXA,
    AGUARDAR,
    MinimalStrategyEngine,
    StrategyInput,
)


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


engine = MinimalStrategyEngine()

alta = engine.analyze(
    StrategyInput(
        asset="Cafeina Index",
        previous_price=100.0,
        current_price=101.0,
        recent_prices=[99.8, 100.4, 101.0],
    )
)
assert_true(alta.decision == ALTA, "deveria gerar ALTA")
assert_true(alta.confidence > 0, "confiança da ALTA inválida")
assert_true(alta.reason, "motivo da ALTA ausente")

baixa = engine.analyze(
    StrategyInput(
        asset="Cafeina Index",
        previous_price=101.0,
        current_price=100.0,
        recent_prices=[101.2, 100.6, 100.0],
    )
)
assert_true(baixa.decision == BAIXA, "deveria gerar BAIXA")
assert_true(baixa.confidence > 0, "confiança da BAIXA inválida")
assert_true(baixa.reason, "motivo da BAIXA ausente")

aguardar = engine.analyze(
    StrategyInput(
        asset="Cafeina Index",
        previous_price=100.0,
        current_price=100.0,
    )
)
assert_true(aguardar.decision == AGUARDAR, "deveria gerar AGUARDAR")
assert_true(aguardar.confidence == 0.0, "confiança do AGUARDAR inválida")
assert_true(aguardar.reason, "motivo do AGUARDAR ausente")

snapshot = alta.to_dict()
for key in ["decision", "confidence", "reason", "asset", "timestamp"]:
    assert_true(key in snapshot, f"campo ausente: {key}")

for invalid in [
    StrategyInput(asset="", previous_price=100, current_price=101),
    StrategyInput(asset="Teste", previous_price=0, current_price=101),
    StrategyInput(asset="Teste", previous_price=100, current_price=0),
]:
    try:
        engine.analyze(invalid)
        raise AssertionError("entrada inválida deveria falhar")
    except ValueError:
        pass

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
source = open("src/predixai/trader/strategy_engine.py", "r", encoding="utf-8").read()
for term in blocked_terms:
    assert_true(term not in source, f"termo proibido encontrado: {term}")

print("PASS: PTP-112E Strategy Engine Mínimo validado")
