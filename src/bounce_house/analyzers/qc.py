"""Quality-control analyzer — clipping and edge-silence detection."""

from __future__ import annotations

import numpy as np

from bounce_house.analyzers.base import AnalysisResult, AnalyzerBase
from bounce_house.audio import AudioData

# -0.1 dBFS: common clip-detection ceiling; DC is already removed at load
_CLIP_THRESHOLD = 10 ** (-0.1 / 20)
_MIN_CLIP_RUN = 3
# -60 dBFS RMS in 10 ms windows counts as silence for edge detection
_SILENCE_THRESHOLD = 10 ** (-60 / 20)
_SILENCE_WINDOW_SEC = 0.01


def _clip_runs(channel: np.ndarray) -> list[int]:
    """Lengths of consecutive-sample runs at/above the clip threshold."""
    clipped = np.abs(channel) >= _CLIP_THRESHOLD
    if not np.any(clipped):
        return []
    edges = np.diff(clipped.astype(np.int8), prepend=0, append=0)
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)
    return [int(e - s) for s, e in zip(starts, ends, strict=True) if e - s >= _MIN_CLIP_RUN]


class QcAnalyzer(AnalyzerBase):
    @property
    def name(self) -> str:
        return "qc"

    def analyze(self, audio: AudioData) -> AnalysisResult:
        metrics: dict = {}

        runs: list[int] = []
        for ch in range(audio.channels):
            runs.extend(_clip_runs(audio.samples[:, ch]))
        metrics["clip_events"] = len(runs)
        metrics["longest_clip_run"] = max(runs) if runs else 0

        window = max(1, int(audio.sample_rate * _SILENCE_WINDOW_SEC))
        # Per-window RMS over the loudest channel mix (max of channels, conservative)
        peak_env = np.max(np.abs(audio.samples), axis=1)
        n_windows = len(peak_env) // window
        if n_windows == 0:
            metrics["leading_silence_sec"] = 0.0
            metrics["trailing_silence_sec"] = 0.0
            return AnalysisResult(module=self.name, metrics=metrics)

        trimmed = peak_env[: n_windows * window].reshape(n_windows, window)
        window_rms = np.sqrt(np.mean(trimmed**2, axis=1))
        loud = window_rms >= _SILENCE_THRESHOLD

        if not np.any(loud):
            metrics["leading_silence_sec"] = round(audio.duration, 2)
            metrics["trailing_silence_sec"] = round(audio.duration, 2)
        else:
            first = int(np.argmax(loud))
            last = int(len(loud) - 1 - np.argmax(loud[::-1]))
            metrics["leading_silence_sec"] = round(first * window / audio.sample_rate, 2)
            metrics["trailing_silence_sec"] = round(
                (len(loud) - 1 - last) * window / audio.sample_rate, 2
            )

        return AnalysisResult(module=self.name, metrics=metrics)

    def compare(self, audio: AudioData, reference: AudioData) -> AnalysisResult:
        return self.analyze(audio)
