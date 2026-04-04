from pathlib import Path

from pyav_hwaccel_autoresearch.reporting import (
    default_suite_graph_path,
    latest_suite_path,
    render_suite_table,
    resolve_suite_path,
    suite_rows,
    write_suite_graph,
)


def _sample_suite() -> dict:
    return {
        "benchmark": "compare-all",
        "results": [
            {
                "fixture_key": "fixture-a",
                "codec_hint": "h264",
                "resolution_key": "source-30s",
                "comparisons": [
                    {
                        "kind": "decode",
                        "status": "completed",
                        "comparison": {
                            "winner": "baseline",
                            "candidate_speedup": 0.75,
                            "baseline": {
                                "case": {"name": "baseline-case"},
                                "median_frames_per_second": 100.0,
                            },
                            "candidate": {
                                "case": {"name": "candidate-case"},
                                "median_frames_per_second": 75.0,
                            },
                        },
                    },
                    {
                        "kind": "encode",
                        "status": "skipped",
                        "reason": "encoder unavailable",
                    },
                ],
            }
        ],
    }


def test_suite_rows_flattens_comparisons() -> None:
    rows = suite_rows(_sample_suite())

    assert len(rows) == 2
    assert rows[0]["fixture_key"] == "fixture-a"
    assert rows[0]["kind"] == "decode"
    assert rows[0]["winner"] == "baseline"
    assert rows[1]["status"] == "skipped"
    assert rows[1]["detail"] == "encoder unavailable"


def test_render_suite_table_outputs_markdown() -> None:
    table = render_suite_table(_sample_suite())

    assert "| Fixture | Codec | Resolution | Kind | Status | Winner |" in table
    assert "| fixture-a | h264 | source-30s | decode | completed | baseline |" in table


def test_render_suite_table_outputs_tsv() -> None:
    table = render_suite_table(_sample_suite(), format="tsv")

    assert table.splitlines()[0].startswith("fixture_key\tcodec_hint\tresolution_key")
    assert "fixture-a\th264\tsource-30s\tdecode\tcompleted\tbaseline" in table


def test_default_suite_graph_path_uses_neighbor_file() -> None:
    suite_path = default_suite_graph_path.__globals__["Path"]("results/runs/run-1/suite.json")

    assert default_suite_graph_path(suite_path).name == "suite-graph.png"


def test_resolve_suite_path_returns_explicit_path() -> None:
    suite_path = Path("results/runs/run-1/suite.json")

    assert resolve_suite_path(suite_path) == suite_path


def test_latest_suite_path_finds_newest(monkeypatch, tmp_path) -> None:
    run_a = tmp_path / "run-a"
    run_b = tmp_path / "run-b"
    run_a.mkdir()
    run_b.mkdir()
    older = run_a / "suite.json"
    newer = run_b / "suite.json"
    older.write_text("{}")
    newer.write_text("{}")
    newer.touch()

    monkeypatch.setattr(
        "pyav_hwaccel_autoresearch.reporting.run_results_dir",
        lambda: tmp_path,
    )

    assert latest_suite_path() == newer
    assert resolve_suite_path(Path("latest")) == newer


def test_write_suite_graph_creates_image(tmp_path) -> None:
    destination = tmp_path / "suite-graph.svg"

    path = write_suite_graph(_sample_suite(), destination, title="Sample Suite", dpi=120)

    assert path == destination
    assert destination.exists()
    assert destination.read_text().lstrip().startswith("<?xml")
