from __future__ import annotations

import json
import resource
import tempfile
import time
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path
from typing import cast

import av
from av.codec.hwaccel import HWAccel
from av.video.stream import VideoStream

from .fixtures import ensure_prepared_fixture, inspect_fixture_variant
from .models import BenchmarkCase, BenchmarkMeasurement, BenchmarkSummary
from .paths import benchmark_report_dir
from .recording import RunRecorder


def _cpu_seconds() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_utime + usage.ru_stime


def _rate_or_default(value: Fraction | None, default: int = 30) -> Fraction | int:
    if value is None:
        return default
    return value


def _validate_frame_count(expected_frames: int, observed_frames: int) -> None:
    if expected_frames > 0 and observed_frames != expected_frames:
        raise RuntimeError(
            f"Expected {expected_frames} frames but observed {observed_frames} frames"
        )


def _decode_once(fixture_path: Path, hwaccel_device: str | None) -> BenchmarkMeasurement:
    cpu_start = _cpu_seconds()
    wall_start = time.perf_counter()
    if hwaccel_device is None:
        container = av.open(str(fixture_path))
    else:
        container = av.open(
            str(fixture_path),
            hwaccel=HWAccel(
                device_type=hwaccel_device,
                allow_software_fallback=False,
            ),
        )

    with container:
        stream = container.streams.video[0]
        if hwaccel_device is None:
            stream.thread_type = "AUTO"

        frame_count = 0
        for _frame in container.decode(video=0):
            frame_count += 1

        is_hwaccel = bool(stream.codec_context.is_hwaccel)
        expected_frames = stream.frames
        codec_name = stream.codec_context.name
        width = stream.width
        height = stream.height
    wall_seconds = time.perf_counter() - wall_start
    cpu_seconds = _cpu_seconds() - cpu_start

    if hwaccel_device is not None and not is_hwaccel:
        raise RuntimeError(f"Hardware decode did not activate for {hwaccel_device}")

    _validate_frame_count(expected_frames, frame_count)
    label = f"decode:{hwaccel_device or 'software'}"
    return BenchmarkMeasurement(
        label=label,
        wall_seconds=wall_seconds,
        cpu_seconds=cpu_seconds,
        frames=frame_count,
        metadata={
            "codec": codec_name,
            "height": height,
            "is_hwaccel": is_hwaccel,
            "width": width,
        },
    )


def _encode_once(fixture_path: Path, codec_name: str, bit_rate: int) -> BenchmarkMeasurement:
    with tempfile.TemporaryDirectory(prefix="pyav-bench-") as tmp_dir_name:
        output_path = Path(tmp_dir_name) / f"encode-{codec_name}.mp4"

        with av.open(str(fixture_path)) as input_container:
            input_stream = input_container.streams.video[0]
            expected_frames = input_stream.frames
            output_rate = _rate_or_default(input_stream.average_rate)

            with av.open(str(output_path), "w") as output_container:
                output_stream = cast(
                    VideoStream,
                    output_container.add_stream(codec_name, rate=output_rate),
                )
                output_stream.width = input_stream.width
                output_stream.height = input_stream.height
                output_stream.pix_fmt = "yuv420p"
                output_stream.bit_rate = bit_rate

                frame_count = 0
                cpu_start = _cpu_seconds()
                wall_start = time.perf_counter()
                for frame in input_container.decode(video=0):
                    frame_count += 1
                    if frame.format.name != "yuv420p":
                        frame = frame.reformat(
                            width=input_stream.width,
                            height=input_stream.height,
                            format="yuv420p",
                        )
                    output_container.mux(output_stream.encode(frame))
                output_container.mux(output_stream.encode(None))
                wall_seconds = time.perf_counter() - wall_start
                cpu_seconds = _cpu_seconds() - cpu_start

        with av.open(str(output_path)) as encoded_container:
            output_frames = sum(1 for _frame in encoded_container.decode(video=0))
            output_stream = encoded_container.streams.video[0]
            output_codec = output_stream.codec_context.name

        _validate_frame_count(expected_frames, frame_count)
        _validate_frame_count(expected_frames, output_frames)
        return BenchmarkMeasurement(
            label=f"encode:{codec_name}",
            wall_seconds=wall_seconds,
            cpu_seconds=cpu_seconds,
            frames=frame_count,
            bytes_total=output_path.stat().st_size,
            metadata={
                "bit_rate": bit_rate,
                "output_codec": output_codec,
                "validated_output_frames": output_frames,
            },
        )


