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


def fixture_cache_dir() -> Path:
    return artifacts_dir() / "fixtures"


def prepared_fixture_dir() -> Path:
    return artifacts_dir() / "prepared"


def results_dir() -> Path:
    return project_root() / "results"


def benchmark_report_dir() -> Path:
    return results_dir() / "benchmarks"


def run_results_dir() -> Path:
    return results_dir() / "runs"


def results_index_path() -> Path:
    return results_dir() / "index.jsonl"


def logs_dir() -> Path:
    return project_root() / "logs"
