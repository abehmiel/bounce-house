"""Perceptual quality analyzer.

Uses timbral_models if installed, otherwise falls back to spectral proxy metrics.
"""

from __future__ import annotations

import librosa
import numpy as np

from bounce_house.analyzers.base import AnalysisResult, AnalyzerBase
from bounce_house.audio import AudioData

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
                result.metrics[diff_key] = round(result.metrics[key] - ref_result.metrics[key], 4)
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
