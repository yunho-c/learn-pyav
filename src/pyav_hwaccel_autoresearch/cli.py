from __future__ import annotations

import argparse
import json
from pathlib import Path

from .fixtures import ensure_fixture, inspect_fixture, list_fixture_assets
from .paths import (
    artifacts_dir,
    fixture_cache_dir,
    logs_dir,
    project_root,
    pyav_checkout_dir,
    results_dir,
)
from .probes import collect_environment_report
from .runner import benchmark_decode, benchmark_encode, write_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PyAV hardware acceleration research utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("doctor", help="Inspect local environment and PyAV/FFmpeg visibility")
    subparsers.add_parser("layout", help="Print project layout and starter fixture targets")

    fixtures_parser = subparsers.add_parser("fixtures", help="List, fetch, and inspect fixtures")
    fixtures_subparsers = fixtures_parser.add_subparsers(dest="fixtures_command", required=True)
    fixtures_subparsers.add_parser("list", help="List available fixture assets")

    fetch_parser = fixtures_subparsers.add_parser("fetch", help="Download a fixture to the cache")
    fetch_parser.add_argument("fixture_key", help="Fixture key from `fixtures list`")

    inspect_parser = fixtures_subparsers.add_parser(
        "inspect",
        help="Download if needed and print probed fixture metadata",
    )
    inspect_parser.add_argument("fixture_key", help="Fixture key from `fixtures list`")

    benchmark_parser = subparsers.add_parser(
        "benchmark",
        help="Run an encode or decode benchmark against a real fixture",
    )
    benchmark_subparsers = benchmark_parser.add_subparsers(
        dest="benchmark_command",
        required=True,
    )

    decode_parser = benchmark_subparsers.add_parser("decode", help="Benchmark video decode")
    decode_parser.add_argument("fixture_key", help="Fixture key from `fixtures list`")
    decode_parser.add_argument("--hwaccel", help="Hardware device name, e.g. videotoolbox")
    decode_parser.add_argument("--repeats", type=int, default=3)
    decode_parser.add_argument("--warmups", type=int, default=1)
    decode_parser.add_argument("--json-output", type=Path)

    encode_parser = benchmark_subparsers.add_parser("encode", help="Benchmark video encode")
    encode_parser.add_argument("fixture_key", help="Fixture key from `fixtures list`")
    encode_parser.add_argument("--codec", required=True, help="Encoder name, e.g. libx264")
    encode_parser.add_argument("--repeats", type=int, default=3)
    encode_parser.add_argument("--warmups", type=int, default=1)
    encode_parser.add_argument("--bit-rate", type=int, default=4_000_000)
    encode_parser.add_argument("--json-output", type=Path)

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
        "fixture_cache_dir": str(fixture_cache_dir()),
        "results_dir": str(results_dir()),
        "logs_dir": str(logs_dir()),
        "fixture_assets": [fixture.to_dict() for fixture in list_fixture_assets()],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_fixtures_list() -> int:
    payload = {"fixtures": [fixture.to_dict() for fixture in list_fixture_assets()]}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_fixtures_fetch(fixture_key: str) -> int:
    path = ensure_fixture(fixture_key)
    print(json.dumps({"fixture_key": fixture_key, "path": str(path)}, indent=2, sort_keys=True))
    return 0


def _cmd_fixtures_inspect(fixture_key: str) -> int:
    fixture = inspect_fixture(fixture_key)
    print(json.dumps(fixture.to_dict(), indent=2, sort_keys=True))
    return 0


def _cmd_benchmark_decode(
    fixture_key: str,
    hwaccel: str | None,
    repeats: int,
    warmups: int,
    json_output: Path | None,
) -> int:
    summary = benchmark_decode(
        fixture_key,
        hwaccel_device=hwaccel,
        repeats=repeats,
        warmups=warmups,
    )
    report_path = write_summary(summary, json_output)
    payload = summary.to_dict()
    payload["report_path"] = str(report_path)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_benchmark_encode(
    fixture_key: str,
    codec_name: str,
    repeats: int,
    warmups: int,
    bit_rate: int,
    json_output: Path | None,
) -> int:
    summary = benchmark_encode(
        fixture_key,
        codec_name=codec_name,
        repeats=repeats,
        warmups=warmups,
        bit_rate=bit_rate,
    )
    report_path = write_summary(summary, json_output)
    payload = summary.to_dict()
    payload["report_path"] = str(report_path)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        return _cmd_doctor()
    if args.command == "layout":
        return _cmd_layout()
    if args.command == "fixtures":
        if args.fixtures_command == "list":
            return _cmd_fixtures_list()
        if args.fixtures_command == "fetch":
            return _cmd_fixtures_fetch(args.fixture_key)
        if args.fixtures_command == "inspect":
            return _cmd_fixtures_inspect(args.fixture_key)
    if args.command == "benchmark":
        if args.benchmark_command == "decode":
            return _cmd_benchmark_decode(
                args.fixture_key,
                args.hwaccel,
                args.repeats,
                args.warmups,
                args.json_output,
            )
        if args.benchmark_command == "encode":
            return _cmd_benchmark_encode(
                args.fixture_key,
                args.codec,
                args.repeats,
                args.warmups,
                args.bit_rate,
                args.json_output,
            )

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
