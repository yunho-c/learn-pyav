from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any, cast

import typer
from av.codec import Codec

from .fixtures import (
    ensure_fixture,
    ensure_prepared_fixture,
    get_fixture_asset,
    inspect_fixture,
    inspect_fixture_variant,
    list_fixture_assets,
    list_resolution_specs,
    variant_key_for,
)
from .paths import (
    artifacts_dir,
    fixture_cache_dir,
    logs_dir,
    project_root,
    pyav_checkout_dir,
    results_dir,
)
from .probes import collect_environment_report
from .recording import RunRecorder
from .reporting import ReportFormat, load_suite, render_suite_table
from .runner import (
    benchmark_decode,
    benchmark_encode,
    compare_decode,
    compare_encode,
    write_summary,
)

app = typer.Typer(
    help="PyAV hardware acceleration research utilities",
    no_args_is_help=True,
)
fixtures_app = typer.Typer(help="List, fetch, and inspect fixtures", no_args_is_help=True)
benchmark_app = typer.Typer(
    help="Run an encode or decode benchmark against a real fixture",
    no_args_is_help=True,
)
report_app = typer.Typer(help="Render saved benchmark reports", no_args_is_help=True)
app.add_typer(fixtures_app, name="fixtures")
app.add_typer(benchmark_app, name="benchmark")
app.add_typer(report_app, name="report")


def _emit_json(payload: Mapping[str, Any]) -> None:
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


def _workload_key(resolution: str, min_duration_seconds: int | None) -> str:
    return variant_key_for(resolution, min_duration_seconds)


def _fixture_selection(fixture_keys: list[str]) -> list[str]:
    if fixture_keys:
        return fixture_keys
    return [fixture.key for fixture in list_fixture_assets()]


def _encoder_available(codec_name: str) -> bool:
    try:
        Codec(codec_name, "w")
    except Exception:
        return False
    return True


@app.command()
def doctor() -> None:
    """Inspect local environment and PyAV/FFmpeg visibility."""
    report = collect_environment_report()
    _emit_json(report.to_dict())


@app.command()
def layout() -> None:
    """Print project layout and starter fixture targets."""
    payload = {
        "project_root": str(project_root()),
        "pyav_checkout": str(pyav_checkout_dir()),
        "artifacts_dir": str(artifacts_dir()),
        "fixture_cache_dir": str(fixture_cache_dir()),
        "results_dir": str(results_dir()),
        "logs_dir": str(logs_dir()),
        "fixture_assets": [fixture.to_dict() for fixture in list_fixture_assets()],
        "resolution_presets": [resolution.to_dict() for resolution in list_resolution_specs()],
    }
    _emit_json(payload)


@fixtures_app.command("list")
def fixtures_list() -> None:
    """List available fixture assets."""
    payload = {"fixtures": [fixture.to_dict() for fixture in list_fixture_assets()]}
    _emit_json(payload)


@fixtures_app.command("resolutions")
def fixtures_resolutions() -> None:
    """List available resolution presets."""
    payload = {"resolutions": [resolution.to_dict() for resolution in list_resolution_specs()]}
    _emit_json(payload)


@fixtures_app.command("fetch")
def fixtures_fetch(
    fixture_key: Annotated[str, typer.Argument(help="Fixture key from `fixtures list`")],
) -> None:
    """Download a fixture to the cache."""
    path = ensure_fixture(fixture_key)
    _emit_json({"fixture_key": fixture_key, "path": str(path)})


@fixtures_app.command("inspect")
def fixtures_inspect(
    fixture_key: Annotated[str, typer.Argument(help="Fixture key from `fixtures list`")],
) -> None:
    """Download if needed and print probed fixture metadata."""
    fixture = inspect_fixture(fixture_key)
    _emit_json(fixture.to_dict())


@fixtures_app.command("prepare")
def fixtures_prepare(
    fixture_key: Annotated[str, typer.Argument(help="Fixture key from `fixtures list`")],
    resolution: Annotated[
        str,
        typer.Option(help="Resolution preset, e.g. 720p, 1080p, source"),
    ] = "source",
    min_duration_seconds: Annotated[
        int | None,
        typer.Option(help="Prepared steady-state workload duration in seconds"),
    ] = None,
) -> None:
    """Prepare a source fixture variant at a specific resolution."""
    path = ensure_prepared_fixture(
        fixture_key,
        resolution,
        min_duration_seconds=min_duration_seconds,
    )
    fixture = inspect_fixture_variant(
        fixture_key,
        resolution,
        min_duration_seconds=min_duration_seconds,
    )
    _emit_json({"path": str(path), "fixture": fixture.to_dict()})


