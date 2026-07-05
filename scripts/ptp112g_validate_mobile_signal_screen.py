from predixai.mobile.signal_screen import MobileSignalScreen, build_mobile_signal_screen


def main() -> None:
    data = {
        "asset": "Cafeina Index",
        "decision": "ALTA",
        "confidence": 82.5,
        "confluence_level": "ALTA",
        "status": "APROVADO",
    }

    screen = build_mobile_signal_screen(data)
    payload = screen.to_dict()

    assert payload["asset"] == "Cafeina Index"
    assert payload["decision"] == "ALTA"
    assert payload["confidence"] == 82.5
    assert payload["confluence_level"] == "ALTA"
    assert payload["status"] == "APROVADO"
    assert payload["session_status"] == "SIMULADA"
    assert payload["bank_mode"] == "SIMULADO"
    assert payload["generated_at"]

    MobileSignalScreen(
        asset="Cafeina Index",
        decision="AGUARDAR",
        confidence=40,
        confluence_level="NEUTRA",
        status="AGUARDAR",
    )

    print("PASS: PTP-112G mobile signal screen validada")


if __name__ == "__main__":
    main()
