from predixai.mobile.operational_preview import calculate_operational_preview

sample = {
    "strategy_mode": "scalper",
    "min_confidence": 0.75,
    "initial_bankroll": 100,
    "initial_entry": 5,
    "risk_profile": "moderate",
    "stop_loss": 20,
    "take_profit": 20,
    "max_signals": 10,
    "max_losses": 3,
    "payout_min": 0.80,
    "expiration_seconds": 60,
    "recovery_enabled": True,
    "max_recovery_steps": 1,
    "recovery_multiplier": 2,
}

preview = calculate_operational_preview(sample)

required = [
    "profile",
    "risk_index",
    "estimated_signals_5m",
    "estimated_signals_hour",
    "scalper_compatible",
    "day_trade_compatible",
    "expected_exposure",
    "stop_supported",
    "recovery_risk",
    "payout_impact",
    "alerts",
    "recommendations",
]

fails = []
for key in required:
    if key not in preview:
        fails.append(f"missing:{key}")

if not isinstance(preview["alerts"], list):
    fails.append("alerts_not_list")

if not isinstance(preview["recommendations"], list):
    fails.append("recommendations_not_list")

if not 0 <= preview["risk_index"] <= 100:
    fails.append("risk_index_out_of_range")

print("PTP-112C VALIDATION")
print("PREVIEW:", preview)
print("PASS" if not fails else "FAIL")
for fail in fails:
    print("FAIL:", fail)

raise SystemExit(1 if fails else 0)