@benchmark_app.command("decode")
def benchmark_decode_command(
    fixture_key: Annotated[str, typer.Argument(help="Fixture key from `fixtures list`")],
    resolution: Annotated[
        str,
        typer.Option(help="Resolution preset, e.g. 720p, 1080p, source"),
    ] = "source",
    hwaccel: Annotated[
        str | None,
        typer.Option(help="Hardware device name, e.g. videotoolbox"),
    ] = None,
    repeats: Annotated[int, typer.Option(help="Number of measured runs")] = 3,
    warmups: Annotated[int, typer.Option(help="Number of warmup runs")] = 1,
    min_duration_seconds: Annotated[
        int | None,
        typer.Option(help="Prepared steady-state workload duration in seconds"),
    ] = None,
    json_output: Annotated[
        Path | None,
        typer.Option(help="Optional output path for the JSON summary"),
    ] = None,
) -> None:
    """Benchmark video decode."""
    workload_key = _workload_key(resolution, min_duration_seconds)
    recorder = RunRecorder("decode", fixture_key, workload_key, hwaccel or "software")
    recorder.note(f"Preparing fixture {fixture_key} at {workload_key}")
    summary = benchmark_decode(
        fixture_key,
        resolution_key=resolution,
        min_duration_seconds=min_duration_seconds,
        hwaccel_device=hwaccel,
        repeats=repeats,
        warmups=warmups,
        recorder=recorder,
    )
    report_path = write_summary(summary, json_output)
    recorder.write_json("report.json", summary.to_dict())
    recorder.write_json("environment.json", collect_environment_report().to_dict())
    recorder.write_summary(summary)
    recorder.print_summary(summary)
    payload = summary.to_dict()
    payload["report_path"] = str(report_path)
    payload["run_dir"] = str(recorder.run_dir)
    payload["run_id"] = recorder.run_id
    _emit_json(payload)


@benchmark_app.command("encode")
def benchmark_encode_command(
    fixture_key: Annotated[str, typer.Argument(help="Fixture key from `fixtures list`")],
    codec: Annotated[str, typer.Option(help="Encoder name, e.g. libx264")],
    resolution: Annotated[
        str,
        typer.Option(help="Resolution preset, e.g. 720p, 1080p, source"),
    ] = "source",
    repeats: Annotated[int, typer.Option(help="Number of measured runs")] = 3,
    warmups: Annotated[int, typer.Option(help="Number of warmup runs")] = 1,
    min_duration_seconds: Annotated[
        int | None,
        typer.Option(help="Prepared steady-state workload duration in seconds"),
    ] = None,
    bit_rate: Annotated[int, typer.Option(help="Target encoder bitrate in bits/sec")] = 4_000_000,
    json_output: Annotated[
        Path | None,
        typer.Option(help="Optional output path for the JSON summary"),
    ] = None,
) -> None:
    """Benchmark video encode."""
    workload_key = _workload_key(resolution, min_duration_seconds)
    recorder = RunRecorder("encode", fixture_key, workload_key, codec)
    recorder.note(f"Preparing fixture {fixture_key} at {workload_key}")
    summary = benchmark_encode(
        fixture_key,
        resolution_key=resolution,
        min_duration_seconds=min_duration_seconds,
        codec_name=codec,
        repeats=repeats,
        warmups=warmups,
        bit_rate=bit_rate,
        recorder=recorder,
    )
    report_path = write_summary(summary, json_output)
    recorder.write_json("report.json", summary.to_dict())
    recorder.write_json("environment.json", collect_environment_report().to_dict())
    recorder.write_summary(summary)
    recorder.print_summary(summary)
    payload = summary.to_dict()
    payload["report_path"] = str(report_path)
    payload["run_dir"] = str(recorder.run_dir)
    payload["run_id"] = recorder.run_id
    _emit_json(payload)


