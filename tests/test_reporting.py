from pyav_hwaccel_autoresearch.reporting import render_suite_table, suite_rows


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
