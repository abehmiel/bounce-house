# Bounce House Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a CLI tool that analyzes .wav files for loudness, spectral balance, stereo/phase, and perceptual quality, producing actionable mix improvement advice.

**Architecture:** Subcommand-based CLI (argparse) with composable analyzer modules. Each analyzer implements an `AnalyzerBase` ABC, takes `AudioData`, returns `AnalysisResult`. A rule engine evaluates metrics against thresholds. Report formatter handles terminal (ANSI) and JSON output.

**Tech Stack:** Python 3.11+, uv, argparse, soundfile, numpy, scipy, pyloudnorm, librosa, pytest

**Design doc:** `docs/plans/2026-02-28-bounce-house-design.md`

---

### Task 1: Project Scaffolding & Packaging

**Files:**
- Create: `pyproject.toml`
- Create: `src/bounce_house/__init__.py`
- Create: `src/bounce_house/cli.py`
- Create: `tests/__init__.py`
- Create: `tests/test_cli.py`
- Create: `.gitignore`

**Step 1: Initialize uv project**

Run: `uv init --lib --name bounce-house`

This creates the basic pyproject.toml. We'll replace its contents entirely.

**Step 2: Write pyproject.toml**

```toml
[project]
name = "bounce-house"
version = "0.1.0"
description = "CLI tool for analyzing audio mixes — loudness, spectral balance, stereo imaging, and actionable advice"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "soundfile>=0.12",
    "numpy>=1.24",
    "scipy>=1.10",
    "pyloudnorm>=0.1",
    "librosa>=0.10",
]

[project.optional-dependencies]
perceptual = ["timbral_models"]
dev = ["pytest>=7.0", "pytest-cov>=4.0"]

[project.scripts]
bounce-house = "bounce_house.cli:main"
bh = "bounce_house.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/bounce_house"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Step 3: Create src/bounce_house/__init__.py**

```python
"""Bounce House — audio mix analysis CLI tool."""

__version__ = "0.1.0"
```

**Step 4: Create minimal cli.py**

```python
"""CLI entry point for bounce-house."""

import argparse
import sys


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bounce-house",
        description="Analyze audio mixes for loudness, spectral balance, stereo imaging, and more.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_get_version()}")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze — full report
    analyze_parser = subparsers.add_parser("analyze", help="Run full analysis on a mix")
    analyze_parser.add_argument("file", help="Path to .wav file")
    analyze_parser.add_argument("--reference", help="Path to reference .wav file")
    analyze_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # loudness
    loudness_parser = subparsers.add_parser("loudness", help="Loudness and dynamics analysis")
    loudness_parser.add_argument("file", help="Path to .wav file")
    loudness_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # spectrum
    spectrum_parser = subparsers.add_parser("spectrum", help="Spectral analysis")
    spectrum_parser.add_argument("file", help="Path to .wav file")
    spectrum_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # stereo
    stereo_parser = subparsers.add_parser("stereo", help="Stereo imaging and phase analysis")
    stereo_parser.add_argument("file", help="Path to .wav file")
    stereo_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # compare
    compare_parser = subparsers.add_parser("compare", help="Compare mix against a reference track")
    compare_parser.add_argument("file", help="Path to .wav file")
    compare_parser.add_argument("reference", help="Path to reference .wav file")
    compare_parser.add_argument("--json", action="store_true", help="Output as JSON")

    return parser


