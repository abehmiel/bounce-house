# Detuning Detection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a TuningAnalyzer that detects reference pitch deviation, pitch drift, and chroma sharpness in audio mixes.

**Architecture:** New `TuningAnalyzer(AnalyzerBase)` in `analyzers/tuning.py`, registered in `cli.py`. Tuning rules added to both profiles. New `detuned_mix` diagnostic pattern. Report renders tuning section. All backed by `librosa.estimate_tuning()` and `librosa.feature.chroma_cqt()` — no new dependencies.

**Tech Stack:** Python 3.11+, librosa (estimate_tuning, chroma_cqt, piptrack), numpy (polyfit), pytest

**Design doc:** `docs/plans/2026-03-01-detuning-detection-design.md`

---

### Task 1: Test Fixtures for Tuning Analysis

**Files:**
- Modify: `tests/conftest.py`

We need fixtures that produce audio with known tuning characteristics. The existing `tmp_wav` generates A440 sine waves. We add fixtures for detuned and drifting audio.

**Step 1: Add detuned and drifting fixtures to conftest.py**

Add after the existing `tmp_reference_wav` fixture at the end of `tests/conftest.py`:

```python
@pytest.fixture
def tmp_detuned_wav(tmp_path) -> Path:
    """Generate a 2-second stereo sine wave tuned to A=445 Hz (~20 cents sharp)."""
    sr = 44100
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    left = 0.5 * np.sin(2 * np.pi * 445 * t)
    right = 0.3 * np.sin(2 * np.pi * 445 * t + np.pi / 4)
    stereo = np.column_stack([left, right])
    path = tmp_path / "detuned.wav"
    sf.write(str(path), stereo, sr, subtype="PCM_16")
    return path


@pytest.fixture
def tmp_drifting_wav(tmp_path) -> Path:
    """Generate a 4-second stereo sine that drifts from 440 to 450 Hz."""
    sr = 44100
    duration = 4.0
    n = int(sr * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    freq = np.linspace(440, 450, n)
    phase = 2 * np.pi * np.cumsum(freq) / sr
    left = 0.5 * np.sin(phase)
    right = 0.3 * np.sin(phase + np.pi / 4)
    stereo = np.column_stack([left, right])
    path = tmp_path / "drifting.wav"
    sf.write(str(path), stereo, sr, subtype="PCM_16")
    return path
```

**Step 2: Run existing tests to confirm fixtures don't break anything**

Run: `uv run pytest tests/ -x -q`
Expected: All 232+ tests pass (fixtures are lazy — only loaded when used).

**Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add detuned and drifting audio fixtures for tuning analyzer"
```

---

### Task 2: TuningAnalyzer Core — Tests

**Files:**
- Create: `tests/test_tuning.py`

Write all tests before implementing the analyzer. Tests use the fixtures from Task 1 plus the existing `tmp_wav` (A440).

**Step 1: Write the test file**

```python
"""Tests for tuning analyzer."""

from bounce_house.analyzers.tuning import TuningAnalyzer
from bounce_house.audio import load_audio


