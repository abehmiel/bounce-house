"""Multi-metric diagnostic pattern engine.

Detects common mixing problems by combining metrics from multiple analyzers.
Each diagnostic pattern defines conditions as (metric_path, operator, threshold)
tuples with a min_match threshold for soft-AND logic.
"""

from __future__ import annotations

import operator as op
from dataclasses import dataclass
from typing import Any

from bounce_house.analyzers.base import AnalysisResult


@dataclass
class Diagnosis:
    """A detected mixing problem from multi-metric pattern matching."""

    pattern: str
    name: str
    severity: str  # "warn" | "fail"
    diagnosis: str
    advice: str
    matched_conditions: int
    total_conditions: int


_OPS = {
    "<": op.lt,
    ">": op.gt,
    "<=": op.le,
    ">=": op.ge,
    "==": op.eq,
}


def resolve_metric(results: list[AnalysisResult], path: str) -> float | None:
    """Resolve a dot-separated metric path against analysis results.

    Path format: "module.metric" or "module.metric.subkey"
    Returns the numeric value or None if not found.
    """
    parts = path.split(".", 2)
    if len(parts) < 2:
        return None

    module = parts[0]
    metric_key = parts[1]
    subkey = parts[2] if len(parts) == 3 else None

    for result in results:
        if result.module != module:
            continue
        value = result.metrics.get(metric_key)
        if value is None:
            return None
        if subkey is not None:
            if isinstance(value, dict):
                sub = value.get(subkey)
                return float(sub) if sub is not None else None
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    return None


def _check_conditions(
    results: list[AnalysisResult],
    conditions: list[tuple[str, str, float]],
) -> int:
    """Count how many conditions match against the analysis results."""
    matched = 0
    for path, op_str, threshold in conditions:
        value = resolve_metric(results, path)
        if value is None:
            continue
        comparator = _OPS.get(op_str)
        if comparator is None:
            continue
        if comparator(value, threshold):
            matched += 1
    return matched


def evaluate_diagnostics(results: list[AnalysisResult]) -> list[Diagnosis]:
    """Evaluate all diagnostic patterns against analysis results.

    Returns a list of Diagnosis objects for every pattern whose matched
    condition count meets or exceeds its min_match threshold.
    """
    diagnoses: list[Diagnosis] = []

    for pattern in _PATTERNS:
        conditions = pattern["conditions"]
        matched = _check_conditions(results, conditions)
        if matched >= pattern["min_match"]:
            diagnoses.append(
                Diagnosis(
                    pattern=pattern["pattern"],
                    name=pattern["name"],
                    severity=pattern["severity"],
                    diagnosis=pattern["diagnosis"],
                    advice=pattern["advice"],
                    matched_conditions=matched,
                    total_conditions=len(conditions),
                )
            )

    return diagnoses


