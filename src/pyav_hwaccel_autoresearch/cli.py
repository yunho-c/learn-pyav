from __future__ import annotations

import argparse
import json

from .fixtures import starter_fixture_specs
from .paths import artifacts_dir, logs_dir, project_root, pyav_checkout_dir, results_dir
from .probes import collect_environment_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PyAV hardware acceleration research utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("doctor", help="Inspect local environment and PyAV/FFmpeg visibility")
    subparsers.add_parser("layout", help="Print project layout and starter fixture targets")
    return parser


def _cmd_doctor() -> int:
    report = collect_environment_report()
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0


def _cmd_layout() -> int:
    payload = {
        "project_root": str(project_root()),
        "pyav_checkout": str(pyav_checkout_dir()),
        "artifacts_dir": str(artifacts_dir()),
        "results_dir": str(results_dir()),
        "logs_dir": str(logs_dir()),
        "starter_fixtures": [fixture.to_dict() for fixture in starter_fixture_specs()],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        return _cmd_doctor()
    if args.command == "layout":
        return _cmd_layout()

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
