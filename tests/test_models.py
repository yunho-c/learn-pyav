from pyav_hwaccel_autoresearch.models import BenchmarkMeasurement


def test_frames_per_second_uses_wall_time() -> None:
    measurement = BenchmarkMeasurement(label="decode", wall_seconds=2.0, frames=240)

    assert measurement.frames_per_second == 120.0


def test_to_dict_includes_derived_fps() -> None:
    measurement = BenchmarkMeasurement(label="encode", wall_seconds=4.0, frames=80)

    assert measurement.to_dict()["frames_per_second"] == 20.0
