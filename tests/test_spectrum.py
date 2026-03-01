"""Tests for spectral balance analyzer."""

from bounce_house.analyzers.spectrum import SpectrumAnalyzer
from bounce_house.audio import load_audio


class TestSpectrumAnalyzer:
    def setup_method(self):
        self.analyzer = SpectrumAnalyzer()

    def test_name(self):
        assert self.analyzer.name == "spectrum"

    def test_analyze_returns_result(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert result.module == "spectrum"

    def test_has_spectral_descriptors(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        for key in ["centroid_hz", "bandwidth_hz", "rolloff_hz", "flatness"]:
            assert key in result.metrics, f"Missing metric: {key}"

    def test_has_band_energies(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert "bands" in result.metrics
        bands = result.metrics["bands"]
        expected_bands = [
            "sub_bass",
            "bass",
            "low_mid",
            "mid",
            "upper_mid",
            "presence",
            "brilliance",
        ]
        for band in expected_bands:
            assert band in bands, f"Missing band: {band}"

    def test_centroid_is_positive(self, tmp_wav):
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        assert result.metrics["centroid_hz"] > 0

    def test_sine_wave_centroid_near_frequency(self, tmp_wav):
        """A 440Hz sine wave should have centroid near 440Hz."""
        audio = load_audio(tmp_wav)
        result = self.analyzer.analyze(audio)
        # Allow some tolerance since it's a windowed STFT
        assert 400 < result.metrics["centroid_hz"] < 500

    def test_compare_has_band_differences(self, tmp_wav, tmp_reference_wav):
        audio = load_audio(tmp_wav)
        ref = load_audio(tmp_reference_wav)
        result = self.analyzer.compare(audio, ref)
        assert "band_differences" in result.metrics
