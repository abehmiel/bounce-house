"""Stereo imaging and phase analyzer."""

from __future__ import annotations

import numpy as np
from scipy.signal import stft

from bounce_house.analyzers.base import AnalysisResult, AnalyzerBase
from bounce_house.audio import AudioData

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

        # Phase correlation (Pearson) — guard against silent/constant channels
        if np.std(L) > 1e-10 and np.std(R) > 1e-10:
            correlation = float(np.corrcoef(L, R)[0, 1])
        else:
            correlation = 1.0  # silence = identical channels = perfectly correlated
        metrics["phase_correlation"] = round(correlation, 4)

        # M/S decomposition
        mid = (L + R) / 2.0
        side = (L - R) / 2.0
        mid_rms = float(np.sqrt(np.mean(mid**2)))
        side_rms = float(np.sqrt(np.mean(side**2)))

        metrics["mid_rms_db"] = round(20 * np.log10(mid_rms + 1e-10), 1)
        metrics["side_rms_db"] = round(20 * np.log10(side_rms + 1e-10), 1)
        metrics["ms_ratio_db"] = round(metrics["mid_rms_db"] - metrics["side_rms_db"], 1)

        # Stereo width: 0 = mono, 0.5 = equal mid/side
        total = mid_rms + side_rms
        metrics["stereo_width"] = round(side_rms / total if total > 0 else 0.0, 4)

        # Channel balance
        l_rms_db = 20 * np.log10(float(np.sqrt(np.mean(L**2))) + 1e-10)
        r_rms_db = 20 * np.log10(float(np.sqrt(np.mean(R**2))) + 1e-10)
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

        metrics["min_block_correlation"] = round(min(block_corrs), 4) if block_corrs else 1.0

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
            Zl_band = Zl[mask, :]
            Zr_band = Zr[mask, :]
            power_l = np.mean(np.abs(Zl_band) ** 2)
            power_r = np.mean(np.abs(Zr_band) ** 2)
            denom = np.sqrt(power_l * power_r)
            if denom < 1e-10:
                corr = 1.0  # silent band = perfectly correlated
            else:
                cross = np.mean(np.real(Zl_band * np.conj(Zr_band)))
                corr = float(cross / denom)
            result[band_name] = round(corr, 4)

        return result
