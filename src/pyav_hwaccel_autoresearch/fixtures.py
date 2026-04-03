from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import Request, urlopen

import av

from .models import FixtureAsset, ResolutionSpec, VideoFixtureSpec
from .paths import fixture_cache_dir, prepared_fixture_dir

PYAV_CURATED_BASE_URL = "https://pyav.org/datasets/"
DEFAULT_DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ),
}

FIXTURE_ASSETS: dict[str, FixtureAsset] = {
    "pexels-night-sky": FixtureAsset(
        key="pexels-night-sky",
        source_url=PYAV_CURATED_BASE_URL + "pexels/time-lapse-video-of-night-sky-857195.mp4",
        relative_path="pexels/time-lapse-video-of-night-sky-857195.mp4",
        description="PyAV curated H.264 night sky timelapse clip.",
        width_hint=1280,
        height_hint=720,
        codec_hint="h264",
    ),
    "pexels-sunset-sea": FixtureAsset(
        key="pexels-sunset-sea",
        source_url=(
            PYAV_CURATED_BASE_URL + "pexels/time-lapse-video-of-sunset-by-the-sea-854400.mp4"
        ),
        relative_path="pexels/time-lapse-video-of-sunset-by-the-sea-854400.mp4",
        description="PyAV curated H.264 sunset timelapse clip.",
        enabled=False,
        width_hint=1280,
        height_hint=720,
        codec_hint="h264",
    ),
    "filesamples-1080p-h264": FixtureAsset(
        key="filesamples-1080p-h264",
        source_url="https://filesamples.com/samples/video/mp4/sample_1920x1080.mp4",
        relative_path="filesamples/sample_1920x1080.mp4",
        description="FileSamples native 1080p MP4 fixture, H.264, 1920x1080, about 24 fps.",
        width_hint=1920,
        height_hint=1080,
        codec_hint="h264",
        size_mb_hint=36,
    ),
    "jellyfin-1080p-hevc": FixtureAsset(
        key="jellyfin-1080p-hevc",
        source_url=(
            "https://fra1.mirror.jellyfin.org/test-videos/SDR/HEVC%208bit/"
            "Test%20Jellyfin%201080p%20HEVC%208bit%203M.mp4"
        ),
        relative_path="jellyfin/test-jellyfin-1080p-hevc-8bit-3m.mp4",
        description="Jellyfin native 1080p MP4 fixture, HEVC, 1920x1080, 60 fps, 3 Mbps.",
        width_hint=1920,
        height_hint=1080,
        codec_hint="hevc",
        size_mb_hint=11,
    ),
    "samplecat-1440p-h264": FixtureAsset(
        key="samplecat-1440p-h264",
        source_url="https://disk.sample.cat/samples/mp4/1416529-uhd_2560_1440_30fps.mp4",
        relative_path="samplecat/1416529-uhd_2560_1440_30fps.mp4",
        description="Sample.Cat native 1440p MP4 fixture, H.264, 2560x1440, 30 fps.",
        width_hint=2560,
        height_hint=1440,
        codec_hint="h264",
        size_mb_hint=18,
    ),
    "filesamples-1440p-hevc": FixtureAsset(
        key="filesamples-1440p-hevc",
        source_url="https://filesamples.com/samples/video/hevc/sample_2560x1440.hevc",
        relative_path="filesamples/sample_2560x1440.mkv",
        download_relative_path="filesamples/sample_2560x1440.hevc",
        source_demuxer="hevc",
        source_frame_rate="25/1",
        description=(
            "FileSamples native 1440p HEVC fixture remuxed locally from a raw bitstream into MKV."
        ),
        width_hint=2560,
        height_hint=1440,
        codec_hint="hevc",
        size_mb_hint=34,
    ),
    "filesamples-4k-h264": FixtureAsset(
        key="filesamples-4k-h264",
        source_url="https://filesamples.com/samples/video/mp4/sample_3840x2160.mp4",
        relative_path="filesamples/sample_3840x2160.mp4",
        description="FileSamples 4K MP4 fixture, H.264, 3840x2160, about 24 fps.",
        width_hint=3840,
        height_hint=2160,
        codec_hint="h264",
        size_mb_hint=126,
    ),
    "gpac-uhd-hevc-4k": FixtureAsset(
        key="gpac-uhd-hevc-4k",
        source_url=(
            "https://download.tsi.telecom-paristech.fr/gpac/dataset/dash/uhd/"
            "mux_sources/hevcds_2160p60_12M.mp4"
        ),
        relative_path="gpac/hevcds_2160p60_12M.mp4",
        description="GPAC UHD dataset fixture, HEVC MP4, 3840x2160, 60 fps, 12 Mbps.",
        width_hint=3840,
        height_hint=2160,
        codec_hint="hevc",
        size_mb_hint=182,
    ),
}

