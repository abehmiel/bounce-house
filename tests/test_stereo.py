"""Tests for stereo imaging and phase analyzer."""

import numpy as np
import pytest
import soundfile as sf

from bounce_house.analyzers.stereo import StereoAnalyzer
from bounce_house.audio import load_audio


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
            "phase_correlation",
            "low_block_correlation",
            "mid_rms_db",
            "side_rms_db",
            "ms_ratio_db",
            "stereo_width",
            "balance_db",
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

    def test_silent_file_phase_correlation_not_nan(self, tmp_silent_wav):
        """Silent stereo file must not produce NaN phase_correlation; it's unknown (None)."""
        audio = load_audio(tmp_silent_wav)
        result = self.analyzer.analyze(audio)
        corr = result.metrics["phase_correlation"]
        assert corr is None

    def test_silent_file_low_block_correlation_not_zero(self, tmp_silent_wav):
        """Silent file: correlation is undefined, so low_block_correlation is None."""
        audio = load_audio(tmp_silent_wav)
        result = self.analyzer.analyze(audio)
        assert result.metrics["low_block_correlation"] is None

    def test_silent_file_no_fail_assessments(self, tmp_silent_wav):
        """Silent file must not trigger false FAIL on phase/correlation metrics.

        stereo_width == 0.0 for a silent file is a genuine (not false) fail under
        the stereo_width range rule — a silent file truly has no stereo width —
        so it's excluded here; this test only guards the phase-correlation-family
        metrics that previously produced spurious fails on degenerate silent input.
        """
        from bounce_house.rules import evaluate_rules

        audio = load_audio(tmp_silent_wav)
        result = self.analyzer.analyze(audio)
        assessments = evaluate_rules(result)
        fails = [a for a in assessments if a.status == "fail" and a.metric != "stereo_width"]
        assert len(fails) == 0

    def test_frequency_width_inverted_channels_negative(self, tmp_path):
        """Phase-inverted channels should show negative per-band correlation."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False)
        signal = 0.5 * np.sin(2 * np.pi * 440 * t)
        stereo = np.column_stack([signal, -signal])
        path = tmp_path / "inverted_fb.wav"
        sf.write(str(path), stereo, sr, subtype="PCM_16")
        audio = load_audio(path)
        result = self.analyzer.analyze(audio)
        fw = result.metrics["frequency_width"]
        # 440 Hz falls in low_mid band (120-500 Hz) — should detect phase inversion
        assert fw["low_mid"] < -0.9

    def test_compare_returns_result(self, tmp_wav, tmp_reference_wav):
        audio = load_audio(tmp_wav)
        ref = load_audio(tmp_reference_wav)
        result = self.analyzer.compare(audio, ref)
        assert "width_difference" in result.metrics

    def test_compare_hard_panned_target_width_difference_is_none(self, tmp_path, tmp_reference_wav):
        """Target with undefined stereo_width (hard-panned) must not crash compare()."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False)
        tone = 0.5 * np.sin(2 * np.pi * 440 * t)
        stereo = np.column_stack([tone, np.zeros_like(tone)])
        path = tmp_path / "hard_panned.wav"
        sf.write(str(path), stereo, sr, subtype="FLOAT")

        audio = load_audio(path)
        ref = load_audio(tmp_reference_wav)
        result = self.analyzer.compare(audio, ref)

        assert result.metrics["stereo_width"] is None
        assert result.metrics["width_difference"] is None

    def test_compare_hard_panned_reference_width_difference_is_none(self, tmp_wav, tmp_path):
        """Reference with undefined stereo_width (hard-panned) must not crash compare()."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False)
        tone = 0.5 * np.sin(2 * np.pi * 440 * t)
        stereo = np.column_stack([tone, np.zeros_like(tone)])
        path = tmp_path / "hard_panned_ref.wav"
        sf.write(str(path), stereo, sr, subtype="FLOAT")

        audio = load_audio(tmp_wav)
        ref = load_audio(path)
        result = self.analyzer.compare(audio, ref)

        assert result.metrics["width_difference"] is None
        assert result.metrics["reference_width"] is None
        assert result.metrics["reference_correlation"] is None


class TestBalanceCompensatedWidth:
    def test_panned_mono_source_has_zero_width(self, tmp_path):
        import soundfile as sf

        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False)
        tone = 0.5 * np.sin(2 * np.pi * 440 * t)
        # Same waveform, unequal levels: panned, but zero decorrelation
        stereo = np.column_stack([tone, 0.3 * tone])
        sf.write(str(tmp_path / "panned.wav"), stereo, sr, subtype="FLOAT")
        result = StereoAnalyzer().analyze(load_audio(tmp_path / "panned.wav"))
        assert result.metrics["stereo_width"] == pytest.approx(0.0, abs=0.02)

    def test_decorrelated_noise_is_wide(self, tmp_pink_wav):
        result = StereoAnalyzer().analyze(load_audio(tmp_pink_wav))
        # Independent L/R noise: near-equal mid and side energy → width ≈ 0.5
        assert result.metrics["stereo_width"] == pytest.approx(0.5, abs=0.08)

    def test_hard_panned_single_channel_width_is_none(self, tmp_path):
        import soundfile as sf

        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False)
        tone = 0.5 * np.sin(2 * np.pi * 440 * t)
        sf.write(
            str(tmp_path / "hard.wav"),
            np.column_stack([tone, np.zeros_like(tone)]),
            sr,
            subtype="FLOAT",
        )
        result = StereoAnalyzer().analyze(load_audio(tmp_path / "hard.wav"))
        assert result.metrics["stereo_width"] is None  # pure pan: width undefined


class TestSilenceIsUnknown:
    def test_silent_file_correlation_is_none(self, tmp_silent_wav):
        result = StereoAnalyzer().analyze(load_audio(tmp_silent_wav))
        assert result.metrics["phase_correlation"] is None
        assert result.metrics["low_block_correlation"] is None

    def test_silent_band_correlation_is_none(self, tmp_wav):
        # 440 Hz sine has no energy in the air band (8-20 kHz)
        result = StereoAnalyzer().analyze(load_audio(tmp_wav))
        assert result.metrics["frequency_width"]["air"] is None

    def test_silent_file_not_assessed_for_correlation(self, tmp_silent_wav):
        from bounce_house.rules import evaluate_rules

        result = StereoAnalyzer().analyze(load_audio(tmp_silent_wav))
        assessed = {a.metric for a in evaluate_rules(result)}
        assert "phase_correlation" not in assessed