@benchmark_app.command("compare-decode")
def benchmark_compare_decode_command(
    fixture_key: Annotated[str, typer.Argument(help="Fixture key from `fixtures list`")],
    hwaccel: Annotated[
        str,
        typer.Option(help="Candidate hardware device name, e.g. videotoolbox"),
    ],
    resolution: Annotated[
        str,
        typer.Option(help="Resolution preset, e.g. 720p, 1080p, source"),
    ] = "source",
    repeats: Annotated[int, typer.Option(help="Number of measured runs")] = 3,
    warmups: Annotated[int, typer.Option(help="Number of warmup runs")] = 1,
    min_duration_seconds: Annotated[
        int | None,
        typer.Option(help="Prepared steady-state workload duration in seconds"),
    ] = None,
) -> None:
    """Compare software decode against a hardware decode candidate."""
    workload_key = _workload_key(resolution, min_duration_seconds)
    recorder = RunRecorder("compare-decode", fixture_key, workload_key, hwaccel)
    recorder.note(f"Preparing fixture {fixture_key} at {workload_key}")
    comparison = compare_decode(
        fixture_key,
        resolution_key=resolution,
        min_duration_seconds=min_duration_seconds,
        candidate_hwaccel_device=hwaccel,
        repeats=repeats,
        warmups=warmups,
        recorder=recorder,
    )
    recorder.write_json("baseline.json", comparison.baseline.to_dict())
    recorder.write_json("candidate.json", comparison.candidate.to_dict())
    recorder.write_json("environment.json", collect_environment_report().to_dict())
    recorder.write_comparison(comparison)
    recorder.print_comparison(comparison)
    payload = comparison.to_dict()
    payload["run_dir"] = str(recorder.run_dir)
    payload["run_id"] = recorder.run_id
    _emit_json(payload)


@benchmark_app.command("compare-encode")
def benchmark_compare_encode_command(
    fixture_key: Annotated[str, typer.Argument(help="Fixture key from `fixtures list`")],
    baseline_codec: Annotated[
        str,
        typer.Option(help="Baseline encoder name, e.g. libx264"),
    ],
    candidate_codec: Annotated[
        str,
        typer.Option(help="Candidate encoder name, e.g. h264_videotoolbox"),
    ],
    resolution: Annotated[
        str,
        typer.Option(help="Resolution preset, e.g. 720p, 1080p, source"),
    ] = "source",
    repeats: Annotated[int, typer.Option(help="Number of measured runs")] = 3,
    warmups: Annotated[int, typer.Option(help="Number of warmup runs")] = 1,
    min_duration_seconds: Annotated[
        int | None,
        typer.Option(help="Prepared steady-state workload duration in seconds"),
    ] = None,
    bit_rate: Annotated[int, typer.Option(help="Target encoder bitrate in bits/sec")] = 4_000_000,
) -> None:
    """Compare one encoder against another on the same workload."""
    case_label = f"{baseline_codec}-vs-{candidate_codec}"
    workload_key = _workload_key(resolution, min_duration_seconds)
    recorder = RunRecorder("compare-encode", fixture_key, workload_key, case_label)
    recorder.note(f"Preparing fixture {fixture_key} at {workload_key}")
    comparison = compare_encode(
        fixture_key,
        resolution_key=resolution,
        min_duration_seconds=min_duration_seconds,
        baseline_codec_name=baseline_codec,
        candidate_codec_name=candidate_codec,
        repeats=repeats,
        warmups=warmups,
        bit_rate=bit_rate,
        recorder=recorder,
    )
    recorder.write_json("baseline.json", comparison.baseline.to_dict())
    recorder.write_json("candidate.json", comparison.candidate.to_dict())
    recorder.write_json("environment.json", collect_environment_report().to_dict())
    recorder.write_comparison(comparison)
    recorder.print_comparison(comparison)
    payload = comparison.to_dict()
    payload["run_dir"] = str(recorder.run_dir)
    payload["run_id"] = recorder.run_id
    _emit_json(payload)


