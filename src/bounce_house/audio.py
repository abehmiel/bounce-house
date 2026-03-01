"""Audio loading and shared data types."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf


@dataclass
class AudioData:
    """Loaded audio data with metadata."""

    samples: np.ndarray  # shape: (num_samples, num_channels), float64
    sample_rate: int
    filepath: Path

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

    try:
        samples, sample_rate = sf.read(str(path), dtype="float64")
    except sf.LibsndfileError as e:
        raise ValueError(f"Cannot read audio file: {path} ({e})") from e

    # Ensure 2D: (num_samples, num_channels)
    if samples.ndim == 1:
        samples = samples[:, np.newaxis]

    return AudioData(samples=samples, sample_rate=sample_rate, filepath=path)
