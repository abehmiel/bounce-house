"""Rhythm analyzer — tempo, tempo stability, and groove.

Deliberately ships no entries in profiles._MASTER_RULES or _MIX_RULES. Tempo is
not a defect: no BPM warrants a warning, and tempo_confidence measures our own
certainty rather than a problem with the mix. Surfacing it as a warning would
pollute the warning/failure counts that drive the summary line and the diff
regression logic. These metrics are informational by design.
"""

from __future__ import annotations

from typing import Any

import librosa
import numpy as np

from bounce_house.analyzers.base import AnalysisResult, AnalyzerBase
from bounce_house.audio import AudioData

# Plausible musical tempo range. Outside this, candidates are metrical
# artifacts rather than tempi anyone would count.
_MIN_BPM = 40.0
_MAX_BPM = 260.0
# Log-normal prior over tempo, centred on 120 BPM with a one-octave sigma.
# Breaks octave ties toward the rate a listener would tap, without hard-coding
# a range that would silently mangle drum & bass or downtempo.
_PRIOR_BPM = 120.0
_PRIOR_WIDTH = 1.0
# Below this normalized top-candidate score the metrical level is contested.
_AMBIGUOUS_BELOW = 0.40
# Shorter than this, there are too few beats to estimate anything honestly.
_MIN_DURATION_SEC = 5.0

# Overlapping-window tempo tracking, mirroring the pitch-drift windows in
# TuningAnalyzer. 12 s holds enough beats for a stable tempogram; the 4 s hop
# localizes a change to within about one window.
_WINDOW_SEC = 12.0
_HOP_SEC = 4.0
# Adjacent windows within this fraction of each other are the same tempo.
_SEGMENT_TOLERANCE = 0.03

_HOP_LENGTH = 512

# Beat-synchronous autocorrelation margin at which a triple grouping is
# decisive. Measured: true-triple 0.506, true-duple 0.045, unaccented 0.264 —
# so 0.40 fires on the first and stays silent on the other two. See the
# design rationale: this detector is deliberately one-sided.
_TRIPLE_MARGIN = 0.40
# Offbeat placement at or above this ratio reads as a shuffle rather than
# straight eighths. Measured: straight 1.112, triplet-swung 1.418.
_SHUFFLE_ABOVE = 1.20

_NOTE_DIVISORS: dict[str, float] = {
    "1/1": 4.0,
    "1/2": 2.0,
    "1/4": 1.0,
    "1/4d": 1.5,
    "1/8": 0.5,
    "1/8d": 0.75,
    "1/8t": 1.0 / 3.0,
    "1/16": 0.25,
}


def _tempo_candidates(
    oenv: np.ndarray, sr: int, hop_length: int = _HOP_LENGTH
) -> list[tuple[float, float]]:
    """Top-3 prior-weighted tempo candidates as (bpm, normalized_score).

    Scores each tempogram lag by autocorrelation strength times a log-normal
    prior, then keeps the strongest peaks that are more than 0.05 octaves apart
    so the list spans distinct metrical levels rather than one blurred peak.
    Returns [] when nothing scores above zero (silence, or no onsets).
    """
    tg = librosa.feature.tempogram(onset_envelope=oenv, sr=sr, hop_length=hop_length)
    ac = np.mean(tg, axis=1)
    freqs = librosa.tempo_frequencies(len(ac), sr=sr, hop_length=hop_length)
    with np.errstate(divide="ignore", invalid="ignore"):
        prior = np.exp(-0.5 * (np.log2(np.maximum(freqs, 1e-9) / _PRIOR_BPM) / _PRIOR_WIDTH) ** 2)
    score = ac * prior
    score[(freqs < _MIN_BPM) | (freqs > _MAX_BPM) | ~np.isfinite(score)] = 0.0
    if not np.any(score > 0):
        return []

    picks: list[tuple[float, float]] = []
    for i in np.argsort(score)[::-1]:
        if score[i] <= 0:
            break
        f = float(freqs[i])
        if any(abs(np.log2(f / p)) < 0.05 for p, _ in picks):
            continue
        picks.append((f, float(score[i])))
        if len(picks) >= 3:
            break

    total = sum(s for _, s in picks) or 1.0
    return [(round(f, 1), round(s / total, 3)) for f, s in picks]


def _segments(
    oenv: np.ndarray,
    sr: int,
    hop_length: int,
    duration: float,
    frames_per_sec: float,
) -> list[dict[str, float]]:
    """Windowed tempo, merged into runs of near-constant BPM.

    Each window gets its own prior-weighted estimate, so a window inherits the
    same octave ambiguity as the global estimate. What the segment list reports
    reliably is *where the tempo changed*, not the absolute BPM of each run.
    """
    if duration < _WINDOW_SEC:
        return []

    win = int(_WINDOW_SEC * frames_per_sec)
    hop = max(1, int(_HOP_SEC * frames_per_sec))
    raw: list[tuple[float, float]] = []
    for start in range(0, len(oenv) - win + 1, hop):
        candidates = _tempo_candidates(oenv[start : start + win], sr, hop_length)
        if candidates:
            raw.append((start / frames_per_sec, candidates[0][0]))
    if not raw:
        return []

    tolerance = np.log2(1 + _SEGMENT_TOLERANCE)
    segs: list[dict[str, float]] = []
    for t, bpm in raw:
        if segs and abs(np.log2(bpm / segs[-1]["bpm"])) < tolerance:
            segs[-1]["end_s"] = round(min(t + _WINDOW_SEC, duration), 2)
            continue
        if segs:
            segs[-1]["end_s"] = round(t, 2)
        segs.append(
            {
                "start_s": round(t, 2),
                "end_s": round(min(t + _WINDOW_SEC, duration), 2),
                "bpm": bpm,
            }
        )
    segs[-1]["end_s"] = round(duration, 2)
    return segs


