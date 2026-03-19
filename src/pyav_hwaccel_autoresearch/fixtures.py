from __future__ import annotations

from .models import VideoFixtureSpec


def starter_fixture_specs() -> list[VideoFixtureSpec]:
    """Initial fixture targets to anchor early benchmark work."""
    return [
        VideoFixtureSpec(
            name="realworld-1080p-h264",
            source="TBD",
            container="mp4",
            codec="h264",
            width=1920,
            height=1080,
            fps=30.0,
            duration_seconds=10.0,
        ),
        VideoFixtureSpec(
            name="realworld-4k-hevc",
            source="TBD",
            container="mp4",
            codec="hevc",
            width=3840,
            height=2160,
            fps=30.0,
            duration_seconds=10.0,
        ),
    ]
