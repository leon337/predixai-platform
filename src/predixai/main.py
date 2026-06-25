"""PredixAI application entrypoint."""

from __future__ import annotations

import sys

from predixai.init import create_application


def main() -> int:
    """Initialize the PredixAI foundation and report the current version."""
    try:
        app = create_application()
        report = app.bootstrap()
    except Exception as exc:
        print(f"PredixAI initialization failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"{report.app_name} {report.version} initialized "
        f"in {report.mode} mode."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
