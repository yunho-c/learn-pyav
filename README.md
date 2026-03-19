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

## Current scope

This initial scaffold is focused on environment repeatability and research-process structure.
Benchmark runners, fixture acquisition, and codec-specific experiment implementations should grow out
of the guidance in `program.md`.
