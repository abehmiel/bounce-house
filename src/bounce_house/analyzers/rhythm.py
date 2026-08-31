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