@benchmark_app.command("compare-all")
def benchmark_compare_all_command(
    fixture: Annotated[
        list[str] | None,
        typer.Option(help="Optional fixture key filter; repeat for multiple fixtures"),
    ] = None,
    resolution: Annotated[
        str,
        typer.Option(help="Resolution preset, e.g. 720p, 1080p, source"),
    ] = "source",
    repeats: Annotated[int, typer.Option(help="Number of measured runs")] = 3,
    warmups: Annotated[int, typer.Option(help="Number of warmup runs")] = 1,
    min_duration_seconds: Annotated[
        int | None,
        typer.Option(help="Prepared steady-state workload duration in seconds"),
    ] = None,
    bit_rate: Annotated[int, typer.Option(help="Target encoder bitrate in bits/sec")] = 4_000_000,
) -> None:
    """Run the established comparison set across the fixture catalog."""
    workload_key = _workload_key(resolution, min_duration_seconds)
    fixture_keys = _fixture_selection(fixture or [])
    fixture_label = "all-fixtures" if not fixture else "-".join(fixture_keys)
    recorder = RunRecorder("compare-all", fixture_label, workload_key, "catalog")
    recorder.note(f"Running catalog comparisons at {workload_key}")

    environment = collect_environment_report()
    recorder.write_json("environment.json", environment.to_dict())
    videotoolbox_available = "videotoolbox" in environment.pyav_hwdevices

    suite_results: list[dict[str, Any]] = []
    for fixture_key in fixture_keys:
        asset = get_fixture_asset(fixture_key)
        codec_hint = asset.codec_hint
        recorder.emit(
            "fixture_started",
            {
                "fixture_key": fixture_key,
                "codec_hint": codec_hint,
            },
        )

        if codec_hint == "h264":
            decode_hwaccel = "videotoolbox"
            baseline_codec = "libx264"
            candidate_codec = "h264_videotoolbox"
        elif codec_hint == "hevc":
            decode_hwaccel = "videotoolbox"
            baseline_codec = "libx265"
            candidate_codec = "hevc_videotoolbox"
        else:
            suite_results.append(
                {
                    "fixture_key": fixture_key,
                    "codec_hint": codec_hint,
                    "status": "skipped",
                    "reason": f"no comparison plan for codec {codec_hint!r}",
                }
            )
            recorder.emit(
                "fixture_skipped",
                {
                    "fixture_key": fixture_key,
                    "reason": f"no comparison plan for codec {codec_hint!r}",
                },
            )
            continue

        fixture_result: dict[str, Any] = {
            "fixture_key": fixture_key,
            "codec_hint": codec_hint,
            "resolution_key": workload_key,
            "comparisons": [],
        }

        if videotoolbox_available:
            try:
                decode_comparison = compare_decode(
                    fixture_key,
                    resolution_key=resolution,
                    min_duration_seconds=min_duration_seconds,
                    candidate_hwaccel_device=decode_hwaccel,
                    repeats=repeats,
                    warmups=warmups,
                    recorder=recorder,
                )
                fixture_result["comparisons"].append(
                    {
                        "kind": "decode",
                        "status": "completed",
                        "comparison": decode_comparison.to_dict(),
                    }
                )
            except Exception as exc:
                fixture_result["comparisons"].append(
                    {
                        "kind": "decode",
                        "status": "failed",
                        "error": str(exc),
                    }
                )
        else:
            fixture_result["comparisons"].append(
                {
                    "kind": "decode",
                    "status": "skipped",
                    "reason": "videotoolbox is not available in this environment",
                }
            )

        if _encoder_available(baseline_codec) and _encoder_available(candidate_codec):
            try:
                encode_comparison = compare_encode(
                    fixture_key,
                    resolution_key=resolution,
                    min_duration_seconds=min_duration_seconds,
                    baseline_codec_name=baseline_codec,
                    candidate_codec_name=candidate_codec,
                    repeats=repeats,
                    warmups=warmups,
                    bit_rate=bit_rate,
                    recorder=recorder,
                )
                fixture_result["comparisons"].append(
                    {
                        "kind": "encode",
                        "status": "completed",
                        "comparison": encode_comparison.to_dict(),
                    }
                )
            except Exception as exc:
                fixture_result["comparisons"].append(
                    {
                        "kind": "encode",
                        "status": "failed",
                        "error": str(exc),
                    }
                )
        else:
            fixture_result["comparisons"].append(
                {
                    "kind": "encode",
                    "status": "skipped",
                    "reason": (
                        f"required encoders unavailable: {baseline_codec}, {candidate_codec}"
                    ),
                }
            )

        recorder.emit(
            "fixture_completed",
            {
                "fixture_key": fixture_key,
                "comparison_count": len(fixture_result["comparisons"]),
            },
        )
        suite_results.append(fixture_result)

    payload = {
        "benchmark": "compare-all",
        "fixture_keys": fixture_keys,
        "resolution_key": workload_key,
        "min_duration_seconds": min_duration_seconds,
        "repeats": repeats,
        "warmups": warmups,
        "bit_rate": bit_rate,
        "results": suite_results,
        "run_dir": str(recorder.run_dir),
        "run_id": recorder.run_id,
    }
    recorder.write_json("suite.json", payload)
    _emit_json(payload)


@report_app.command("suite-table")
def report_suite_table_command(
    suite_path: Annotated[
        Path,
        typer.Argument(help="Path to a saved suite.json file"),
    ],
    format: Annotated[
        str,
        typer.Option(help="Output format: markdown, json, or tsv"),
    ] = "markdown",
) -> None:
    """Render a flat aggregate table from a saved suite.json."""
    if format not in {"markdown", "json", "tsv"}:
        raise typer.BadParameter("format must be one of: markdown, json, tsv")
    suite = load_suite(suite_path)
    typer.echo(render_suite_table(suite, format=cast(ReportFormat, format)))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
