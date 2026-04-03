from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import matplotlib

matplotlib.use("Agg")

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


def default_suite_graph_path(suite_path: Path, suffix: str = ".png") -> Path:
    return suite_path.with_name(f"{suite_path.stem}-graph{suffix}")


def write_suite_graph(
    suite: dict[str, Any],
    destination: Path,
    *,
    title: str | None = None,
    dpi: int = 160,
) -> Path:
    from matplotlib import pyplot as plt

    rows = [row for row in suite_rows(suite) if row["status"] == "completed"]
    decode_rows = [row for row in rows if row["kind"] == "decode"]
    encode_rows = [row for row in rows if row["kind"] == "encode"]

    if not rows:
        raise ValueError("suite does not contain any completed comparisons to plot")

    def fixture_label(row: dict[str, Any]) -> str:
        return f"{row['fixture_key']} ({row['resolution_key']})"

    fig, axes = plt.subplots(1, 2, figsize=(16, 6), constrained_layout=True)
    kind_specs = [
        ("Decode", decode_rows, axes[0]),
        ("Encode", encode_rows, axes[1]),
    ]
    baseline_color = "#355C7D"
    candidate_color = "#2A9D8F"

    for kind_title, kind_rows, axis in kind_specs:
        if not kind_rows:
            axis.set_visible(False)
            continue

        labels = [fixture_label(row) for row in kind_rows]
        positions = list(range(len(kind_rows)))
        baseline = [float(row["baseline_fps"]) for row in kind_rows]
        candidate = [float(row["candidate_fps"]) for row in kind_rows]
        bar_height = 0.36

        axis.barh(
            [position - bar_height / 2 for position in positions],
            baseline,
            height=bar_height,
            color=baseline_color,
            label="Software",
        )
        axis.barh(
            [position + bar_height / 2 for position in positions],
            candidate,
            height=bar_height,
            color=candidate_color,
            label="Hardware",
        )
        axis.set_title(kind_title)
        axis.set_xlabel("Frames per second")
        axis.set_yticks(positions)
        axis.set_yticklabels(labels)
        axis.invert_yaxis()
        axis.grid(axis="x", alpha=0.25)

        max_value = max(max(baseline), max(candidate))
        padding = max_value * 0.04 if max_value else 1.0
        axis.set_xlim(0, max_value + padding * 6)

        for index, row in enumerate(kind_rows):
            winner = "HW" if row["winner"] == "candidate" else "SW"
            speedup = row["candidate_speedup"]
            axis.text(
                max(baseline[index], candidate[index]) + padding,
                index,
                f"{winner} {speedup:.2f}x",
                va="center",
                fontsize=8,
            )

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=2,
        frameon=False,
    )
    fig.suptitle(title or suite.get("run_id") or "PyAV Compare-All Suite", fontsize=14)

    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return destination
