# Bounce House — Audio Mix Analysis CLI Tool Design

## Overview

Bounce House is a CLI tool that analyzes .wav files and produces a comprehensive mix report with actionable advice. It supports standalone analysis and reference track comparison as first-class features. The tool works entirely offline with rule-based advice — no LLM or API keys required.

The name references Logic Pro's "bounce" export terminology.

## CLI Interface

**Commands:**

```bash
bounce-house analyze mix.wav                    # full report (all modules)
bounce-house analyze mix.wav --json             # structured JSON output
bounce-house analyze mix.wav --reference ref.wav # full report vs reference
bounce-house loudness mix.wav                   # loudness/dynamics only
bounce-house spectrum mix.wav                   # spectral analysis only
bounce-house stereo mix.wav                     # stereo/phase only
bounce-house compare mix.wav ref.wav            # reference comparison
bounce-house compare mix.wav ref.wav --json     # reference comparison as JSON
```

`bh` is registered as a shorter alias via a second console_scripts entry point.

All subcommands accept `--json` for machine-readable output.

## Architecture: Subcommand + Composable Modules

Each analysis domain is both a standalone subcommand and a composable module. The `analyze` command runs all modules; `compare` runs all modules with reference comparison. Individual subcommands (`loudness`, `spectrum`, `stereo`) run a single module.

### Project Structure

```
bounce_house/
├── pyproject.toml
├── src/
│   └── bounce_house/
│       ├── __init__.py
│       ├── cli.py              # argparse setup, subcommand dispatch
│       ├── audio.py            # shared audio loading (soundfile wrapper)
│       ├── report.py           # output formatting (terminal + JSON)
│       ├── rules.py            # rule-based advice engine
│       ├── analyzers/
│       │   ├── __init__.py
│       │   ├── base.py         # AnalyzerBase ABC
│       │   ├── loudness.py     # LUFS, true peak, LRA, crest, DR
│       │   ├── spectrum.py     # spectral centroid, tonal balance, band energy
│       │   ├── stereo.py       # phase correlation, M/S, width, balance
│       │   └── perceptual.py   # timbral descriptors
│       └── compare.py          # reference comparison logic
├── tests/
│   ├── conftest.py
│   ├── test_loudness.py
│   ├── test_spectrum.py
│   ├── test_stereo.py
│   └── test_cli.py
└── docs/
    ├── research/
    └── plans/
```

### Core Data Types

```python
@dataclass
class AudioData:
    samples: np.ndarray   # shape: (num_samples, num_channels)
    sample_rate: int
    filepath: Path

@dataclass
class Assessment:
    metric: str       # e.g., "integrated_lufs"
    value: float
    status: str       # "pass" | "warn" | "fail"
    message: str      # human-readable advice
    reference: float | None

@dataclass
class AnalysisResult:
    module: str
    metrics: dict[str, Any]
    assessments: list[Assessment]

class AnalyzerBase(ABC):
    @abstractmethod
    def analyze(self, audio: AudioData) -> AnalysisResult: ...

    @abstractmethod
    def compare(self, audio: AudioData, reference: AudioData) -> AnalysisResult: ...
```

Audio is loaded once via soundfile, then passed to each analyzer.

## Analysis Modules

### Loudness & Dynamics

Uses pyloudnorm for LUFS/LRA, ffmpeg for true peak (with sample-peak fallback), numpy for crest factor.

**Metrics:** integrated LUFS, momentary LUFS max, short-term LUFS max, true peak dBTP, LRA (LU), crest factor (dB), dynamic range (DR).

### Spectral Balance

Uses librosa for spectral features and band energy computation.

**Metrics:** spectral centroid (Hz), bandwidth (Hz), rolloff at 85% (Hz), flatness. Energy in 7 mixing-relevant bands: sub-bass (20-60), bass (60-250), low-mid (250-500), mid (500-2k), upper-mid (2k-4k), presence (4k-6k), brilliance (6k-20k).

In compare mode: per-band dB difference from reference.

### Stereo & Phase

Pure numpy/scipy. No external dependencies beyond the scientific stack.

**Metrics:** phase correlation (Pearson), minimum 50ms block correlation, M/S decomposition (mid RMS, side RMS, M/S ratio dB), stereo width (0=mono, 0.5=full), channel balance (dB), frequency-dependent stereo width in 5 bands (sub/bass, low-mid, mid, upper-mid, air).

### Perceptual (optional)

Uses timbral_models if installed, otherwise skips with a note.

**Metrics:** brightness, warmth, hardness/harshness estimates.

## Rule-Based Advice Engine

Rules are defined as data, not hardcoded conditionals. Each rule maps a metric to threshold ranges and actionable advice messages.

### Default Thresholds

| Metric | Pass | Warn | Fail |
|--------|------|------|------|
| Integrated LUFS | -16 to -8 | -20 to -16 or -8 to -6 | below -20 or above -6 |
| True peak | below -1.0 dBTP | -1.0 to -0.5 dBTP | above -0.5 dBTP |
| LRA | 5-15 LU | 3-5 or 15-20 LU | below 3 or above 20 LU |
| Crest factor | above 10 dB | 6-10 dB | below 6 dB |
| Phase correlation | above 0.3 | 0.0-0.3 | below 0.0 |
| Min block correlation | above 0.0 | -0.3 to 0.0 | below -0.3 |
| Bass correlation (<120Hz) | above 0.8 | 0.5-0.8 | below 0.5 |
| Stereo balance | within 0.5 dB | 0.5-1.5 dB | beyond 1.5 dB |

In reference comparison mode, rules flag per-band deviations exceeding 3 dB, stereo width differences, and loudness mismatches.

Advice messages are concrete and actionable, e.g.:
- "Bass correlation is 0.32 — consider using a mid/side EQ to mono frequencies below 120 Hz"
- "True peak is -0.2 dBTP — add a limiter ceiling at -1.0 dBTP to avoid inter-sample peaks on codec conversion"

## Output Formats

### Terminal (default)

Rich formatted output using ANSI colors and Unicode box-drawing characters. Sections for each analysis domain, pass/warn/fail indicators, and a suggestions section at the bottom with a summary count.

### JSON (--json flag)

Structured dict with keys: `file`, `format`, `loudness`, `spectrum`, `stereo`, `perceptual`, `assessments`, `summary`.

## Dependencies

### Required

- soundfile — WAV loading
- numpy — array math, stereo analysis
- scipy — STFT for frequency-dependent stereo width
- pyloudnorm — ITU-R BS.1770-4 LUFS/LRA
- librosa — spectral features

### Optional

- timbral_models — perceptual descriptors (graceful fallback if missing)

### External Tools

- ffmpeg — true peak measurement (falls back to sample peak with warning if not found)

### Dev

- pytest, pytest-cov

## Packaging

- uv for dependency management and project setup
- pyproject.toml with console_scripts entry points for both `bounce-house` and `bh`
- src layout (src/bounce_house/)
