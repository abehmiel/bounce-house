"""Rule-based advice engine.

Rules are defined as data. Each rule checks a metric from an AnalysisResult
and produces an Assessment with a pass/warn/fail status and actionable message.
"""

from __future__ import annotations

from bounce_house.analyzers.base import AnalysisResult, Assessment


def evaluate_rules(result: AnalysisResult) -> list[Assessment]:
    """Evaluate all applicable rules for a given analysis result."""
    rules = _RULES.get(result.module, [])
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


def _lufs_status(value: float) -> str:
    if -16 <= value <= -8:
        return "pass"
    if -20 <= value < -16 or -8 < value <= -6:
        return "warn"
    return "fail"


def _true_peak_status(value: float) -> str:
    if value < -1.0:
        return "pass"
    if value <= -0.5:
        return "warn"
    return "fail"


def _lra_status(value: float) -> str:
    if 5 <= value <= 15:
        return "pass"
    if 3 <= value < 5 or 15 < value <= 20:
        return "warn"
    return "fail"


def _crest_status(value: float) -> str:
    if value > 10:
        return "pass"
    if value >= 6:
        return "warn"
    return "fail"


def _correlation_status(value: float) -> str:
    if value > 0.3:
        return "pass"
    if value >= 0.0:
        return "warn"
    return "fail"


def _min_block_corr_status(value: float) -> str:
    if value > 0.0:
        return "pass"
    if value >= -0.3:
        return "warn"
    return "fail"


def _balance_status(value: float) -> str:
    v = abs(value)
    if v <= 0.5:
        return "pass"
    if v <= 1.5:
        return "warn"
    return "fail"


_RULES: dict[str, list[dict]] = {
    "loudness": [
        {
            "metric": "integrated_lufs",
            "evaluate": _lufs_status,
            "messages": {
                "pass": "Integrated loudness is {value:.1f} LUFS — within target range",
                "warn": "Integrated loudness is {value:.1f} LUFS — outside typical -16 to -8 range",
                "fail": "Integrated loudness is {value:.1f} LUFS — significantly outside target range, check your gain staging",
            },
        },
        {
            "metric": "true_peak_dbtp",
            "evaluate": _true_peak_status,
            "messages": {
                "pass": "True peak is {value:.1f} dBTP — safe headroom",
                "warn": "True peak is {value:.1f} dBTP — close to clipping, consider lowering limiter ceiling to -1.0 dBTP",
                "fail": "True peak is {value:.1f} dBTP — risk of inter-sample peaks on codec conversion, add a limiter ceiling at -1.0 dBTP",
            },
        },
        {
            "metric": "loudness_range_lu",
            "evaluate": _lra_status,
            "messages": {
                "pass": "Loudness range is {value:.1f} LU — healthy dynamics",
                "warn": "Loudness range is {value:.1f} LU — dynamics may be too compressed or too wide",
                "fail": "Loudness range is {value:.1f} LU — extreme dynamics, review compressor/limiter settings",
            },
        },
        {
            "metric": "crest_factor_db",
            "evaluate": _crest_status,
            "messages": {
                "pass": "Crest factor is {value:.1f} dB — good transient headroom",
                "warn": "Crest factor is {value:.1f} dB — transients may be over-compressed",
                "fail": "Crest factor is {value:.1f} dB — heavily squashed, reduce limiting or compression",
            },
        },
    ],
    "stereo": [
        {
            "metric": "phase_correlation",
            "evaluate": _correlation_status,
            "messages": {
                "pass": "Phase correlation is {value:+.3f} — good mono compatibility",
                "warn": "Phase correlation is {value:+.3f} — may lose energy in mono playback",
                "fail": "Phase correlation is {value:+.3f} — significant phase cancellation, check stereo effects",
            },
        },
        {
            "metric": "min_block_correlation",
            "evaluate": _min_block_corr_status,
            "messages": {
                "pass": "Minimum block correlation is {value:+.3f} — no phase issues detected",
                "warn": "Minimum block correlation is {value:+.3f} — some sections have near-zero or negative correlation",
                "fail": "Minimum block correlation is {value:+.3f} — severe phase cancellation in some sections",
            },
        },
        {
            "metric": "balance_db",
            "evaluate": _balance_status,
            "messages": {
                "pass": "Channel balance is {value:+.1f} dB — centered",
                "warn": "Channel balance is {value:+.1f} dB — slight imbalance, check panning",
                "fail": "Channel balance is {value:+.1f} dB — significant imbalance, review pan positions",
            },
        },
    ],
}
