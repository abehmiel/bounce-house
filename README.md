# Bounce House

[![CI](https://github.com/abehmiel/bounce-house/actions/workflows/ci.yml/badge.svg)](https://github.com/abehmiel/bounce-house/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A CLI audio analysis tool that tells you what's wrong with your mix — and what to do about it.

Bounce House runs 26 metrics across loudness, spectral balance, stereo imaging, tuning, and perceptual quality. Every metric gets a pass/warn/fail assessment with plain-English advice. Nine diagnostic patterns catch common mixing problems (muddy low end, crushed dynamics, mono-incompatible stereo) by combining evidence across modules. Compare against a reference track, batch-analyze an album, or pipe `--json` into your CI pipeline.

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

**True peak measurement** — install [ffmpeg](https://ffmpeg.org/) for inter-sample true peak detection via the `loudnorm` filter. Without ffmpeg, bounce-house falls back to sample peak measurement.

## Usage

### Full analysis

```bash
bounce-house analyze mix.wav
```

### Individual modules

Run a single analysis module when you only care about one domain:

```bash
bounce-house loudness mix.wav    # EBU R128 loudness, dynamics, crest factor
bounce-house spectrum mix.wav    # Spectral centroid, bandwidth, band energies
bounce-house stereo mix.wav      # Phase correlation, M/S ratio, stereo width
bounce-house perceptual mix.wav  # Brightness, warmth (proxy or timbral_models)
bounce-house tuning mix.wav      # Tuning deviation, pitch drift, chroma sharpness
```

### Compare against a reference

```bash
bounce-house compare mix.wav reference.wav
```

Shows all metrics for your mix alongside band-by-band energy differences against the reference track. Useful for matching tonal balance to a commercially released track in your genre.

### Explain metrics

Built-in documentation for every metric — what it measures, why it matters, good ranges, and genre-specific context:

```bash
bounce-house explain                  # Overview of all metrics
bounce-house explain loudness         # All metrics in a module
bounce-house explain crest            # Single metric (fuzzy matched)
bounce-house explain lra --technical  # Include measurement standards
```

### Batch directory analysis

Analyze all WAV files in a directory at once — great for checking an album, stems folder, or CI pipeline:

```bash
bounce-house dir ./masters/                    # All WAVs in directory
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

JSON output includes a top-level `"schema_version": 1` field; non-finite measurements
(e.g., LUFS of digital silence) are serialized as `null`.

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

```
════════════════════════════════════════════════════════════
  BOUNCE HOUSE — Master Analysis Report
  mix.wav (44100 Hz, stereo, 0:10)
════════════════════════════════════════════════════════════

── Loudness & Dynamics ────────────────────────────────────
  Integrated LUFS        -9.5  PASS
  Loudness Range         +1.0  FAIL
  Sample Peak            -3.1
  True Peak              -3.1  PASS
  RMS Level              -11.7
  Crest Factor           +8.6  WARN
  PLR                    +6.4  FAIL

── Spectral Balance ───────────────────────────────────────
  Centroid               6,021.8 Hz
  Bandwidth              6,995.6 Hz
  Rolloff (85%)          15,729.8 Hz
  Flatness               0.0066

  sub-bass                    5.7 dB
  bass                       38.9 dB
  low-mid                    33.1 dB
  mid                        21.6 dB
  upper-mid                   0.3 dB
  presence                    0.3 dB
  brilliance                  0.3 dB

── Stereo & Phase ─────────────────────────────────────────
  Phase Correlation      0.9674  PASS
  Mid RMS                -11.8
  Side RMS               -29.5
  M/S Ratio              +17.7
  Stereo Width           0.1147
  Balance                +0.3  PASS
  Min Block Corr         0.9641
  Block Corr (p5)        0.9659  PASS

  Frequency-dependent correlation:
    sub-bass           +1.000
    low-mid            +0.954
    mid                +0.980
    upper-mid          -0.001
    air                +0.003

── Perceptual Quality ─────────────────────────────────────
  Brightness             0.0086
  Warmth                 0.2260

── Tuning & Pitch ─────────────────────────────────────────
  Tuning Deviation       -3.0 cents  PASS
  Concert Pitch          439.2 Hz
  Closest Standard       A=440
  Pitch Drift (std)      +0.0 cents
  Pitch Drift (range)    +0.0 cents  PASS
  Pitch Trend            -0.0 cents
  Chroma Sharpness       0.8700  PASS

── Suggestions ────────────────────────────────────────────
  FAIL  Loudness range is 1.0 LU — extreme dynamics, review compressor/limiter settings
  FAIL  PLR is 6.4 dB — heavily limited, consider backing off the limiter
  WARN  Crest factor is 8.6 dB — transients may be over-compressed

── Mix Diagnostics ────────────────────────────────────────
  WARN  Muddy Mix — Low-mid buildup causing muddy mix
        Cut 2-4 dB in the 200-500 Hz range. Check for overlapping bass, guitar body, and vocal chest resonance. Use a high-pass filter on non-bass instruments to remove unnecessary low-mid energy.
  WARN  Harsh / Brittle Mix — Excessive high-mid energy causing harshness
        Check for resonant peaks in the 2-5 kHz range on vocals and guitars. Apply narrow-Q cuts of -2 to -4 dB at problem frequencies. Consider a de-esser on vocals targeting 5-8 kHz. Rather than boosting highs, try cutting low-mids to improve clarity.
  WARN  Flat / Lifeless Mix — Mix lacks spatial depth and dynamic variation
        Add spatial depth with reverb and delay. Vary dynamics between sections (quieter verses, louder choruses). Check panning — spreading instruments across the stereo field adds life. Even small stereo width differences between verse and chorus create perceived energy.

════════════════════════════════════════════════════════════
  1 warning(s), 2 failure(s)
════════════════════════════════════════════════════════════
```

## Metrics

Bounce House measures 26 metrics across 5 analysis modules. Run `bounce-house explain` for full documentation including genre-specific context and measurement standards.

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

### Spectral Balance

| Metric | What it measures | Good range | Assessed |
|--------|-----------------|------------|----------|
| Spectral Centroid | Center of mass — correlates with brightness | 1500 to 3500 Hz | — |
| Spectral Bandwidth | Energy spread around centroid | 1500 to 4000 Hz | — |
| Spectral Rolloff (85%) | Upper edge of significant energy | 4000 to 8000 Hz | — |
| Spectral Flatness | Tonality vs. noise (0.0 = tone, 1.0 = noise) | 0.1 to 0.4 | — |
| Band Energies | Energy in 7 frequency bands (sub-bass through brilliance) | Relative | — |

### Stereo & Phase

| Metric | What it measures | Good range | Assessed |
|--------|-----------------|------------|----------|
| Phase Correlation | L/R correlation — mono compatibility | Above +0.3 | ✓ |
| Mid RMS | Center channel energy (M/S) | Relative | — |
| Side RMS | Difference channel energy (M/S) | Relative | — |
| M/S Ratio | Mid-to-side balance | 3 to 12 dB | — |
| Stereo Width | Side-to-total energy ratio | 0.2 to 0.4 | — |
| Channel Balance | L/R level difference | Within +/- 0.5 dB | ✓ |
| Block Correlation (p5) | Worst sustained phase in 50 ms windows (5th percentile) | Above 0.0 | ✓ |
| Frequency-Dependent Correlation | Per-band stereo correlation | Sub-bass >0.9 | — |

### Perceptual Quality

| Metric | What it measures | Good range | Assessed |
|--------|-----------------|------------|----------|
| Brightness | High-frequency energy ratio | 0.1 to 0.3 | — |
| Warmth | Low-mid energy ratio | 0.1 to 0.3 | — |

### Tuning & Pitch

| Metric | What it measures | Good range | Assessed |
|--------|-----------------|------------|----------|
| Tuning Deviation | Offset from A440 concert pitch | Within ±8 cents | ✓ |
| Concert Pitch (A) | Estimated frequency of concert A | 435 to 445 Hz | — |
| Pitch Drift Range | Total pitch excursion over time | Under 8 cents | ✓ |
| Chroma Sharpness | How well-defined pitch content is (0-1) | Above 0.6 | ✓ |

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
wav file
  │
  ▼
audio.py          Load via soundfile → AudioData (samples, sr, channels)
  │
  ▼
analyzers/        Each analyzer extends BaseAnalyzer
  ├── loudness    EBU R128 via pyloudnorm, crest factor, true peak (ffmpeg)
  ├── spectrum    librosa spectral features + 7-band energy via STFT
  ├── stereo      Phase correlation, M/S decomposition, frequency-dependent width
  ├── perceptual  Brightness/warmth (proxy or timbral_models)
  └── tuning      Pitch deviation, drift, chroma sharpness (librosa)
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
- **Metric docs live in code** — `metric_docs.py` contains all 26 metric explanations, used by both the `explain` command and (potentially) report tooltips
- **Diagnostics combine metrics** — `diagnostics.py` defines pattern conditions as data, evaluated with soft-AND logic across modules

## How It Compares

Most audio measurement tools are either GUI plugins or single-purpose CLI utilities:

- **bx_meter, Youlean, Insight** — DAW plugins with visual meters. Great for real-time monitoring during mixing, but can't be scripted, automated, or run in CI.
- **EXPOSE** — batch loudness scanner. Focuses on loudness compliance (LUFS, true peak) for delivery. Doesn't cover spectral balance, stereo imaging, or actionable mix advice.
- **loudness-scanner** — CLI for EBU R128 loudness only. Single metric, no spectral or stereo analysis.

Bounce House combines multi-domain analysis (loudness + spectrum + stereo + perceptual) with a rule engine that produces actionable mixing advice — all from the command line. Pipe `--json` output into your own scripts or CI workflows.

## Dependencies

Core: `soundfile`, `numpy`, `scipy`, `pyloudnorm`, `librosa`, `rich`

Optional: `timbral_models` (perceptual analysis), `ffmpeg` (true peak measurement)

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
├── audio.py             Audio loading (soundfile → AudioData)
├── cli.py               CLI entry point and argparse setup
├── rules.py             Pass/warn/fail assessment rules
├── report.py            Terminal and JSON formatters
├── metric_docs.py       Metric documentation for explain command
├── diagnostics.py       Multi-metric diagnostic pattern engine
├── profiles.py          Stage profiles (mix vs. master thresholds)
└── analyzers/
    ├── base.py          BaseAnalyzer, AnalysisResult, Assessment
    ├── loudness.py      EBU R128, dynamics, true peak
    ├── spectrum.py      Spectral features, band energies
    ├── stereo.py        Phase, M/S, stereo width
    ├── perceptual.py    Brightness, warmth
    └── tuning.py        Tuning deviation, pitch drift, chroma sharpness
tests/
├── conftest.py          Synthetic audio fixtures
├── test_audio.py
├── test_cli.py
├── test_diagnostics.py
├── test_explain.py
├── test_loudness.py
├── test_perceptual.py
├── test_profiles.py
├── test_report.py
├── test_rules.py
├── test_spectrum.py
├── test_stereo.py
└── test_tuning.py
```

## License

MIT
