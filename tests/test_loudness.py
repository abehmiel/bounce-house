"""Tests for loudness and dynamics analyzer."""

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