RESOLUTION_SPECS: dict[str, ResolutionSpec] = {
    "source": ResolutionSpec(
        key="source",
        target_height=None,
        description="Original source resolution.",
    ),
    "480p": ResolutionSpec(
        key="480p",
        target_height=480,
        description="Prepared 480p variant preserving aspect ratio.",
    ),
    "720p": ResolutionSpec(
        key="720p",
        target_height=720,
        description="Prepared 720p variant preserving aspect ratio.",
    ),
    "1080p": ResolutionSpec(
        key="1080p",
        target_height=1080,
        description="Prepared 1080p variant preserving aspect ratio.",
    ),
    "2160p": ResolutionSpec(
        key="2160p",
        target_height=2160,
        description="Prepared 2160p variant preserving aspect ratio.",
    ),
}


def list_fixture_assets(*, include_disabled: bool = False) -> list[FixtureAsset]:
    fixtures = list(FIXTURE_ASSETS.values())
    if include_disabled:
        return fixtures
    return [fixture for fixture in fixtures if fixture.enabled]


def list_resolution_specs() -> list[ResolutionSpec]:
    return list(RESOLUTION_SPECS.values())


def get_fixture_asset(key: str) -> FixtureAsset:
    try:
        return FIXTURE_ASSETS[key]
    except KeyError as exc:
        raise KeyError(f"Unknown fixture key: {key}") from exc


def get_resolution_spec(key: str) -> ResolutionSpec:
    try:
        return RESOLUTION_SPECS[key]
    except KeyError as exc:
        raise KeyError(f"Unknown resolution key: {key}") from exc


def fixture_local_path(asset: FixtureAsset) -> Path:
    return fixture_cache_dir() / asset.relative_path


def fixture_download_path(asset: FixtureAsset) -> Path:
    relative_path = asset.download_relative_path or asset.relative_path
    return fixture_cache_dir() / relative_path


def prepared_fixture_path(asset: FixtureAsset, resolution_key: str) -> Path:
    source_name = Path(asset.relative_path).stem
    return prepared_fixture_dir() / asset.key / resolution_key / f"{source_name}.mp4"


def variant_key_for(resolution_key: str, min_duration_seconds: int | None = None) -> str:
    if min_duration_seconds is None:
        return resolution_key
    return f"{resolution_key}-{min_duration_seconds}s"