def _get_version() -> str:
    from bounce_house import __version__
    return __version__


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    print(f"Command: {args.command}, File: {args.file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Step 5: Create .gitignore**

```
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
.venv/
.uv/
*.wav
```

**Step 6: Create tests/__init__.py (empty)**

**Step 7: Write the failing test for CLI**

Create `tests/test_cli.py`:

```python
"""Tests for CLI argument parsing and dispatch."""

from bounce_house.cli import create_parser, main


class TestParser:
    def test_analyze_requires_file(self):
        parser = create_parser()
        # argparse exits on missing required args, so we check parse_args works with file
        args = parser.parse_args(["analyze", "mix.wav"])
        assert args.command == "analyze"
        assert args.file == "mix.wav"
        assert args.reference is None
        assert args.json is False

    def test_analyze_with_reference(self):
        parser = create_parser()
        args = parser.parse_args(["analyze", "mix.wav", "--reference", "ref.wav"])
        assert args.reference == "ref.wav"

    def test_analyze_with_json(self):
        parser = create_parser()
        args = parser.parse_args(["analyze", "mix.wav", "--json"])
        assert args.json is True

    def test_loudness_subcommand(self):
        parser = create_parser()
        args = parser.parse_args(["loudness", "mix.wav"])
        assert args.command == "loudness"

    def test_spectrum_subcommand(self):
        parser = create_parser()
        args = parser.parse_args(["spectrum", "mix.wav"])
        assert args.command == "spectrum"

    def test_stereo_subcommand(self):
        parser = create_parser()
        args = parser.parse_args(["stereo", "mix.wav"])
        assert args.command == "stereo"

    def test_compare_subcommand(self):
        parser = create_parser()
        args = parser.parse_args(["compare", "mix.wav", "ref.wav"])
        assert args.command == "compare"
        assert args.file == "mix.wav"
        assert args.reference == "ref.wav"

    def test_no_command_returns_1(self):
        assert main([]) == 1
```

**Step 8: Install project and run tests**

Run: `uv sync --dev`
Run: `uv run pytest tests/test_cli.py -v`
Expected: All tests PASS

**Step 9: Commit**

```bash
git add pyproject.toml src/ tests/ .gitignore
git commit -m "feat: scaffold project with CLI argument parsing

Set up uv project with src layout, argparse-based CLI with subcommands
(analyze, loudness, spectrum, stereo, compare), console_scripts for
bounce-house and bh aliases, and CLI parser tests."
```

---

### Task 2: Audio Loading Module

**Files:**
- Create: `src/bounce_house/audio.py`
- Create: `tests/conftest.py`
- Create: `tests/test_audio.py`

**Step 1: Write test fixtures — synthetic WAV generators**

Create `tests/conftest.py`:

```python
"""Shared test fixtures — synthetic audio generators."""

import numpy as np
import soundfile as sf
import pytest
from pathlib import Path


@pytest.fixture
def tmp_wav(tmp_path) -> Path:
    """Generate a 1-second stereo 440Hz sine wave at 44100 Hz, 16-bit."""
    sr = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    left = 0.5 * np.sin(2 * np.pi * 440 * t)
    right = 0.3 * np.sin(2 * np.pi * 440 * t + np.pi / 4)  # slight phase offset
    stereo = np.column_stack([left, right])
    path = tmp_path / "test.wav"
    sf.write(str(path), stereo, sr, subtype="PCM_16")
    return path


@pytest.fixture
def tmp_mono_wav(tmp_path) -> Path:
    """Generate a 1-second mono 440Hz sine wave."""
    sr = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    mono = 0.5 * np.sin(2 * np.pi * 440 * t)
    path = tmp_path / "mono.wav"
    sf.write(str(path), mono, sr, subtype="PCM_16")
    return path


@pytest.fixture
def tmp_silent_wav(tmp_path) -> Path:
    """Generate a 1-second stereo silent file."""
    sr = 44100
    silence = np.zeros((sr, 2))
    path = tmp_path / "silent.wav"
    sf.write(str(path), silence, sr, subtype="PCM_16")
    return path


@pytest.fixture
def tmp_reference_wav(tmp_path) -> Path:
    """Generate a 1-second stereo reference with different spectral character."""
    sr = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Richer harmonic content than the test signal
    left = 0.4 * np.sin(2 * np.pi * 440 * t) + 0.2 * np.sin(2 * np.pi * 880 * t)
    right = 0.4 * np.sin(2 * np.pi * 440 * t) + 0.2 * np.sin(2 * np.pi * 880 * t)
    stereo = np.column_stack([left, right])
    path = tmp_path / "reference.wav"
    sf.write(str(path), stereo, sr, subtype="PCM_16")
    return path
```

**Step 2: Write failing tests for audio loading**

Create `tests/test_audio.py`:

```python
"""Tests for audio loading module."""

import numpy as np
from pathlib import Path
from bounce_house.audio import load_audio, AudioData


def test_load_stereo_wav(tmp_wav):
    audio = load_audio(tmp_wav)
    assert isinstance(audio, AudioData)
    assert audio.sample_rate == 44100
    assert audio.samples.ndim == 2
    assert audio.samples.shape[1] == 2
    assert audio.filepath == tmp_wav


def test_load_mono_wav(tmp_mono_wav):
    audio = load_audio(tmp_mono_wav)
    # Mono files should be reshaped to (N, 1) for consistent handling
    assert audio.samples.ndim == 2
    assert audio.samples.shape[1] == 1


def test_load_preserves_sample_values(tmp_wav):
    audio = load_audio(tmp_wav)
    # Samples should be float64 in range [-1, 1]
    assert audio.samples.dtype == np.float64
    assert np.max(np.abs(audio.samples)) <= 1.0


def test_load_nonexistent_file_raises():
    import pytest
    with pytest.raises(FileNotFoundError):
        load_audio(Path("/nonexistent/file.wav"))


def test_audio_data_channels(tmp_wav):
    audio = load_audio(tmp_wav)
    assert audio.channels == 2


def test_audio_data_duration(tmp_wav):
    audio = load_audio(tmp_wav)
    assert abs(audio.duration - 1.0) < 0.01


def test_audio_data_is_stereo(tmp_wav, tmp_mono_wav):
    stereo = load_audio(tmp_wav)
    mono = load_audio(tmp_mono_wav)
    assert stereo.is_stereo is True
    assert mono.is_stereo is False
```

**Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_audio.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bounce_house.audio'`

**Step 4: Implement audio.py**

Create `src/bounce_house/audio.py`:

```python
"""Audio loading and shared data types."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf


@dataclass
class AudioData:
    """Loaded audio data with metadata."""

    samples: np.ndarray  # shape: (num_samples, num_channels), float64
    sample_rate: int
    filepath: Path

    @property
    def channels(self) -> int:
        return self.samples.shape[1]

    @property
    def duration(self) -> float:
        return self.samples.shape[0] / self.sample_rate

    @property
    def is_stereo(self) -> bool:
        return self.channels >= 2


def load_audio(path: Path) -> AudioData:
    """Load a WAV file and return AudioData.

    Mono files are reshaped to (N, 1) for consistent handling.
    Raises FileNotFoundError if the file doesn't exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    samples, sample_rate = sf.read(str(path), dtype="float64")

    # Ensure 2D: (num_samples, num_channels)
    if samples.ndim == 1:
        samples = samples[:, np.newaxis]

    return AudioData(samples=samples, sample_rate=sample_rate, filepath=path)
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_audio.py -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add src/bounce_house/audio.py tests/conftest.py tests/test_audio.py
git commit -m "feat: add audio loading module with AudioData type

Loads WAV files via soundfile, normalizes mono to 2D array shape,
provides channels/duration/is_stereo properties. Includes synthetic
WAV test fixtures for stereo, mono, silent, and reference signals."
```

---

### Task 3: Analyzer Base Class

**Files:**
- Create: `src/bounce_house/analyzers/__init__.py`
- Create: `src/bounce_house/analyzers/base.py`

**Step 1: Write base.py**

Create `src/bounce_house/analyzers/__init__.py` (empty).

Create `src/bounce_house/analyzers/base.py`:

```python
"""Base types and abstract class for analyzers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from bounce_house.audio import AudioData


@dataclass
class Assessment:
    """A single rule-based judgment on a metric."""

    metric: str
    value: float
    status: str  # "pass" | "warn" | "fail"
    message: str
    reference: float | None = None


@dataclass
class AnalysisResult:
    """Results from a single analysis module."""

    module: str
    metrics: dict[str, Any] = field(default_factory=dict)
    assessments: list[Assessment] = field(default_factory=list)


class AnalyzerBase(ABC):
    """Abstract base class for analysis modules."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short name for this analyzer (e.g., 'loudness')."""
        ...

    @abstractmethod
    def analyze(self, audio: AudioData) -> AnalysisResult:
        """Analyze a single audio file."""
        ...

    @abstractmethod
    def compare(self, audio: AudioData, reference: AudioData) -> AnalysisResult:
        """Analyze audio file relative to a reference."""
        ...
```

**Step 2: No test needed — this is an ABC with no logic. Verified via usage in subsequent tasks.**

**Step 3: Commit**

```bash
git add src/bounce_house/analyzers/
git commit -m "feat: add AnalyzerBase ABC and result data types

Defines Assessment, AnalysisResult dataclasses and the AnalyzerBase
abstract class that all analysis modules implement."
```

---

### Task 4: Loudness & Dynamics Analyzer

**Files:**
- Create: `src/bounce_house/analyzers/loudness.py`
- Create: `tests/test_loudness.py`

**Step 1: Write failing tests**

Create `tests/test_loudness.py`:

```python
"""Tests for loudness and dynamics analyzer."""

import numpy as np
import soundfile as sf
from pathlib import Path

from bounce_house.audio import load_audio
from bounce_house.analyzers.loudness import LoudnessAnalyzer


class TestLoudnessAnalyzer:
    def setup_method(self):
        self.analyzer = LoudnessAnalyzer()

    def test_name(self):
        assert self.analyzer.name == "loudness"

    def test_analyze_returns_result(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert result.module == "loudness"

    def test_analyze_has_expected_metrics(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        expected_keys = {
            "integrated_lufs",
            "loudness_range_lu",
            "sample_peak_dbfs",
            "true_peak_dbtp",
            "crest_factor_db",
            "rms_db",
        }
        assert expected_keys.issubset(set(result.metrics.keys()))

    def test_integrated_lufs_is_negative(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert result.metrics["integrated_lufs"] < 0

    def test_sample_peak_within_range(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        # For a 0.5 amplitude sine, peak should be around -6 dBFS
        assert -10 < result.metrics["sample_peak_dbfs"] < 0

    def test_crest_factor_positive(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert result.metrics["crest_factor_db"] > 0

    def test_silent_file_handling(self, tmp_silent_wav):
        audio = load_audio(tmp_silent_wav)
        result = self.analyzer.analyze(audio)
        # Should not crash on silence, LUFS should be very negative
        assert result.metrics["integrated_lufs"] < -60

    def test_compare_returns_result(self, tmp_wav, tmp_reference_wav):
        audio = load_audio(tmp_wav)
        ref = load_audio(tmp_reference_wav)
        result = self.analyzer.compare(audio, ref)
        assert result.module == "loudness"
        assert "lufs_difference" in result.metrics

    def test_compare_shows_difference(self, tmp_wav, tmp_reference_wav):
        audio = load_audio(tmp_wav)
        ref = load_audio(tmp_reference_wav)
        result = self.analyzer.compare(audio, ref)
        # Difference should be a real number
        assert isinstance(result.metrics["lufs_difference"], float)
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_loudness.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement loudness.py**

Create `src/bounce_house/analyzers/loudness.py`:

```python
"""Loudness and dynamics analyzer."""

from __future__ import annotations

import shutil
import subprocess
import json
import tempfile

import numpy as np
import pyloudnorm as pyln

from bounce_house.audio import AudioData
from bounce_house.analyzers.base import AnalyzerBase, AnalysisResult


class LoudnessAnalyzer(AnalyzerBase):
    @property
    def name(self) -> str:
        return "loudness"

    def analyze(self, audio: AudioData) -> AnalysisResult:
        metrics: dict = {}

        # Downmix to mono for loudness measurement if needed
        if audio.channels >= 2:
            samples_for_lufs = audio.samples
        else:
            samples_for_lufs = audio.samples[:, 0]

        # LUFS and LRA via pyloudnorm
        meter = pyln.Meter(audio.sample_rate)
        integrated = meter.integrated_loudness(samples_for_lufs)
        metrics["integrated_lufs"] = round(integrated, 1)

        # pyloudnorm doesn't expose LRA as a standalone method on all versions,
        # so we compute it if available
        try:
            lra = meter.loudness_range(samples_for_lufs)
            metrics["loudness_range_lu"] = round(lra, 1)
        except (AttributeError, Exception):
            metrics["loudness_range_lu"] = None

        # Sample peak
        peak_linear = np.max(np.abs(audio.samples))
        sample_peak_db = 20 * np.log10(peak_linear + 1e-10)
        metrics["sample_peak_dbfs"] = round(sample_peak_db, 1)

        # True peak via ffmpeg (falls back to sample peak)
        true_peak = self._measure_true_peak(audio)
        metrics["true_peak_dbtp"] = true_peak if true_peak is not None else metrics["sample_peak_dbfs"]
        metrics["true_peak_available"] = true_peak is not None

        # RMS
        rms_linear = np.sqrt(np.mean(audio.samples ** 2))
        rms_db = 20 * np.log10(rms_linear + 1e-10)
        metrics["rms_db"] = round(rms_db, 1)

        # Crest factor: peak / RMS in dB
        crest_db = sample_peak_db - rms_db
        metrics["crest_factor_db"] = round(crest_db, 1)

        return AnalysisResult(module=self.name, metrics=metrics)

    def compare(self, audio: AudioData, reference: AudioData) -> AnalysisResult:
        result = self.analyze(audio)
        ref_result = self.analyze(reference)

        lufs_diff = result.metrics["integrated_lufs"] - ref_result.metrics["integrated_lufs"]
        result.metrics["lufs_difference"] = round(lufs_diff, 1)
        result.metrics["reference_lufs"] = ref_result.metrics["integrated_lufs"]

        if ref_result.metrics["loudness_range_lu"] is not None and result.metrics["loudness_range_lu"] is not None:
            lra_diff = result.metrics["loudness_range_lu"] - ref_result.metrics["loudness_range_lu"]
            result.metrics["lra_difference"] = round(lra_diff, 1)

        peak_diff = result.metrics["sample_peak_dbfs"] - ref_result.metrics["sample_peak_dbfs"]
        result.metrics["peak_difference"] = round(peak_diff, 1)

        return result

    def _measure_true_peak(self, audio: AudioData) -> float | None:
        """Measure true peak via ffmpeg loudnorm filter. Returns None if ffmpeg unavailable."""
        if shutil.which("ffmpeg") is None:
            return None

        try:
            cmd = [
                "ffmpeg", "-i", str(audio.filepath),
                "-af", "loudnorm=print_format=json",
                "-f", "null", "-",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            # loudnorm JSON is in stderr
            stderr = proc.stderr
            # Find the JSON block
            json_start = stderr.rfind("{")
            json_end = stderr.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(stderr[json_start:json_end])
                tp = float(data.get("input_tp", 0))
                return round(tp, 1)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError, OSError):
            pass
        return None
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_loudness.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/bounce_house/analyzers/loudness.py tests/test_loudness.py
git commit -m "feat: add loudness and dynamics analyzer

Measures integrated LUFS, LRA, sample peak, true peak (via ffmpeg),
RMS, and crest factor. Comparison mode computes differences from
reference. Falls back to sample peak when ffmpeg is unavailable."
```

---

### Task 5: Spectral Balance Analyzer

**Files:**
- Create: `src/bounce_house/analyzers/spectrum.py`
- Create: `tests/test_spectrum.py`

**Step 1: Write failing tests**

Create `tests/test_spectrum.py`:

```python
"""Tests for spectral balance analyzer."""

import numpy as np
import soundfile as sf
from pathlib import Path

from bounce_house.audio import load_audio
from bounce_house.analyzers.spectrum import SpectrumAnalyzer


class TestSpectrumAnalyzer:
    def setup_method(self):
        self.analyzer = SpectrumAnalyzer()

    def test_name(self):
        assert self.analyzer.name == "spectrum"

    def test_analyze_returns_result(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert result.module == "spectrum"

    def test_has_spectral_descriptors(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        for key in ["centroid_hz", "bandwidth_hz", "rolloff_hz", "flatness"]:
            assert key in result.metrics, f"Missing metric: {key}"

    def test_has_band_energies(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert "bands" in result.metrics
        bands = result.metrics["bands"]
        expected_bands = ["sub_bass", "bass", "low_mid", "mid", "upper_mid", "presence", "brilliance"]
        for band in expected_bands:
            assert band in bands, f"Missing band: {band}"

    def test_centroid_is_positive(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert result.metrics["centroid_hz"] > 0

    def test_sine_wave_centroid_near_frequency(self, tmp_wav):
        """A 440Hz sine wave should have centroid near 440Hz."""
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        # Allow some tolerance since it's a windowed STFT
        assert 400 < result.metrics["centroid_hz"] < 500

    def test_compare_has_band_differences(self, tmp_wav, tmp_reference_wav):
        audio = load_audio(tmp_wav)
        ref = load_audio(tmp_reference_wav)
        result = self.analyzer.compare(audio, ref)
        assert "band_differences" in result.metrics
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_spectrum.py -v`
Expected: FAIL

**Step 3: Implement spectrum.py**

Create `src/bounce_house/analyzers/spectrum.py`:

```python
"""Spectral balance analyzer."""

from __future__ import annotations

import numpy as np
import librosa

from bounce_house.audio import AudioData
from bounce_house.analyzers.base import AnalyzerBase, AnalysisResult


# Mixing-relevant frequency bands
BANDS = [
    ("sub_bass", 20, 60),
    ("bass", 60, 250),
    ("low_mid", 250, 500),
    ("mid", 500, 2000),
    ("upper_mid", 2000, 4000),
    ("presence", 4000, 6000),
    ("brilliance", 6000, 20000),
]


class SpectrumAnalyzer(AnalyzerBase):
    @property
    def name(self) -> str:
        return "spectrum"

    def analyze(self, audio: AudioData) -> AnalysisResult:
        metrics: dict = {}

        # Downmix to mono for spectral analysis
        if audio.is_stereo:
            y = np.mean(audio.samples, axis=1)
        else:
            y = audio.samples[:, 0]

        sr = audio.sample_rate

        # Spectral shape descriptors (frame-wise, then averaged)
        centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
        bandwidth = float(np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr)))
        rolloff = float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)))
        flatness = float(np.mean(librosa.feature.spectral_flatness(y=y)))

        metrics["centroid_hz"] = round(centroid, 1)
        metrics["bandwidth_hz"] = round(bandwidth, 1)
        metrics["rolloff_hz"] = round(rolloff, 1)
        metrics["flatness"] = round(flatness, 6)

        # Band energies
        n_fft = 4096
        S = np.abs(librosa.stft(y, n_fft=n_fft)) ** 2
        freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

        band_energies = {}
        for band_name, lo, hi in BANDS:
            mask = (freqs >= lo) & (freqs < hi)
            if np.any(mask):
                energy_db = float(10 * np.log10(np.mean(S[mask, :]) + 1e-10))
            else:
                energy_db = -100.0
            band_energies[band_name] = round(energy_db, 1)

        metrics["bands"] = band_energies

        return AnalysisResult(module=self.name, metrics=metrics)

    def compare(self, audio: AudioData, reference: AudioData) -> AnalysisResult:
        result = self.analyze(audio)
        ref_result = self.analyze(reference)

        band_diffs = {}
        for band_name, _, _ in BANDS:
            mix_energy = result.metrics["bands"][band_name]
            ref_energy = ref_result.metrics["bands"][band_name]
            band_diffs[band_name] = round(mix_energy - ref_energy, 1)

        result.metrics["band_differences"] = band_diffs
        result.metrics["reference_bands"] = ref_result.metrics["bands"]

        centroid_diff = result.metrics["centroid_hz"] - ref_result.metrics["centroid_hz"]
        result.metrics["centroid_difference_hz"] = round(centroid_diff, 1)

        return result
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_spectrum.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/bounce_house/analyzers/spectrum.py tests/test_spectrum.py
git commit -m "feat: add spectral balance analyzer

