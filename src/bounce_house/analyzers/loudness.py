"""Loudness and dynamics analyzer."""

from __future__ import annotations

import numpy as np
import pyloudnorm as pyln
from scipy.signal import resample_poly

from bounce_house.analyzers.base import AnalysisResult, AnalyzerBase
from bounce_house.audio import AudioData


def _true_peak_dbtp(samples: np.ndarray, sample_rate: int) -> float:
    """True peak per ITU-R BS.1770-4: oversample and take the max magnitude.

    4x oversampling for common rates; 2x is sufficient at >=96 kHz.
    resample_poly's Kaiser-windowed polyphase FIR approximates the Annex 2
    interpolation filter within its stated tolerances.
    """
    factor = 2 if sample_rate >= 96000 else 4
    peak = 0.0
    for ch in range(samples.shape[1]):
        upsampled = resample_poly(samples[:, ch], factor, 1)
        peak = max(peak, float(np.max(np.abs(upsampled))))
    return float(20.0 * np.log10(peak + 1e-10))


def _dr_score(samples: np.ndarray, sample_rate: int) -> float | None:
    """TT/Pleasurize-style DR: second-highest block peak vs loudest-20% block RMS.

    Uses 3 s blocks and the DR convention's doubled-energy RMS
    (sqrt(2*mean(x^2))). Returns None for audio shorter than one block.
    """
    block = 3 * sample_rate
    n_blocks = samples.shape[0] // block
    if n_blocks < 1:
        return None

    channel_dr = []
    for ch in range(samples.shape[1]):
        x = samples[: n_blocks * block, ch].reshape(n_blocks, block)
        block_rms = np.sqrt(2.0 * np.mean(x**2, axis=1))
        block_peaks = np.sort(np.max(np.abs(x), axis=1))
        p2 = block_peaks[-2] if n_blocks >= 2 else block_peaks[-1]
        k = max(1, int(round(0.2 * n_blocks)))
        loudest = np.sort(block_rms)[-k:]
        rms20 = float(np.sqrt(np.mean(loudest**2)))
        if rms20 > 1e-10 and p2 > 1e-10:
            channel_dr.append(20.0 * np.log10(p2 / rms20))

    return round(float(np.mean(channel_dr)), 1) if channel_dr else None


