"""Bounce-over-bounce diffing — what moved between two versions of a mix."""

from __future__ import annotations

from dataclasses import dataclass, field

_STATUS_RANK = {"pass": 0, "warn": 1, "fail": 2}

# Minimum |delta| for a metric change to be worth reporting, by exact key
# or by suffix fallback. Non-numeric and curve/dict metrics are never diffed.
SIGNIFICANCE_EXACT: dict[str, float] = {
    "integrated_lufs": 0.3,
    "true_peak_dbtp": 0.3,
    "phase_correlation": 0.05,
    "low_block_correlation": 0.05,
    "stereo_width": 0.02,
    "low_end_reliance": 0.02,
    "brightness": 0.02,
    "warmth": 0.02,
    "flatness": 0.02,
    "chroma_sharpness": 0.02,
    "clip_events": 1.0,
    "tempo_bpm": 1.0,
}
SIGNIFICANCE_SUFFIX: list[tuple[str, float]] = [
    ("_cents", 2.0),
    ("_hz", 100.0),
    ("_db", 0.5),
    ("_dbfs", 0.5),
    ("_dbtp", 0.5),
    ("_lu", 0.5),
    ("_sec", 0.5),
]
_DEFAULT_SIGNIFICANCE = 0.5
_EXCLUDED_KEYS = {
    "rms_curve_db",
    "correlation_curve",
    "note_ms",
    "tempo_segments",
    "tempo_candidates",
}


def _significance(metric: str) -> float:
    if metric in SIGNIFICANCE_EXACT:
        return SIGNIFICANCE_EXACT[metric]
    for suffix, threshold in SIGNIFICANCE_SUFFIX:
        if metric.endswith(suffix):
            return threshold
    return _DEFAULT_SIGNIFICANCE


@dataclass(frozen=True)
class MetricChange:
    module: str
    metric: str
    old: float
    new: float
    delta: float
    old_status: str | None = None
    new_status: str | None = None


@dataclass
class BounceDiff:
    improvements: list[MetricChange] = field(default_factory=list)
    regressions: list[MetricChange] = field(default_factory=list)
    changes: list[MetricChange] = field(default_factory=list)
    diagnostics_resolved: list[str] = field(default_factory=list)
    diagnostics_introduced: list[str] = field(default_factory=list)
    unchanged_count: int = 0


def _flat_numeric(metrics: dict) -> dict[str, float]:
    """Flatten one level of dicts; keep finite numerics; drop curves/strings/bools."""
    flat: dict[str, float] = {}
    for key, value in metrics.items():
        if key in _EXCLUDED_KEYS:
            continue
        if isinstance(value, dict):
            for sub, sub_value in value.items():
                if isinstance(sub_value, int | float) and not isinstance(sub_value, bool):
                    flat[f"{key}.{sub}"] = float(sub_value)
        elif isinstance(value, int | float) and not isinstance(value, bool):
            flat[key] = float(value)
    return flat


def compute_diff(old_data: dict, new_data: dict) -> BounceDiff:
    """Compare two _analyze_file outputs. Categorize by status transition first,
    then by significant numeric delta; count the insignificant rest."""
    diff = BounceDiff()

    old_by_module = {r.module: r for r in old_data["results"]}
    new_by_module = {r.module: r for r in new_data["results"]}

    for module, new_result in new_by_module.items():
        old_result = old_by_module.get(module)
        if old_result is None:
            continue
        old_status = {a.metric: a.status for a in old_result.assessments}
        new_status = {a.metric: a.status for a in new_result.assessments}
        old_flat = _flat_numeric(old_result.metrics)
        new_flat = _flat_numeric(new_result.metrics)

        for metric, new_value in new_flat.items():
            old_value = old_flat.get(metric)
            if old_value is None:
                continue
            delta = round(new_value - old_value, 4)
            base_key = metric.split(".", 1)[0]
            change = MetricChange(
                module=module,
                metric=metric,
                old=old_value,
                new=new_value,
                delta=delta,
                old_status=old_status.get(base_key),
                new_status=new_status.get(base_key),
            )
            old_rank = _STATUS_RANK.get(old_status.get(base_key, ""))
            new_rank = _STATUS_RANK.get(new_status.get(base_key, ""))
            if old_rank is not None and new_rank is not None and new_rank < old_rank:
                diff.improvements.append(change)
            elif old_rank is not None and new_rank is not None and new_rank > old_rank:
                diff.regressions.append(change)
            elif abs(delta) >= _significance(metric.split(".", 1)[-1]):
                diff.changes.append(change)
            else:
                diff.unchanged_count += 1

    old_patterns = {d.pattern for d in old_data.get("diagnoses") or []}
    new_patterns = {d.pattern for d in new_data.get("diagnoses") or []}
    diff.diagnostics_resolved = sorted(old_patterns - new_patterns)
    diff.diagnostics_introduced = sorted(new_patterns - old_patterns)

    return diff
