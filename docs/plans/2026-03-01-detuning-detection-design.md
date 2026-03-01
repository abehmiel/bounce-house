# Detuning Detection Design

## Problem

Audio mixes can suffer from tuning problems that degrade quality:
- **Wrong reference pitch**: instruments tuned to different concert pitch standards (A=440 vs A=432 vs A=442)
- **Pitch drift / wow**: instruments or recordings slowly drifting sharp or flat over time
- **Poor intonation**: instruments not cleanly tuned to any equal-tempered pitch, producing diffuse pitch content

These problems are difficult to hear in context but become apparent on careful listening or when comparing against a reference. An automated check can catch them before release.

## Approach

Use librosa's existing tuning estimation and chroma analysis functions — no new dependencies required. The approach works on full polyphonic stereo mixes.

### Technical Foundation

**Global tuning estimation**: `librosa.estimate_tuning()` uses `piptrack()` (parabolic interpolation on STFT peaks) to find spectral peaks, then builds a histogram of each peak's deviation from the nearest equal-tempered semitone. The histogram peak gives the most likely global tuning offset. Works on polyphonic content because it aggregates across all detected pitches via majority vote.

**Pitch drift detection**: Run `estimate_tuning()` on overlapping 10-second windows with 5-second hop. Compute standard deviation, range, and linear regression slope of the resulting tuning curve. A positive slope means the recording is drifting sharp; high standard deviation means unstable pitch.

**Chroma sharpness**: Compute `chroma_cqt(tuning=0)` — forcing A440 alignment rather than auto-correcting for detuning. In well-tuned audio, energy concentrates crisply in individual chroma bins. In detuned audio, energy "smears" across adjacent bins. Measure this by computing the mean peak-to-sidelobe ratio across chroma frames.

### Alternatives Considered

- **Beating detection via Hilbert envelope analysis**: Would catch two instruments at slightly different pitches causing audible pulsing. Rejected for v1 due to high false-positive risk on full mixes (tremolo, compressor pumping, and musical dynamics produce similar patterns). Could be added later.
- **Spotify Basic Pitch (neural polyphonic transcription)**: Would give per-note deviation from equal temperament. Rejected due to heavy dependency (TensorFlow/ONNX, ~200MB+). Overkill for a CLI tool.
- **CREPE / pYIN**: Monophonic-only pitch trackers. Not suitable for full mixes.

## New Analyzer Module

File: `src/bounce_house/analyzers/tuning.py`

Class: `TuningAnalyzer(AnalyzerBase)` with `name = "tuning"`

### Metrics

| Metric key | Type | Description |
|---|---|---|
| `tuning_deviation_cents` | float | Global offset from A440 in cents |
| `estimated_a_hz` | float | Estimated concert A frequency |
| `closest_standard` | str | Nearest recognized standard (e.g., "A=442") |
| `pitch_drift_std_cents` | float | Std deviation of windowed tuning — higher = less stable |
| `pitch_drift_range_cents` | float | Max minus min of windowed tuning |
| `pitch_drift_trend_cents_per_min` | float | Linear regression slope — positive = drifting sharp |
| `chroma_sharpness` | float | Peak-to-sidelobe ratio in forced-A440 chromagram (0-1) |

### Implementation

1. Mono downmix (same pattern as `SpectrumAnalyzer`)
2. `librosa.estimate_tuning(y=y, sr=sr, resolution=0.01)` for global deviation
3. Convert to Hz: `estimated_a = 440.0 * 2**(deviation_cents / 1200)`
4. Classify against known standards (A=432, 435, 438, 440, 441, 442, 443, 444)
5. Sliding window `estimate_tuning()` for drift metrics
6. `np.polyfit(degree=1)` on windowed tuning for trend
7. `librosa.feature.chroma_cqt(y=y, sr=sr, tuning=0)` for sharpness
8. Per-frame peak-to-mean ratio of chroma vector, averaged across frames

### Compare Mode

Computes metrics for both audio files, reports tuning deviation difference between them. Catches mismatched reference pitch between a mix and its reference track.

## Rules

Added to both master and mix profiles in `profiles.py`.

### Tuning Deviation

| Status | Condition |
|---|---|
| pass | \|deviation\| < 8 cents |
| warn | \|deviation\| < 20 cents |
| fail | \|deviation\| >= 20 cents |

### Pitch Drift

| Status | Condition |
|---|---|
| pass | range < 8 cents |
| warn | range < 20 cents |
| fail | range >= 20 cents |

### Chroma Sharpness

| Status | Condition |
|---|---|
| pass | sharpness > 0.6 |
| warn | sharpness > 0.3 |
| fail | sharpness <= 0.3 |

Thresholds are intentionally loose to minimize false positives on full mixes, where `estimate_tuning()` has inherent estimation noise. Can be tightened after real-world testing.

## Diagnostic Pattern

```
"detuned_mix" pattern:
  conditions:
    - abs(tuning.tuning_deviation_cents) > 15
    - tuning.pitch_drift_range_cents > 15
    - tuning.chroma_sharpness < 0.4
  min_match: 2
  severity: warn
  diagnosis: "Possible tuning issues — pitch instability or non-standard tuning"
  advice: "Check instrument tuning against a reference. If pitch drifts over
           time, re-record or apply pitch correction. If the concert pitch is
           intentionally non-440, this warning can be ignored."
```

## Report Output

New "Tuning" section in the report, following existing format conventions.

Pass example:
```
 Tuning
  ✓ Estimated concert pitch: A=440.2 Hz (+0.8 cents from A440)
  ✓ Pitch stability: ±2.1 cents (range 4.3 cents) — stable
  ✓ Chroma definition: 0.82 — well-defined pitch content
```

Fail example:
```
 Tuning
  ⚠ Estimated concert pitch: A=443.1 Hz (+12.2 cents from A440)
    — closest standard: A=443, check if instruments match reference pitch
  ✗ Pitch stability: ±8.4 cents (range 19.5 cents) — significant drift
    — pitch drifts sharp at +3.2 cents/minute, consider re-recording
  ✓ Chroma definition: 0.71 — adequate pitch content
```

## Files Changed

- **New**: `src/bounce_house/analyzers/tuning.py` — TuningAnalyzer
- **Modified**: `src/bounce_house/analyzers/__init__.py` — register analyzer
- **Modified**: `src/bounce_house/profiles.py` — tuning rules + detuned_mix pattern
- **Modified**: `src/bounce_house/report.py` — tuning section in report
- **New**: `tests/test_tuning.py` — analyzer tests
- **Modified**: `tests/test_profiles.py` — rule/pattern tests

## Dependencies

None new. Uses `librosa` (already installed), `numpy`, `scipy`.
