"""Tests for audio loading module."""

import numpy as np
from pathlib import Path
from bounce_house.audio import load_audio, AudioData


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


def test_audio_data_is_stereo(tmp_wav, tmp_mono_wav):
    stereo = load_audio(tmp_wav)
    mono = load_audio(tmp_mono_wav)
    assert stereo.is_stereo is True
    assert mono.is_stereo is False