def benchmark_decode(
    fixture_key: str,
    *,
    resolution_key: str,
    hwaccel_device: str | None,
    repeats: int,
    warmups: int,
    recorder: RunRecorder | None = None,
) -> BenchmarkSummary:
    fixture_path = ensure_prepared_fixture(fixture_key, resolution_key)
    fixture = inspect_fixture_variant(fixture_key, resolution_key)
    case = BenchmarkCase(
        name=f"{fixture_key}-{resolution_key}-decode-{hwaccel_device or 'software'}",
        mode="decode",
        resolution_key=resolution_key,
        container=fixture.container,
        codec=fixture.codec,
        hardware_accel=hwaccel_device,
    )

    if recorder is not None:
        recorder.emit(
            "benchmark_started",
            {
                "benchmark": "decode",
                "fixture_key": fixture_key,
                "resolution_key": resolution_key,
                "hardware_accel": hwaccel_device,
            },
        )

    for _ in range(warmups):
        _decode_once(fixture_path, hwaccel_device)

    measurements = [_decode_once(fixture_path, hwaccel_device) for _ in range(repeats)]
    if recorder is not None:
        for measurement in measurements:
            recorder.emit("measurement_completed", measurement.to_dict())
    return BenchmarkSummary(
        benchmark="decode",
        fixture=fixture,
        case=case,
        measurements=measurements,
        warmups=warmups,
    )


def benchmark_encode(
    fixture_key: str,
    *,
    resolution_key: str,
    codec_name: str,
    repeats: int,
    warmups: int,
    bit_rate: int,
    recorder: RunRecorder | None = None,
) -> BenchmarkSummary:
    fixture_path = ensure_prepared_fixture(fixture_key, resolution_key)
    fixture = inspect_fixture_variant(fixture_key, resolution_key)
    case = BenchmarkCase(
        name=f"{fixture_key}-{resolution_key}-encode-{codec_name}",
        mode="encode",
        resolution_key=resolution_key,
        container="mp4",
        codec=codec_name,
        hardware_accel="videotoolbox" if "videotoolbox" in codec_name else None,
        options={"bit_rate": str(bit_rate)},
    )

    if recorder is not None:
        recorder.emit(
            "benchmark_started",
            {
                "benchmark": "encode",
                "fixture_key": fixture_key,
                "resolution_key": resolution_key,
                "codec": codec_name,
                "bit_rate": bit_rate,
            },
        )

    for _ in range(warmups):
        _encode_once(fixture_path, codec_name, bit_rate)

    measurements = [_encode_once(fixture_path, codec_name, bit_rate) for _ in range(repeats)]
    if recorder is not None:
        for measurement in measurements:
            recorder.emit("measurement_completed", measurement.to_dict())
    return BenchmarkSummary(
        benchmark="encode",
        fixture=fixture,
        case=case,
        measurements=measurements,
        warmups=warmups,
    )


def default_report_path(summary: BenchmarkSummary) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    slug = (
        f"{summary.benchmark}-{summary.fixture.key}-{summary.fixture.variant_key}-"
        f"{summary.case.codec}-{summary.case.hardware_accel or 'software'}"
    ).replace("/", "-")
    return benchmark_report_dir() / f"{timestamp}-{slug}.json"


def write_summary(summary: BenchmarkSummary, path: Path | None = None) -> Path:
    destination = path or default_report_path(summary)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    return destination
