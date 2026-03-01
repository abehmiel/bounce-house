"""Tests for tuning analyzer."""

from bounce_house.analyzers.tuning import TuningAnalyzer
from bounce_house.audio import load_audio


class TestTuningAnalyzer:
    def setup_method(self):
        self.analyzer = TuningAnalyzer()

    def test_name(self):
        assert self.analyzer.name == "tuning"

    def test_analyze_returns_result(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert result.module == "tuning"

    def test_has_all_metrics(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        expected = [
            "tuning_deviation_cents",
            "estimated_a_hz",
            "closest_standard",
            "pitch_drift_std_cents",
            "pitch_drift_range_cents",
            "pitch_drift_trend_cents_per_min",
            "chroma_sharpness",
        ]
        for key in expected:
            assert key in result.metrics, f"Missing metric: {key}"

    def test_440_sine_is_near_zero_deviation(self, tmp_wav):
        """A 440Hz sine wave should have near-zero tuning deviation."""
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert abs(result.metrics["tuning_deviation_cents"]) < 10

    def test_440_estimated_a_near_440(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert 435 < result.metrics["estimated_a_hz"] < 445

    def test_440_closest_standard(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert result.metrics["closest_standard"] == "A=440"

    def test_detuned_has_large_deviation(self, tmp_detuned_wav):
        """A 445Hz sine should show significant positive deviation."""
        audio = load_audio(tmp_detuned_wav)
        result = self.analyzer.analyze(audio)
        assert result.metrics["tuning_deviation_cents"] > 10

    def test_detuned_estimated_a_above_440(self, tmp_detuned_wav):
        audio = load_audio(tmp_detuned_wav)
        result = self.analyzer.analyze(audio)
        assert result.metrics["estimated_a_hz"] > 442

    def test_drifting_has_high_range(self, tmp_drifting_wav):
        """A signal drifting from 440 to 450 Hz should show high pitch range."""
        audio = load_audio(tmp_drifting_wav)
        result = self.analyzer.analyze(audio)
        assert result.metrics["pitch_drift_range_cents"] > 5

    def test_stable_has_low_range(self, tmp_wav):
        """A stable 440Hz signal should have low pitch drift range."""
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert result.metrics["pitch_drift_range_cents"] < 20

    def test_chroma_sharpness_is_bounded(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert 0 <= result.metrics["chroma_sharpness"] <= 1.0

    def test_compare_returns_tuning_difference(self, tmp_wav, tmp_detuned_wav):
        audio = load_audio(tmp_wav)
        ref = load_audio(tmp_detuned_wav)
        result = self.analyzer.compare(audio, ref)
        assert "tuning_difference_cents" in result.metrics

    def test_compare_same_file_near_zero_diff(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.compare(audio, audio)
        assert abs(result.metrics["tuning_difference_cents"]) < 5
