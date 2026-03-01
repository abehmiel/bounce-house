"""Tests for perceptual analyzer."""

from bounce_house.analyzers.perceptual import PerceptualAnalyzer
from bounce_house.audio import load_audio


class TestPerceptualAnalyzer:
    def setup_method(self):
        self.analyzer = PerceptualAnalyzer()

    def test_name(self):
        assert self.analyzer.name == "perceptual"

    def test_analyze_returns_result(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert result.module == "perceptual"

    def test_has_brightness_estimate(self, tmp_wav):
        """Even without timbral_models, brightness proxy should be present."""
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert "brightness" in result.metrics

    def test_has_warmth_estimate(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert "warmth" in result.metrics

    def test_timbral_available_flag(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert "timbral_models_available" in result.metrics
