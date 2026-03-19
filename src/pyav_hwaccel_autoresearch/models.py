from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class VideoFixtureSpec:
    name: str
    source: str
    container: str
    codec: str
    width: int
    height: int
    fps: float
    duration_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    mode: str
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
