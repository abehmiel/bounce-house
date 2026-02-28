"""Tests for stereo imaging and phase analyzer."""

import numpy as np
import soundfile as sf
from pathlib import Path

from bounce_house.audio import load_audio, AudioData
from bounce_house.analyzers.stereo import StereoAnalyzer


class TestStereoAnalyzer:
    def setup_method(self):
        self.analyzer = StereoAnalyzer()

    def test_name(self):
        assert self.analyzer.name == "stereo"

    def test_analyze_returns_result(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert result.module == "stereo"

    def test_has_expected_metrics(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        expected = {
            "phase_correlation", "min_block_correlation",
            "mid_rms_db", "side_rms_db", "ms_ratio_db",
            "stereo_width", "balance_db",
        }
        assert expected.issubset(set(result.metrics.keys()))

    def test_has_frequency_stereo_width(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert "frequency_width" in result.metrics

    def test_mono_identical_channels_correlation_is_1(self, tmp_path):
        """Identical L and R should give correlation of +1."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False)
        signal = 0.5 * np.sin(2 * np.pi * 440 * t)
        stereo = np.column_stack([signal, signal])
        path = tmp_path / "identical.wav"
        sf.write(str(path), stereo, sr, subtype="PCM_16")
        audio = load_audio(path)
        result = self.analyzer.analyze(audio)
        assert result.metrics["phase_correlation"] > 0.99

    def test_inverted_phase_correlation_is_negative(self, tmp_path):
        """L and -R should give correlation of -1."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False)
        signal = 0.5 * np.sin(2 * np.pi * 440 * t)
        stereo = np.column_stack([signal, -signal])
        path = tmp_path / "inverted.wav"
        sf.write(str(path), stereo, sr, subtype="PCM_16")
        audio = load_audio(path)
        result = self.analyzer.analyze(audio)
        assert result.metrics["phase_correlation"] < -0.99

    def test_stereo_width_zero_for_mono(self, tmp_path):
        """Identical channels should have width near 0."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False)
        signal = 0.5 * np.sin(2 * np.pi * 440 * t)
        stereo = np.column_stack([signal, signal])
        path = tmp_path / "mono_stereo.wav"
        sf.write(str(path), stereo, sr, subtype="PCM_16")
        audio = load_audio(path)
        result = self.analyzer.analyze(audio)
        assert result.metrics["stereo_width"] < 0.01

    def test_mono_file_skips_analysis(self, tmp_mono_wav):
        audio = load_audio(tmp_mono_wav)
        result = self.analyzer.analyze(audio)
        assert result.metrics.get("mono_file") is True

    def test_compare_returns_result(self, tmp_wav, tmp_reference_wav):
        audio = load_audio(tmp_wav)
        ref = load_audio(tmp_reference_wav)
        result = self.analyzer.compare(audio, ref)
        assert "width_difference" in result.metrics
