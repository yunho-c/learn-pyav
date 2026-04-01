from __future__ import annotations

import json
import platform
import socket
import subprocess
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from .models import BenchmarkComparison, BenchmarkSummary
from .paths import results_index_path, run_results_dir


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _slugify(value: str) -> str:
    allowed = []
    for char in value:
        if char.isalnum() or char in {"-", "_"}:
            allowed.append(char.lower())
        else:
            allowed.append("-")
    return "".join(allowed).strip("-")


def _git_sha() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


class RunRecorder:
    def __init__(self, benchmark: str, fixture_key: str, resolution_key: str, case_label: str):
        timestamp = _now_utc()
        slug = _slugify(f"{benchmark}-{fixture_key}-{resolution_key}-{case_label}")
        self.run_id = f"{timestamp.strftime('%Y%m%dT%H%M%SZ')}-{slug}"
        self.run_dir = run_results_dir() / self.run_id
        self.events_path = self.run_dir / "events.jsonl"
        self.console = Console(stderr=True)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.context = {
            "run_id": self.run_id,
            "started_at": timestamp.isoformat(),
            "benchmark": benchmark,
            "fixture_key": fixture_key,
            "resolution_key": resolution_key,
            "case_label": case_label,
            "git_sha": _git_sha(),
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
        }
        self.write_json("run.json", self.context)

    def emit(self, event: str, payload: Mapping[str, Any] | None = None) -> None:
        record = {
            "timestamp": _now_utc().isoformat(),
            "event": event,
            "payload": dict(payload or {}),
        }
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def note(self, message: str) -> None:
        self.console.print(f"[bold cyan]{message}[/bold cyan]")

    def write_json(self, name: str, payload: Mapping[str, Any]) -> Path:
        path = self.run_dir / name
        path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True))
        return path

    def write_summary(self, summary: BenchmarkSummary) -> Path:
        path = self.write_json("summary.json", summary.to_dict())
        index_entry = {
            "run_id": self.run_id,
            "run_dir": str(self.run_dir),
            "benchmark": summary.benchmark,
            "fixture_key": summary.fixture.key,
            "resolution_key": summary.fixture.variant_key,
            "case_name": summary.case.name,
            "codec": summary.case.codec,
            "hardware_accel": summary.case.hardware_accel,
            "median_wall_seconds": summary.median_wall_seconds,
            "median_frames_per_second": summary.median_frames_per_second,
        }
        index_path = results_index_path()
        index_path.parent.mkdir(parents=True, exist_ok=True)
        with index_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(index_entry, sort_keys=True) + "\n")
        return path

    def write_comparison(self, comparison: BenchmarkComparison) -> Path:
        path = self.write_json("comparison.json", comparison.to_dict())
        index_entry = {
            "run_id": self.run_id,
            "run_dir": str(self.run_dir),
            "benchmark": comparison.benchmark,
            "fixture_key": comparison.fixture.key,
            "resolution_key": comparison.fixture.variant_key,
            "baseline_case_name": comparison.baseline.case.name,
            "candidate_case_name": comparison.candidate.case.name,
            "candidate_speedup": comparison.candidate_speedup,
            "winner": comparison.winner,
        }
        index_path = results_index_path()
        index_path.parent.mkdir(parents=True, exist_ok=True)
        with index_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(index_entry, sort_keys=True) + "\n")
        return path

    def print_summary(self, summary: BenchmarkSummary) -> None:
        table = Table(title=f"{summary.benchmark.title()} Benchmark")
        table.add_column("Field", style="bold")
        table.add_column("Value")
        table.add_row("Fixture", summary.fixture.key)
        table.add_row("Resolution", summary.fixture.variant_key)
        table.add_row("Case", summary.case.name)
        table.add_row("Codec", summary.case.codec)
        table.add_row("HWAccel", summary.case.hardware_accel or "software")
        table.add_row("Median wall", f"{summary.median_wall_seconds:.4f}s")
        table.add_row("Median FPS", f"{summary.median_frames_per_second:.2f}")
        table.add_row("Run ID", self.run_id)
        self.console.print(table)
        self.console.print(f"[green]Saved run data[/green] {self.run_dir}")

    def print_comparison(self, comparison: BenchmarkComparison) -> None:
        table = Table(title=f"{comparison.benchmark.title()} Comparison")
        table.add_column("Field", style="bold")
        table.add_column("Value")
        table.add_row("Fixture", comparison.fixture.key)
        table.add_row("Resolution", comparison.fixture.variant_key)
        table.add_row("Baseline", comparison.baseline.case.name)
        table.add_row("Candidate", comparison.candidate.case.name)
        table.add_row(
            "Baseline FPS",
            f"{comparison.baseline.median_frames_per_second:.2f}",
        )
        table.add_row(
            "Candidate FPS",
            f"{comparison.candidate.median_frames_per_second:.2f}",
        )
        table.add_row("Candidate speedup", f"{comparison.candidate_speedup:.2f}x")
        table.add_row("Winner", comparison.winner)
        table.add_row("Run ID", self.run_id)
        self.console.print(table)
        self.console.print(f"[green]Saved run data[/green] {self.run_dir}")
