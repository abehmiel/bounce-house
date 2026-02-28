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
