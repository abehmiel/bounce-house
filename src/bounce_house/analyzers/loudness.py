"""Loudness and dynamics analyzer."""

from __future__ import annotations

import json
import shutil
import subprocess

import numpy as np
import pyloudnorm as pyln

from bounce_house.analyzers.base import AnalysisResult, AnalyzerBase
from bounce_house.audio import AudioData


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
            sample_peak_dbfs (float): Maximum absolute sample value in dBFS.
            true_peak_dbtp (float): True peak in dBTP via ffmpeg; falls back to sample peak.
            true_peak_available (bool): Whether ffmpeg-based true peak was measured.
            rms_db (float): RMS level in dB.
            crest_factor_db (float): Peak-to-RMS ratio in dB.
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

        # Sample peak in dBFS
        peak_linear = float(np.max(np.abs(audio.samples)))
        sample_peak_db = 20.0 * np.log10(peak_linear + 1e-10)
        metrics["sample_peak_dbfs"] = round(float(sample_peak_db), 1)

        # True peak via ffmpeg; fall back to sample peak when ffmpeg is unavailable.
        true_peak = self._measure_true_peak(audio)
        metrics["true_peak_dbtp"] = (
            true_peak if true_peak is not None else metrics["sample_peak_dbfs"]
        )
        metrics["true_peak_available"] = true_peak is not None

        # RMS level in dB
        rms_linear = float(np.sqrt(np.mean(audio.samples**2)))
        rms_db = 20.0 * np.log10(rms_linear + 1e-10)
        metrics["rms_db"] = round(float(rms_db), 1)

        # Crest factor: undefined for silence
        if peak_linear < 1e-8:
            metrics["crest_factor_db"] = None
        else:
            crest_db = float(sample_peak_db) - float(rms_db)
            metrics["crest_factor_db"] = round(float(crest_db), 1)

        # PLR (Peak-to-Loudness Ratio): over-compression indicator
        if metrics.get("true_peak_dbtp") is not None and metrics["integrated_lufs"] is not None:
            metrics["plr_db"] = round(
                float(metrics["true_peak_dbtp"]) - float(metrics["integrated_lufs"]), 1
            )

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

    def _measure_true_peak(self, audio: AudioData) -> float | None:
        """Measure true peak via ffmpeg loudnorm filter.

        Returns the input true peak in dBTP, or None if ffmpeg is unavailable,
        the file path is unresolvable, or parsing fails.
        """
        if shutil.which("ffmpeg") is None:
            return None

        try:
            cmd = [
                "ffmpeg",
                "-i",
                str(audio.filepath),
                "-af",
                "loudnorm=print_format=json",
                "-f",
                "null",
                "-",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            stderr = proc.stderr
            # The loudnorm JSON block is written to stderr at the end of the run.
            json_start = stderr.rfind("{")
            json_end = stderr.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(stderr[json_start:json_end])
                raw_tp = data.get("input_tp")
                if raw_tp is None:
                    return None
                tp = float(raw_tp)
                return round(tp, 1)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError, OSError):
            pass
        return None
