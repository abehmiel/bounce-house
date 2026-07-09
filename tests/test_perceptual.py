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


class TestTimbralNamespacing:
    def test_proxy_stays_authoritative_when_timbral_installed(self, tmp_wav, monkeypatch):
        import bounce_house.analyzers.perceptual as perceptual_mod

        class FakeTimbral:
            @staticmethod
            def timbral_brightness(path):
                return 62.0  # timbral_models uses ~0-100 scales

            @staticmethod
            def timbral_warmth(path):
                return 48.0

            @staticmethod
            def timbral_hardness(path):
                return 55.0

            @staticmethod
            def timbral_roughness(path):
                return 12.0

        monkeypatch.setattr(perceptual_mod, "_HAS_TIMBRAL", True)
        monkeypatch.setattr(perceptual_mod, "timbral_models", FakeTimbral, raising=False)

        result = perceptual_mod.PerceptualAnalyzer().analyze(load_audio(tmp_wav))
        # Diagnostics depend on brightness/warmth being 0-1 proxy ratios — always
        assert 0.0 <= result.metrics["brightness"] <= 1.0
        assert 0.0 <= result.metrics["warmth"] <= 1.0
        # Timbral scores are exposed under their own keys
        assert result.metrics["timbral_brightness"] == 62.0
        assert result.metrics["timbral_warmth"] == 48.0
        assert result.metrics["hardness"] == 55.0
        assert result.metrics["roughness"] == 12.0
