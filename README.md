# Bounce House

[![CI](https://github.com/abehmiel/bounce-house/actions/workflows/ci.yml/badge.svg)](https://github.com/abehmiel/bounce-house/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

CLI tool for analyzing audio mixes — loudness, spectral balance, stereo imaging, and actionable mixing advice.

Bounce House reads a `.wav` file and reports EBU R128 loudness, spectral distribution across 7 frequency bands, stereo phase/width analysis, and perceptual brightness/warmth. Every metric gets a pass/warn/fail assessment with plain-English suggestions for what to fix. Compare your mix against a reference track to see band-by-band differences.

## Quick Start

```bash
# Install with uv (recommended)
uv sync

# Analyze a mix
bounce-house analyze mix.wav

# Short alias
bh analyze mix.wav
```

## Installation

### Using uv (recommended)

```bash
cd bounce-house
uv sync
```

### Using pip

```bash
cd bounce-house
pip install .
```

### From GitHub (no clone needed)

```bash
pip install git+https://github.com/abehmiel/bounce-house.git
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
```

### Compare against a reference

```bash
bounce-house compare mix.wav reference.wav
```

Shows all metrics for your mix alongside band-by-band energy differences against the reference track. Useful for matching tonal balance to a commercially released track in your genre.

### Explain metrics

Built-in documentation for every metric — what it measures, why it matters, good ranges, and genre-specific context:

```bash
bounce-house explain              # Overview of all metrics
bounce-house explain loudness     # All metrics in a module
bounce-house explain crest        # Single metric (fuzzy matched)
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

Exit codes for CI/CD gating: `0` = all pass, `1` = warnings, `2` = failures. Corrupt files are logged to stderr without stopping the batch.

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

## Example Output

```
════════════════════════════════════════════════════════════
  BOUNCE HOUSE — Mix Analysis Report
  mix.wav (44100 Hz, stereo, 0:03)
════════════════════════════════════════════════════════════

── Loudness & Dynamics ────────────────────────────────────
  Integrated LUFS        -7.8  WARN
  Loudness Range         +2.6  FAIL
  Sample Peak            -5.5
  True Peak              -5.5  PASS
  RMS Level              -10.0
  Crest Factor           +4.6  FAIL

── Spectral Balance ───────────────────────────────────────
  Centroid               624 Hz
  Bandwidth              774 Hz
  Rolloff (85%)          891 Hz
  Flatness               0.0000

  sub-bass                    7.0 dB
  bass                       40.9 dB
  low-mid                    34.3 dB
  mid                        22.2 dB
  upper-mid                   9.4 dB
  presence                  -30.7 dB
  brilliance                -43.4 dB

── Stereo & Phase ─────────────────────────────────────────
  Phase Correlation      0.9813  PASS
  Mid RMS                -10.1
  Side RMS               -29.7
  M/S Ratio              +19.6
  Stereo Width           0.0950
  Balance                +0.7  WARN
  Min Block Corr         0.9813  PASS

  Frequency-dependent correlation:
    sub-bass           +0.999
    low-mid            +0.990
    mid                +0.940
    upper-mid          +0.697
    air                +1.000

── Perceptual Quality ─────────────────────────────────────
  Brightness             0.0000
  Warmth                 0.9184

── Suggestions ────────────────────────────────────────────
  FAIL  Loudness range is 2.6 LU — extreme dynamics, review compressor/limiter settings
  FAIL  Crest factor is 4.6 dB — heavily squashed, reduce limiting or compression
  WARN  Integrated loudness is -7.8 LUFS — outside typical -16 to -8 range
  WARN  Channel balance is +0.7 dB — slight imbalance, check panning

── Mix Diagnostics ────────────────────────────────────────
  FAIL  Over-Compressed — Over-compressed master; dynamics crushed
        Reduce bus compressor ratio or increase threshold. Ease off the
        limiter — aim for at least 8 dB crest factor.

════════════════════════════════════════════════════════════
  2 warning(s), 2 failure(s)
════════════════════════════════════════════════════════════
```

## Metrics

Bounce House measures 22 metrics across 4 analysis modules. Run `bounce-house explain` for full documentation including genre-specific context and measurement standards.

### Loudness & Dynamics

| Metric | What it measures | Good range |
|--------|-----------------|------------|
| Integrated LUFS | Perceived loudness (ITU-R BS.1770) | -16 to -8 LUFS |
| Loudness Range (LRA) | Dynamic spread, quiet to loud (EBU R128) | 5 to 15 LU |
| True Peak | Maximum reconstructed waveform level | Below -1.0 dBTP |
| Sample Peak | Maximum digital sample value | Below -0.3 dBFS |
| RMS Level | Average signal power | -20 to -10 dB |
| Crest Factor | Peak-to-RMS ratio (transient headroom) | 8 to 14 dB |
| PLR | Peak-to-Loudness Ratio — over-compression indicator | Above 10 dB |

### Spectral Balance

| Metric | What it measures | Good range |
|--------|-----------------|------------|
| Spectral Centroid | Center of mass — correlates with brightness | 1500 to 3500 Hz |
| Spectral Bandwidth | Energy spread around centroid | 1500 to 4000 Hz |
| Spectral Rolloff (85%) | Upper edge of significant energy | 4000 to 8000 Hz |
| Spectral Flatness | Tonality vs. noise (0.0 = tone, 1.0 = noise) | 0.1 to 0.4 |
| Band Energies | Energy in 7 frequency bands (sub-bass through brilliance) | Relative |

### Stereo & Phase

| Metric | What it measures | Good range |
|--------|-----------------|------------|
| Phase Correlation | L/R correlation — mono compatibility | +0.3 to +0.7 |
| Mid RMS | Center channel energy (M/S) | Relative |
| Side RMS | Difference channel energy (M/S) | Relative |
| M/S Ratio | Mid-to-side balance | 3 to 12 dB |
| Stereo Width | Side-to-total energy ratio | 0.2 to 0.4 |
| Channel Balance | L/R level difference | Within +/- 0.5 dB |
| Min Block Correlation | Worst-case phase in any 50ms window | Above 0.0 |
| Frequency-Dependent Correlation | Per-band stereo correlation | Sub-bass >0.9 |

### Perceptual Quality

| Metric | What it measures | Good range |
|--------|-----------------|------------|
| Brightness | High-frequency energy ratio | 0.1 to 0.3 |
| Warmth | Low-mid energy ratio | 0.1 to 0.3 |

## Mix Diagnostics

Beyond per-metric pass/warn/fail assessments, Bounce House includes a **multi-metric diagnostic engine** that detects 8 common mixing problems by combining evidence across modules. Diagnostics appear in a dedicated section at the bottom of the report when triggered.

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
  └── perceptual  Brightness/warmth (proxy or timbral_models)
  │
  ▼
rules.py          Data-driven pass/warn/fail rules per metric
  │
  ▼
diagnostics.py    Multi-metric pattern engine (8 mixing problems)
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
- **Metric docs live in code** — `metric_docs.py` contains all 22 metric explanations, used by both the `explain` command and (potentially) report tooltips
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

# Run tests
uv run pytest

# Run linter
uv run ruff check src/ tests/

# Run type checker
uv run mypy src/
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
    └── perceptual.py    Brightness, warmth
tests/
├── conftest.py          Synthetic audio fixtures
├── test_audio.py
├── test_loudness.py
├── test_spectrum.py
├── test_stereo.py
├── test_rules.py
├── test_report.py
├── test_cli.py
└── test_diagnostics.py
```

## License

MIT
