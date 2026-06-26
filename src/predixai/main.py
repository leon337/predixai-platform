"""PredixAI application entrypoint."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from predixai.init import create_application


def main(argv: Sequence[str] | None = None) -> int:
    """Run PredixAI foundation commands."""
    args = _parse_args(argv)

    try:
        app = create_application()
        report = app.bootstrap()
        print(
            f"{report.app_name} {report.version} initialized "
            f"in {report.mode} mode."
        )
        if args.capture:
            metadata = app.capture_snapshot()
            print(f"Manual capture saved: {metadata.file_path}")
        if args.live_once:
            report = app.live_once()
            print(
                "Live validation completed: "
                f"{report.total_captures} captures, status={report.status}"
            )
    except Exception as exc:
        print(f"PredixAI command failed: {exc}", file=sys.stderr)
        return 1

    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="predixai")
    parser.add_argument(
        "--capture",
        action="store_true",
        help="Capture one manual full-screen PNG snapshot.",
    )
    parser.add_argument(
        "--live-once",
        action="store_true",
        help="Run one live validation candle without automation.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
