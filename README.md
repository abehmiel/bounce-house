# Bounce House

[![CI](https://github.com/abehmiel/bounce-house/actions/workflows/ci.yml/badge.svg)](https://github.com/abehmiel/bounce-house/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A CLI audio analysis tool that tells you what's wrong with your mix — and what to do about it.

Bounce House runs 39 metrics across loudness, spectral balance, stereo imaging, mono/small-speaker translation, tuning, quality control, and perceptual quality — 7 modules in all. Every metric gets a pass/warn/fail assessment with plain-English advice. Nine diagnostic patterns catch common mixing problems (muddy low end, crushed dynamics, mono-incompatible stereo) by combining evidence across modules. Compare against a reference track, batch-analyze an album, or pipe `--json` into your CI pipeline.

I made this while working on a new DIY aggressive guitar-and-synth music project, listening to my first round of mixes on a car stereo and being utterly dismayed with bounces gone wrong. There was so much to fix. I wondered if I should create a tool to save some time and be more goal-directed in my mixing and mastering process (you obviously still have to listen to your mixes). I bit the bullet and made the bulk of bounce-house across just a few days while in Albany, NY visiting family. The more you know 🌈 

## Quick Start

```bash
# Run without installing (requires uv: https://docs.astral.sh/uv/)
uvx --from git+https://github.com/abehmiel/bounce-house bounce-house analyze mix.wav

# Or install it on your PATH
uv tool install git+https://github.com/abehmiel/bounce-house
bounce-house analyze mix.wav
bh analyze mix.wav          # short alias
```

## Installation

> bounce-house is not yet published to PyPI, so install it from GitHub for now.
> Once it's on PyPI, the shorter `uvx bounce-house` / `uv tool install bounce-house`
> forms below will work too.

### From GitHub (recommended)

```bash
uv tool install git+https://github.com/abehmiel/bounce-house   # puts bounce-house/bh on your PATH
# or one-off: uvx --from git+https://github.com/abehmiel/bounce-house bounce-house analyze mix.wav
```

### From a clone (for development)

```bash
git clone https://github.com/abehmiel/bounce-house.git
cd bounce-house
uv sync
uv run bounce-house analyze mix.wav   # uv sync does NOT put bounce-house on PATH; use `uv run`
```

### Once published to PyPI (not live yet)

```bash
uv tool install bounce-house     # puts bounce-house/bh on your PATH
# or: pipx install bounce-house
# or: pip install bounce-house
# or run without installing: uvx bounce-house analyze mix.wav
```

### Optional dependencies

**Perceptual analysis** — install `timbral_models` for AudioCommons perceptual metrics (brightness, warmth, hardness, roughness) instead of proxy calculations:

```bash
uv sync --extra perceptual
# or: pip install ".[perceptual]"
```

## Usage

### Full analysis

```bash
bounce-house analyze mix.wav
```

### Supported file formats

WAV, FLAC, AIFF, and OGG are accepted everywhere a file path is expected —
`analyze`, `compare`, the single-module commands, and `dir` (which discovers
all supported formats in a directory, not just WAV). MP3 and M4A are not
decoded directly; convert them first:

```bash
ffmpeg -i input.mp3 output.wav
```

### Individual modules

Run a single analysis module when you only care about one domain:

```bash
bounce-house loudness mix.wav      # EBU R128 loudness, dynamics, crest factor
bounce-house spectrum mix.wav      # Spectral centroid, bandwidth, band energies
bounce-house stereo mix.wav        # Phase correlation, M/S ratio, stereo width
bounce-house translation mix.wav   # Mono loss, per-band cancellation, small-speaker low-end reliance
bounce-house perceptual mix.wav    # Brightness, warmth (+ timbral_models scores if installed)
bounce-house tuning mix.wav        # Tuning deviation, pitch drift, chroma sharpness
bounce-house qc mix.wav            # Clipping, leading/trailing silence
```

### Genre-calibrated targets

```bash
bounce-house analyze mix.wav --genre edm
```

`--genre` (pop, rock, edm, hip_hop, metal, folk) overlays genre-specific target
ranges on top of the stage profile, on `analyze`, `dir`, `compare`, and the
single-module commands. These targets are provisional engineering priors, not
calibrated from real-song evals yet — the terminal report and JSON both label
genre-affected metrics accordingly (see [TODO](TODO.md) for the deferred
calibration stage).

### Compare against a reference

```bash
bounce-house compare mix.wav reference.wav
```

Shows all metrics for your mix alongside band-by-band energy differences against the reference track. Useful for matching tonal balance to a commercially released track in your genre.

### Diff two bounces

```bash
bounce-house diff old.wav new.wav
```

Compares two bounces of the *same* mix — e.g. before/after a mastering pass, or your last two exports — and reports what moved:

- **Improved** — metrics whose pass/warn/fail status got better between bounces
- **Regressed** — metrics whose status got worse
- **Changed** — metrics that moved by more than a per-metric significance threshold but didn't cross a status boundary (reported for awareness, not scored)
- **Diagnostics** — mix diagnostic patterns (see [Mix Diagnostics](#mix-diagnostics)) resolved or newly introduced between the two bounces

Exit codes make this CI-friendly: `0` = no regressions, `1` = at least one regression or a newly introduced diagnostic. Wire it into a pipeline to gate on "did my mix get worse":

```bash
bounce-house diff last_release.wav new_bounce.wav || echo "regression detected, blocking merge"
```

`--json` emits the same categorization as structured data for tooling.

### Explain metrics

Built-in documentation for every metric — what it measures, why it matters, good ranges, and genre-specific context:

```bash
bounce-house explain                  # Overview of all metrics
bounce-house explain loudness         # All metrics in a module
bounce-house explain crest            # Single metric (fuzzy matched)
bounce-house explain lra --technical  # Include measurement standards
```

### Batch directory analysis

Analyze all supported audio files (wav/flac/aiff/ogg) in a directory at once — great for checking an album, stems folder, or CI pipeline:

```bash
bounce-house dir ./masters/                    # All supported files in directory
bounce-house dir ./masters/ --recursive        # Include subdirectories
bounce-house dir ./masters/ --json             # Machine-readable output
bounce-house dir ./masters/ --reference ref.wav  # Compare all against reference
```

Each file gets a full report, followed by a summary table:

```
════════════════════════════════════════════════════════════
  DIRECTORY SUMMARY (3 files)
════════════════════════════════════════════════════════════

  File                       LUFS   Peak  Crest   W   F  Status
  ────────────────────────────────────────────────────────
  track_01.wav              -13.2   -1.0   10.2   0   0  PASS
  track_02.wav              -11.8   -0.5    8.1   1   0  WARN
  track_03.wav               -7.4   -0.1    5.2   1   2  FAIL

════════════════════════════════════════════════════════════
  2 warning(s), 2 failure(s) across 3 files
════════════════════════════════════════════════════════════
```

Exit codes are shared by all analysis commands — see JSON output below. Corrupt files are logged to stderr without stopping the batch.

### Mix vs. Master Mode

By default, bounce-house analyzes audio as a finished master. For pre-master
mixes, use `--stage mix` to get thresholds calibrated for mixing:

```bash
bounce-house analyze my_mix.wav --stage mix
bounce-house dir ./mixes --stage mix
```

Mix mode adjusts:
- LUFS targets (-24 to -14 instead of -16 to -8)
- Peak thresholds (warns at -3 dBFS instead of -1 dBTP)
- Crest factor tolerance (more lenient for unmixed dynamics)
- Disables streaming-readiness checks
- Adds headroom and bus limiter diagnostics

### JSON output

All analysis commands support `--json` for machine-readable output:

```bash
bounce-house analyze mix.wav --json
bounce-house loudness mix.wav --json
bounce-house dir ./masters/ --json
```

JSON output includes a top-level `"schema_version": 2` field; non-finite measurements
(e.g., LUFS of digital silence) are serialized as `null`.

The terminal report renders level-over-time and correlation-over-time as compact
sparklines (`▁▂▃▄▅▆▇█`) so you can eyeball dynamics and phase behavior at a glance.
`--json` carries the same data as plot-ready 50-point `rms_curve_db` and
`correlation_curve` arrays, so you can feed them into your own plotting tools instead
of eyeballing the sparkline.

True peak is measured natively — BS.1770-style 4x oversampling implemented in-process
— so there's no ffmpeg dependency and no `true_peak_available` flag to check; every
analysis gets a true peak reading.

All analysis commands (`analyze`, `compare`, `dir`, and the single-module commands)
exit with `0` = all checks passed, `1` = warnings (also used for unreadable-file
errors), `2` = failures — so any of them can gate a CI pipeline.

For `dir`, any unreadable file is skipped rather than aborting the batch, but a
skipped file forces the exit code to at least `1` and appears in the JSON
`skipped` array (with `summary.total_skipped`) — so a partial batch never reports
success. `summary.total_files` continues to count only the successfully analyzed
files.

Color is used only when stdout is a terminal. Set `NO_COLOR=1` to force plain
output, or `FORCE_COLOR=1` to keep colors when piping.

## Example Output

Real output from `bounce-house analyze mix.wav` (`NO_COLOR=1` to keep this block plain-text):

```
════════════════════════════════════════════════════════════
  BOUNCE HOUSE — Master Analysis Report
  mix.wav (44100 Hz, stereo, 0:08)
════════════════════════════════════════════════════════════

── Loudness & Dynamics ────────────────────────────────────
  Integrated LUFS        -15.6  PASS
  Loudness Range         +1.5  FAIL
  Sample Peak            -1.0
  True Peak              -0.5  WARN
  RMS Level              -17.4
  DC Offset              -53.1  PASS
  Crest Factor           +16.1  PASS
  PLR                    +15.1  PASS
  DR (Dynamic Range)     11.9000  PASS
  Level                  █▂▂▆▁▂▆▄▂▆▃▂▅▃▂▆▄▂▆▃▁▅▅▁▂█▂▂▆▁▂▆▄▂▆▃▂▅▃▂▆▄▂▆▃▁▅▄▁▂

── Spectral Balance ───────────────────────────────────────
  Centroid               2,613.5 Hz
  Bandwidth              2,465.6 Hz
  Rolloff (85%)          5,091.9 Hz
  Flatness               0.0179

  sub-bass                   16.0 dB rel  ████████████
  bass                       18.4 dB rel  ████████████
  low-mid                     8.4 dB rel  ██████████
  mid                         1.8 dB rel  █████████
  upper-mid                 -23.4 dB rel  ███
  presence                  -19.2 dB rel  ████
  brilliance                -12.3 dB rel  ██████

── Stereo & Phase ─────────────────────────────────────────
  Phase Correlation      0.9989  PASS
  Mid RMS                -17.4
  Side RMS               -49.8
  M/S Ratio              +32.4  FAIL
  Balance                +0.1  PASS
  Stereo Width           0.0226  FAIL
  Block Corr (p5)        0.9980  PASS
  Correlation            ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇

  Frequency-dependent correlation:
    sub-bass           +1.000
    low-mid            +1.000
    mid                +0.999
    upper-mid          +1.000
    air                +1.000

── Translation (Mono & Small Speakers) ────────────────────
  Mono Loss              -0.0  PASS
  Worst Band (mono)      sub_bass
  Worst Band Loss        -0.0
  Low-End Reliance       0.7100  FAIL

  Mono loss by band:
    sub-bass           -0.0 dB
    low-mid            -0.0 dB
    mid                -0.0 dB
    upper-mid          -0.0 dB
    air                -0.0 dB

── Perceptual Quality ─────────────────────────────────────
  Brightness             0.0521
  Warmth                 0.1228

── Tuning & Pitch ─────────────────────────────────────────
  Tuning Deviation       +4.0 cents  PASS
  Concert Pitch          441.0 Hz
  Closest Standard       A=441
  Pitch Drift (std)      +4.5 cents  PASS
  Pitch Drift (range)    +9.0 cents  WARN
  Pitch Trend            +96.4 cents
  Chroma Sharpness       0.3050  WARN

── Quality Control ────────────────────────────────────────
  Clip Events            0  PASS
  Longest Clip Run       0
  Leading Silence        0.0000  PASS
  Trailing Silence       0.0000  PASS

── Suggestions ────────────────────────────────────────────
  FAIL  Loudness range is 1.5 LU — extreme dynamics, review compressor/limiter settings
  FAIL  Stereo width is 0.02 — far outside the 0.08-0.45 target
  FAIL  M/S ratio is 32.40 dB — far outside the 3.0-12.0 dB target
  FAIL  Low-end reliance is 0.71 — far outside the 0.0-0.35 target
  WARN  True peak is -0.5 dBTP — close to clipping, consider lowering limiter ceiling to -1.0 dBTP
  WARN  Pitch stability: 9.0 cents range — moderate drift, consider pitch correction
  WARN  Chroma definition: 0.30 — somewhat diffuse pitch content

── Mix Diagnostics ────────────────────────────────────────
  WARN  Flat / Lifeless Mix — Mix lacks spatial depth and dynamic variation
        Add spatial depth with reverb and delay. Vary dynamics between sections (quieter verses, louder choruses). Check panning — spreading instruments across the stereo field adds life. Even small stereo width differences between verse and chorus create perceived energy.
  FAIL  Streaming-Unfriendly Master — Master too hot for streaming platforms
        Spotify normalizes to -14 LUFS, Apple Music to -16 LUFS. Your track will be turned down, and the aggressive limiting will be audible. Consider mastering to -9 to -12 LUFS with a -1.0 dBTP ceiling. The quieter version will actually sound better after platform normalization because it retains more dynamics.

════════════════════════════════════════════════════════════
  3 warning(s), 4 failure(s)
════════════════════════════════════════════════════════════
```

## Metrics

Bounce House measures 39 metrics across 7 analysis modules. Run `bounce-house explain` for full documentation including genre-specific context and measurement standards.

Metrics marked ✓ get a pass/warn/fail assessment; unmarked metrics are reported for information and reference comparison.

### Loudness & Dynamics

| Metric | What it measures | Good range | Assessed |
|--------|-----------------|------------|----------|
| Integrated LUFS | Perceived loudness (ITU-R BS.1770) | -16 to -8 LUFS | ✓ |
| Loudness Range (LRA) | Dynamic spread, quiet to loud (EBU R128) | 5 to 15 LU | ✓ |
| True Peak | Maximum reconstructed waveform level | Below -1.0 dBTP | ✓ |
| Sample Peak | Maximum digital sample value | Below -0.3 dBFS | — |
| RMS Level | Average signal power | -20 to -10 dB | — |
| Crest Factor | Peak-to-RMS ratio (transient headroom) | 8 to 14 dB | ✓ |
| PLR | Peak-to-Loudness Ratio — over-compression indicator | Above 10 dB | ✓ |
| DC Offset | Constant (0 Hz) offset removed before analysis | Below -60 dBFS | — |
| DR (Dynamic Range) | TT/Pleasurize-convention loud-passage dynamics | DR 7 or above | ✓ |
| Level Over Time | RMS level curve across the file, 50 points (sparkline in terminal) | Informational | — |

### Spectral Balance

| Metric | What it measures | Good range | Assessed |
|--------|-----------------|------------|----------|
| Spectral Centroid | Center of mass — correlates with brightness | 1500 to 3500 Hz | — |
| Spectral Bandwidth | Energy spread around centroid | 1500 to 4000 Hz | — |
| Spectral Rolloff (85%) | Upper edge of significant energy | 4000 to 8000 Hz | — |
| Spectral Flatness | Tonality vs. noise (0.0 = tone, 1.0 = noise) | 0.1 to 0.4 | — |
| Band Energies | Energy in 7 frequency bands (sub-bass through brilliance) | Relative | — |

Band energies are reported in dB relative to the file's own broadband average (20 Hz-20 kHz mean power density), not absolute dBFS — a positive value means that band sits above the mix's average spectral density, negative means below. Because values are relative, they're comparable between files regardless of overall level.

### Stereo & Phase

| Metric | What it measures | Good range | Assessed |
|--------|-----------------|------------|----------|
| Phase Correlation | L/R correlation — mono compatibility | Above +0.5 | ✓ |
| Mid RMS | Center channel energy (M/S) | Relative | — |
| Side RMS | Difference channel energy (M/S) | Relative | — |
| M/S Ratio | Mid-to-side balance | 3 to 12 dB | ✓ |
| Stereo Width | L/R decorrelation, balance-compensated | 0.08 to 0.45 | ✓ |
| Channel Balance | L/R level difference | Within +/- 0.5 dB | ✓ |
| Block Correlation (p5) | Worst sustained phase in 50 ms windows (5th percentile) | Above 0.0 | ✓ |
| Frequency-Dependent Correlation | Per-band stereo correlation | Sub-bass >0.9 | — |
| Correlation Over Time | Phase correlation curve across the file, 50 points (sparkline in terminal) | Informational | — |

### Translation (Mono & Small Speakers)

| Metric | What it measures | Good range | Assessed |
|--------|-----------------|------------|----------|
| Mono Loss | Energy lost when the mix is summed to mono | 0 to -1 dB | ✓ |
| Mono Loss by Band | Where in the spectrum mono summing cancels energy | Each band 0 to -1 dB | — |
| Low-End Reliance | Fraction of the mix's energy below 120 Hz | 0.05 to 0.35 | ✓ |

Mono Loss by Band is reported alongside the worst-offending band and its loss
in dB (`worst_mono_band` / `worst_mono_band_loss_db` in JSON) so you know
where to look, but only the broadband `mono_loss_db` and `low_end_reliance`
carry pass/warn/fail rules.

### Perceptual Quality

| Metric | What it measures | Good range | Assessed |
|--------|-----------------|------------|----------|
| Brightness | High-frequency energy ratio (always computed, 0-1 proxy) | 0.1 to 0.3 | — |
| Warmth | Low-mid energy ratio (always computed, 0-1 proxy) | 0.1 to 0.3 | — |
| Timbral Brightness | AudioCommons perceptual brightness score | ~0-100 scale | — |
| Timbral Warmth | AudioCommons perceptual warmth score | ~0-100 scale | — |

Timbral Brightness/Warmth require the optional `perceptual` extra (`uv sync --extra perceptual`); they're reported alongside — not instead of — the always-on Brightness/Warmth proxies, which are what drive the rule and diagnostic engines.

### Tuning & Pitch

| Metric | What it measures | Good range | Assessed |
|--------|-----------------|------------|----------|
| Tuning Deviation | Offset from A440 concert pitch | Within ±8 cents | ✓ |
| Concert Pitch (A) | Estimated frequency of concert A | 435 to 445 Hz | — |
| Pitch Drift Range | Total pitch excursion over time | Under 8 cents | ✓ |
| Pitch Drift (std) | Standard deviation of tuning across time windows | Under 5 cents | ✓ |
| Chroma Sharpness | How well-defined pitch content is (0-1) | Above 0.6 | ✓ |

### Quality Control

| Metric | What it measures | Good range | Assessed |
|--------|-----------------|------------|----------|
| Clip Events | Count of hard-clipped sample runs (≥3 consecutive samples at −0.1 dBFS) | 0 | ✓ |
| Longest Clip Run | Length in samples of the longest flattened run | 0 samples | — |
| Leading Silence | Silence before the audio starts | 0 to 0.5 s | ✓ |
| Trailing Silence | Silence after the audio ends | 0 to 5 s | ✓ |

## Mix Diagnostics

Beyond per-metric pass/warn/fail assessments, Bounce House includes a **multi-metric diagnostic engine** that detects 9 common mixing problems by combining evidence across modules. Diagnostics appear in a dedicated section at the bottom of the report when triggered.

Each pattern uses soft-AND logic: a problem fires when enough conditions match (e.g., 2 of 3), so a single borderline metric won't produce a false alarm.

| Pattern | Severity | What it detects |
|---------|----------|----------------|
| Muddy Mix | warn | Low-mid buildup — centroid too low, warmth too high |
| Harsh / Brittle | warn | Excessive high-mid energy — bright, fatiguing |
| Thin / Weak | warn | Missing low-frequency body — HPFs too aggressive |
| Over-Compressed | fail | Dynamics crushed — low crest factor, hot LUFS, low LRA |
| Flat / Lifeless | warn | No stereo width or dynamic variation |
| Mono Incompatible | fail | Wide stereo with phase cancellation in mono |
| Wide Bass | warn | Stereo bass losing energy on mono playback |
| Detuned Mix | warn | Pitch instability or non-standard tuning |
| Streaming-Unfriendly | fail | Too hot for platform normalization (-14 LUFS target) |

Diagnostics layer on top of individual metric rules — they don't replace them. A mix can have clean per-metric scores but still trigger a diagnostic (e.g., "streaming-unfriendly" combines LUFS, true peak, and LRA).

## Architecture

Bounce House follows a pipeline: **load → analyze → assess → diagnose → format**.

```
wav/flac/aiff/ogg file
  │
  ▼
audio.py          Load via soundfile → AudioData (samples, sr, channels)
  │
  ▼
analyzers/        Each analyzer extends BaseAnalyzer
  ├── loudness    EBU R128 via pyloudnorm, crest factor, true peak
  ├── spectrum    librosa spectral features + 7-band energy via STFT
  ├── stereo      Phase correlation, M/S decomposition, frequency-dependent width
  ├── translation Mono-sum loss, per-band mono cancellation, low-end reliance
  ├── perceptual  Brightness/warmth proxy (+ timbral_models scores if installed)
  ├── tuning      Pitch deviation, drift, chroma sharpness (librosa)
  └── qc          Clipping detection, leading/trailing silence
  │
  ▼
rules.py          Data-driven pass/warn/fail rules per metric
  │
  ▼
diagnostics.py    Multi-metric pattern engine (9 mixing problems)
  │
  ▼
report.py         Terminal (ANSI) or JSON formatter
  │
  ▼
cli.py            argparse dispatch, entry point: bounce-house / bh
```

Key design decisions:
- **Analyzers are stateless** — each takes `AudioData` and returns `AnalysisResult` with a metrics dict
- **Rules are data, not code** — adding a new assessment rule means adding a dict entry, not writing a function
- **Metric docs live in code** — `metric_docs.py` contains all 39 metric explanations, used by both the `explain` command and (potentially) report tooltips
- **Diagnostics combine metrics** — `diagnostics.py` defines pattern conditions as data, evaluated with soft-AND logic across modules

## How It Compares

Most audio measurement tools are either GUI plugins or single-purpose CLI utilities:

- **bx_meter, Youlean, Insight** — DAW plugins with visual meters. Great for real-time monitoring during mixing, but can't be scripted, automated, or run in CI.
- **EXPOSE** — batch loudness scanner. Focuses on loudness compliance (LUFS, true peak) for delivery. Doesn't cover DR/dynamic-range scoring, spectral balance, stereo imaging, or actionable mix advice.
- **loudness-scanner** — CLI for EBU R128 loudness only. Single metric, no true peak, DR, spectral, or stereo analysis.

Bounce House combines multi-domain analysis (loudness + spectrum + stereo + translation + perceptual + tuning + quality control) with a rule engine that produces actionable mixing advice — all from the command line. True peak and DR (dynamic range) scoring are computed natively with no external dependencies. Pipe `--json` output into your own scripts or CI workflows, or use `diff` to gate CI on regressions between bounces.

## Dependencies

Core: `soundfile`, `numpy`, `scipy`, `pyloudnorm`, `librosa`, `rich`

Optional: `timbral_models` (perceptual analysis)

## Development

```bash
# Clone and install dev dependencies
git clone https://github.com/abehmiel/bounce-house.git
cd bounce-house
uv sync --extra dev

# Set up pre-commit hooks
uv run pre-commit install

# Run tests (the dev extra provides pytest)
uv run --extra dev pytest

# Run linter
uv run --extra dev ruff check src/ tests/

# Run type checker
uv run --extra dev mypy src/
```

### Project layout

```
src/bounce_house/
├── __init__.py          Version
├── audio.py             Audio loading (soundfile → AudioData), multi-format support
├── cli.py               CLI entry point and argparse setup
├── rules.py             Pass/warn/fail assessment rules
├── report.py            Terminal and JSON formatters
├── metric_docs.py       Metric documentation for explain command
├── diagnostics.py       Multi-metric diagnostic pattern engine
├── profiles.py          Stage profiles (mix vs. master thresholds)
├── genres.py            Genre target overlays (provisional) + --genre flag support
└── analyzers/
    ├── base.py          BaseAnalyzer, AnalysisResult, Assessment
    ├── loudness.py      EBU R128, dynamics, true peak
    ├── spectrum.py      Spectral features, band energies
    ├── stereo.py        Phase, M/S, stereo width
    ├── translation.py   Mono loss, per-band mono cancellation, low-end reliance
    ├── perceptual.py    Brightness, warmth
    ├── tuning.py        Tuning deviation, pitch drift, chroma sharpness
    └── qc.py            Clipping detection, leading/trailing silence
tests/
├── conftest.py          Synthetic audio fixtures
├── test_audio.py
├── test_cli.py
├── test_diagnostics.py
├── test_explain.py
├── test_genres.py
├── test_loudness.py
├── test_perceptual.py
├── test_profiles.py
├── test_qc.py
├── test_report.py
├── test_rules.py
├── test_spectrum.py
├── test_stereo.py
├── test_translation.py
└── test_tuning.py
```

## License

MIT
