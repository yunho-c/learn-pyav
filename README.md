# pyav-hwaccel-autoresearch

Autoresearch-style validation and benchmarking for hardware-accelerated video encode/decode in
[`PyAV`](https://github.com/PyAV-Org/PyAV).

The repo is structured for iterative agent-driven work:

- `program.md` defines the research loop, constraints, and acceptance bar.
- `src/pyav_hwaccel_autoresearch/` contains reusable probes, models, and CLI entry points.
- `tests/` holds fast correctness checks for the local scaffolding.
- `external/pyav/` is a local editable checkout of `PyAV`, installed by `pixi`.
- `external/autoresearch/` is upstream inspiration and reference material.

## Setup

```bash
pixi install
pixi run doctor
pixi run test
```

## First benchmark commands

```bash
pixi run python -m pyav_hwaccel_autoresearch.cli fixtures list
pixi run python -m pyav_hwaccel_autoresearch.cli benchmark decode pexels-night-sky
pixi run python -m pyav_hwaccel_autoresearch.cli benchmark decode pexels-night-sky --hwaccel videotoolbox
pixi run python -m pyav_hwaccel_autoresearch.cli benchmark encode pexels-night-sky --codec libx264
pixi run python -m pyav_hwaccel_autoresearch.cli benchmark encode pexels-night-sky --codec h264_videotoolbox
```

The fixture catalog now includes both small PyAV-curated 720p clips and larger native 4K sample
sources. The 4K assets are intentionally heavyweight and are meant for real throughput comparisons,
not fast default tests.

## Current scope

This initial scaffold is focused on environment repeatability and research-process structure.
The repo now includes a first real benchmark slice for fixture acquisition plus software and
VideoToolbox encode/decode comparisons. The next layer should expand fixture coverage, add richer
correctness checks, and grow benchmark reporting.
