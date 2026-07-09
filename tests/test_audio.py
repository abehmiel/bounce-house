"""Tests for audio loading module."""

from pathlib import Path

import numpy as np
import pytest

from bounce_house.audio import AudioData, load_audio


def test_load_stereo_wav(tmp_wav):
    audio = load_audio(tmp_wav)
    assert isinstance(audio, AudioData)
    assert audio.sample_rate == 44100
    assert audio.samples.ndim == 2
    assert audio.samples.shape[1] == 2
    assert audio.filepath == tmp_wav


def test_load_mono_wav(tmp_mono_wav):
    audio = load_audio(tmp_mono_wav)
    # Mono files should be reshaped to (N, 1) for consistent handling
    assert audio.samples.ndim == 2
    assert audio.samples.shape[1] == 1


def test_load_preserves_sample_values(tmp_wav):
    audio = load_audio(tmp_wav)
    # Samples should be float64 in range [-1, 1]
    assert audio.samples.dtype == np.float64
    assert np.max(np.abs(audio.samples)) <= 1.0


def test_load_nonexistent_file_raises():
    import pytest

    with pytest.raises(FileNotFoundError):
        load_audio(Path("/nonexistent/file.wav"))


def test_audio_data_channels(tmp_wav):
    audio = load_audio(tmp_wav)
    assert audio.channels == 2


def test_audio_data_duration(tmp_wav):
    audio = load_audio(tmp_wav)
    assert abs(audio.duration - 1.0) < 0.01


def test_load_corrupt_file_raises_value_error(tmp_path):
    """A file that exists but is not valid audio raises ValueError."""
    import pytest

    corrupt = tmp_path / "corrupt.wav"
    corrupt.write_bytes(b"NOTANAUDIOFILE\x00\x01\x02\x03")
    with pytest.raises(ValueError, match="Cannot read audio file"):
        load_audio(corrupt)


def test_audio_data_is_stereo(tmp_wav, tmp_mono_wav):
    stereo = load_audio(tmp_wav)
    mono = load_audio(tmp_mono_wav)
    assert stereo.is_stereo is True
    assert mono.is_stereo is False


class TestRealisticFixtures:
    def test_mixlike_fixture_analyzes_end_to_end(self, tmp_mixlike_wav):
        from bounce_house.cli import _analyze_file
        from bounce_house.profiles import get_profile

        data = _analyze_file(str(tmp_mixlike_wav), profile=get_profile("master"))
        loudness = next(r for r in data["results"] if r.module == "loudness")
        # Music-shaped signal: sane loudness and dynamics, no crash anywhere
        assert -30.0 < loudness.metrics["integrated_lufs"] < -3.0
        assert 3.0 < loudness.metrics["crest_factor_db"] < 25.0

    def test_pink_fixture_is_deterministic(self, tmp_pink_wav):
        from bounce_house.audio import load_audio
        from tests.conftest import _pink_noise

        audio = load_audio(tmp_pink_wav)
        assert audio.channels == 2
        assert audio.duration == pytest.approx(8.0, abs=0.01)
        assert float(np.max(np.abs(audio.samples))) > 0.5
        # Seeded generator produces identical noise on every invocation
        a = _pink_noise(4096, np.random.default_rng(42))
        b = _pink_noise(4096, np.random.default_rng(42))
        assert np.array_equal(a, b)
