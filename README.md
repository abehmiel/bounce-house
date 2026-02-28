# Bounce House

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

### JSON output

All analysis commands support `--json` for machine-readable output:

```bash
bounce-house analyze mix.wav --json
bounce-house loudness mix.wav --json
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

════════════════════════════════════════════════════════════
  2 warning(s), 2 failure(s)
════════════════════════════════════════════════════════════
```

## Metrics

Bounce House measures 21 metrics across 4 analysis modules. Run `bounce-house explain` for full documentation including genre-specific context and measurement standards.

### Loudness & Dynamics

| Metric | What it measures | Good range |
|--------|-----------------|------------|
| Integrated LUFS | Perceived loudness (ITU-R BS.1770) | -16 to -8 LUFS |
| Loudness Range (LRA) | Dynamic spread, quiet to loud (EBU R128) | 5 to 15 LU |
| True Peak | Maximum reconstructed waveform level | Below -1.0 dBTP |
| Sample Peak | Maximum digital sample value | Below -0.3 dBFS |
| RMS Level | Average signal power | -20 to -10 dB |
| Crest Factor | Peak-to-RMS ratio (transient headroom) | 8 to 14 dB |

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

## Architecture

Bounce House follows a pipeline: **load → analyze → assess → format**.

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
report.py         Terminal (ANSI) or JSON formatter
  │
  ▼
cli.py            argparse dispatch, entry point: bounce-house / bh
```

Key design decisions:
- **Analyzers are stateless** — each takes `AudioData` and returns `AnalysisResult` with a metrics dict
- **Rules are data, not code** — adding a new assessment rule means adding a dict entry, not writing a function
- **Metric docs live in code** — `metric_docs.py` contains all 21 metric explanations, used by both the `explain` command and (potentially) report tooltips

## How It Compares

Most audio measurement tools are either GUI plugins or single-purpose CLI utilities:

- **bx_meter, Youlean, Insight** — DAW plugins with visual meters. Great for real-time monitoring during mixing, but can't be scripted, automated, or run in CI.
- **EXPOSE** — batch loudness scanner. Focuses on loudness compliance (LUFS, true peak) for delivery. Doesn't cover spectral balance, stereo imaging, or actionable mix advice.
- **loudness-scanner** — CLI for EBU R128 loudness only. Single metric, no spectral or stereo analysis.

Bounce House combines multi-domain analysis (loudness + spectrum + stereo + perceptual) with a rule engine that produces actionable mixing advice — all from the command line. Pipe `--json` output into your own scripts or CI workflows.

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=bounce_house
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
└── test_cli.py
```

## License

MIT
