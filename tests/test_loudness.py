"""Tests for loudness and dynamics analyzer."""

import numpy as np
import pytest

from bounce_house.analyzers.loudness import LoudnessAnalyzer
from bounce_house.audio import load_audio


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

    def test_silent_file_crest_factor_is_none(self, tmp_silent_wav):
        """Crest factor is undefined for silence — must be None, not 0.0."""
        audio = load_audio(tmp_silent_wav)
        result = self.analyzer.analyze(audio)
        assert result.metrics["crest_factor_db"] is None

    def test_true_peak_missing_key_returns_none(self, tmp_wav, monkeypatch):
        """If ffmpeg JSON lacks input_tp, _measure_true_peak returns None."""
        import json as json_mod
        import subprocess

        fake_json = json_mod.dumps({"input_i": "-14.0", "input_lra": "6.0"})
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=f"header\n{fake_json}\n"
        )
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_result)
        monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/ffmpeg")

        audio = load_audio(tmp_wav)
        result = self.analyzer._measure_true_peak(audio)
        assert result is None

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


def test_plr_computed(tmp_wav):
    """PLR (Peak-to-Loudness Ratio) should be true_peak - integrated_lufs."""
    from bounce_house.analyzers.loudness import LoudnessAnalyzer
    from bounce_house.audio import load_audio

    audio = load_audio(tmp_wav)
    analyzer = LoudnessAnalyzer()
    result = analyzer.analyze(audio)

    assert "plr_db" in result.metrics
    expected = result.metrics["true_peak_dbtp"] - result.metrics["integrated_lufs"]
    assert abs(result.metrics["plr_db"] - round(expected, 1)) < 0.01


class TestShortFile:
    def test_short_file_does_not_crash(self, tmp_short_wav):
        audio = load_audio(tmp_short_wav)
        result = LoudnessAnalyzer().analyze(audio)
        assert result.metrics["integrated_lufs"] is None
        assert result.metrics["loudness_range_lu"] is None
        # Peak/RMS/crest don't need 400 ms of audio and must still be measured
        assert result.metrics["sample_peak_dbfs"] is not None
        assert result.metrics["crest_factor_db"] is not None
        # PLR requires integrated LUFS, so it must be absent (not a TypeError)
        assert "plr_db" not in result.metrics

    def test_short_file_cli_analyze_does_not_crash(self, tmp_short_wav):
        from bounce_house.cli import main

        # Exit code may be 0/1/2 depending on assessments; anything but a traceback is fine
        assert main(["analyze", str(tmp_short_wav)]) in (0, 1, 2)

    def test_short_file_compare_does_not_crash(self, tmp_short_wav, tmp_wav):
        audio = load_audio(tmp_short_wav)
        reference = load_audio(tmp_wav)
        result = LoudnessAnalyzer().compare(audio, reference)
        assert result.metrics["integrated_lufs"] is None
        assert "lufs_difference" not in result.metrics


class TestDcOffsetMetric:
    def test_dc_offset_metric_and_clean_rms(self, tmp_path):
        import soundfile as sf

        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False)
        signal = 0.3 + 0.1 * np.sin(2 * np.pi * 440 * t)
        sf.write(str(tmp_path / "dc.wav"), np.column_stack([signal, signal]), sr, subtype="FLOAT")
        result = LoudnessAnalyzer().analyze(load_audio(tmp_path / "dc.wav"))
        # DC no longer inflates RMS: 0.1 sine → RMS 0.0707 → -23.0 dB
        assert result.metrics["rms_db"] == pytest.approx(-23.0, abs=0.5)
        # The removed offset is reported: 20*log10(0.3) ≈ -10.5 dBFS
        assert result.metrics["dc_offset_db"] == pytest.approx(-10.5, abs=0.3)

    def test_clean_file_reports_negligible_dc(self, tmp_wav):
        result = LoudnessAnalyzer().analyze(load_audio(tmp_wav))
        assert result.metrics["dc_offset_db"] < -60.0


class TestPerChannelCrest:
    def test_hard_panned_sine_crest_is_3db(self, tmp_path):
        import soundfile as sf

        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False)
        left = 0.5 * np.sin(2 * np.pi * 440 * t)
        right = np.zeros_like(left)  # hard-panned: silent right channel
        sf.write(str(tmp_path / "panned.wav"), np.column_stack([left, right]), sr, subtype="FLOAT")
        result = LoudnessAnalyzer().analyze(load_audio(tmp_path / "panned.wav"))
        # A sine's true crest factor is 20*log10(sqrt(2)) = 3.01 dB; the silent
        # channel must not dilute it (pooled math reported 6.0 dB here)
        assert result.metrics["crest_factor_db"] == pytest.approx(3.0, abs=0.2)

    def test_centered_sine_crest_unchanged(self, tmp_path):
        import soundfile as sf

        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False)
        sine = 0.5 * np.sin(2 * np.pi * 440 * t)
        sf.write(str(tmp_path / "center.wav"), np.column_stack([sine, sine]), sr, subtype="FLOAT")
        result = LoudnessAnalyzer().analyze(load_audio(tmp_path / "center.wav"))
        assert result.metrics["crest_factor_db"] == pytest.approx(3.0, abs=0.2)