def _download_to_path(source_url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(source_url, headers=DEFAULT_DOWNLOAD_HEADERS)

    with urlopen(request) as response:
        if response.status != 200:
            raise RuntimeError(f"Failed to download {source_url}: HTTP {response.status}")

        with NamedTemporaryFile(delete=False, dir=destination.parent) as tmp:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                tmp.write(chunk)
            tmp_path = Path(tmp.name)

    tmp_path.replace(destination)


def _remux_fixture(
    source_path: Path,
    destination: Path,
    *,
    source_demuxer: str | None,
    source_frame_rate: str | None,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    if source_demuxer is not None:
        command.extend(["-f", source_demuxer])
    command.extend(["-i", str(source_path), "-c", "copy"])
    if source_demuxer == "hevc":
        frame_rate = source_frame_rate or "25/1"
        command.extend(
            [
                "-bsf:v",
                f"setts=pts=N:dts=N:duration=1:time_base={frame_rate}",
            ]
        )
    command.append(str(destination))
    subprocess.run(command, check=True)


def ensure_fixture(key: str, force: bool = False) -> Path:
    asset = get_fixture_asset(key)
    target = fixture_local_path(asset)
    download_target = fixture_download_path(asset)
    needs_download = force or not download_target.exists()
    needs_remux = download_target != target and (force or not target.exists())

    if needs_download:
        _download_to_path(asset.source_url, download_target)
    if needs_remux:
        _remux_fixture(
            download_target,
            target,
            source_demuxer=asset.source_demuxer,
            source_frame_rate=asset.source_frame_rate,
        )
    elif download_target == target and needs_download:
        return download_target
    return target


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _derive_scaled_dimensions(width: int, height: int, target_height: int) -> tuple[int, int]:
    if target_height >= height:
        return width, height

    scale = target_height / height
    scaled_width = max(2, int(2 * round((width * scale) / 2)))
    return scaled_width, target_height


def _count_video_frames(path: Path) -> int:
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        return sum(1 for _ in container.decode(stream))


def _inspect_video_path(asset: FixtureAsset, path: Path, variant_key: str) -> VideoFixtureSpec:
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        fps = float(stream.average_rate) if stream.average_rate is not None else 0.0
        frame_count = stream.frames
        if stream.duration is not None and stream.time_base is not None:
            duration_seconds = float(stream.duration * stream.time_base)
        elif container.duration is not None:
            duration_seconds = float(container.duration / av.time_base)
        else:
            duration_seconds = 0.0

        if frame_count <= 0:
            frame_count = _count_video_frames(path)

        expected_duration = float(frame_count / fps) if frame_count > 0 and fps > 0.0 else 0.0
        if expected_duration > 0.0 and (
            duration_seconds <= 0.0 or duration_seconds > (expected_duration * 4.0)
        ):
            duration_seconds = expected_duration

        return VideoFixtureSpec(
            key=asset.key,
            variant_key=variant_key,
            path=str(path),
            source_url=asset.source_url,
            description=asset.description,
            container=path.suffix.lstrip("."),
            codec=stream.codec_context.name,
            width=stream.width,
            height=stream.height,
            fps=fps,
            duration_seconds=duration_seconds,
            frames=frame_count,
        )


def inspect_fixture(key: str) -> VideoFixtureSpec:
    asset = get_fixture_asset(key)
    path = ensure_fixture(key)
    return _inspect_video_path(asset, path, variant_key="source")


def ensure_prepared_fixture(
    key: str,
    resolution_key: str,
    min_duration_seconds: int | None = None,
    force: bool = False,
) -> Path:
    asset = get_fixture_asset(key)
    resolution = get_resolution_spec(resolution_key)
    source_path = ensure_fixture(key)
    preparation_input_path = fixture_download_path(asset) if asset.source_demuxer is not None else source_path
    source_spec = inspect_fixture(key)
    needs_duration_control = min_duration_seconds is not None
    needs_duration_extension = (
        needs_duration_control and source_spec.duration_seconds < min_duration_seconds
    )
    if resolution.key == "source" and not needs_duration_control:
        return source_path

    variant_key = variant_key_for(resolution.key, min_duration_seconds)
    target_path = prepared_fixture_path(asset, variant_key)
    if target_path.exists() and not force:
        return target_path

    target_height = resolution.target_height
    if target_height is None:
        target_width = source_spec.width
        target_height = source_spec.height
    else:
        target_width, target_height = _derive_scaled_dimensions(
            source_spec.width,
            source_spec.height,
            target_height,
        )

    filter_args: list[str] = []
    if target_width != source_spec.width or target_height != source_spec.height:
        filter_args = ["-vf", f"scale={target_width}:{target_height}"]

    target_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
    ]
    if needs_duration_extension:
        command.extend(["-stream_loop", "-1"])
    if asset.source_demuxer is not None:
        command.extend(["-f", asset.source_demuxer])
    if asset.source_frame_rate is not None:
        command.extend(["-r", asset.source_frame_rate])
    command.extend(["-i", str(preparation_input_path)])
    if min_duration_seconds is not None:
        command.extend(["-t", str(min_duration_seconds)])
    command.extend(
        [
            *filter_args,
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-an",
            str(target_path),
        ]
    )
    subprocess.run(command, check=True, capture_output=True, text=True)
    return target_path


def inspect_fixture_variant(
    key: str,
    resolution_key: str,
    min_duration_seconds: int | None = None,
) -> VideoFixtureSpec:
    asset = get_fixture_asset(key)
    variant_key = variant_key_for(resolution_key, min_duration_seconds)
    path = ensure_prepared_fixture(key, resolution_key, min_duration_seconds=min_duration_seconds)
    return _inspect_video_path(asset, path, variant_key=variant_key)
