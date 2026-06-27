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
        if args.live_calibrate:
            result = app.live_calibrate()
            print(
                "Live calibration completed: "
                f"{len(result.field_results)} fields, status=READY"
            )
        if args.live_once:
            result = app.live_once()
            report = result["report"] if isinstance(result, dict) else result
            print(
                "Live validation completed: "
                f"{report.total_captures} captures, status={report.status}"
            )
        if args.dashboard:
            from predixai.dashboard.dashboard_server import run_dashboard_server

            run_dashboard_server()
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
    parser.add_argument(
        "--live-calibrate",
        action="store_true",
        help="Run an isolated live calibration pass for broker fields.",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Run the local PredixAI visual dashboard.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
