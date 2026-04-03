from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

ReportFormat = Literal["markdown", "json", "tsv"]


def load_suite(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def suite_rows(suite: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for fixture in suite["results"]:
        for comparison_entry in fixture["comparisons"]:
            row: dict[str, Any] = {
                "fixture_key": fixture["fixture_key"],
                "codec_hint": fixture.get("codec_hint"),
                "resolution_key": fixture.get("resolution_key"),
                "kind": comparison_entry["kind"],
                "status": comparison_entry["status"],
            }
            if comparison_entry["status"] == "completed":
                comparison = comparison_entry["comparison"]
                row.update(
                    {
                        "winner": comparison["winner"],
                        "baseline_fps": comparison["baseline"]["median_frames_per_second"],
                        "candidate_fps": comparison["candidate"]["median_frames_per_second"],
                        "candidate_speedup": comparison["candidate_speedup"],
                        "baseline_case": comparison["baseline"]["case"]["name"],
                        "candidate_case": comparison["candidate"]["case"]["name"],
                    }
                )
            else:
                row.update(
                    {
                        "winner": None,
                        "baseline_fps": None,
                        "candidate_fps": None,
                        "candidate_speedup": None,
                        "baseline_case": None,
                        "candidate_case": None,
                        "detail": comparison_entry.get("reason") or comparison_entry.get("error"),
                    }
                )
            rows.append(row)
    return rows


def render_suite_table(suite: dict[str, Any], format: ReportFormat = "markdown") -> str:
    rows = suite_rows(suite)
    if format == "json":
        return json.dumps(rows, indent=2, sort_keys=True)
    if format == "tsv":
        headers = [
            "fixture_key",
            "codec_hint",
            "resolution_key",
            "kind",
            "status",
            "winner",
            "baseline_fps",
            "candidate_fps",
            "candidate_speedup",
        ]
        lines = ["\t".join(headers)]
        for row in rows:
            values = ["" if row.get(header) is None else str(row.get(header)) for header in headers]
            lines.append("\t".join(values))
        return "\n".join(lines)

    headers = [
        "Fixture",
        "Codec",
        "Resolution",
        "Kind",
        "Status",
        "Winner",
        "Baseline FPS",
        "Candidate FPS",
        "Speedup",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        baseline_fps = f"{row['baseline_fps']:.2f}" if row.get("baseline_fps") is not None else ""
        candidate_fps = (
            f"{row['candidate_fps']:.2f}" if row.get("candidate_fps") is not None else ""
        )
        speedup = (
            f"{row['candidate_speedup']:.2f}x" if row.get("candidate_speedup") is not None else ""
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["fixture_key"]),
                    str(row["codec_hint"]),
                    str(row["resolution_key"]),
                    str(row["kind"]),
                    str(row["status"]),
                    "" if row.get("winner") is None else str(row["winner"]),
                    baseline_fps,
                    candidate_fps,
                    speedup,
                ]
            )
            + " |"
        )
    return "\n".join(lines)
