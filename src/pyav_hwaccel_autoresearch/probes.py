from __future__ import annotations

import importlib.metadata
import shutil
import subprocess
from dataclasses import asdict, dataclass
from typing import Any

from .paths import project_root, pyav_checkout_dir


@dataclass(frozen=True)
class CommandProbe:
    command: str
    found: bool
    returncode: int | None
    stdout: str
    stderr: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EnvironmentReport:
    project_root: str
    pyav_checkout: str
    pyav_checkout_exists: bool
    av_distribution_version: str | None
    ffmpeg: CommandProbe
    ffmpeg_hwaccels: CommandProbe
    pkg_config_avcodec: CommandProbe

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_root": self.project_root,
            "pyav_checkout": self.pyav_checkout,
            "pyav_checkout_exists": self.pyav_checkout_exists,
            "av_distribution_version": self.av_distribution_version,
            "ffmpeg": self.ffmpeg.to_dict(),
            "ffmpeg_hwaccels": self.ffmpeg_hwaccels.to_dict(),
            "pkg_config_avcodec": self.pkg_config_avcodec.to_dict(),
        }


def _run_probe(*command: str) -> CommandProbe:
    executable = shutil.which(command[0])
    if executable is None:
        return CommandProbe(
            command=" ".join(command),
            found=False,
            returncode=None,
            stdout="",
            stderr=f"{command[0]} not found on PATH",
        )

    completed = subprocess.run(
        list(command),
        capture_output=True,
        text=True,
        check=False,
    )
    return CommandProbe(
        command=" ".join(command),
        found=True,
        returncode=completed.returncode,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
    )


def probe_av_distribution_version() -> str | None:
    try:
        return importlib.metadata.version("av")
    except importlib.metadata.PackageNotFoundError:
        return None


def collect_environment_report() -> EnvironmentReport:
    return EnvironmentReport(
        project_root=str(project_root()),
        pyav_checkout=str(pyav_checkout_dir()),
        pyav_checkout_exists=pyav_checkout_dir().exists(),
        av_distribution_version=probe_av_distribution_version(),
        ffmpeg=_run_probe("ffmpeg", "-version"),
        ffmpeg_hwaccels=_run_probe("ffmpeg", "-hide_banner", "-hwaccels"),
        pkg_config_avcodec=_run_probe("pkg-config", "--modversion", "libavcodec"),
    )
