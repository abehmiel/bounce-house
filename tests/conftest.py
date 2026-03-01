"""Shared test fixtures — synthetic audio generators."""

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf


@pytest.fixture
def tmp_wav(tmp_path) -> Path:
    """Generate a 1-second stereo 440Hz sine wave at 44100 Hz, 16-bit."""
    sr = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    left = 0.5 * np.sin(2 * np.pi * 440 * t)
    right = 0.3 * np.sin(2 * np.pi * 440 * t + np.pi / 4)  # slight phase offset
    stereo = np.column_stack([left, right])
    path = tmp_path / "test.wav"
    sf.write(str(path), stereo, sr, subtype="PCM_16")
    return path


@pytest.fixture
def tmp_mono_wav(tmp_path) -> Path:
    """Generate a 1-second mono 440Hz sine wave."""
    sr = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    mono = 0.5 * np.sin(2 * np.pi * 440 * t)
    path = tmp_path / "mono.wav"
    sf.write(str(path), mono, sr, subtype="PCM_16")
    return path


@pytest.fixture
def tmp_silent_wav(tmp_path) -> Path:
    """Generate a 1-second stereo silent file."""
    sr = 44100
    silence = np.zeros((sr, 2))
    path = tmp_path / "silent.wav"
    sf.write(str(path), silence, sr, subtype="PCM_16")
    return path


@pytest.fixture
def tmp_wav_dir(tmp_path) -> Path:
    """Generate a directory with 3 stereo WAV files for batch testing."""
    sr = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    for i, name in enumerate(["track_a.wav", "track_b.wav", "track_c.wav"]):
        freq = 440 * (i + 1)
        left = 0.5 * np.sin(2 * np.pi * freq * t)
        right = 0.3 * np.sin(2 * np.pi * freq * t + np.pi / 4)
        stereo = np.column_stack([left, right])
        sf.write(str(tmp_path / name), stereo, sr, subtype="PCM_16")
    return tmp_path


@pytest.fixture
def tmp_reference_wav(tmp_path) -> Path:
    """Generate a 1-second stereo reference with different spectral character."""
    sr = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Richer harmonic content than the test signal
    left = 0.4 * np.sin(2 * np.pi * 440 * t) + 0.2 * np.sin(2 * np.pi * 880 * t)
    right = 0.4 * np.sin(2 * np.pi * 440 * t) + 0.2 * np.sin(2 * np.pi * 880 * t)
    stereo = np.column_stack([left, right])
    path = tmp_path / "reference.wav"
    sf.write(str(path), stereo, sr, subtype="PCM_16")
    return path
