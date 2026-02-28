"""Base types and abstract class for analyzers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from bounce_house.audio import AudioData


@dataclass
class Assessment:
    """A single rule-based judgment on a metric."""

    metric: str
    value: float
    status: str  # "pass" | "warn" | "fail"
    message: str
    reference: float | None = None


@dataclass
class AnalysisResult:
    """Results from a single analysis module."""

    module: str
    metrics: dict[str, Any] = field(default_factory=dict)
    assessments: list[Assessment] = field(default_factory=list)


class AnalyzerBase(ABC):
    """Abstract base class for analysis modules."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short name for this analyzer (e.g., 'loudness')."""
        ...

    @abstractmethod
    def analyze(self, audio: AudioData) -> AnalysisResult:
        """Analyze a single audio file."""
        ...

    @abstractmethod
    def compare(self, audio: AudioData, reference: AudioData) -> AnalysisResult:
        """Analyze audio file relative to a reference."""
        ...
