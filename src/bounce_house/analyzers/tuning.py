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
        # Adapt window size for short audio (need at least 2 windows)
        duration_sec = len(y) / sr
        if duration_sec >= 20.0:
            window_sec = 10.0
            hop_sec = 5.0
        elif duration_sec >= 2.0:
            window_sec = duration_sec / 4.0
            hop_sec = window_sec / 2.0
        else:
            window_sec = duration_sec
            hop_sec = duration_sec

        window_samples = int(window_sec * sr)
        hop_samples = max(1, int(hop_sec * sr))

        tuning_curve: list[float] = []
        if len(y) >= window_samples and window_samples > 0:
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
            result.metrics["tuning_deviation_cents"] - ref_result.metrics["tuning_deviation_cents"],
            1,
        )
        result.metrics["tuning_difference_cents"] = diff
        result.metrics["reference_estimated_a_hz"] = ref_result.metrics["estimated_a_hz"]

        return result
