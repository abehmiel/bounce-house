"""Audio loading and shared data types."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".wav", ".flac", ".aiff", ".aif", ".ogg"})


@dataclass
class AudioData:
    """Loaded audio data with metadata."""

    samples: np.ndarray  # shape: (num_samples, num_channels), float64
    sample_rate: int
    filepath: Path
    dc_offset: np.ndarray | None = None  # per-channel mean removed at load, shape (channels,)
    # Peak of the delivered waveform BEFORE DC removal — the real headroom ceiling.
    # None for hand-built AudioData; analyzers fall back to the (DC-free) sample peak then.
    raw_sample_peak: float | None = None
    # Delivered per-sample waveform BEFORE DC removal, shape (num_samples, num_channels).
    # None for hand-built AudioData; analyzers fall back to the (DC-free) samples then.
    raw_samples: np.ndarray | None = None

    @property
    def channels(self) -> int:
        return int(self.samples.shape[1])

    @property
    def duration(self) -> float:
        return float(self.samples.shape[0] / self.sample_rate)

    @property
    def is_stereo(self) -> bool:
        return self.channels >= 2


def load_audio(path: Path) -> AudioData:
    """Load a WAV file and return AudioData.

    Mono files are reshaped to (N, 1) for consistent handling.
    Raises FileNotFoundError if the file doesn't exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(e.lstrip(".") for e in SUPPORTED_EXTENSIONS))
        raise ValueError(
            f"Unsupported format '{ext}': {path}. Supported: {supported}. "
            f"For mp3/m4a, convert first: ffmpeg -i input{ext} output.wav"
        )

    try:
        samples, sample_rate = sf.read(str(path), dtype="float64")
    except sf.LibsndfileError as e:
        raise ValueError(f"Cannot read audio file: {path} ({e})") from e

    # Ensure 2D: (num_samples, num_channels)
    if samples.ndim == 1:
        samples = samples[:, np.newaxis]

    # Capture the delivered waveform (and its peak) before DC removal — this is
    # the true headroom ceiling for clipping/true-peak checks. DC is then
    # removed so RMS, crest, and spectral measurements run on the audio
    # content, not the offset.
    raw_samples = samples
    raw_sample_peak = float(np.max(np.abs(samples)))
    dc_offset = samples.mean(axis=0)
    samples = samples - dc_offset

    return AudioData(
        samples=samples,
        sample_rate=sample_rate,
        filepath=path,
        dc_offset=dc_offset,
        raw_sample_peak=raw_sample_peak,
        raw_samples=raw_samples,
    )
