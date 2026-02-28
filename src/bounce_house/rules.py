"""Rule-based advice engine.

Rules are defined as data. Each rule checks a metric from an AnalysisResult
and produces an Assessment with a pass/warn/fail status and actionable message.
"""

from __future__ import annotations

from bounce_house.analyzers.base import AnalysisResult, Assessment
from bounce_house.profiles import Profile, get_profile


def evaluate_rules(result: AnalysisResult, profile: Profile | None = None) -> list[Assessment]:
    """Evaluate all applicable rules for a given analysis result."""
    if profile is None:
        profile = get_profile("master")
    rules = profile.rules.get(result.module, [])
    assessments = []

    for rule in rules:
        metric = rule["metric"]
        value = _get_metric(result.metrics, metric)
        if value is None:
            continue

        status = rule["evaluate"](value)
        message = rule["messages"][status].format(value=value)
        assessments.append(
            Assessment(
                metric=metric,
                value=value,
                status=status,
                message=message,
                reference=rule.get("reference"),
            )
        )

    # Reference comparison rules (band deviations)
    if result.module == "spectrum" and "band_differences" in result.metrics:
        for band, diff in result.metrics["band_differences"].items():
            if abs(diff) > 3.0:
                status = "warn" if abs(diff) <= 6.0 else "fail"
                direction = "above" if diff > 0 else "below"
                assessments.append(
                    Assessment(
                        metric=f"band_diff_{band}",
                        value=diff,
                        status=status,
                        message=f"{band.replace('_', '-')} band is {diff:+.1f} dB {direction} reference",
                        reference=0.0,
                    )
                )

    return assessments


def _get_metric(metrics: dict, key: str) -> float | None:
    """Safely extract a metric, returning None if missing."""
    value = metrics.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
