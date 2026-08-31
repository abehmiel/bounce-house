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
def tmp_sparse_constant_wav(tmp_path) -> Path:
    """60-second sparse kick at an exactly constant 120 BPM, quiet and noisy.

    Windowed tempo estimation jitters between neighbouring tempogram bins on
    material this sparse, so this fixture exists to prove the analyzer does not
    publish a timeline of tempo changes for audio whose tempo never changes.
    """
    sr = 44100
    rng = np.random.default_rng(6)
    dur = 60.0
    n = int(sr * dur)
    y = np.zeros(n)
    for start in np.arange(0, dur, 0.5):
        idx = int(start * sr)
        seg = np.arange(min(int(0.15 * sr), n - idx))
        y[idx : idx + len(seg)] += np.sin(2 * np.pi * 55 * seg / sr) * np.exp(-seg / (0.01 * sr))
    y += 0.35 * rng.standard_normal(n)
    y = y / np.max(np.abs(y)) * 0.89
    path = tmp_path / "sparse_constant.wav"
    sf.write(str(path), np.column_stack([y, y]), sr, subtype="PCM_16")
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


@pytest.fixture
def tmp_detuned_wav(tmp_path) -> Path:
    """Generate a 2-second stereo sine wave tuned to A=445 Hz (~20 cents sharp)."""
    sr = 44100
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    left = 0.5 * np.sin(2 * np.pi * 445 * t)
    right = 0.3 * np.sin(2 * np.pi * 445 * t + np.pi / 4)
    stereo = np.column_stack([left, right])
    path = tmp_path / "detuned.wav"
    sf.write(str(path), stereo, sr, subtype="PCM_16")
    return path


@pytest.fixture
def tmp_drifting_wav(tmp_path) -> Path:
    """Generate a 4-second stereo sine that drifts from 440 to 450 Hz."""
    sr = 44100
    duration = 4.0
    n = int(sr * duration)
    freq = np.linspace(440, 450, n)
    phase = 2 * np.pi * np.cumsum(freq) / sr
    left = 0.5 * np.sin(phase)
    right = 0.3 * np.sin(phase + np.pi / 4)
    stereo = np.column_stack([left, right])
    path = tmp_path / "drifting.wav"
    sf.write(str(path), stereo, sr, subtype="PCM_16")
    return path


@pytest.fixture
def tmp_short_wav(tmp_path) -> Path:
    """Generate a 0.2-second stereo file — shorter than pyloudnorm's 400 ms gating block."""
    sr = 44100
    duration = 0.2
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    left = 0.5 * np.sin(2 * np.pi * 440 * t)
    right = 0.3 * np.sin(2 * np.pi * 440 * t + np.pi / 4)
    stereo = np.column_stack([left, right])
    path = tmp_path / "short.wav"
    sf.write(str(path), stereo, sr, subtype="PCM_16")
    return path


def _pink_noise(n: int, rng: np.random.Generator) -> np.ndarray:
    """Pink (1/f power density) noise via spectral shaping, peak-normalized to 1.0."""
    white = rng.standard_normal(n)
    spec = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(n, d=1.0 / 44100)
    freqs[0] = freqs[1]  # avoid divide-by-zero at DC
    spec /= np.sqrt(freqs)
    pink = np.fft.irfft(spec, n)
    return pink / np.max(np.abs(pink))


@pytest.fixture
def tmp_pink_wav(tmp_path) -> Path:
    """8-second stereo pink noise at ~-3 dBFS peak — known 1/f density for spectral theory tests."""
    sr = 44100
    rng = np.random.default_rng(42)
    left = 0.7 * _pink_noise(sr * 8, rng)
    right = 0.7 * _pink_noise(sr * 8, rng)  # independent channels
    stereo = np.column_stack([left, right])
    path = tmp_path / "pink.wav"
    sf.write(str(path), stereo, sr, subtype="PCM_16")
    return path


@pytest.fixture
def tmp_mixlike_wav(tmp_path) -> Path:
    """8-second deterministic pseudo-music: kick + bass + chord stack + hat bursts."""
    sr = 44100
    rng = np.random.default_rng(42)
    n = sr * 8
    t = np.arange(n) / sr

    kick = np.zeros(n)
    for start in np.arange(0, 8, 0.5):
        idx = int(start * sr)
        seg = np.arange(min(int(0.15 * sr), n - idx))
        kick[idx : idx + len(seg)] += np.sin(2 * np.pi * 55 * seg / sr) * np.exp(-seg / (0.03 * sr))

    bass = 0.3 * np.sin(2 * np.pi * 110 * t)

    chord = np.zeros(n)
    for f0 in (220.0, 277.18, 329.63):  # A major triad
        for h in range(1, 6):
            chord += np.sin(2 * np.pi * f0 * h * t + rng.uniform(0, 2 * np.pi)) / h
    chord *= 0.08

    # lead melody in the mid band (500-2000 Hz) so the mix is not hollow there
    lead = 0.15 * np.sin(2 * np.pi * 660 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 2 * t))

    hats = np.zeros(n)
    noise = rng.standard_normal(n)
    for start in np.arange(0.125, 8, 0.25):
        idx = int(start * sr)
        seg = np.arange(min(int(0.05 * sr), n - idx))
        hats[idx : idx + len(seg)] += noise[idx : idx + len(seg)] * np.exp(-seg / (0.01 * sr))
    hats = 0.3 * np.diff(hats, prepend=0.0)  # differentiator ≈ crude high-pass

    left = 0.8 * kick + bass + chord + lead + hats
    right = 0.8 * kick + bass + 0.9 * chord + lead + 1.1 * hats
    stereo = np.column_stack([left, right])
    stereo *= 0.89 / np.max(np.abs(stereo))  # peak ≈ -1 dBFS
    path = tmp_path / "mixlike.wav"
    sf.write(str(path), stereo, sr, subtype="PCM_16")
    return path


