"""Translation analyzer — how the mix survives mono and small-speaker playback."""

from __future__ import annotations

import numpy as np
from scipy.signal import stft

from bounce_house.analyzers.base import AnalysisResult, AnalyzerBase
from bounce_house.audio import AudioData

# Same banding as the stereo analyzer's frequency-dependent correlation
FREQ_BANDS = [
    ("sub_bass", 20, 120),
    ("low_mid", 120, 500),
    ("mid", 500, 2000),
    ("upper_mid", 2000, 8000),
    ("air", 8000, 20000),
]

# Small speakers (phones, laptops, Bluetooth minis) reproduce little below this
_SMALL_SPEAKER_CUTOFF_HZ = 120.0


class TranslationAnalyzer(AnalyzerBase):
    @property
    def name(self) -> str:
        return "translation"

    def analyze(self, audio: AudioData) -> AnalysisResult:
        metrics: dict = {}
        sr = audio.sample_rate

        if audio.is_stereo:
            L = audio.samples[:, 0]
            R = audio.samples[:, 1]
            mono = (L + R) / 2.0

            # Broadband mono loss: mono-sum power vs average per-channel power.
            # 0 dB = perfectly mono-compatible; -3 dB = hard-panned (pan law);
            # very negative = anti-phase cancellation.
            stereo_power = float(np.mean(audio.samples**2))
            mono_power = float(np.mean(mono**2))
            loss_db = 10.0 * np.log10((mono_power + 1e-12) / (stereo_power + 1e-12))
            metrics["mono_loss_db"] = round(max(loss_db, -100.0), 1)

            # Per-band mono loss localizes the cancellation
            f, _, Zl = stft(L, sr, nperseg=4096)
            _, _, Zr = stft(R, sr, nperseg=4096)
            Zm = (Zl + Zr) / 2.0
            band_loss: dict[str, float] = {}
            for band_name, lo, hi in FREQ_BANDS:
                mask = (f >= lo) & (f < hi)
                if not np.any(mask):
                    band_loss[band_name] = 0.0
                    continue
                stereo_band = float(
                    np.mean(np.abs(Zl[mask, :]) ** 2 + np.abs(Zr[mask, :]) ** 2) / 2.0
                )
                mono_band = float(np.mean(np.abs(Zm[mask, :]) ** 2))
                band_db = 10.0 * np.log10((mono_band + 1e-12) / (stereo_band + 1e-12))
                band_loss[band_name] = round(max(band_db, -100.0), 1)
            metrics["band_mono_loss"] = band_loss
            worst = min(band_loss, key=lambda name: band_loss[name])
            metrics["worst_band"] = worst
            metrics["worst_band_loss_db"] = band_loss[worst]

            y = mono
        else:
            metrics["mono_loss_db"] = 0.0
            y = audio.samples[:, 0]

        # Low-end reliance: fraction of total energy small speakers cannot reproduce
        f_m, _, Zy = stft(y, sr, nperseg=4096)
        power = np.abs(Zy) ** 2
        total = float(np.sum(power))
        low = float(np.sum(power[f_m < _SMALL_SPEAKER_CUTOFF_HZ, :]))
        metrics["low_end_reliance"] = round(low / (total + 1e-12), 3)

        return AnalysisResult(module=self.name, metrics=metrics)

    def compare(self, audio: AudioData, reference: AudioData) -> AnalysisResult:
        result = self.analyze(audio)
        ref_result = self.analyze(reference)
        result.metrics["mono_loss_difference"] = round(
            result.metrics["mono_loss_db"] - ref_result.metrics["mono_loss_db"], 1
        )
        result.metrics["reference_mono_loss_db"] = ref_result.metrics["mono_loss_db"]
        return result
