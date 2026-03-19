# pyav hwaccel autoresearch

This repository exists to answer a concrete question with evidence:

**Does PyAV actually exercise hardware-accelerated video encode/decode paths on a given machine, and are those paths materially faster than software baselines?**

The project is not a generic media playground. It is an autonomous research workspace for:

1. detecting which acceleration paths are available,
2. validating that PyAV can drive them correctly,
3. benchmarking them against software encode/decode,
4. preserving enough evidence that the conclusions are reproducible.

## Mission

Build a codebase that can repeatedly produce trustworthy answers like:

- "On this Apple Silicon machine, H.264 VideoToolbox encode is 2.4x faster than libx264 for this fixture set."
- "Decode looks hardware-backed for HEVC, but total wall time is not better than software for 1080p clips."
- "PyAV exposes codec X, but the attempted hardware path silently falls back to software."

Every claim should be backed by:

- a concrete benchmark run,
- saved metadata about the environment and codec configuration,
- correctness validation on actual video inputs and outputs,
- numerical comparison against a software baseline.

## Operating principles

1. **Evidence over optimism.** Never claim a path is hardware accelerated just because a codec name contains `nvenc`, `videotoolbox`, `qsv`, `vaapi`, or similar. Confirm via runtime behavior, metadata, and speed comparison.
2. **Real media first.** Benchmarks should involve actual video files, not only synthetic frame loops. Synthetic inputs are useful for controlled probes, but real fixture clips are required for conclusions.
3. **Baseline always.** Every hardware candidate needs a software baseline for the same container, codec family, resolution, and output target when possible.
4. **Correctness gates precede benchmarks.** A faster result is not meaningful if frame counts, timestamps, stream metadata, decode integrity, or output playability are wrong.
5. **Small, inspectable steps.** Prefer adding reusable probes, fixtures, and benchmark runners over throwing one-off shell scripts into the repo.
6. **Keep architecture clean.** Separate capability probing, fixture management, benchmark execution, and report generation. Avoid making one file do everything.
7. **Preserve the trail.** Benchmark artifacts, metadata snapshots, and result summaries should make it easy to understand what happened without rereading the code.

## In-scope files

Read these first before making meaningful changes:

- `program.md` — the operating manual for the agent.
- `README.md` — repo intent and top-level layout.
- `pyproject.toml` — environment, tasks, and local dependency wiring.
- `src/pyav_hwaccel_autoresearch/` — reusable project code.
- `tests/` — fast checks that should remain green.

These external directories matter, but they are not the default place to edit:

- `external/pyav/` — local editable checkout of PyAV. Treat as read-only unless there is a strong reason to patch PyAV itself.
- `external/autoresearch/` — reference material and inspiration, not the execution target for this repo.

## Default repository shape

The codebase should evolve toward these responsibilities:

- `src/pyav_hwaccel_autoresearch/probes.py`
  Environment and capability inspection.
  Example responsibilities: ffmpeg build info, hwaccel listing, codec enumeration, PyAV version and import checks.

- `src/pyav_hwaccel_autoresearch/fixtures.py`
  Real video fixture metadata and acquisition logic.
  Example responsibilities: fixture manifest, cache paths, checksums, clip trimming, download bookkeeping.

- `src/pyav_hwaccel_autoresearch/runner.py`
  Reusable execution logic for encode/decode jobs.
  Example responsibilities: run configs, timing, repeat policy, subprocess isolation when needed, artifact collection.

- `src/pyav_hwaccel_autoresearch/models.py`
  Shared typed data structures for fixtures, benchmark cases, and measurements.

- `src/pyav_hwaccel_autoresearch/cli.py`
  Thin command surface for repeatable operations such as `doctor`, `probe`, `benchmark`, and `report`.

- `tests/`
  Fast structural tests.
  Prefer unit tests for schema, path handling, and report parsing. Keep slow video benchmarks out of the default test path unless explicitly marked.

- `results/` or `artifacts/`
  Generated outputs. These should be ignored by git.

## What success looks like

A high-quality result for a hardware path should eventually include all of the following:

1. a fixture manifest describing which clips were used,
2. a machine/environment snapshot,
3. a software baseline result,
4. a hardware candidate result,
5. correctness checks for outputs,
6. repeated timings with summary statistics,
7. a concise conclusion about whether the path is genuinely beneficial.

