from pyav_hwaccel_autoresearch.models import (
    BenchmarkCase,
    BenchmarkMeasurement,
    BenchmarkSummary,
    VideoFixtureSpec,
)
from pyav_hwaccel_autoresearch.runner import default_report_path


def test_default_report_path_uses_benchmark_directory() -> None:
    summary = BenchmarkSummary(
        benchmark="decode",
        fixture=VideoFixtureSpec(
            key="fixture",
            variant_key="source",
            path="/tmp/input.mp4",
            source_url="https://example.com/input.mp4",
            description="fixture",
            container="mp4",
            codec="h264",
            width=1280,
            height=720,
            fps=25.0,
            duration_seconds=1.0,
            frames=25,
        ),
        case=BenchmarkCase(
            name="fixture-decode-software",
            mode="decode",
            resolution_key="source",
            container="mp4",
            codec="h264",
        ),
        measurements=[BenchmarkMeasurement(label="decode:software", wall_seconds=1.0, frames=25)],
        warmups=0,
    )

    assert default_report_path(summary).suffix == ".json"
    assert "benchmarks" in default_report_path(summary).parts