def _rhythmic(dur: float, bpm: float, swing: float = 0.0, seed: int = 42) -> np.ndarray:
    """Deterministic pseudo-music with a known tempo: kick on beats, hats on eighths.

    swing=0.0 places offbeat hats at the exact midpoint; swing=0.33 approximates
    triplet swing. Returns a stereo array peak-normalized to about -1 dBFS.
    """
    sr = 44100
    rng = np.random.default_rng(seed)
    n = int(sr * dur)
    t = np.arange(n) / sr
    beat = 60.0 / bpm

    kick = np.zeros(n)
    for start in np.arange(0, dur, beat):
        idx = int(start * sr)
        seg = np.arange(min(int(0.15 * sr), n - idx))
        kick[idx : idx + len(seg)] += np.sin(2 * np.pi * 55 * seg / sr) * np.exp(-seg / (0.03 * sr))

    bass = 0.3 * np.sin(2 * np.pi * 110 * t)

    chord = np.zeros(n)
    for f0 in (220.0, 277.18, 329.63):
        for h in range(1, 6):
            chord += np.sin(2 * np.pi * f0 * h * t + rng.uniform(0, 2 * np.pi)) / h
    chord *= 0.08

    lead = 0.15 * np.sin(2 * np.pi * 660 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 2 * t))

    hats = np.zeros(n)
    noise = rng.standard_normal(n)
    offbeat = beat / 2 * (1 + swing)
    for k in range(int(dur / beat) + 1):
        for pos in (k * beat, k * beat + offbeat):
            if pos >= dur:
                continue
            idx = int(pos * sr)
            seg = np.arange(min(int(0.05 * sr), n - idx))
            hats[idx : idx + len(seg)] += noise[idx : idx + len(seg)] * np.exp(-seg / (0.01 * sr))
    hats = 0.3 * np.diff(hats, prepend=0.0)

    left = 0.8 * kick + bass + chord + lead + hats
    right = 0.8 * kick + bass + 0.9 * chord + lead + 1.1 * hats
    stereo = np.column_stack([left, right])
    return stereo * (0.89 / np.max(np.abs(stereo)))


@pytest.fixture
def tmp_tempo_120_wav(tmp_path) -> Path:
    """16-second stereo pseudo-music at a known 120 BPM."""
    path = tmp_path / "tempo120.wav"
    sf.write(str(path), _rhythmic(16.0, 120.0), 44100, subtype="PCM_16")
    return path


@pytest.fixture
def tmp_tempo_change_wav(tmp_path) -> Path:
    """32-second file: 16 s at 120 BPM followed by 16 s at 90 BPM."""
    audio = np.vstack([_rhythmic(16.0, 120.0), _rhythmic(16.0, 90.0, seed=7)])
    path = tmp_path / "tempo_change.wav"
    sf.write(str(path), audio, 44100, subtype="PCM_16")
    return path


@pytest.fixture
def tmp_swung_wav(tmp_path) -> Path:
    """16-second stereo pseudo-music at 120 BPM with triplet-swung offbeats."""
    path = tmp_path / "swung.wav"
    sf.write(str(path), _rhythmic(16.0, 120.0, swing=0.33), 44100, subtype="PCM_16")
    return path


@pytest.fixture
def tmp_long_silent_wav(tmp_path) -> Path:
    """8-second stereo silence — long enough to reach the no-onset branch.

    The existing tmp_silent_wav is 1 s, so it exits via the duration guard and
    never exercises the empty-candidates path.
    """
    path = tmp_path / "long_silent.wav"
    sf.write(str(path), np.zeros((44100 * 8, 2)), 44100, subtype="PCM_16")
    return path


@pytest.fixture
def tmp_mono_tempo_wav(tmp_path) -> Path:
    """16-second MONO pseudo-music at 120 BPM — exercises the mono index path.

    The existing tmp_mono_wav is 1 s and exits via the duration guard, so the
    audio.samples[:, 0] branch is otherwise untested.
    """
    mono = _rhythmic(16.0, 120.0).mean(axis=1)
    path = tmp_path / "mono_tempo.wav"
    sf.write(str(path), mono, 44100, subtype="PCM_16")
    return path


@pytest.fixture
def tmp_tempo_90_wav(tmp_path) -> Path:
    """16-second stereo pseudo-music at 90 BPM — the known octave-error case.

    The eighth-note hat layer creates a competing 180 BPM pulse, so the top
    candidate is the octave-doubled one. Used to test that the TRUE tempo still
    appears among the candidates.
    """
    path = tmp_path / "tempo90.wav"
    sf.write(str(path), _rhythmic(16.0, 90.0), 44100, subtype="PCM_16")
    return path
