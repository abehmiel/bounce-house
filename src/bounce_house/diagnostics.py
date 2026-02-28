"""Multi-metric diagnostic pattern engine.

Detects common mixing problems by combining metrics from multiple analyzers.
Each diagnostic pattern defines conditions as (metric_path, operator, threshold)
tuples with a min_match threshold for soft-AND logic.
"""

from __future__ import annotations

import operator as op
from dataclasses import dataclass

from bounce_house.analyzers.base import AnalysisResult
from bounce_house.profiles import Profile, get_profile


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


def evaluate_diagnostics(
    results: list[AnalysisResult],
    profile: Profile | None = None,
) -> list[Diagnosis]:
    """Evaluate all diagnostic patterns against analysis results.

    Returns a list of Diagnosis objects for every pattern whose matched
    condition count meets or exceeds its min_match threshold.
    """
    if profile is None:
        profile = get_profile("master")

    diagnoses: list[Diagnosis] = []

    for pattern in profile.patterns:
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