class TestTuningAnalyzer:
    def setup_method(self):
        self.analyzer = TuningAnalyzer()

    def test_name(self):
        assert self.analyzer.name == "tuning"

    def test_analyze_returns_result(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert result.module == "tuning"

    def test_has_all_metrics(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        expected = [
            "tuning_deviation_cents",
            "estimated_a_hz",
            "closest_standard",
            "pitch_drift_std_cents",
            "pitch_drift_range_cents",
            "pitch_drift_trend_cents_per_min",
            "chroma_sharpness",
        ]
        for key in expected:
            assert key in result.metrics, f"Missing metric: {key}"

    def test_440_sine_is_near_zero_deviation(self, tmp_wav):
        """A 440Hz sine wave should have near-zero tuning deviation."""
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert abs(result.metrics["tuning_deviation_cents"]) < 10

    def test_440_estimated_a_near_440(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert 435 < result.metrics["estimated_a_hz"] < 445

    def test_440_closest_standard(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert result.metrics["closest_standard"] == "A=440"

    def test_detuned_has_large_deviation(self, tmp_detuned_wav):
        """A 445Hz sine should show significant positive deviation."""
        audio = load_audio(tmp_detuned_wav)
        result = self.analyzer.analyze(audio)
        assert result.metrics["tuning_deviation_cents"] > 10

    def test_detuned_estimated_a_above_440(self, tmp_detuned_wav):
        audio = load_audio(tmp_detuned_wav)
        result = self.analyzer.analyze(audio)
        assert result.metrics["estimated_a_hz"] > 442

    def test_drifting_has_high_range(self, tmp_drifting_wav):
        """A signal drifting from 440 to 450 Hz should show high pitch range."""
        audio = load_audio(tmp_drifting_wav)
        result = self.analyzer.analyze(audio)
        assert result.metrics["pitch_drift_range_cents"] > 5

    def test_stable_has_low_range(self, tmp_wav):
        """A stable 440Hz signal should have low pitch drift range."""
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert result.metrics["pitch_drift_range_cents"] < 20

    def test_chroma_sharpness_is_bounded(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert 0 <= result.metrics["chroma_sharpness"] <= 1.0

    def test_compare_returns_tuning_difference(self, tmp_wav, tmp_detuned_wav):
        audio = load_audio(tmp_wav)
        ref = load_audio(tmp_detuned_wav)
        result = self.analyzer.compare(audio, ref)
        assert "tuning_difference_cents" in result.metrics

    def test_compare_same_file_near_zero_diff(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.compare(audio, audio)
        assert abs(result.metrics["tuning_difference_cents"]) < 5
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_tuning.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bounce_house.analyzers.tuning'`

**Step 3: Commit**

```bash
git add tests/test_tuning.py
git commit -m "test: add failing tests for TuningAnalyzer"
```

---

### Task 3: TuningAnalyzer Core — Implementation

**Files:**
- Create: `src/bounce_house/analyzers/tuning.py`

**Step 1: Write the analyzer**

```python
"""Tuning and pitch stability analyzer."""

from __future__ import annotations

import librosa
import numpy as np

from bounce_house.analyzers.base import AnalysisResult, AnalyzerBase
from bounce_house.audio import AudioData

# Known concert pitch standards and their deviation from A440 in cents
_STANDARDS: dict[str, float] = {
    "A=432": -31.77,
    "A=435": -19.56,
    "A=438": -7.89,
    "A=440": 0.0,
    "A=441": 3.93,
    "A=442": 7.85,
    "A=443": 11.76,
    "A=444": 15.67,
}


def _find_closest_standard(deviation_cents: float) -> str:
    """Find the named concert pitch standard closest to the measured deviation."""
    return min(_STANDARDS, key=lambda s: abs(_STANDARDS[s] - deviation_cents))


class TuningAnalyzer(AnalyzerBase):
    @property
    def name(self) -> str:
        return "tuning"

    def analyze(self, audio: AudioData) -> AnalysisResult:
        metrics: dict = {}

        # Mono downmix
        if audio.is_stereo:  # noqa: SIM108
            y = np.mean(audio.samples, axis=1)
        else:
            y = audio.samples[:, 0]

        sr = audio.sample_rate

        # Global tuning estimation (fraction of a chroma bin)
        tuning = librosa.estimate_tuning(y=y, sr=sr, resolution=0.01)
        deviation_cents = round(float(tuning) * 100, 1)
        estimated_a = round(440.0 * 2 ** (deviation_cents / 1200), 1)
        closest = _find_closest_standard(deviation_cents)

        metrics["tuning_deviation_cents"] = deviation_cents
        metrics["estimated_a_hz"] = estimated_a
        metrics["closest_standard"] = closest

        # Pitch drift via windowed tuning estimation
        window_sec = 10.0
        hop_sec = 5.0
        window_samples = int(window_sec * sr)
        hop_samples = int(hop_sec * sr)

        tuning_curve: list[float] = []
        if len(y) >= window_samples:
            for start in range(0, len(y) - window_samples + 1, hop_samples):
                segment = y[start : start + window_samples]
                t = librosa.estimate_tuning(y=segment, sr=sr, resolution=0.01)
                tuning_curve.append(float(t) * 100)
        else:
            # Audio shorter than one window — use global estimate
            tuning_curve = [deviation_cents]

        tc = np.array(tuning_curve)
        drift_std = round(float(np.std(tc)), 1) if len(tc) > 1 else 0.0
        drift_range = round(float(np.ptp(tc)), 1) if len(tc) > 1 else 0.0

        # Linear trend (cents per minute)
        if len(tc) > 1:
            x = np.arange(len(tc)) * hop_sec / 60.0  # in minutes
            coeffs = np.polyfit(x, tc, 1)
            trend = round(float(coeffs[0]), 1)
        else:
            trend = 0.0

        metrics["pitch_drift_std_cents"] = drift_std
        metrics["pitch_drift_range_cents"] = drift_range
        metrics["pitch_drift_trend_cents_per_min"] = trend

        # Chroma sharpness: peak-to-mean ratio on forced-A440 chromagram
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, tuning=0)
        # Per-frame: max bin value / mean of all bins
        frame_maxes = np.max(chroma, axis=0)
        frame_means = np.mean(chroma, axis=0)
        # Avoid division by zero for silent frames
        valid = frame_means > 1e-10
        if np.any(valid):
            ratios = frame_maxes[valid] / frame_means[valid]
            # Normalize: ratio of 12 means all energy in one bin (perfect),
            # ratio of 1 means uniform (noise). Map to 0-1 scale.
            sharpness = round(float(np.mean((ratios - 1) / 11)), 3)
            sharpness = max(0.0, min(1.0, sharpness))
        else:
            sharpness = 0.0

        metrics["chroma_sharpness"] = sharpness

        return AnalysisResult(module=self.name, metrics=metrics)

    def compare(self, audio: AudioData, reference: AudioData) -> AnalysisResult:
        result = self.analyze(audio)
        ref_result = self.analyze(reference)

        diff = round(
            result.metrics["tuning_deviation_cents"]
            - ref_result.metrics["tuning_deviation_cents"],
            1,
        )
        result.metrics["tuning_difference_cents"] = diff
        result.metrics["reference_estimated_a_hz"] = ref_result.metrics["estimated_a_hz"]

        return result
```

**Step 2: Run tests to verify they pass**

Run: `uv run pytest tests/test_tuning.py -v`
Expected: All 14 tests PASS.

**Step 3: Run full test suite to check for regressions**

Run: `uv run pytest tests/ -x -q`
Expected: All tests pass.

**Step 4: Run linter and type checker**

Run: `uv run ruff check src/bounce_house/analyzers/tuning.py && uv run ruff format --check src/bounce_house/analyzers/tuning.py && uv run mypy src/bounce_house/analyzers/tuning.py`
Expected: Clean.

**Step 5: Commit**

```bash
git add src/bounce_house/analyzers/tuning.py
git commit -m "feat: implement TuningAnalyzer with pitch deviation, drift, and chroma sharpness"
```

---

### Task 4: Register TuningAnalyzer in CLI

**Files:**
- Modify: `src/bounce_house/cli.py`

The analyzer needs to be added to `ALL_ANALYZERS` and a subcommand registered.

**Step 1: Add import and registration to cli.py**

In `cli.py`, add import after the existing analyzer imports (line ~24):

```python
from bounce_house.analyzers.tuning import TuningAnalyzer
```

Add `TuningAnalyzer()` to `ALL_ANALYZERS` list (line ~48):

```python
ALL_ANALYZERS = [
    LoudnessAnalyzer(),
    SpectrumAnalyzer(),
    StereoAnalyzer(),
    PerceptualAnalyzer(),
    TuningAnalyzer(),
]
```

Add "tuning" to the subcommand loop in `create_parser()` (line ~86):

```python
    for name, desc in [
        ("loudness", "Loudness and dynamics analysis"),
        ("spectrum", "Spectral analysis"),
        ("stereo", "Stereo imaging and phase analysis"),
        ("perceptual", "Perceptual quality analysis"),
        ("tuning", "Tuning and pitch stability analysis"),
    ]:
```

**Step 2: Run full test suite**

Run: `uv run pytest tests/ -x -q`
Expected: All tests pass.

**Step 3: Run lint**

Run: `uv run ruff check src/bounce_house/cli.py`
Expected: Clean.

**Step 4: Commit**

```bash
git add src/bounce_house/cli.py
git commit -m "feat: register TuningAnalyzer in CLI and add tuning subcommand"
```

---

### Task 5: Tuning Rules in Profiles — Tests

**Files:**
- Modify: `tests/test_profiles.py`

**Step 1: Add tuning rule tests**

Append to the end of `tests/test_profiles.py`:

```python
class TestTuningRules:
    def test_master_has_tuning_rules(self):
        profile = get_profile("master")
        assert "tuning" in profile.rules

    def test_mix_has_tuning_rules(self):
        profile = get_profile("mix")
        assert "tuning" in profile.rules

    def test_tuning_deviation_pass(self):
        profile = get_profile("master")
        rule = [r for r in profile.rules["tuning"] if r["metric"] == "tuning_deviation_cents"][0]
        assert rule["evaluate"](5.0) == "pass"
        assert rule["evaluate"](-7.0) == "pass"

    def test_tuning_deviation_warn(self):
        profile = get_profile("master")
        rule = [r for r in profile.rules["tuning"] if r["metric"] == "tuning_deviation_cents"][0]
        assert rule["evaluate"](12.0) == "warn"
        assert rule["evaluate"](-15.0) == "warn"

    def test_tuning_deviation_fail(self):
        profile = get_profile("master")
        rule = [r for r in profile.rules["tuning"] if r["metric"] == "tuning_deviation_cents"][0]
        assert rule["evaluate"](25.0) == "fail"

    def test_pitch_drift_pass(self):
        profile = get_profile("master")
        rule = [r for r in profile.rules["tuning"] if r["metric"] == "pitch_drift_range_cents"][0]
        assert rule["evaluate"](3.0) == "pass"

    def test_pitch_drift_fail(self):
        profile = get_profile("master")
        rule = [r for r in profile.rules["tuning"] if r["metric"] == "pitch_drift_range_cents"][0]
        assert rule["evaluate"](25.0) == "fail"

    def test_chroma_sharpness_pass(self):
        profile = get_profile("master")
        rule = [r for r in profile.rules["tuning"] if r["metric"] == "chroma_sharpness"][0]
        assert rule["evaluate"](0.75) == "pass"

    def test_chroma_sharpness_fail(self):
        profile = get_profile("master")
        rule = [r for r in profile.rules["tuning"] if r["metric"] == "chroma_sharpness"][0]
        assert rule["evaluate"](0.2) == "fail"

    def test_both_profiles_have_detuned_mix_pattern(self):
        for stage in ("master", "mix"):
            profile = get_profile(stage)
            pattern_ids = [p["pattern"] for p in profile.patterns]
            assert "detuned_mix" in pattern_ids, f"{stage} profile missing detuned_mix"
```

**Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_profiles.py::TestTuningRules -v`
Expected: FAIL — `"tuning" not in profile.rules`

**Step 3: Commit**

```bash
git add tests/test_profiles.py
git commit -m "test: add failing tests for tuning rules in profiles"
```

---

### Task 6: Tuning Rules in Profiles — Implementation

**Files:**
- Modify: `src/bounce_house/profiles.py`

Add tuning rules and the `detuned_mix` diagnostic pattern to both master and mix profiles.

**Step 1: Add tuning rule functions and data**

Add before the `MASTER_PROFILE = Profile(...)` line (around line 359) in `profiles.py`:

```python
def _tuning_deviation_status(value: float) -> str:
    if abs(value) < 8:
        return "pass"
    if abs(value) < 20:
        return "warn"
    return "fail"


def _pitch_drift_status(value: float) -> str:
    if value < 8:
        return "pass"
    if value < 20:
        return "warn"
    return "fail"


def _chroma_sharpness_status(value: float) -> str:
    if value > 0.6:
        return "pass"
    if value > 0.3:
        return "warn"
    return "fail"
```

Add tuning rules to `_MASTER_RULES` dict (after the `"stereo"` key):

```python
    "tuning": [
        {
            "metric": "tuning_deviation_cents",
            "evaluate": _tuning_deviation_status,
            "messages": {
                "pass": (
                    "Estimated concert pitch: A={estimated_a:.1f} Hz"
                    " ({value:+.1f} cents from A440) — within tolerance"
                ),
                "warn": (
                    "Estimated concert pitch: A={estimated_a:.1f} Hz"
                    " ({value:+.1f} cents from A440)"
                    " — check if instruments match reference pitch"
                ),
                "fail": (
                    "Estimated concert pitch: A={estimated_a:.1f} Hz"
                    " ({value:+.1f} cents from A440)"
                    " — significant deviation, check tuning reference"
                ),
            },
        },
        {
            "metric": "pitch_drift_range_cents",
            "evaluate": _pitch_drift_status,
            "messages": {
                "pass": "Pitch stability: {value:.1f} cents range — stable",
                "warn": (
                    "Pitch stability: {value:.1f} cents range"
                    " — moderate drift, consider pitch correction"
                ),
                "fail": (
                    "Pitch stability: {value:.1f} cents range"
                    " — significant drift, re-record or apply pitch correction"
                ),
            },
        },
        {
            "metric": "chroma_sharpness",
            "evaluate": _chroma_sharpness_status,
            "messages": {
                "pass": "Chroma definition: {value:.2f} — well-defined pitch content",
                "warn": (
                    "Chroma definition: {value:.2f}"
                    " — somewhat diffuse pitch content"
                ),
                "fail": (
                    "Chroma definition: {value:.2f}"
                    " — very diffuse pitch content, check intonation"
                ),
            },
        },
    ],
```

Add the `detuned_mix` pattern to `_MASTER_PATTERNS` list:

```python
    {
        "pattern": "detuned_mix",
        "name": "Detuned Mix",
        "conditions": [
            ("tuning.tuning_deviation_cents", ">", 15),
            ("tuning.pitch_drift_range_cents", ">", 15),
            ("tuning.chroma_sharpness", "<", 0.4),
        ],
        "min_match": 2,
        "severity": "warn",
        "diagnosis": "Possible tuning issues — pitch instability or non-standard tuning",
        "advice": (
            "Check instrument tuning against a reference. If pitch drifts over "
            "time, re-record or apply pitch correction. If the concert pitch is "
            "intentionally non-440, this warning can be ignored."
        ),
    },
```

For the mix profile, set `"tuning"` rules identical to master (like stereo):

In `_MIX_RULES`, add:

```python
    "tuning": _MASTER_RULES["tuning"],  # identical
```

The `detuned_mix` pattern will be inherited automatically since mix patterns derive from master patterns (it's included in `_MASTER_PATTERNS` which `_MIX_PATTERNS` is built from).

**Important note on rule messages**: The tuning deviation rule messages reference `{estimated_a}` which is not a standard format variable. The rules engine in `rules.py` only formats with `{value}`. Two options:
- Option A: Only use `{value}` in messages (simpler, consistent with existing rules)
- Option B: Extend the rules engine to pass all metrics

**Go with Option A** — keep messages using only `{value}`:

```python
"pass": "Tuning deviation is {value:+.1f} cents from A440 — within tolerance",
"warn": "Tuning deviation is {value:+.1f} cents from A440 — check reference pitch",
"fail": "Tuning deviation is {value:+.1f} cents from A440 — significant, check tuning",
```

**Step 2: Run profile tests**

Run: `uv run pytest tests/test_profiles.py -v`
Expected: All tests PASS.

**Step 3: Run full test suite**

Run: `uv run pytest tests/ -x -q`
Expected: All tests pass.

**Step 4: Run lint**

Run: `uv run ruff check src/bounce_house/profiles.py && uv run mypy src/bounce_house/profiles.py`
Expected: Clean.

**Step 5: Commit**

```bash
git add src/bounce_house/profiles.py
git commit -m "feat: add tuning rules and detuned_mix diagnostic pattern to profiles"
```

---

### Task 7: Report Display — Tests

**Files:**
- Modify: `tests/test_report.py`

**Step 1: Check existing report test structure**

Read `tests/test_report.py` to understand the test pattern used, then add tests for the tuning section rendering. The tuning metrics need to appear in both terminal and JSON output.

Add tests that verify:
- Terminal output includes a "Tuning" section header when tuning results are present
- JSON output includes a `"tuning"` key with the expected metrics
- The `_MODULE_TITLES` dict in report.py includes the tuning module

**Step 2: Run to verify they fail, then proceed to Task 8 for implementation**

Run: `uv run pytest tests/test_report.py -v -k tuning`
Expected: FAIL

**Step 3: Commit**

```bash
git add tests/test_report.py
git commit -m "test: add failing tests for tuning section in report output"
```

---

### Task 8: Report Display — Implementation

**Files:**
- Modify: `src/bounce_house/report.py`

**Step 1: Add tuning module to report.py**

Add to `_MODULE_TITLES` dict (line ~29):

```python
_MODULE_TITLES = {
    "loudness": "Loudness & Dynamics",
    "spectrum": "Spectral Balance",
    "stereo": "Stereo & Phase",
    "perceptual": "Perceptual Quality",
    "tuning": "Tuning & Pitch",
}
```

Add tuning metric display names to `_METRIC_NAMES` dict:

```python
    "tuning_deviation_cents": "Tuning Deviation",
    "estimated_a_hz": "Concert Pitch",
    "closest_standard": "Closest Standard",
    "pitch_drift_std_cents": "Pitch Drift (std)",
    "pitch_drift_range_cents": "Pitch Drift (range)",
    "pitch_drift_trend_cents_per_min": "Pitch Trend",
    "chroma_sharpness": "Chroma Sharpness",
```

Add `"closest_standard"` to `_SKIP_METRICS` so it doesn't render as a separate line (it's informational, shown in the tuning deviation assessment message):

Actually — `closest_standard` is a string, not a float, so `_format_value` will handle it as `str(value)`. It's fine to display it. Leave it in.

**Step 2: Add tuning metric formatting to `_format_value`**

Add cents formatting support in `_format_value` (around line 337):

```python
def _format_value(key: str, value: Any) -> str:
    """Format a metric value for display based on its key suffix."""
    if isinstance(value, str):
        return value
    if isinstance(value, float):
        if "cents" in key:
            return f"{value:+.1f} cents"
        if "hz" in key.lower():
            return f"{value:,.1f} Hz"
        if "db" in key.lower() or "lufs" in key or "lu" in key:
            return f"{value:+.1f}"
        return f"{value:.4f}"
    return str(value)
```

Note: changed the Hz format from `,.0f` to `,.1f` only for estimated_a_hz (which needs decimal precision). Actually the existing hz format shows `440 Hz` as an integer which is fine for centroid but not for `estimated_a_hz = 440.2`. The simplest fix: add a specific check for `"cents"` key suffix before the `"hz"` check. The `"estimated_a_hz"` key will still match the `"hz"` check — but since it's a float like 440.2, `{value:,.0f}` rounds it. We want `440.2 Hz`. So change the hz format to `.1f` for precision.

Actually, keep it simple — the `cents` check handles drift metrics, and `estimated_a_hz` benefits from one decimal. Change hz format string to `{value:,.1f} Hz`.

**Step 3: Run report tests**

Run: `uv run pytest tests/test_report.py -v`
Expected: All pass.

**Step 4: Run lint**

Run: `uv run ruff check src/bounce_house/report.py`
Expected: Clean.

**Step 5: Commit**

```bash
git add src/bounce_house/report.py
git commit -m "feat: add tuning section to terminal and JSON report output"
```

---

### Task 9: Metric Docs for Explain Command

**Files:**
- Modify: `src/bounce_house/metric_docs.py`

**Step 1: Add tuning metric documentation**

Add `MetricDoc` entries for the tuning metrics, add them to `METRICS`, add `"tuning"` to `MODULES` and `MODULE_TITLES`.

Tuning metric docs to add:

```python
_TUNING_DEVIATION = MetricDoc(
    key="tuning_deviation_cents",
    name="Tuning Deviation",
    module="tuning",
    summary="Offset from A440 concert pitch in cents.",
    explanation=(
        "Measures how far the overall tuning of the recording deviates from "
        "the standard A=440 Hz reference. Positive values mean sharp, negative "
        "means flat. Some orchestras tune to A=442 or A=443. Older recordings "
        "or analog tape transfers may show arbitrary tuning offsets."
    ),
    good_range="Within ±8 cents of A440",
    genre_notes=(
        "Classical orchestras commonly tune to A=441-443. Baroque period "
        "instruments may use A=415. Some genres deliberately use A=432."
    ),
    technical=(
        "Estimated via librosa.estimate_tuning() which builds a histogram of "
        "spectral peak deviations from the equal-tempered grid. Resolution: "
        "1 cent. Works on polyphonic content."
    ),
    aliases=["tuning", "pitch", "concert_pitch", "a440"],
)

_ESTIMATED_A = MetricDoc(
    key="estimated_a_hz",
    name="Concert Pitch (A)",
    module="tuning",
    summary="Estimated frequency of concert A in Hz.",
    explanation=(
        "The estimated absolute frequency of the note A above middle C. "
        "Standard tuning is A=440 Hz. This is derived from the tuning "
        "deviation measurement."
    ),
    good_range="435-445 Hz",
    genre_notes="See tuning_deviation_cents for genre context.",
    technical="Computed as 440 * 2^(deviation_cents / 1200).",
    aliases=["concert_a", "a_hz"],
)

_PITCH_DRIFT_RANGE = MetricDoc(
    key="pitch_drift_range_cents",
    name="Pitch Drift Range",
    module="tuning",
    summary="Total pitch excursion over the track duration.",
    explanation=(
        "Measures how much the overall tuning varies from start to finish. "
        "A high range indicates pitch drift — the recording drifting sharp or "
        "flat over time. Common in analog tape transfers, poorly calibrated "
        "instruments, or recordings with temperature-induced tuning drift."
    ),
    good_range="Under 8 cents",
    genre_notes=(
        "Live recordings may show more drift than studio recordings. "
        "Analog tape wow can produce 5-20 cents of drift."
    ),
    technical=(
        "Computed by running librosa.estimate_tuning() on overlapping 10-second "
        "windows with 5-second hop, then taking max - min of the resulting curve."
    ),
    aliases=["drift", "pitch_drift", "wow"],
)

_CHROMA_SHARPNESS = MetricDoc(
    key="chroma_sharpness",
    name="Chroma Sharpness",
    module="tuning",
    summary="How well-defined the pitch content is (0-1 scale).",
    explanation=(
        "Measures whether pitch energy concentrates cleanly in individual "
        "chroma bins or spreads diffusely across them. Well-tuned recordings "
        "produce sharp chroma peaks; detuned or poorly intonated recordings "
        "produce broad, smeared distributions."
    ),
    good_range="Above 0.6",
    genre_notes=(
        "Noise-heavy genres (industrial, lo-fi) will naturally score lower. "
        "Highly pitched content (piano, strings) scores higher."
    ),
    technical=(
        "Computed from librosa.feature.chroma_cqt() with forced A440 alignment "
        "(tuning=0). Per-frame peak-to-mean ratio of the 12-bin chroma vector, "
        "normalized to a 0-1 scale where 1.0 = all energy in a single bin."
    ),
    aliases=["chroma", "intonation"],
)
```

Add to `METRICS` dict, `MODULES` dict, and `MODULE_TITLES`.

**Step 2: Run explain tests**

Run: `uv run pytest tests/test_explain.py -v`
Expected: All pass.

**Step 3: Run lint**

Run: `uv run ruff check src/bounce_house/metric_docs.py`
Expected: Clean.

**Step 4: Commit**

```bash
git add src/bounce_house/metric_docs.py
git commit -m "docs: add tuning metric documentation for explain command"
```

---

### Task 10: Integration Test — Full Pipeline

**Files:**
- Modify: `tests/test_cli.py`

**Step 1: Add integration test for tuning in full pipeline**

Add a test that runs the full `analyze` command and verifies tuning metrics appear in the output:

```python
def test_analyze_includes_tuning(self, tmp_wav):
    """Full analyze should include tuning section."""
    result = main(["analyze", str(tmp_wav)])
    assert result == 0
    # Verify tuning analyzer ran by checking it doesn't error
```

Add a test for the `tuning` subcommand:

```python
def test_tuning_subcommand(self, tmp_wav):
    """The tuning subcommand should work standalone."""
    result = main(["tuning", str(tmp_wav)])
    assert result == 0
```

Add a JSON output test to verify tuning metrics in structured output:

```python
def test_json_includes_tuning(self, tmp_wav, capsys):
    """JSON output should include tuning metrics."""
    main(["analyze", str(tmp_wav), "--json"])
    captured = capsys.readouterr()
    import json
    data = json.loads(captured.out)
    assert "tuning" in data
    assert "tuning_deviation_cents" in data["tuning"]
```

**Step 2: Run integration tests**

Run: `uv run pytest tests/test_cli.py -v -k tuning`
Expected: All pass.

**Step 3: Run full test suite as final regression check**

Run: `uv run pytest tests/ -v`
Expected: All tests pass. Total count should be ~245+ (232 original + ~13 new).

**Step 4: Run lint and type check on all modified files**

Run: `uv run ruff check src/bounce_house/ && uv run ruff format --check src/bounce_house/ && uv run mypy src/bounce_house/`
Expected: Clean.

**Step 5: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: add integration tests for tuning analysis in CLI pipeline"
```

---

### Task 11: Final Verification and README Update

**Files:**
- Modify: `README.md`

**Step 1: Update README to mention tuning analysis**

Add "tuning & pitch stability" to the feature list and add the `tuning` subcommand to the usage examples.

**Step 2: Run the tool manually on a real file (if available) or the test fixture**

Run: `uv run bounce-house analyze tests/conftest.py` — this will fail since it's not a wav file, but verify the help works:

Run: `uv run bounce-house tuning --help`
Expected: Shows help for tuning subcommand.

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add tuning analysis to README feature list"
```
