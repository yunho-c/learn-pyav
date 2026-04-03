from __future__ import annotations

from dataclasses import asdict, dataclass, field
from statistics import median
from typing import Any


@dataclass(frozen=True)
class FixtureAsset:
    key: str
    source_url: str
    relative_path: str
    description: str
    download_relative_path: str | None = None
    source_demuxer: str | None = None
    source_frame_rate: str | None = None
    enabled: bool = True
    width_hint: int | None = None
    height_hint: int | None = None
    codec_hint: str | None = None
    size_mb_hint: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResolutionSpec:
    key: str
    target_height: int | None
    description: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VideoFixtureSpec:
    key: str
    variant_key: str
    path: str
    source_url: str
    description: str
    container: str
    codec: str
    width: int
    height: int
    fps: float
    duration_seconds: float
    frames: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    mode: str
    resolution_key: str
    container: str
    codec: str
    hardware_accel: str | None = None
    options: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkMeasurement:
    label: str
    wall_seconds: float
    frames: int
    cpu_seconds: float | None = None
    bytes_total: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def frames_per_second(self) -> float:
        if self.wall_seconds <= 0:
            raise ValueError("wall_seconds must be positive")
        return self.frames / self.wall_seconds

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["frames_per_second"] = self.frames_per_second
        return data


@dataclass(frozen=True)
class BenchmarkSummary:
    benchmark: str
    fixture: VideoFixtureSpec
    case: BenchmarkCase
    measurements: list[BenchmarkMeasurement]
    warmups: int

    @property
    def median_wall_seconds(self) -> float:
        return median(measurement.wall_seconds for measurement in self.measurements)

    @property
    def median_frames_per_second(self) -> float:
        return median(measurement.frames_per_second for measurement in self.measurements)

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark": self.benchmark,
            "fixture": self.fixture.to_dict(),
            "case": self.case.to_dict(),
            "warmups": self.warmups,
            "measurements": [measurement.to_dict() for measurement in self.measurements],
            "median_wall_seconds": self.median_wall_seconds,
            "median_frames_per_second": self.median_frames_per_second,
        }


@dataclass(frozen=True)
class BenchmarkComparison:
    benchmark: str
    fixture: VideoFixtureSpec
    baseline: BenchmarkSummary
    candidate: BenchmarkSummary

    @property
    def candidate_speedup(self) -> float:
        return self.candidate.median_frames_per_second / self.baseline.median_frames_per_second

    @property
    def winner(self) -> str:
        if self.candidate_speedup > 1.0:
            return "candidate"
        if self.candidate_speedup < 1.0:
            return "baseline"
        return "tie"

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark": self.benchmark,
            "fixture": self.fixture.to_dict(),
            "baseline": self.baseline.to_dict(),
            "candidate": self.candidate.to_dict(),
            "candidate_speedup": self.candidate_speedup,
            "winner": self.winner,
        }
