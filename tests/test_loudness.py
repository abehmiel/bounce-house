"""Tests for loudness and dynamics analyzer."""

import numpy as np
import soundfile as sf
from pathlib import Path

from bounce_house.audio import load_audio
from bounce_house.analyzers.loudness import LoudnessAnalyzer


class TestLoudnessAnalyzer:
    def setup_method(self):
        self.analyzer = LoudnessAnalyzer()

    def test_name(self):
        assert self.analyzer.name == "loudness"

    def test_analyze_returns_result(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert result.module == "loudness"

    def test_analyze_has_expected_metrics(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        expected_keys = {
            "integrated_lufs",
            "loudness_range_lu",
            "sample_peak_dbfs",
            "true_peak_dbtp",
            "crest_factor_db",
            "rms_db",
        }
        assert expected_keys.issubset(set(result.metrics.keys()))

    def test_integrated_lufs_is_negative(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert result.metrics["integrated_lufs"] < 0

    def test_sample_peak_within_range(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        # For a 0.5 amplitude sine, peak should be around -6 dBFS
        assert -10 < result.metrics["sample_peak_dbfs"] < 0

    def test_crest_factor_positive(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert result.metrics["crest_factor_db"] > 0

    def test_silent_file_handling(self, tmp_silent_wav):
        audio = load_audio(tmp_silent_wav)
        result = self.analyzer.analyze(audio)
        # Should not crash on silence, LUFS should be very negative
        assert result.metrics["integrated_lufs"] < -60

    def test_compare_returns_result(self, tmp_wav, tmp_reference_wav):
        audio = load_audio(tmp_wav)
        ref = load_audio(tmp_reference_wav)
        result = self.analyzer.compare(audio, ref)
        assert result.module == "loudness"
        assert "lufs_difference" in result.metrics

    def test_compare_shows_difference(self, tmp_wav, tmp_reference_wav):
        audio = load_audio(tmp_wav)
        ref = load_audio(tmp_reference_wav)
        result = self.analyzer.compare(audio, ref)
        # Difference should be a real number
        assert isinstance(result.metrics["lufs_difference"], float)
