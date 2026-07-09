"""Tests for spectral balance analyzer."""

import pytest

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


class TestRelativeBands:
    def test_bands_invariant_to_gain(self, tmp_pink_wav, tmp_path):
        import soundfile as sf

        audio = load_audio(tmp_pink_wav)
        quiet = audio.samples * 0.25  # -12 dB
        sf.write(str(tmp_path / "quiet.wav"), quiet, audio.sample_rate, subtype="FLOAT")
        loud_bands = SpectrumAnalyzer().analyze(audio).metrics["bands"]
        quiet_audio = load_audio(tmp_path / "quiet.wav")
        quiet_bands = SpectrumAnalyzer().analyze(quiet_audio).metrics["bands"]
        for band in loud_bands:
            assert loud_bands[band] == pytest.approx(quiet_bands[band], abs=0.3)

    def test_compare_band_diffs_ignore_level(self, tmp_pink_wav, tmp_path):
        import soundfile as sf

        audio = load_audio(tmp_pink_wav)
        quiet_path = tmp_path / "quiet.wav"
        sf.write(str(quiet_path), audio.samples * 0.25, audio.sample_rate, subtype="FLOAT")
        result = SpectrumAnalyzer().compare(audio, load_audio(quiet_path))
        # Same spectrum at different levels: every band difference ≈ 0
        for band, diff in result.metrics["band_differences"].items():
            assert abs(diff) < 0.5, f"{band} shows spurious {diff} dB from pure level change"


class TestBandRatios:
    def test_pink_noise_ratios_match_1_over_f_theory(self, tmp_pink_wav):
        result = SpectrumAnalyzer().analyze(load_audio(tmp_pink_wav))
        r = result.metrics["band_ratios"]
        # Pink noise density theory: ln(hi/lo)/(hi-lo) per band (see plan Task 5)
        assert r["low_mid_minus_mid"] == pytest.approx(4.8, abs=2.0)
        assert r["bass_minus_mid"] == pytest.approx(9.1, abs=2.5)
        assert r["upper_mid_minus_mid"] == pytest.approx(-4.3, abs=2.0)

    def test_ratios_invariant_to_gain(self, tmp_pink_wav, tmp_path):
        import soundfile as sf

        audio = load_audio(tmp_pink_wav)
        quiet_path = tmp_path / "quiet.wav"
        sf.write(str(quiet_path), audio.samples * 0.25, audio.sample_rate, subtype="FLOAT")
        loud = SpectrumAnalyzer().analyze(audio).metrics["band_ratios"]
        quiet = SpectrumAnalyzer().analyze(load_audio(quiet_path)).metrics["band_ratios"]
        for key in loud:
            assert loud[key] == pytest.approx(quiet[key], abs=0.3)
