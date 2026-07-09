# Changelog

All notable changes to Bounce House will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - UNRELEASED

### Fixed
- `uvx` / `pip install git+…` installs failed on dependency resolution (numba floored to >=0.60)
- Files shorter than 400 ms crashed loudness analysis; LUFS/LRA now report as unavailable
- `--json` emitted non-standard `NaN`/`-Infinity`; non-finite values now serialize as `null`
- `dir` returned exit `0` even when some files were skipped; a skipped file now forces exit ≥1 and appears in the JSON `skipped` array
- README installation instructions did not work as written

### Changed
- `analyze`, `compare`, and single-module commands now exit 0/1/2 (pass/warn/fail) like `dir`
- ANSI color is applied only on TTY stdout; `NO_COLOR` and `FORCE_COLOR` are respected
- JSON output now carries `"schema_version": 1`

### Added
- PyPI releases via trusted publishing on tag push

## [0.1.0] - 2026-03-11

### Added

- **Full mix analysis** — 26 metrics across 5 modules: loudness, spectrum, stereo, perceptual, and tuning
- **EBU R128 loudness** — integrated LUFS, loudness range, true peak (via ffmpeg), crest factor, PLR
- **Spectral analysis** — centroid, bandwidth, rolloff, flatness, and 7-band energy breakdown (sub-bass through brilliance)
- **Stereo imaging** — phase correlation, M/S decomposition, stereo width, frequency-dependent correlation
- **Perceptual quality** — brightness and warmth via proxy metrics or AudioCommons timbral_models
- **Tuning & pitch** — deviation from A440, pitch drift over time, chroma sharpness
- **Pass/warn/fail rules** — data-driven threshold engine with plain-English suggestions
- **Mix diagnostics** — 9 multi-metric patterns (muddy, harsh, thin, over-compressed, flat, mono-incompatible, wide bass, detuned, streaming-unfriendly) using soft-AND logic
- **Mix vs. master mode** — `--stage mix` adjusts thresholds for pre-master mixes
- **Reference comparison** — `bounce-house compare mix.wav reference.wav` for band-by-band differences
- **Batch analysis** — `bounce-house dir ./masters/` with recursive scan, summary table, and CI-ready exit codes
- **Built-in docs** — `bounce-house explain` with fuzzy matching, genre context, and `--technical` flag
- **JSON output** — `--json` on all commands for pipeline integration
- **Short alias** — `bh` as an alternative to `bounce-house`