The final benchmark suite should be able to answer both:

- "Is this path available?"
- "Is this path worth using?"

## Setup workflow

When starting work in a fresh clone:

1. Confirm the submodules are present:
   - `external/pyav`
   - `external/autoresearch`
2. Install the workspace with `pixi install`.
3. Run `pixi run doctor`.
4. Run `pixi run test`.
5. Inspect local FFmpeg / PyAV capability information before designing any benchmark.

Do not begin with benchmark implementation until the environment probe is trustworthy.

## Research loop

The loop in this repo is not "edit model, train five minutes." It is:

1. **Probe**
   Identify what the local machine plausibly supports.
   Examples:
   - available hwaccels from FFmpeg,
   - encode/decode codecs present in PyAV,
   - whether local FFmpeg is linked in a way PyAV can build against.

2. **Select one narrow hypothesis**
   Good examples:
   - "VideoToolbox H.264 encode through PyAV is faster than libx264 on 1080p clips."
   - "HEVC decode uses a hardware path but total throughput is not better than software."
   - "The requested hardware codec silently falls back to software in PyAV."

3. **Implement the minimum reusable code**
   Prefer reusable benchmark case definitions and typed result objects.
   Avoid single-use scripts when the logic belongs in `src/`.

4. **Validate correctness first**
   At minimum:
   - output container opens,
   - stream metadata is sane,
   - expected number of frames is preserved where appropriate,
   - decode of produced output succeeds,
   - obvious corruption is absent.

5. **Benchmark**
   Run repeated measurements and collect:
   - wall-clock time,
   - throughput (frames/sec or video-seconds/sec),
   - file size or bitrate where relevant,
   - CPU time or other profiler output if useful,
   - environment metadata.

6. **Compare against baseline**
   No hardware result stands alone. Compare to a software path for the same job.

7. **Keep or discard**
   Keep changes that improve the codebase's ability to produce trustworthy answers.
   Discard complexity that does not improve correctness, evidence quality, or experiment speed.

## Benchmark design rules

When adding encode/decode benchmarks, follow these rules:

1. **Separate encode and decode measurements.**
   Combined transcoding benchmarks are useful later, but they hide where the gain actually came from.

2. **Measure repeated runs.**
   One timing is not enough. Use warmups plus multiple measured runs and report median, min, max, and spread.

3. **Normalize the work.**
   Same input fixture, same duration, same target container, same output dimensions, same quality target or bitrate strategy where feasible.

4. **Track fallbacks explicitly.**
   If a requested hardware path errors or falls back, record that outcome instead of quietly dropping it.

5. **Do not overfit to one machine.**
   Platform-specific code is fine, but keep the surrounding interfaces cross-platform so the repo can compare Apple, NVIDIA, Intel, VAAPI, and software paths under one architecture.

6. **Prefer machine-readable artifacts.**
   JSON or TSV summaries are better than prose-only logs.

## Guardrails

- Do not patch `external/pyav/` casually. Only do that if the research clearly shows the behavior being tested is blocked by PyAV itself and the patch belongs upstream.
- Do not hardcode one platform's assumptions into the whole architecture.
- Do not interpret "hardware" from naming alone.
- Do not accept faster-but-broken outputs.
- Do not let benchmark scripts mutate source files or rely on hidden local state.

## Logging and artifacts

Generated outputs should eventually include:

- raw benchmark records,
- summarized comparison tables,
- environment snapshots,
- stderr/stdout logs for failed runs,
- optional profiler outputs.

Keep generated data under ignored directories such as:

- `artifacts/`
- `results/`
- `logs/`

The repository should stay clean between experiments.

## First milestones

Before broad codec coverage, aim for this sequence:

1. solid environment probe (`doctor` plus structured capability report),
2. fixture manifest and cache layout,
3. one end-to-end software encode/decode benchmark,
4. one end-to-end hardware candidate benchmark on the current machine,
5. baseline vs hardware comparison output,
6. expansion to additional codecs / platforms.

## Default bias

When unsure what to do next, prefer work in this order:

1. improve observability,
2. improve correctness validation,
3. improve benchmark repeatability,
4. add one new hardware path,
5. optimize ergonomics.

The point of this repo is not to produce the most code. The point is to produce trustworthy answers about PyAV hardware acceleration.
