from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def external_dir() -> Path:
    return project_root() / "external"


def pyav_checkout_dir() -> Path:
    return external_dir() / "pyav"


def artifacts_dir() -> Path:
    return project_root() / "artifacts"


def results_dir() -> Path:
    return project_root() / "results"


def logs_dir() -> Path:
    return project_root() / "logs"
