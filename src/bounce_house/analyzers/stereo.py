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
            correlation = round(float(np.corrcoef(L, R)[0, 1]), 4)
        else:
            correlation = None  # silence: correlation is undefined, not perfect
        metrics["phase_correlation"] = correlation

        # M/S decomposition
        mid = (L + R) / 2.0
        side = (L - R) / 2.0
        mid_rms = float(np.sqrt(np.mean(mid**2)))
        side_rms = float(np.sqrt(np.mean(side**2)))

        metrics["mid_rms_db"] = round(20 * np.log10(mid_rms + 1e-10), 1)
        metrics["side_rms_db"] = round(20 * np.log10(side_rms + 1e-10), 1)
        metrics["ms_ratio_db"] = round(metrics["mid_rms_db"] - metrics["side_rms_db"], 1)

        # Channel balance
        l_rms = float(np.sqrt(np.mean(L**2)))
        r_rms = float(np.sqrt(np.mean(R**2)))
        l_rms_db = 20 * np.log10(l_rms + 1e-10)
        r_rms_db = 20 * np.log10(r_rms + 1e-10)
        metrics["balance_db"] = round(l_rms_db - r_rms_db, 1)

        # Stereo width measures DECORRELATION, not panning: normalize channels to
        # equal RMS first so a panned mono source reads 0. Pure imbalance is
        # balance_db's job; width is undefined when a channel is silent.
        if l_rms > 1e-10 and r_rms > 1e-10:
            Ln = L / l_rms
            Rn = R / r_rms
            mid_n_rms = float(np.sqrt(np.mean(((Ln + Rn) / 2.0) ** 2)))
            side_n_rms = float(np.sqrt(np.mean(((Ln - Rn) / 2.0) ** 2)))
            total_n = mid_n_rms + side_n_rms
            metrics["stereo_width"] = round(side_n_rms / total_n, 4) if total_n > 0 else None
        else:
            metrics["stereo_width"] = None

        # Windowed phase correlation (50ms blocks)
        block_size = int(audio.sample_rate * 0.05)
        num_blocks = len(L) // block_size
        block_values: list[float | None] = []
        for i in range(num_blocks):
            start = i * block_size
            end = start + block_size
            bl = L[start:end]
            br = R[start:end]
            if np.std(bl) > 1e-10 and np.std(br) > 1e-10:
                block_values.append(float(np.corrcoef(bl, br)[0, 1]))
            else:
                block_values.append(None)
        block_corrs = [v for v in block_values if v is not None]

        metrics["low_block_correlation"] = (
            round(float(np.percentile(block_corrs, 5)), 4) if block_corrs else None
        )

        # Correlation over time, bucketed to <=50 points for report/JSON.
        # Integer edge boundaries partition every block into exactly `points`
        # buckets (sizes differ by at most 1) so no trailing blocks are dropped.
        n = len(block_values)
        points = min(50, n) if block_values else 0
        curve: list[float | None] = []
        if points:
            edges = [i * n // points for i in range(points + 1)]
            for i in range(points):
                bucket = [v for v in block_values[edges[i] : edges[i + 1]] if v is not None]
                curve.append(round(float(np.mean(bucket)), 3) if bucket else None)
        metrics["correlation_curve"] = curve

        # Frequency-dependent stereo width
        freq_width = self._frequency_stereo_width(L, R, audio.sample_rate)
        metrics["frequency_width"] = freq_width

        return AnalysisResult(module=self.name, metrics=metrics)

    def compare(self, audio: AudioData, reference: AudioData) -> AnalysisResult:
        result = self.analyze(audio)
        ref_result = self.analyze(reference)

        if result.metrics.get("mono_file") or ref_result.metrics.get("mono_file"):
            return result

        # width is undefined when either side has undefined stereo_width
        width = result.metrics["stereo_width"]
        ref_width = ref_result.metrics["stereo_width"]
        result.metrics["width_difference"] = (
            round(width - ref_width, 4) if width is not None and ref_width is not None else None
        )

        # difference is undefined when either side has undefined phase_correlation
        corr = result.metrics["phase_correlation"]
        ref_corr = ref_result.metrics["phase_correlation"]
        result.metrics["correlation_difference"] = (
            round(corr - ref_corr, 4) if corr is not None and ref_corr is not None else None
        )

        result.metrics["reference_width"] = ref_result.metrics["stereo_width"]
        result.metrics["reference_correlation"] = ref_result.metrics["phase_correlation"]

        return result

    def _frequency_stereo_width(
        self, L: np.ndarray, R: np.ndarray, sr: int, nperseg: int = 4096
    ) -> dict[str, float | None]:
        """Compute per-band correlation between L and R channels."""
        f, _, Zl = stft(L, sr, nperseg=nperseg)
        _, _, Zr = stft(R, sr, nperseg=nperseg)

        result: dict[str, float | None] = {}
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
                result[band_name] = None  # silent band: correlation undefined
                continue
            cross = np.mean(np.real(Zl_band * np.conj(Zr_band)))
            result[band_name] = round(float(cross / denom), 4)

        return result
