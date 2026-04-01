from pyav_hwaccel_autoresearch.models import (
    BenchmarkCase,
    BenchmarkComparison,
    BenchmarkMeasurement,
    BenchmarkSummary,
    VideoFixtureSpec,
)


def test_frames_per_second_uses_wall_time() -> None:
    measurement = BenchmarkMeasurement(label="decode", wall_seconds=2.0, frames=240)

    assert measurement.frames_per_second == 120.0


def test_to_dict_includes_derived_fps() -> None:
    measurement = BenchmarkMeasurement(label="encode", wall_seconds=4.0, frames=80)

    assert measurement.to_dict()["frames_per_second"] == 20.0


def test_benchmark_comparison_reports_candidate_speedup() -> None:
    fixture = VideoFixtureSpec(
        key="fixture",
        variant_key="720p",
        path="/tmp/input.mp4",
        source_url="https://example.com/input.mp4",
        description="fixture",
        container="mp4",
        codec="h264",
        width=1280,
        height=720,
        fps=30.0,
        duration_seconds=1.0,
        frames=30,
    )
    baseline = BenchmarkSummary(
        benchmark="decode",
        fixture=fixture,
        case=BenchmarkCase(
            name="software",
            mode="decode",
            resolution_key="720p",
            container="mp4",
            codec="h264",
        ),
        measurements=[BenchmarkMeasurement(label="decode:software", wall_seconds=2.0, frames=240)],
        warmups=0,
    )
    candidate = BenchmarkSummary(
        benchmark="decode",
        fixture=fixture,
        case=BenchmarkCase(
            name="videotoolbox",
            mode="decode",
            resolution_key="720p",
            container="mp4",
            codec="h264",
            hardware_accel="videotoolbox",
        ),
        measurements=[
            BenchmarkMeasurement(label="decode:videotoolbox", wall_seconds=1.0, frames=240)
        ],
        warmups=0,
    )

    comparison = BenchmarkComparison(
        benchmark="decode",
        fixture=fixture,
        baseline=baseline,
        candidate=candidate,
    )

    assert comparison.candidate_speedup == 2.0
    assert comparison.winner == "candidate"
