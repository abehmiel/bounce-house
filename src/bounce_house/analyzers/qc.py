"""Quality-control analyzer — clipping and edge-silence detection."""

from __future__ import annotations

import numpy as np

from bounce_house.analyzers.base import AnalysisResult, AnalyzerBase
from bounce_house.audio import AudioData

# -0.1 dBFS: common clip-detection ceiling. Clipping is a delivered-waveform
# property, so clip-run detection reads the pre-DC waveform (see analyze()).
_CLIP_THRESHOLD = 10 ** (-0.1 / 20)
_MIN_CLIP_RUN = 3
# -60 dBFS RMS in 10 ms windows counts as silence for edge detection
_SILENCE_THRESHOLD = 10 ** (-60 / 20)
_SILENCE_WINDOW_SEC = 0.01


def _clip_intervals(channel: np.ndarray) -> list[tuple[int, int]]:
    """(start, end) sample-index intervals of consecutive runs at/above the clip
    threshold, filtered to runs of at least _MIN_CLIP_RUN samples."""
    clipped = np.abs(channel) >= _CLIP_THRESHOLD
    if not np.any(clipped):
        return []
    edges = np.diff(clipped.astype(np.int8), prepend=0, append=0)
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)
    return [(int(s), int(e)) for s, e in zip(starts, ends, strict=True) if e - s >= _MIN_CLIP_RUN]


def _merge_intervals(intervals: list[tuple[int, int]]) -> int:
    """Count merged time-overlapping/adjacent (start, end) intervals as single events."""
    if not intervals:
        return 0
    ordered = sorted(intervals)
    count = 1
    current_end = ordered[0][1]
    for start, end in ordered[1:]:
        if start <= current_end:  # overlapping or adjacent in time -> same event
            current_end = max(current_end, end)
        else:
            count += 1
            current_end = end
    return count


class QcAnalyzer(AnalyzerBase):
    @property
    def name(self) -> str:
        return "qc"

    def analyze(self, audio: AudioData) -> AnalysisResult:
        metrics: dict = {}

        # Clip detection reads the delivered pre-DC waveform — clipping is a
        # property of what was actually printed, not the DC-free analysis signal.
        waveform = audio.raw_samples if audio.raw_samples is not None else audio.samples
        all_intervals: list[tuple[int, int]] = []
        longest_run = 0
        for ch in range(audio.channels):
            intervals = _clip_intervals(waveform[:, ch])
            all_intervals.extend(intervals)
            for start, end in intervals:
                longest_run = max(longest_run, end - start)
        metrics["clip_events"] = _merge_intervals(all_intervals)
        metrics["longest_clip_run"] = longest_run

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