_PATTERNS: list[dict] = [
    {
        "pattern": "muddy_mix",
        "name": "Muddy Mix",
        "conditions": [
            ("spectrum.centroid_hz", "<", 1500),
            ("perceptual.warmth", ">", 0.25),
            ("spectrum.bands.low_mid", ">", -12.0),
            ("perceptual.brightness", "<", 0.08),
        ],
        "min_match": 2,
        "severity": "warn",
        "diagnosis": "Low-mid buildup causing muddy mix",
        "advice": (
            "Cut 2-4 dB in the 200-500 Hz range. Check for overlapping bass, "
            "guitar body, and vocal chest resonance. Use a high-pass filter on "
            "non-bass instruments to remove unnecessary low-mid energy."
        ),
    },
    {
        "pattern": "harsh_mix",
        "name": "Harsh / Brittle Mix",
        "conditions": [
            ("spectrum.centroid_hz", ">", 2800),
            ("perceptual.brightness", ">", 0.20),
            ("perceptual.warmth", "<", 0.10),
            ("spectrum.bands.upper_mid", ">", -12.0),
        ],
        "min_match": 2,
        "severity": "warn",
        "diagnosis": "Excessive high-mid energy causing harshness",
        "advice": (
            "Check for resonant peaks in the 2-5 kHz range on vocals and guitars. "
            "Apply narrow-Q cuts of -2 to -4 dB at problem frequencies. Consider "
            "a de-esser on vocals targeting 5-8 kHz. Rather than boosting highs, "
            "try cutting low-mids to improve clarity."
        ),
    },
    {
        "pattern": "thin_mix",
        "name": "Thin / Weak Mix",
        "conditions": [
            ("perceptual.warmth", "<", 0.08),
            ("spectrum.bands.bass", "<", -28.0),
            ("spectrum.bands.low_mid", "<", -25.0),
            ("spectrum.centroid_hz", ">", 2500),
        ],
        "min_match": 2,
        "severity": "warn",
        "diagnosis": "Insufficient low-frequency energy; mix sounds thin",
        "advice": (
            "Check if high-pass filters are set too high. Typical HPF for vocals "
            "is 80-120 Hz, not 200+ Hz. Verify your monitoring: untreated rooms "
            "can cause phantom bass buildup that leads to over-cutting. Compare "
            "your bass/low-mid levels against a reference track."
        ),
    },
    {
        "pattern": "over_compressed",
        "name": "Over-Compressed",
        "conditions": [
            ("loudness.crest_factor_db", "<", 6),
            ("loudness.integrated_lufs", ">", -8),
            ("loudness.loudness_range_lu", "<", 4),
        ],
        "min_match": 2,
        "severity": "fail",
        "diagnosis": "Over-compressed master; dynamics crushed",
        "advice": (
            "Reduce bus compressor ratio or increase threshold. Ease off the "
            "limiter \u2014 aim for at least 8 dB crest factor. Target LRA above "
            "5 LU for streaming. Spotify normalizes to -14 LUFS, so pushing "
            "beyond -8 gains nothing and costs dynamics."
        ),
    },
    {
        "pattern": "flat_lifeless",
        "name": "Flat / Lifeless Mix",
        "conditions": [
            ("stereo.stereo_width", "<", 0.08),
            ("loudness.loudness_range_lu", "<", 5),
            ("stereo.phase_correlation", ">", 0.9),
        ],
        "min_match": 2,
        "severity": "warn",
        "diagnosis": "Mix lacks spatial depth and dynamic variation",
        "advice": (
            "Add spatial depth with reverb and delay. Vary dynamics between "
            "sections (quieter verses, louder choruses). Check panning \u2014 "
            "spreading instruments across the stereo field adds life. Even small "
            "stereo width differences between verse and chorus create perceived energy."
        ),
    },
    {
        "pattern": "mono_incompatible",
        "name": "Mono Incompatible",
        "conditions": [
            ("stereo.phase_correlation", "<", 0.1),
            ("stereo.stereo_width", ">", 0.30),
            ("stereo.frequency_width.sub_bass", "<", 0.7),
        ],
        "min_match": 2,
        "severity": "fail",
        "diagnosis": "Wide stereo image with poor mono compatibility",
        "advice": (
            "Bass frequencies below 200 Hz should be summed to mono. Check stereo "
            "widening plugins for phase issues. Test your mix in mono \u2014 any "
            "element that disappears or gets quieter has a phase problem. Bluetooth "
            "speakers, phone speakers, and PA mono subs will expose this."
        ),
    },
    {
        "pattern": "wide_bass",
        "name": "Wide Bass",
        "conditions": [
            ("stereo.frequency_width.sub_bass", "<", 0.6),
            ("stereo.frequency_width.low_mid", "<", 0.7),
        ],
        "min_match": 1,
        "severity": "warn",
        "diagnosis": "Stereo bass causing energy loss and muddiness",
        "advice": (
            "Apply a mid/side EQ to mono everything below 150-200 Hz. Check that "
            "kick and bass are panned center. Stereo bass sounds wide on headphones "
            "but loses power on mono playback systems (phones, clubs, PA centers)."
        ),
    },
    {
        "pattern": "streaming_unfriendly",
        "name": "Streaming-Unfriendly Master",
        "conditions": [
            ("loudness.integrated_lufs", ">", -7),
            ("loudness.true_peak_dbtp", ">", -1.0),
            ("loudness.loudness_range_lu", "<", 4),
        ],
        "min_match": 2,
        "severity": "fail",
        "diagnosis": "Master too hot for streaming platforms",
        "advice": (
            "Spotify normalizes to -14 LUFS, Apple Music to -16 LUFS. Your track "
            "will be turned down, and the aggressive limiting will be audible. "
            "Consider mastering to -9 to -12 LUFS with a -1.0 dBTP ceiling. The "
            "quieter version will actually sound better after platform "
            "normalization because it retains more dynamics."
        ),
    },
]