Computes centroid, bandwidth, rolloff, flatness, and energy in 7
mixing-relevant frequency bands. Comparison mode shows per-band
dB difference from reference."
```

---

### Task 6: Stereo & Phase Analyzer

**Files:**
- Create: `src/bounce_house/analyzers/stereo.py`
- Create: `tests/test_stereo.py`

**Step 1: Write failing tests**

Create `tests/test_stereo.py`:

```python
"""Tests for stereo imaging and phase analyzer."""

import numpy as np
import soundfile as sf
from pathlib import Path

from bounce_house.audio import load_audio, AudioData
from bounce_house.analyzers.stereo import StereoAnalyzer


class TestStereoAnalyzer:
    def setup_method(self):
        self.analyzer = StereoAnalyzer()

    def test_name(self):
        assert self.analyzer.name == "stereo"

    def test_analyze_returns_result(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert result.module == "stereo"

    def test_has_expected_metrics(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        expected = {
            "phase_correlation", "min_block_correlation",
            "mid_rms_db", "side_rms_db", "ms_ratio_db",
            "stereo_width", "balance_db",
        }
        assert expected.issubset(set(result.metrics.keys()))

    def test_has_frequency_stereo_width(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert "frequency_width" in result.metrics

    def test_mono_identical_channels_correlation_is_1(self, tmp_path):
        """Identical L and R should give correlation of +1."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False)
        signal = 0.5 * np.sin(2 * np.pi * 440 * t)
        stereo = np.column_stack([signal, signal])
        path = tmp_path / "identical.wav"
        sf.write(str(path), stereo, sr, subtype="PCM_16")
        audio = load_audio(path)
        result = self.analyzer.analyze(audio)
        assert result.metrics["phase_correlation"] > 0.99

    def test_inverted_phase_correlation_is_negative(self, tmp_path):
        """L and -R should give correlation of -1."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False)
        signal = 0.5 * np.sin(2 * np.pi * 440 * t)
        stereo = np.column_stack([signal, -signal])
        path = tmp_path / "inverted.wav"
        sf.write(str(path), stereo, sr, subtype="PCM_16")
        audio = load_audio(path)
        result = self.analyzer.analyze(audio)
        assert result.metrics["phase_correlation"] < -0.99

    def test_stereo_width_zero_for_mono(self, tmp_path):
        """Identical channels should have width near 0."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False)
        signal = 0.5 * np.sin(2 * np.pi * 440 * t)
        stereo = np.column_stack([signal, signal])
        path = tmp_path / "mono_stereo.wav"
        sf.write(str(path), stereo, sr, subtype="PCM_16")
        audio = load_audio(path)
        result = self.analyzer.analyze(audio)
        assert result.metrics["stereo_width"] < 0.01

    def test_mono_file_skips_analysis(self, tmp_mono_wav):
        audio = load_audio(tmp_mono_wav)
        result = self.analyzer.analyze(audio)
        assert result.metrics.get("mono_file") is True

    def test_compare_returns_result(self, tmp_wav, tmp_reference_wav):
        audio = load_audio(tmp_wav)
        ref = load_audio(tmp_reference_wav)
        result = self.analyzer.compare(audio, ref)
        assert "width_difference" in result.metrics
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_stereo.py -v`
Expected: FAIL

**Step 3: Implement stereo.py**

Create `src/bounce_house/analyzers/stereo.py`:

```python
"""Stereo imaging and phase analyzer."""

from __future__ import annotations

import numpy as np
from scipy.signal import stft

from bounce_house.audio import AudioData
from bounce_house.analyzers.base import AnalyzerBase, AnalysisResult


FREQ_BANDS = [
    ("sub_bass", 20, 120),
    ("low_mid", 120, 500),
    ("mid", 500, 2000),
    ("upper_mid", 2000, 8000),
    ("air", 8000, 20000),
]


class StereoAnalyzer(AnalyzerBase):
    @property
    def name(self) -> str:
        return "stereo"

    def analyze(self, audio: AudioData) -> AnalysisResult:
        metrics: dict = {}

        if not audio.is_stereo:
            metrics["mono_file"] = True
            return AnalysisResult(module=self.name, metrics=metrics)

        L = audio.samples[:, 0]
        R = audio.samples[:, 1]

        # Phase correlation (Pearson)
        correlation = float(np.corrcoef(L, R)[0, 1])
        metrics["phase_correlation"] = round(correlation, 4)

        # M/S decomposition
        mid = (L + R) / 2.0
        side = (L - R) / 2.0
        mid_rms = float(np.sqrt(np.mean(mid ** 2)))
        side_rms = float(np.sqrt(np.mean(side ** 2)))

        metrics["mid_rms_db"] = round(20 * np.log10(mid_rms + 1e-10), 1)
        metrics["side_rms_db"] = round(20 * np.log10(side_rms + 1e-10), 1)
        metrics["ms_ratio_db"] = round(metrics["mid_rms_db"] - metrics["side_rms_db"], 1)

        # Stereo width: 0 = mono, 0.5 = equal mid/side
        total = mid_rms + side_rms
        metrics["stereo_width"] = round(side_rms / total if total > 0 else 0.0, 4)

        # Channel balance
        l_rms_db = 20 * np.log10(float(np.sqrt(np.mean(L ** 2))) + 1e-10)
        r_rms_db = 20 * np.log10(float(np.sqrt(np.mean(R ** 2))) + 1e-10)
        metrics["balance_db"] = round(l_rms_db - r_rms_db, 1)

        # Windowed phase correlation (50ms blocks)
        block_size = int(audio.sample_rate * 0.05)
        num_blocks = len(L) // block_size
        block_corrs = []
        for i in range(num_blocks):
            start = i * block_size
            end = start + block_size
            bl = L[start:end]
            br = R[start:end]
            if np.std(bl) > 1e-10 and np.std(br) > 1e-10:
                block_corrs.append(float(np.corrcoef(bl, br)[0, 1]))

        metrics["min_block_correlation"] = round(min(block_corrs), 4) if block_corrs else 0.0

        # Frequency-dependent stereo width
        freq_width = self._frequency_stereo_width(L, R, audio.sample_rate)
        metrics["frequency_width"] = freq_width

        return AnalysisResult(module=self.name, metrics=metrics)

    def compare(self, audio: AudioData, reference: AudioData) -> AnalysisResult:
        result = self.analyze(audio)
        ref_result = self.analyze(reference)

        if result.metrics.get("mono_file") or ref_result.metrics.get("mono_file"):
            return result

        result.metrics["width_difference"] = round(
            result.metrics["stereo_width"] - ref_result.metrics["stereo_width"], 4
        )
        result.metrics["correlation_difference"] = round(
            result.metrics["phase_correlation"] - ref_result.metrics["phase_correlation"], 4
        )
        result.metrics["reference_width"] = ref_result.metrics["stereo_width"]
        result.metrics["reference_correlation"] = ref_result.metrics["phase_correlation"]

        return result

    def _frequency_stereo_width(
        self, L: np.ndarray, R: np.ndarray, sr: int, nperseg: int = 4096
    ) -> dict[str, float]:
        """Compute per-band correlation between L and R channels."""
        f, _, Zl = stft(L, sr, nperseg=nperseg)
        _, _, Zr = stft(R, sr, nperseg=nperseg)

        result = {}
        for band_name, lo, hi in FREQ_BANDS:
            mask = (f >= lo) & (f < hi)
            if not np.any(mask):
                result[band_name] = 0.0
                continue
            l_energy = np.abs(Zl[mask, :]).flatten()
            r_energy = np.abs(Zr[mask, :]).flatten()
            if np.std(l_energy) > 1e-10 and np.std(r_energy) > 1e-10:
                corr = float(np.corrcoef(l_energy, r_energy)[0, 1])
            else:
                corr = 1.0  # identical/silent = correlated
            result[band_name] = round(corr, 4)

        return result
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_stereo.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/bounce_house/analyzers/stereo.py tests/test_stereo.py
git commit -m "feat: add stereo imaging and phase analyzer

Computes phase correlation, M/S decomposition, stereo width, channel
balance, windowed correlation (50ms blocks), and frequency-dependent
stereo width in 5 bands. Handles mono files gracefully."
```

---

### Task 7: Perceptual Analyzer (Optional timbral_models)

**Files:**
- Create: `src/bounce_house/analyzers/perceptual.py`
- Create: `tests/test_perceptual.py`

**Step 1: Write failing tests**

Create `tests/test_perceptual.py`:

```python
"""Tests for perceptual analyzer."""

from bounce_house.audio import load_audio
from bounce_house.analyzers.perceptual import PerceptualAnalyzer


class TestPerceptualAnalyzer:
    def setup_method(self):
        self.analyzer = PerceptualAnalyzer()

    def test_name(self):
        assert self.analyzer.name == "perceptual"

    def test_analyze_returns_result(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert result.module == "perceptual"

    def test_has_brightness_estimate(self, tmp_wav):
        """Even without timbral_models, brightness proxy should be present."""
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert "brightness" in result.metrics

    def test_has_warmth_estimate(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert "warmth" in result.metrics

    def test_timbral_available_flag(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert "timbral_models_available" in result.metrics
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_perceptual.py -v`
Expected: FAIL

**Step 3: Implement perceptual.py**

Create `src/bounce_house/analyzers/perceptual.py`:

```python
"""Perceptual quality analyzer.

Uses timbral_models if installed, otherwise falls back to spectral proxy metrics.
"""

from __future__ import annotations

import numpy as np
import librosa

from bounce_house.audio import AudioData
from bounce_house.analyzers.base import AnalyzerBase, AnalysisResult

try:
    import timbral_models
    _HAS_TIMBRAL = True
except ImportError:
    _HAS_TIMBRAL = False


class PerceptualAnalyzer(AnalyzerBase):
    @property
    def name(self) -> str:
        return "perceptual"

    def analyze(self, audio: AudioData) -> AnalysisResult:
        metrics: dict = {"timbral_models_available": _HAS_TIMBRAL}

        if _HAS_TIMBRAL:
            metrics.update(self._analyze_timbral(audio))
        else:
            metrics.update(self._analyze_proxy(audio))

        return AnalysisResult(module=self.name, metrics=metrics)

    def compare(self, audio: AudioData, reference: AudioData) -> AnalysisResult:
        result = self.analyze(audio)
        ref_result = self.analyze(reference)

        for key in ["brightness", "warmth"]:
            if key in result.metrics and key in ref_result.metrics:
                diff_key = f"{key}_difference"
                result.metrics[diff_key] = round(
                    result.metrics[key] - ref_result.metrics[key], 4
                )
                result.metrics[f"reference_{key}"] = ref_result.metrics[key]

        return result

    def _analyze_timbral(self, audio: AudioData) -> dict:
        """Full timbral analysis using timbral_models."""
        filepath = str(audio.filepath)
        results = {}
        try:
            results["brightness"] = round(timbral_models.timbral_brightness(filepath), 4)
        except Exception:
            results["brightness"] = None
        try:
            results["warmth"] = round(timbral_models.timbral_warmth(filepath), 4)
        except Exception:
            results["warmth"] = None
        try:
            results["hardness"] = round(timbral_models.timbral_hardness(filepath), 4)
        except Exception:
            results["hardness"] = None
        try:
            results["roughness"] = round(timbral_models.timbral_roughness(filepath), 4)
        except Exception:
            results["roughness"] = None
        return results

    def _analyze_proxy(self, audio: AudioData) -> dict:
        """Proxy brightness/warmth estimates from spectral features."""
        if audio.is_stereo:
            y = np.mean(audio.samples, axis=1)
        else:
            y = audio.samples[:, 0]

        sr = audio.sample_rate

        # Brightness proxy: ratio of energy above 4kHz to total energy
        S = np.abs(librosa.stft(y, n_fft=4096)) ** 2
        freqs = librosa.fft_frequencies(sr=sr, n_fft=4096)

        total_energy = np.sum(S)
        high_mask = freqs >= 4000
        high_energy = np.sum(S[high_mask, :])
        brightness = float(high_energy / (total_energy + 1e-10))

        # Warmth proxy: ratio of energy in 200-500 Hz to total
        warm_mask = (freqs >= 200) & (freqs < 500)
        warm_energy = np.sum(S[warm_mask, :])
        warmth = float(warm_energy / (total_energy + 1e-10))

        return {
            "brightness": round(brightness, 4),
            "warmth": round(warmth, 4),
            "proxy_metrics": True,
        }
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_perceptual.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/bounce_house/analyzers/perceptual.py tests/test_perceptual.py
git commit -m "feat: add perceptual quality analyzer

Uses timbral_models for brightness, warmth, hardness, roughness when
available. Falls back to spectral proxy metrics (energy ratios) when
timbral_models is not installed."
```

---

### Task 8: Rule-Based Advice Engine

**Files:**
- Create: `src/bounce_house/rules.py`
- Create: `tests/test_rules.py`

**Step 1: Write failing tests**

Create `tests/test_rules.py`:

```python
"""Tests for rule-based advice engine."""

from bounce_house.analyzers.base import AnalysisResult
from bounce_house.rules import evaluate_rules


class TestRuleEngine:
    def test_loudness_pass(self):
        result = AnalysisResult(
            module="loudness",
            metrics={"integrated_lufs": -12.0, "true_peak_dbtp": -1.5,
                     "loudness_range_lu": 8.0, "crest_factor_db": 14.0},
        )
        assessments = evaluate_rules(result)
        statuses = [a.status for a in assessments]
        assert all(s == "pass" for s in statuses)

    def test_loudness_too_hot(self):
        result = AnalysisResult(
            module="loudness",
            metrics={"integrated_lufs": -5.0, "true_peak_dbtp": 0.2,
                     "loudness_range_lu": 2.0, "crest_factor_db": 4.0},
        )
        assessments = evaluate_rules(result)
        fails = [a for a in assessments if a.status == "fail"]
        assert len(fails) >= 2  # LUFS and true peak should fail

    def test_stereo_phase_warning(self):
        result = AnalysisResult(
            module="stereo",
            metrics={"phase_correlation": 0.1, "min_block_correlation": -0.1,
                     "balance_db": 0.2},
        )
        assessments = evaluate_rules(result)
        warns = [a for a in assessments if a.status == "warn"]
        assert len(warns) >= 1

    def test_stereo_out_of_phase_fail(self):
        result = AnalysisResult(
            module="stereo",
            metrics={"phase_correlation": -0.5, "min_block_correlation": -0.8,
                     "balance_db": 0.1},
        )
        assessments = evaluate_rules(result)
        fails = [a for a in assessments if a.status == "fail"]
        assert len(fails) >= 1

    def test_reference_band_deviation(self):
        result = AnalysisResult(
            module="spectrum",
            metrics={"bands": {}, "band_differences": {"low_mid": 5.0, "bass": 1.0}},
        )
        assessments = evaluate_rules(result)
        warns_or_fails = [a for a in assessments if a.status in ("warn", "fail")]
        assert any("low_mid" in a.metric for a in warns_or_fails)

    def test_assessments_have_messages(self):
        result = AnalysisResult(
            module="loudness",
            metrics={"integrated_lufs": -5.0, "true_peak_dbtp": 0.2,
                     "loudness_range_lu": 2.0, "crest_factor_db": 4.0},
        )
        assessments = evaluate_rules(result)
        for a in assessments:
            assert isinstance(a.message, str)
            assert len(a.message) > 0

    def test_unknown_module_returns_empty(self):
        result = AnalysisResult(module="unknown", metrics={})
        assessments = evaluate_rules(result)
        assert assessments == []

    def test_missing_metrics_skipped_gracefully(self):
        result = AnalysisResult(module="loudness", metrics={"integrated_lufs": -12.0})
        assessments = evaluate_rules(result)
        # Should only assess metrics that are present, not crash
        assert isinstance(assessments, list)
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_rules.py -v`
Expected: FAIL

**Step 3: Implement rules.py**

Create `src/bounce_house/rules.py`:

```python
"""Rule-based advice engine.

Rules are defined as data. Each rule checks a metric from an AnalysisResult
and produces an Assessment with a pass/warn/fail status and actionable message.
"""

from __future__ import annotations

from bounce_house.analyzers.base import AnalysisResult, Assessment


def evaluate_rules(result: AnalysisResult) -> list[Assessment]:
    """Evaluate all applicable rules for a given analysis result."""
    rules = _RULES.get(result.module, [])
    assessments = []

    for rule in rules:
        metric = rule["metric"]
        value = _get_metric(result.metrics, metric)
        if value is None:
            continue

        status = rule["evaluate"](value)
        message = rule["messages"][status].format(value=value)
        assessments.append(
            Assessment(
                metric=metric,
                value=value,
                status=status,
                message=message,
                reference=rule.get("reference"),
            )
        )

    # Reference comparison rules (band deviations)
    if result.module == "spectrum" and "band_differences" in result.metrics:
        for band, diff in result.metrics["band_differences"].items():
            if abs(diff) > 3.0:
                status = "warn" if abs(diff) <= 6.0 else "fail"
                direction = "above" if diff > 0 else "below"
                assessments.append(
                    Assessment(
                        metric=f"band_diff_{band}",
                        value=diff,
                        status=status,
                        message=f"{band.replace('_', '-')} band is {diff:+.1f} dB {direction} reference",
                        reference=0.0,
                    )
                )

    return assessments


def _get_metric(metrics: dict, key: str) -> float | None:
    """Safely extract a metric, returning None if missing."""
    value = metrics.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _lufs_status(value: float) -> str:
    if -16 <= value <= -8:
        return "pass"
    if -20 <= value < -16 or -8 < value <= -6:
        return "warn"
    return "fail"


def _true_peak_status(value: float) -> str:
    if value < -1.0:
        return "pass"
    if value <= -0.5:
        return "warn"
    return "fail"


def _lra_status(value: float) -> str:
    if 5 <= value <= 15:
        return "pass"
    if 3 <= value < 5 or 15 < value <= 20:
        return "warn"
    return "fail"


def _crest_status(value: float) -> str:
    if value > 10:
        return "pass"
    if value >= 6:
        return "warn"
    return "fail"


def _correlation_status(value: float) -> str:
    if value > 0.3:
        return "pass"
    if value >= 0.0:
        return "warn"
    return "fail"


def _min_block_corr_status(value: float) -> str:
    if value > 0.0:
        return "pass"
    if value >= -0.3:
        return "warn"
    return "fail"


def _balance_status(value: float) -> str:
    v = abs(value)
    if v <= 0.5:
        return "pass"
    if v <= 1.5:
        return "warn"
    return "fail"


_RULES: dict[str, list[dict]] = {
    "loudness": [
        {
            "metric": "integrated_lufs",
            "evaluate": _lufs_status,
            "messages": {
                "pass": "Integrated loudness is {value:.1f} LUFS — within target range",
                "warn": "Integrated loudness is {value:.1f} LUFS — outside typical -16 to -8 range",
                "fail": "Integrated loudness is {value:.1f} LUFS — significantly outside target range, check your gain staging",
            },
        },
        {
            "metric": "true_peak_dbtp",
            "evaluate": _true_peak_status,
            "messages": {
                "pass": "True peak is {value:.1f} dBTP — safe headroom",
                "warn": "True peak is {value:.1f} dBTP — close to clipping, consider lowering limiter ceiling to -1.0 dBTP",
                "fail": "True peak is {value:.1f} dBTP — risk of inter-sample peaks on codec conversion, add a limiter ceiling at -1.0 dBTP",
            },
        },
        {
            "metric": "loudness_range_lu",
            "evaluate": _lra_status,
            "messages": {
                "pass": "Loudness range is {value:.1f} LU — healthy dynamics",
                "warn": "Loudness range is {value:.1f} LU — dynamics may be too compressed or too wide",
                "fail": "Loudness range is {value:.1f} LU — extreme dynamics, review compressor/limiter settings",
            },
        },
        {
            "metric": "crest_factor_db",
            "evaluate": _crest_status,
            "messages": {
                "pass": "Crest factor is {value:.1f} dB — good transient headroom",
                "warn": "Crest factor is {value:.1f} dB — transients may be over-compressed",
                "fail": "Crest factor is {value:.1f} dB — heavily squashed, reduce limiting or compression",
            },
        },
    ],
    "stereo": [
        {
            "metric": "phase_correlation",
            "evaluate": _correlation_status,
            "messages": {
                "pass": "Phase correlation is {value:+.3f} — good mono compatibility",
                "warn": "Phase correlation is {value:+.3f} — may lose energy in mono playback",
                "fail": "Phase correlation is {value:+.3f} — significant phase cancellation, check stereo effects",
            },
        },
        {
            "metric": "min_block_correlation",
            "evaluate": _min_block_corr_status,
            "messages": {
                "pass": "Minimum block correlation is {value:+.3f} — no phase issues detected",
                "warn": "Minimum block correlation is {value:+.3f} — some sections have near-zero or negative correlation",
                "fail": "Minimum block correlation is {value:+.3f} — severe phase cancellation in some sections",
            },
        },
        {
            "metric": "balance_db",
            "evaluate": _balance_status,
            "messages": {
                "pass": "Channel balance is {value:+.1f} dB — centered",
                "warn": "Channel balance is {value:+.1f} dB — slight imbalance, check panning",
                "fail": "Channel balance is {value:+.1f} dB — significant imbalance, review pan positions",
            },
        },
    ],
}
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_rules.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/bounce_house/rules.py tests/test_rules.py
git commit -m "feat: add rule-based advice engine

Data-driven rules for loudness (LUFS, true peak, LRA, crest factor),
stereo (phase correlation, block correlation, balance), and reference
comparison (per-band deviation). Produces actionable Assessment objects."
```

---

### Task 9: Report Formatter (Terminal + JSON)

**Files:**
- Create: `src/bounce_house/report.py`
- Create: `tests/test_report.py`

**Step 1: Write failing tests**

Create `tests/test_report.py`:

```python
"""Tests for report formatting."""

import json

from bounce_house.audio import AudioData
from bounce_house.analyzers.base import AnalysisResult, Assessment
from bounce_house.report import format_terminal, format_json


def _make_results():
    return [
        AnalysisResult(
            module="loudness",
            metrics={"integrated_lufs": -12.0, "true_peak_dbtp": -1.5},
            assessments=[
                Assessment("integrated_lufs", -12.0, "pass",
                           "Integrated loudness is -12.0 LUFS — within target range"),
            ],
        ),
        AnalysisResult(
            module="stereo",
            metrics={"phase_correlation": 0.62, "stereo_width": 0.31},
        ),
    ]


class TestTerminalFormat:
    def test_returns_string(self):
        output = format_terminal(_make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4})
        assert isinstance(output, str)

    def test_contains_file_name(self):
        output = format_terminal(_make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4})
        assert "mix.wav" in output

    def test_contains_module_sections(self):
        output = format_terminal(_make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4})
        assert "Loudness" in output
        assert "Stereo" in output

    def test_contains_pass_indicator(self):
        output = format_terminal(_make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4})
        assert "PASS" in output

    def test_contains_summary(self):
        output = format_terminal(_make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4})
        assert "warning" in output.lower() or "failure" in output.lower() or "0" in output


class TestJsonFormat:
    def test_returns_valid_json(self):
        output = format_json(_make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4})
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_has_file_key(self):
        output = format_json(_make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4})
        data = json.loads(output)
        assert data["file"] == "mix.wav"

    def test_has_module_keys(self):
        output = format_json(_make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4})
        data = json.loads(output)
        assert "loudness" in data
        assert "stereo" in data

    def test_has_summary(self):
        output = format_json(_make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4})
        data = json.loads(output)
        assert "summary" in data
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_report.py -v`
Expected: FAIL

**Step 3: Implement report.py**

Create `src/bounce_house/report.py`:

```python
"""Report formatting — terminal (ANSI) and JSON output."""

from __future__ import annotations

import json
from typing import Any

from bounce_house.analyzers.base import AnalysisResult, Assessment


# ANSI color codes
_RESET = "\033[0m"
_BOLD = "\033[1m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_DIM = "\033[2m"

_STATUS_COLORS = {"pass": _GREEN, "warn": _YELLOW, "fail": _RED}
_STATUS_LABELS = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}

_MODULE_TITLES = {
    "loudness": "Loudness & Dynamics",
    "spectrum": "Spectral Balance",
    "stereo": "Stereo & Phase",
    "perceptual": "Perceptual Quality",
}

# Display-friendly metric names
_METRIC_NAMES = {
    "integrated_lufs": "Integrated LUFS",
    "true_peak_dbtp": "True Peak",
    "true_peak_available": None,  # skip display
    "loudness_range_lu": "Loudness Range",
    "sample_peak_dbfs": "Sample Peak",
    "rms_db": "RMS Level",
    "crest_factor_db": "Crest Factor",
    "centroid_hz": "Centroid",
    "bandwidth_hz": "Bandwidth",
    "rolloff_hz": "Rolloff (85%)",
    "flatness": "Flatness",
    "phase_correlation": "Phase Correlation",
    "min_block_correlation": "Min Block Corr",
    "mid_rms_db": "Mid RMS",
    "side_rms_db": "Side RMS",
    "ms_ratio_db": "M/S Ratio",
    "stereo_width": "Stereo Width",
    "balance_db": "Balance",
    "brightness": "Brightness",
    "warmth": "Warmth",
    "hardness": "Hardness",
    "roughness": "Roughness",
    "timbral_models_available": None,
    "proxy_metrics": None,
    "mono_file": None,
}


def format_terminal(
    results: list[AnalysisResult],
    filename: str,
    file_info: dict[str, Any],
) -> str:
    """Format analysis results as rich terminal output."""
    lines: list[str] = []

    # Header
    duration_str = _format_duration(file_info.get("duration", 0))
    sr = file_info.get("sample_rate", 0)
    ch = file_info.get("channels", 0)
    ch_str = "stereo" if ch == 2 else f"{ch}ch" if ch > 2 else "mono"

    lines.append("")
    lines.append(f"{_BOLD}{'═' * 60}{_RESET}")
    lines.append(f"{_BOLD}  BOUNCE HOUSE — Mix Analysis Report{_RESET}")
    lines.append(f"{_DIM}  {filename} ({sr} Hz, {ch_str}, {duration_str}){_RESET}")
    lines.append(f"{_BOLD}{'═' * 60}{_RESET}")

    # Collect all assessments for summary
    all_assessments: list[Assessment] = []

    for result in results:
        title = _MODULE_TITLES.get(result.module, result.module.title())
        lines.append("")
        lines.append(f"{_BOLD}── {title} {'─' * (55 - len(title))}{_RESET}")

        # Metrics
        assessment_map = {a.metric: a for a in result.assessments}
        all_assessments.extend(result.assessments)

        # Handle special cases
        if result.metrics.get("mono_file"):
            lines.append(f"  {_DIM}Mono file — stereo analysis skipped{_RESET}")
            continue

        # Band energies (special formatting)
        bands = result.metrics.get("bands")
        band_diffs = result.metrics.get("band_differences")
        freq_width = result.metrics.get("frequency_width")

        for key, value in result.metrics.items():
            display_name = _METRIC_NAMES.get(key)
            if display_name is None:
                continue
            if key in ("bands", "band_differences", "reference_bands", "frequency_width"):
                continue
            # Skip reference/diff keys in main display
            if key.startswith("reference_") or key.endswith("_difference"):
                continue

            assessment = assessment_map.get(key)
            status_str = ""
            if assessment:
                color = _STATUS_COLORS[assessment.status]
                label = _STATUS_LABELS[assessment.status]
                status_str = f"  {color}{label}{_RESET}"

            value_str = _format_value(key, value)
            lines.append(f"  {display_name:<22} {value_str}{status_str}")

        # Band energies
        if bands:
            lines.append("")
            for band_name, energy in bands.items():
                label = band_name.replace("_", "-")
                diff_str = ""
                if band_diffs and band_name in band_diffs:
                    diff = band_diffs[band_name]
                    if abs(diff) > 3.0:
                        color = _YELLOW if abs(diff) <= 6.0 else _RED
                        diff_str = f"  {color}{diff:+.1f} dB vs ref{_RESET}"
                lines.append(f"  {label:<22} {energy:>8.1f} dB{diff_str}")

        # Frequency-dependent stereo width
        if freq_width:
            lines.append("")
            lines.append(f"  {_DIM}Frequency-dependent correlation:{_RESET}")
            for band_name, corr in freq_width.items():
                label = band_name.replace("_", "-")
                lines.append(f"    {label:<18} {corr:+.3f}")

    # Suggestions section
    warns = [a for a in all_assessments if a.status == "warn"]
    fails = [a for a in all_assessments if a.status == "fail"]

    if warns or fails:
        lines.append("")
        lines.append(f"{_BOLD}── Suggestions {'─' * 44}{_RESET}")
        for a in fails:
            lines.append(f"  {_RED}FAIL{_RESET}  {a.message}")
        for a in warns:
            lines.append(f"  {_YELLOW}WARN{_RESET}  {a.message}")

    # Summary
    lines.append("")
    lines.append(f"{_BOLD}{'═' * 60}{_RESET}")
    lines.append(f"  {len(warns)} warning(s), {len(fails)} failure(s)")
    lines.append(f"{_BOLD}{'═' * 60}{_RESET}")
    lines.append("")

    return "\n".join(lines)


def format_json(
    results: list[AnalysisResult],
    filename: str,
    file_info: dict[str, Any],
) -> str:
    """Format analysis results as JSON."""
    output: dict[str, Any] = {
        "file": filename,
        "format": file_info,
    }

    all_assessments: list[dict] = []

    for result in results:
        output[result.module] = result.metrics
        for a in result.assessments:
            all_assessments.append({
                "metric": a.metric,
                "value": a.value,
                "status": a.status,
                "message": a.message,
                "reference": a.reference,
            })

    warns = sum(1 for a in all_assessments if a["status"] == "warn")
    fails = sum(1 for a in all_assessments if a["status"] == "fail")

    output["assessments"] = all_assessments
    output["summary"] = {"warnings": warns, "failures": fails}

    return json.dumps(output, indent=2)


def _format_duration(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def _format_value(key: str, value: Any) -> str:
    if isinstance(value, float):
        if "hz" in key.lower():
            return f"{value:,.0f} Hz"
        if "db" in key.lower() or "lufs" in key or "lu" in key:
            return f"{value:+.1f}"
        return f"{value:.4f}"
    return str(value)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_report.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/bounce_house/report.py tests/test_report.py
git commit -m "feat: add report formatter for terminal and JSON output

Terminal output uses ANSI colors and Unicode box-drawing with module
sections, pass/warn/fail indicators, band energies, and a suggestions
summary. JSON output mirrors the same data as structured dict."
```

---

### Task 10: Wire Up CLI Dispatch

**Files:**
- Modify: `src/bounce_house/cli.py`
- Modify: `tests/test_cli.py`

**Step 1: Write integration tests**

Add to `tests/test_cli.py`:

```python
"""Tests for CLI argument parsing and full dispatch."""

import json
from bounce_house.cli import create_parser, main


class TestParser:
    def test_analyze_requires_file(self):
        parser = create_parser()
        args = parser.parse_args(["analyze", "mix.wav"])
        assert args.command == "analyze"
        assert args.file == "mix.wav"
        assert args.reference is None
        assert args.json is False

    def test_analyze_with_reference(self):
        parser = create_parser()
        args = parser.parse_args(["analyze", "mix.wav", "--reference", "ref.wav"])
        assert args.reference == "ref.wav"

    def test_analyze_with_json(self):
        parser = create_parser()
        args = parser.parse_args(["analyze", "mix.wav", "--json"])
        assert args.json is True

    def test_loudness_subcommand(self):
        parser = create_parser()
        args = parser.parse_args(["loudness", "mix.wav"])
        assert args.command == "loudness"

    def test_spectrum_subcommand(self):
        parser = create_parser()
        args = parser.parse_args(["spectrum", "mix.wav"])
        assert args.command == "spectrum"

    def test_stereo_subcommand(self):
        parser = create_parser()
        args = parser.parse_args(["stereo", "mix.wav"])
        assert args.command == "stereo"

    def test_compare_subcommand(self):
        parser = create_parser()
        args = parser.parse_args(["compare", "mix.wav", "ref.wav"])
        assert args.command == "compare"
        assert args.file == "mix.wav"
        assert args.reference == "ref.wav"

    def test_no_command_returns_1(self):
        assert main([]) == 1


class TestFullAnalysis:
    def test_analyze_runs_successfully(self, tmp_wav):
        result = main(["analyze", str(tmp_wav)])
        assert result == 0

    def test_analyze_json_output(self, tmp_wav, capsys):
        main(["analyze", str(tmp_wav), "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "loudness" in data
        assert "spectrum" in data
        assert "stereo" in data

    def test_loudness_subcommand_runs(self, tmp_wav):
        result = main(["loudness", str(tmp_wav)])
        assert result == 0

    def test_spectrum_subcommand_runs(self, tmp_wav):
        result = main(["spectrum", str(tmp_wav)])
        assert result == 0

    def test_stereo_subcommand_runs(self, tmp_wav):
        result = main(["stereo", str(tmp_wav)])
        assert result == 0

    def test_compare_runs(self, tmp_wav, tmp_reference_wav):
        result = main(["compare", str(tmp_wav), str(tmp_reference_wav)])
        assert result == 0

    def test_compare_json_output(self, tmp_wav, tmp_reference_wav, capsys):
        main(["compare", str(tmp_wav), str(tmp_reference_wav), "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "loudness" in data
        assert "band_differences" in data.get("spectrum", {})

    def test_nonexistent_file_returns_1(self):
        result = main(["analyze", "/nonexistent/file.wav"])
        assert result == 1

    def test_analyze_with_reference(self, tmp_wav, tmp_reference_wav):
        result = main(["analyze", str(tmp_wav), "--reference", str(tmp_reference_wav)])
        assert result == 0
```

**Step 2: Run tests to verify new tests fail**

Run: `uv run pytest tests/test_cli.py -v`
Expected: New `TestFullAnalysis` tests FAIL (old parser tests still pass)

**Step 3: Rewrite cli.py with full dispatch**

Replace `src/bounce_house/cli.py` entirely:

```python
"""CLI entry point for bounce-house."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bounce_house.audio import load_audio
from bounce_house.analyzers.base import AnalysisResult
from bounce_house.analyzers.loudness import LoudnessAnalyzer
from bounce_house.analyzers.spectrum import SpectrumAnalyzer
from bounce_house.analyzers.stereo import StereoAnalyzer
from bounce_house.analyzers.perceptual import PerceptualAnalyzer
from bounce_house.rules import evaluate_rules
from bounce_house.report import format_terminal, format_json


ALL_ANALYZERS = [
    LoudnessAnalyzer(),
    SpectrumAnalyzer(),
    StereoAnalyzer(),
    PerceptualAnalyzer(),
]

ANALYZER_MAP = {a.name: a for a in ALL_ANALYZERS}


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bounce-house",
        description="Analyze audio mixes for loudness, spectral balance, stereo imaging, and more.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_get_version()}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze — full report
    analyze_parser = subparsers.add_parser("analyze", help="Run full analysis on a mix")
    analyze_parser.add_argument("file", help="Path to .wav file")
    analyze_parser.add_argument("--reference", help="Path to reference .wav file")
    analyze_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Individual module subcommands
    for name, desc in [
        ("loudness", "Loudness and dynamics analysis"),
        ("spectrum", "Spectral analysis"),
        ("stereo", "Stereo imaging and phase analysis"),
    ]:
        sub = subparsers.add_parser(name, help=desc)
        sub.add_argument("file", help="Path to .wav file")
        sub.add_argument("--json", action="store_true", help="Output as JSON")

    # compare
    compare_parser = subparsers.add_parser("compare", help="Compare mix against a reference track")
    compare_parser.add_argument("file", help="Path to .wav file")
    compare_parser.add_argument("reference", help="Path to reference .wav file")
    compare_parser.add_argument("--json", action="store_true", help="Output as JSON")

    return parser


def _get_version() -> str:
    from bounce_house import __version__
    return __version__


def _run_analysis(
    file_path: str,
    reference_path: str | None = None,
    analyzers: list | None = None,
    use_json: bool = False,
) -> int:
    """Run analysis and print report. Returns exit code."""
    path = Path(file_path)
    try:
        audio = load_audio(path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    reference = None
    if reference_path:
        try:
            reference = load_audio(Path(reference_path))
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    if analyzers is None:
        analyzers = ALL_ANALYZERS

    results: list[AnalysisResult] = []
    for analyzer in analyzers:
        if reference:
            result = analyzer.compare(audio, reference)
        else:
            result = analyzer.analyze(audio)

        # Apply rules
        assessments = evaluate_rules(result)
        result.assessments = assessments
        results.append(result)

    file_info = {
        "sample_rate": audio.sample_rate,
        "channels": audio.channels,
        "duration": round(audio.duration, 1),
    }

    if use_json:
        print(format_json(results, str(path), file_info))
    else:
        print(format_terminal(results, str(path), file_info))

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    use_json = getattr(args, "json", False)

    if args.command == "analyze":
        return _run_analysis(args.file, args.reference, None, use_json)
    elif args.command == "compare":
        return _run_analysis(args.file, args.reference, None, use_json)
    elif args.command in ANALYZER_MAP:
        analyzer = ANALYZER_MAP[args.command]
        return _run_analysis(args.file, None, [analyzer], use_json)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

**Step 4: Run all tests**

Run: `uv run pytest -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/bounce_house/cli.py tests/test_cli.py
git commit -m "feat: wire up CLI dispatch with all analyzers

Full analyze command runs loudness, spectrum, stereo, and perceptual
analyzers. Individual subcommands run single modules. Compare mode
runs all analyzers against a reference track. Terminal and JSON output
supported via --json flag."
```

---

### Task 11: Manual Smoke Test and Polish

**Step 1: Create a test WAV and run the tool end-to-end**

```bash
# Generate a test file with ffmpeg
ffmpeg -f lavfi -i "sine=frequency=440:duration=5" -ac 2 -ar 44100 /tmp/test_mix.wav

# Run full analysis
uv run bounce-house analyze /tmp/test_mix.wav

# Run with JSON
uv run bounce-house analyze /tmp/test_mix.wav --json

# Run individual subcommands
uv run bounce-house loudness /tmp/test_mix.wav
uv run bounce-house spectrum /tmp/test_mix.wav
uv run bounce-house stereo /tmp/test_mix.wav

# Test the bh alias
uv run bh analyze /tmp/test_mix.wav
```

**Step 2: Verify output looks correct and fix any formatting issues**

Review terminal output for:
- Header displays correctly with file info
- Each section has proper formatting
- PASS/WARN/FAIL indicators show with correct colors
- Suggestions section appears if there are warnings/failures
- Summary line is accurate

**Step 3: Run full test suite**

Run: `uv run pytest -v --tb=short`
Expected: All PASS

**Step 4: Clean up test WAV**

```bash
rm /tmp/test_mix.wav
```

**Step 5: Commit any fixes**

```bash
git add -A
git commit -m "fix: polish report formatting after smoke test"
```

(Skip if no changes needed.)

---

### Task 12: Final Test Run and Tag v0.1.0

**Step 1: Run full test suite with coverage**

Run: `uv run pytest --cov=bounce_house --cov-report=term-missing -v`
Expected: All PASS, decent coverage

**Step 2: Verify install works**

```bash
uv run bounce-house --version
uv run bh --version
```

**Step 3: Tag the release**

```bash
git tag v0.1.0
```

---

## Summary

| Task | What it builds | Test file |
|------|---------------|-----------|
| 1 | Project scaffolding, CLI parser | test_cli.py |
| 2 | Audio loading (AudioData) | test_audio.py |
| 3 | AnalyzerBase ABC | (verified by usage) |
| 4 | Loudness analyzer | test_loudness.py |
| 5 | Spectrum analyzer | test_spectrum.py |
| 6 | Stereo analyzer | test_stereo.py |
| 7 | Perceptual analyzer | test_perceptual.py |
| 8 | Rule-based advice engine | test_rules.py |
| 9 | Report formatter | test_report.py |
| 10 | CLI dispatch wiring | test_cli.py (extended) |
| 11 | Smoke test and polish | manual |
| 12 | Final test run and v0.1.0 tag | all |
