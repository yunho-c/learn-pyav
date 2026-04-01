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
        width_hint=1280,
        height_hint=720,
        codec_hint="h264",
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


def list_fixture_assets() -> list[FixtureAsset]:
    return list(FIXTURE_ASSETS.values())


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


def prepared_fixture_path(asset: FixtureAsset, resolution_key: str) -> Path:
    source_name = Path(asset.relative_path).stem
    return prepared_fixture_dir() / asset.key / resolution_key / f"{source_name}.mp4"


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


def ensure_fixture(key: str, force: bool = False) -> Path:
    asset = get_fixture_asset(key)
    target = fixture_local_path(asset)
    if force or not target.exists():
        _download_to_path(asset.source_url, target)
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


def _inspect_video_path(asset: FixtureAsset, path: Path, variant_key: str) -> VideoFixtureSpec:
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        fps = float(stream.average_rate) if stream.average_rate is not None else 0.0
        if stream.duration is not None and stream.time_base is not None:
            duration_seconds = float(stream.duration * stream.time_base)
        else:
            duration_seconds = 0.0

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
            frames=stream.frames,
        )


def inspect_fixture(key: str) -> VideoFixtureSpec:
    asset = get_fixture_asset(key)
    path = ensure_fixture(key)
    return _inspect_video_path(asset, path, variant_key="source")


def ensure_prepared_fixture(
    key: str,
    resolution_key: str,
    force: bool = False,
) -> Path:
    asset = get_fixture_asset(key)
    resolution = get_resolution_spec(resolution_key)
    source_path = ensure_fixture(key)
    if resolution.key == "source":
        return source_path

    target_path = prepared_fixture_path(asset, resolution.key)
    if target_path.exists() and not force:
        return target_path

    source_spec = inspect_fixture(key)
    target_height = resolution.target_height
    if target_height is None:
        return source_path

    target_width, target_height = _derive_scaled_dimensions(
        source_spec.width,
        source_spec.height,
        target_height,
    )

    target_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_path),
        "-vf",
        f"scale={target_width}:{target_height}",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "18",
        "-an",
        str(target_path),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    return target_path


def inspect_fixture_variant(key: str, resolution_key: str) -> VideoFixtureSpec:
    asset = get_fixture_asset(key)
    path = ensure_prepared_fixture(key, resolution_key)
    return _inspect_video_path(asset, path, variant_key=resolution_key)
