from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import urlopen

import av

from .models import FixtureAsset, VideoFixtureSpec
from .paths import fixture_cache_dir

PYAV_CURATED_BASE_URL = "https://pyav.org/datasets/"

FIXTURE_ASSETS: dict[str, FixtureAsset] = {
    "pexels-night-sky": FixtureAsset(
        key="pexels-night-sky",
        source_url=PYAV_CURATED_BASE_URL + "pexels/time-lapse-video-of-night-sky-857195.mp4",
        relative_path="pexels/time-lapse-video-of-night-sky-857195.mp4",
        description="PyAV curated H.264 night sky timelapse clip.",
    ),
    "pexels-sunset-sea": FixtureAsset(
        key="pexels-sunset-sea",
        source_url=(
            PYAV_CURATED_BASE_URL + "pexels/time-lapse-video-of-sunset-by-the-sea-854400.mp4"
        ),
        relative_path="pexels/time-lapse-video-of-sunset-by-the-sea-854400.mp4",
        description="PyAV curated H.264 sunset timelapse clip.",
    ),
}


def list_fixture_assets() -> list[FixtureAsset]:
    return list(FIXTURE_ASSETS.values())


def get_fixture_asset(key: str) -> FixtureAsset:
    try:
        return FIXTURE_ASSETS[key]
    except KeyError as exc:
        raise KeyError(f"Unknown fixture key: {key}") from exc


def fixture_local_path(asset: FixtureAsset) -> Path:
    return fixture_cache_dir() / asset.relative_path


def _download_to_path(source_url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(source_url) as response:
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


def inspect_fixture(key: str) -> VideoFixtureSpec:
    asset = get_fixture_asset(key)
    path = ensure_fixture(key)
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        fps = float(stream.average_rate) if stream.average_rate is not None else 0.0
        if stream.duration is not None and stream.time_base is not None:
            duration_seconds = float(stream.duration * stream.time_base)
        else:
            duration_seconds = 0.0

        return VideoFixtureSpec(
            key=asset.key,
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