class LoudnessAnalyzer(AnalyzerBase):
    """Measure integrated LUFS, LRA, sample peak, true peak, RMS, and crest factor."""

    @property
    def name(self) -> str:
        return "loudness"

    def analyze(self, audio: AudioData) -> AnalysisResult:
        """Analyze loudness and dynamics of a single audio file.

        Returns an AnalysisResult with the following metrics:
            integrated_lufs (float): Integrated loudness per ITU-R BS.1770-4.
            loudness_range_lu (float | None): Loudness range in LU, or None if unavailable.
            sample_peak_dbfs (float): Peak of the delivered waveform in dBFS,
                measured before DC removal (DC consumes real headroom).
            true_peak_dbtp (float): True peak in dBTP via native polyphase oversampling.
            rms_db (float): RMS level in dB.
            crest_factor_db (float): Per-channel peak-to-RMS ratio in dB, averaged over
                active channels.
            dc_offset_db (float): DC offset removed at load, in dBFS (informational).
            dr_score (float | None): TT/Pleasurize-style dynamic range score, or None
                for audio shorter than one 3 s block.
        """
        metrics: dict = {}

        # pyloudnorm expects (num_samples,) for mono or (num_samples, num_channels) for multi.
        # AudioData always stores (num_samples, num_channels), so pass as-is for stereo;
        # squeeze to 1-D for mono to satisfy pyloudnorm's channel-count expectations.
        if audio.channels >= 2:  # noqa: SIM108
            samples_for_lufs = audio.samples
        else:
            samples_for_lufs = audio.samples[:, 0]

        meter = pyln.Meter(audio.sample_rate)

        try:
            integrated = meter.integrated_loudness(samples_for_lufs)
            metrics["integrated_lufs"] = round(float(integrated), 1)
        except ValueError:
            # Shorter than the 400 ms BS.1770 gating block — LUFS undefined
            metrics["integrated_lufs"] = None

        try:
            lra = meter.loudness_range(samples_for_lufs)
            metrics["loudness_range_lu"] = round(float(lra), 1)
        except Exception:
            metrics["loudness_range_lu"] = None

        # Sample peak in dBFS — measured on the delivered waveform (DC included),
        # since a DC offset consumes real headroom. AudioData.raw_sample_peak holds
        # the pre-DC-removal peak; hand-built AudioData (tests) has no raw peak, so
        # use the DC-free sample peak there.
        peak_linear = float(np.max(np.abs(audio.samples)))
        headroom_peak = audio.raw_sample_peak if audio.raw_sample_peak is not None else peak_linear
        sample_peak_db = 20.0 * np.log10(headroom_peak + 1e-10)
        metrics["sample_peak_dbfs"] = round(float(sample_peak_db), 1)

        # True peak: native BS.1770-4-style oversampled measurement, on the same
        # pre-DC-removal waveform as sample_peak_dbfs (DC consumes real headroom).
        headroom_samples = audio.raw_samples if audio.raw_samples is not None else audio.samples
        metrics["true_peak_dbtp"] = round(_true_peak_dbtp(headroom_samples, audio.sample_rate), 1)

        # RMS level in dB
        rms_linear = float(np.sqrt(np.mean(audio.samples**2)))
        rms_db = 20.0 * np.log10(rms_linear + 1e-10)
        metrics["rms_db"] = round(float(rms_db), 1)

        # DC offset removed at load — reported so the user knows their converter/plugin adds one
        if audio.dc_offset is not None:
            dc_db = 20.0 * np.log10(float(np.max(np.abs(audio.dc_offset))) + 1e-10)
            metrics["dc_offset_db"] = round(float(dc_db), 1)

        # Crest factor per channel (peak vs RMS of the SAME channel), averaged over
        # active channels — pooling channels understates RMS for panned content and
        # inflates crest by up to 3 dB. Undefined for silence.
        per_channel_ms = np.mean(audio.samples**2, axis=0)
        active = per_channel_ms > 1e-16
        if peak_linear < 1e-8 or not np.any(active):
            metrics["crest_factor_db"] = None
        else:
            ch_peaks = np.max(np.abs(audio.samples), axis=0)[active]
            ch_rms = np.sqrt(per_channel_ms[active])
            crest_db = float(np.mean(20.0 * np.log10((ch_peaks + 1e-10) / (ch_rms + 1e-10))))
            metrics["crest_factor_db"] = round(crest_db, 1)

        # PLR (Peak-to-Loudness Ratio): over-compression indicator
        if metrics.get("true_peak_dbtp") is not None and metrics["integrated_lufs"] is not None:
            metrics["plr_db"] = round(
                float(metrics["true_peak_dbtp"]) - float(metrics["integrated_lufs"]), 1
            )

        metrics["dr_score"] = _dr_score(audio.samples, audio.sample_rate)

        return AnalysisResult(module=self.name, metrics=metrics)

    def compare(self, audio: AudioData, reference: AudioData) -> AnalysisResult:
        """Analyze audio relative to a reference file.

        Extends the analysis result for `audio` with difference metrics:
            lufs_difference (float): Integrated LUFS of audio minus that of reference.
            reference_lufs (float): Integrated LUFS of the reference file.
            lra_difference (float): LRA difference if both values are available.
            peak_difference (float): Sample peak difference in dB.
        """
        result = self.analyze(audio)
        ref_result = self.analyze(reference)

        if (
            result.metrics["integrated_lufs"] is not None
            and ref_result.metrics["integrated_lufs"] is not None
        ):
            lufs_diff = result.metrics["integrated_lufs"] - ref_result.metrics["integrated_lufs"]
            result.metrics["lufs_difference"] = round(float(lufs_diff), 1)
        result.metrics["reference_lufs"] = ref_result.metrics["integrated_lufs"]

        if (
            ref_result.metrics["loudness_range_lu"] is not None
            and result.metrics["loudness_range_lu"] is not None
        ):
            lra_diff = result.metrics["loudness_range_lu"] - ref_result.metrics["loudness_range_lu"]
            result.metrics["lra_difference"] = round(float(lra_diff), 1)

        peak_diff = result.metrics["sample_peak_dbfs"] - ref_result.metrics["sample_peak_dbfs"]
        result.metrics["peak_difference"] = round(float(peak_diff), 1)

        return result