def _swing_ratio(oenv: np.ndarray, bpm: float, frames_per_sec: float) -> float | None:
    """Offbeat placement as a ratio of the straight midpoint.

    1.0 is dead-straight eighths, about 1.33 is triplet swing. Computed as the
    onset-strength-weighted mean phase within the beat, restricted to the
    offbeat region so the downbeat transient does not dominate the average.
    """
    times = np.arange(len(oenv)) / frames_per_sec
    beat = 60.0 / bpm
    phase = (times % beat) / beat
    offbeat = (phase > 0.25) & (phase < 0.9)
    weights = oenv[offbeat]
    if weights.size == 0 or weights.sum() <= 0:
        return None
    return round(float(np.average(phase[offbeat], weights=weights)) / 0.5, 3)


def _triple_hint(oenv: np.ndarray, sr: int, bpm: float, hop_length: int) -> bool:
    """One-sided triple-grouping detector — True only on decisive evidence.

    Compares beat-synchronous onset autocorrelation at lag 3 against lag 4. A
    two-sided version is not shippable: on unaccented material lag 3 wins by a
    moderate margin even when the music is in four. Gating hard at
    _TRIPLE_MARGIN turns that false positive into silence. Reports grouping
    only; notated meter is out of scope by design.
    """
    _, beats = librosa.beat.beat_track(
        onset_envelope=oenv, sr=sr, hop_length=hop_length, bpm=bpm, units="frames"
    )
    if len(beats) < 12:
        return False
    beat_sync = librosa.util.sync(oenv[np.newaxis, :], beats, aggregate=np.max)[0]
    beat_sync = beat_sync - beat_sync.mean()
    ac = np.correlate(beat_sync, beat_sync, mode="full")[len(beat_sync) - 1 :]
    if ac.size < 5 or ac[0] == 0:
        return False
    ac = ac / ac[0]
    return bool(ac[3] > ac[4] and (ac[3] - ac[4]) >= _TRIPLE_MARGIN)


def _empty_metrics() -> dict[str, Any]:
    """Metric set for audio we cannot honestly measure — every key still present."""
    return {
        "tempo_bpm": None,
        "tempo_confidence": 0.0,
        "tempo_stability": "unmeasurable",
        "tempo_candidates": [],
        "tempo_segments": [],
        "swing_ratio": None,
        "subdivision": None,
        "triple_meter_hint": False,
        "note_ms": {},
    }


class RhythmAnalyzer(AnalyzerBase):
    @property
    def name(self) -> str:
        return "rhythm"

    def analyze(self, audio: AudioData) -> AnalysisResult:
        if audio.duration < _MIN_DURATION_SEC:
            return AnalysisResult(module=self.name, metrics=_empty_metrics())

        y = np.mean(audio.samples, axis=1) if audio.is_stereo else audio.samples[:, 0]
        sr = audio.sample_rate
        oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=_HOP_LENGTH)
        frames_per_sec = sr / _HOP_LENGTH

        candidates = _tempo_candidates(oenv, sr, _HOP_LENGTH)
        if not candidates:
            return AnalysisResult(module=self.name, metrics=_empty_metrics())

        bpm, confidence = candidates[0]
        metrics: dict[str, Any] = _empty_metrics()
        metrics["tempo_bpm"] = bpm
        metrics["tempo_confidence"] = confidence
        metrics["tempo_candidates"] = [{"bpm": f, "score": s} for f, s in candidates]

        segments = _segments(oenv, sr, _HOP_LENGTH, audio.duration, frames_per_sec)
        metrics["tempo_segments"] = segments
        if confidence < _AMBIGUOUS_BELOW:
            metrics["tempo_stability"] = "ambiguous"
        elif not segments:
            metrics["tempo_stability"] = "unmeasurable"
        elif len(segments) == 1:
            metrics["tempo_stability"] = "constant"
        else:
            metrics["tempo_stability"] = "varying"

        # Swing is measured as phase WITHIN the beat, so it is only meaningful
        # when we believe the beat. On an octave-wrong estimate the "beat" is
        # really an eighth note and the ratio is noise — measured: the 90 BPM
        # fixture reads 1.454 ("shuffled") on straight material. Gate it.
        # The triple hint is deliberately NOT gated: it carries its own,
        # stricter margin test, and it fires correctly on the waltz fixture
        # (confidence 0.375) which this gate would otherwise suppress.
        if confidence >= _AMBIGUOUS_BELOW:
            swing = _swing_ratio(oenv, bpm, frames_per_sec)
            metrics["swing_ratio"] = swing
            if swing is not None:
                metrics["subdivision"] = "shuffled" if swing >= _SHUFFLE_ABOVE else "straight"
        metrics["triple_meter_hint"] = _triple_hint(oenv, sr, bpm, _HOP_LENGTH)

        beat_ms = 60000.0 / bpm
        metrics["note_ms"] = {
            name: round(beat_ms * divisor, 1) for name, divisor in _NOTE_DIVISORS.items()
        }

        return AnalysisResult(module=self.name, metrics=metrics)

    def compare(self, audio: AudioData, reference: AudioData) -> AnalysisResult:
        result = self.analyze(audio)
        ref = self.analyze(reference)
        result.metrics["reference_tempo_bpm"] = ref.metrics["tempo_bpm"]
        if result.metrics["tempo_bpm"] is None or ref.metrics["tempo_bpm"] is None:
            result.metrics["tempo_difference_bpm"] = None
        else:
            result.metrics["tempo_difference_bpm"] = round(
                result.metrics["tempo_bpm"] - ref.metrics["tempo_bpm"], 1
            )
        return result
