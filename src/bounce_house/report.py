"""Report formatting — terminal (ANSI) and JSON output."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from bounce_house.analyzers.base import AnalysisResult, Assessment
from bounce_house.bounce_diff import BounceDiff, MetricChange
from bounce_house.diagnostics import Diagnosis
from bounce_house.metric_docs import METRICS, MODULE_TITLES, MODULES, MetricDoc

# ANSI color codes
_RESET = "\033[0m"
_BOLD = "\033[1m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_DIM = "\033[2m"

_STATUS_COLORS = {"pass": _GREEN, "warn": _YELLOW, "fail": _RED}
_STATUS_LABELS = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}

_MODULE_TITLES = {
    "loudness": "Loudness & Dynamics",
    "spectrum": "Spectral Balance",
    "stereo": "Stereo & Phase",
    "translation": "Translation (Mono & Small Speakers)",
    "perceptual": "Perceptual Quality",
    "tuning": "Tuning & Pitch",
    "rhythm": "Rhythm & Groove",
    "qc": "Quality Control",
}

# Metrics to hide from terminal display entirely
_SKIP_METRICS: frozenset[str] = frozenset(
    {
        "timbral_models_available",
        "proxy_metrics",
        "mono_file",
    }
)

# Display-friendly metric names
_METRIC_NAMES = {
    "integrated_lufs": "Integrated LUFS",
    "true_peak_dbtp": "True Peak",
    "loudness_range_lu": "Loudness Range",
    "sample_peak_dbfs": "Sample Peak",
    "rms_db": "RMS Level",
    "crest_factor_db": "Crest Factor",
    "plr_db": "PLR",
    "dc_offset_db": "DC Offset",
    "dr_score": "DR (Dynamic Range)",
    "centroid_hz": "Centroid",
    "bandwidth_hz": "Bandwidth",
    "rolloff_hz": "Rolloff (85%)",
    "flatness": "Flatness",
    "phase_correlation": "Phase Correlation",
    "low_block_correlation": "Block Corr (p5)",
    "mid_rms_db": "Mid RMS",
    "side_rms_db": "Side RMS",
    "ms_ratio_db": "M/S Ratio",
    "stereo_width": "Stereo Width",
    "balance_db": "Balance",
    "brightness": "Brightness",
    "warmth": "Warmth",
    "timbral_brightness": "Brightness (timbral)",
    "timbral_warmth": "Warmth (timbral)",
    "hardness": "Hardness",
    "roughness": "Roughness",
    "tuning_deviation_cents": "Tuning Deviation",
    "estimated_a_hz": "Concert Pitch",
    "closest_standard": "Closest Standard",
    "pitch_drift_std_cents": "Pitch Drift (std)",
    "pitch_drift_range_cents": "Pitch Drift (range)",
    "pitch_drift_trend_cents_per_min": "Pitch Trend",
    "chroma_sharpness": "Chroma Sharpness",
    "tempo_bpm": "Tempo",
    "tempo_confidence": "Tempo Confidence",
    "tempo_stability": "Tempo Stability",
    "swing_ratio": "Swing Ratio",
    "subdivision": "Subdivision",
    "clip_events": "Clip Events",
    "longest_clip_run": "Longest Clip Run",
    "leading_silence_sec": "Leading Silence",
    "trailing_silence_sec": "Trailing Silence",
    "mono_loss_db": "Mono Loss",
    "worst_band": "Worst Band (mono)",
    "worst_band_loss_db": "Worst Band Loss",
    "low_end_reliance": "Low-End Reliance",
}

_SPARK_CHARS = "▁▂▃▄▅▆▇█"


def _sparkline(values: list, lo: float, hi: float) -> str:
    """Map values to eight-level block characters; None renders as a space."""
    span = hi - lo if hi > lo else 1.0
    chars = []
    for v in values:
        if v is None:
            chars.append(" ")
            continue
        idx = int((min(max(v, lo), hi) - lo) / span * (len(_SPARK_CHARS) - 1))
        idx = min(max(idx, 0), len(_SPARK_CHARS) - 1)
        chars.append(_SPARK_CHARS[idx])
    return "".join(chars)


_SCHEMA_VERSION = 3  # 3: rhythm module added (Stage 5)


def _sanitize(obj: Any) -> Any:
    """Replace non-finite floats (NaN, ±Infinity) with None for strict RFC 8259 JSON."""
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [_sanitize(v) for v in obj]
    return obj


def format_terminal(
    results: list[AnalysisResult],
    filename: str,
    file_info: dict[str, Any],
    diagnoses: list[Diagnosis] | None = None,
    stage: str = "master",
    genre=None,
) -> str:
    """Format analysis results as rich terminal output.

    Args:
        results: List of analysis results from each module.
        filename: Name of the analyzed audio file.
        file_info: Dict with keys 'sample_rate', 'channels', 'duration'.
        diagnoses: Optional list of Diagnosis objects from the pattern engine.
        genre: Optional genres.GenreProfile overlay applied to the analysis.

    Returns:
        A string with ANSI color codes suitable for terminal display.
    """
    lines: list[str] = []

    # Header
    duration_str = _format_duration(file_info.get("duration", 0))
    sr = file_info.get("sample_rate", 0)
    ch = file_info.get("channels", 0)
    ch_str = "stereo" if ch == 2 else f"{ch}ch" if ch > 2 else "mono"

    lines.append("")
    lines.append(f"{_BOLD}{'═' * 60}{_RESET}")
    stage_label = "Pre-Master Mix Analysis" if stage == "mix" else "Master Analysis Report"
    lines.append(f"{_BOLD}  BOUNCE HOUSE — {stage_label}{_RESET}")
    lines.append(f"{_DIM}  {filename} ({sr} Hz, {ch_str}, {duration_str}){_RESET}")
    if genre is not None:
        tag = " (provisional targets)" if genre.provisional else ""
        lines.append(f"{_DIM}  Genre targets: {genre.display_name}{tag}{_RESET}")
    lines.append(f"{_BOLD}{'═' * 60}{_RESET}")

    # Collect all assessments for summary
    all_assessments: list[Assessment] = []

    for result in results:
        title = _MODULE_TITLES.get(result.module, result.module.title())
        lines.append("")
        lines.append(f"{_BOLD}── {title} {'─' * (55 - len(title))}{_RESET}")

        # Metrics
        assessment_map = {a.metric: a for a in result.assessments}
        all_assessments.extend(result.assessments)

        # Handle special cases
        if result.metrics.get("mono_file"):
            lines.append(f"  {_DIM}Mono file — stereo analysis skipped{_RESET}")
            continue

        # Band energies (special formatting)
        bands = result.metrics.get("bands")
        band_diffs = result.metrics.get("band_differences")
        freq_width = result.metrics.get("frequency_width")

        for key, value in result.metrics.items():
            if key in _SKIP_METRICS:
                continue
            if key in (
                "bands",
                "band_differences",
                "reference_bands",
                "frequency_width",
                "band_ratios",
                "band_mono_loss",
                "rms_curve_db",
                "correlation_curve",
                "note_ms",
                "tempo_segments",
                "tempo_candidates",
            ):
                continue
            # Skip reference/diff keys in main display
            if key.startswith("reference_") or key.endswith("_difference"):
                continue
            if value is None:
                continue

            display_name = _METRIC_NAMES.get(key, key.replace("_", " ").title())

            assessment = assessment_map.get(key)
            status_str = ""
            if assessment:
                color = _STATUS_COLORS[assessment.status]
                label = _STATUS_LABELS[assessment.status]
                status_str = f"  {color}{label}{_RESET}"

            value_str = _format_value(key, value)
            lines.append(f"  {display_name:<22} {value_str}{status_str}")

        rms_curve = result.metrics.get("rms_curve_db")
        if rms_curve:
            lo = min(max(min(rms_curve), -60.0), max(rms_curve))
            spark = _sparkline(rms_curve, lo=lo, hi=max(rms_curve))
            lines.append(f"  {'Level':<22} {_DIM}{spark}{_RESET}")

        corr_curve = result.metrics.get("correlation_curve")
        if corr_curve:
            spark = _sparkline(corr_curve, lo=-1.0, hi=1.0)
            lines.append(f"  {'Correlation':<22} {_DIM}{spark}{_RESET}")

        # Band energies
        if bands:
            lines.append("")
            for band_name, energy in bands.items():
                label = band_name.replace("_", "-")
                bar_len = int((min(max(energy, -40.0), 15.0) + 40.0) / 55.0 * 12)
                bar = "█" * bar_len
                diff_str = ""
                if band_diffs and band_name in band_diffs:
                    diff = band_diffs[band_name]
                    if abs(diff) > 3.0:
                        color = _YELLOW if abs(diff) <= 6.0 else _RED
                        diff_str = f"  {color}{diff:+.1f} dB vs ref{_RESET}"
                lines.append(
                    f"  {label:<22} {energy:>8.1f} dB rel  {_DIM}{bar:<12}{_RESET}{diff_str}"
                )

        # Frequency-dependent stereo width
        if freq_width:
            lines.append("")
            lines.append(f"  {_DIM}Frequency-dependent correlation:{_RESET}")
            for band_name, corr in freq_width.items():
                label = band_name.replace("_", "-")
                corr_str = f"{corr:+.3f}" if corr is not None else "  n/a"
                lines.append(f"    {label:<18} {corr_str}")

        band_mono_loss = result.metrics.get("band_mono_loss")
        if band_mono_loss:
            lines.append("")
            lines.append(f"  {_DIM}Mono loss by band:{_RESET}")
            for band_name, loss in band_mono_loss.items():
                label = band_name.replace("_", "-")
                lines.append(f"    {label:<18} {loss:+.1f} dB")

        segments = result.metrics.get("tempo_segments")
        if segments and len(segments) > 1:
            lines.append("")
            lines.append(f"  {_DIM}Tempo over time:{_RESET}")
            for seg in segments:
                span = f"{_format_duration(seg['start_s'])}-{_format_duration(seg['end_s'])}"
                lines.append(f"    {span:<18} {seg['bpm']:.1f} BPM")

        candidates = result.metrics.get("tempo_candidates")
        if candidates and len(candidates) > 1:
            alts = "  ".join(f"{c['bpm']:.1f} ({c['score']:.2f})" for c in candidates[1:])
            lines.append(f"  {'Also plausible':<22} {_DIM}{alts}{_RESET}")

        note_ms = result.metrics.get("note_ms")
        if note_ms:
            lines.append("")
            lines.append(f"  {_DIM}Note lengths (delay/release times):{_RESET}")
            for name, ms in note_ms.items():
                lines.append(f"    {name:<18} {ms:>8.1f} ms")

    # Suggestions section
    warns = [a for a in all_assessments if a.status == "warn"]
    fails = [a for a in all_assessments if a.status == "fail"]

    if warns or fails:
        lines.append("")
        lines.append(f"{_BOLD}── Suggestions {'─' * 44}{_RESET}")
        for a in fails:
            lines.append(f"  {_RED}FAIL{_RESET}  {a.message}")
        for a in warns:
            lines.append(f"  {_YELLOW}WARN{_RESET}  {a.message}")

    # Mix Diagnostics section
    if diagnoses:
        lines.append("")
        lines.append(f"{_BOLD}── Mix Diagnostics {'─' * 40}{_RESET}")
        for d in diagnoses:
            color = _RED if d.severity == "fail" else _YELLOW
            label = "FAIL" if d.severity == "fail" else "WARN"
            lines.append(f"  {color}{label}{_RESET}  {_BOLD}{d.name}{_RESET} — {d.diagnosis}")
            lines.append(f"        {d.advice}")

    # Summary
    lines.append("")
    lines.append(f"{_BOLD}{'═' * 60}{_RESET}")
    lines.append(f"  {len(warns)} warning(s), {len(fails)} failure(s)")
    lines.append(f"{_BOLD}{'═' * 60}{_RESET}")
    lines.append("")

    return "\n".join(lines)


def format_json(
    results: list[AnalysisResult],
    filename: str,
    file_info: dict[str, Any],
    diagnoses: list[Diagnosis] | None = None,
    stage: str = "master",
    genre=None,
) -> str:
    """Format analysis results as JSON.

    Args:
        results: List of analysis results from each module.
        filename: Name of the analyzed audio file.
        file_info: Dict with keys 'sample_rate', 'channels', 'duration'.
        diagnoses: Optional list of Diagnosis objects from the pattern engine.
        genre: Optional genres.GenreProfile overlay applied to the analysis.

    Returns:
        A JSON-encoded string with file info, per-module metrics,
        all assessments, and a summary of warnings/failures.
    """
    output: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "file": filename,
        "format": file_info,
        "stage": stage,
        "genre": genre.name if genre is not None else None,
        "genre_provisional": genre.provisional if genre is not None else None,
    }

    all_assessments: list[dict] = []

    for result in results:
        output[result.module] = result.metrics
        for a in result.assessments:
            all_assessments.append(
                {
                    "metric": a.metric,
                    "value": a.value,
                    "status": a.status,
                    "message": a.message,
                    "reference": a.reference,
                }
            )

    warns = sum(1 for a in all_assessments if a["status"] == "warn")
    fails = sum(1 for a in all_assessments if a["status"] == "fail")

    output["assessments"] = all_assessments
    output["summary"] = {"warnings": warns, "failures": fails}

    if diagnoses:
        output["diagnostics"] = [
            {
                "pattern": d.pattern,
                "name": d.name,
                "severity": d.severity,
                "diagnosis": d.diagnosis,
                "advice": d.advice,
                "matched_conditions": d.matched_conditions,
                "total_conditions": d.total_conditions,
            }
            for d in diagnoses
        ]

    return json.dumps(_sanitize(output), indent=2, allow_nan=False)


def format_explain_overview() -> str:
    """Format overview of all metrics — one line per metric, grouped by module."""
    lines: list[str] = []

    lines.append("")
    lines.append(f"{_BOLD}{'═' * 60}{_RESET}")
    lines.append(f"{_BOLD}  BOUNCE HOUSE — Metric Reference{_RESET}")
    lines.append(f"{_BOLD}{'═' * 60}{_RESET}")

    for module_key, metric_keys in MODULES.items():
        title = MODULE_TITLES.get(module_key, module_key.title())
        lines.append("")
        lines.append(f"{_BOLD}── {title} {'─' * (55 - len(title))}{_RESET}")

        for key in metric_keys:
            doc = METRICS[key]
            lines.append(f"  {doc.name:<24} {_DIM}{doc.summary}{_RESET}")

    lines.append("")
    lines.append(f"{_DIM}  Use 'bounce-house explain <module>' for details.{_RESET}")
    lines.append(f"{_DIM}  Use 'bounce-house explain <metric>' for a single metric.{_RESET}")
    lines.append(f"{_DIM}  Add --technical for measurement standards and methods.{_RESET}")
    lines.append("")

    return "\n".join(lines)


def format_explain_module(module: str, technical: bool = False) -> str:
    """Format full explanation of all metrics in a module."""
    title = MODULE_TITLES.get(module, module.title())
    metric_keys = MODULES[module]

    lines: list[str] = []
    lines.append("")
    lines.append(f"{_BOLD}── {title} {'─' * (55 - len(title))}{_RESET}")

    for key in metric_keys:
        doc = METRICS[key]
        lines.extend(_format_metric_block(doc, technical))

    lines.append("")
    return "\n".join(lines)


def format_explain_metric(key: str, technical: bool = False) -> str:
    """Format a single metric's full documentation."""
    doc = METRICS[key]
    lines: list[str] = []
    lines.append("")
    lines.extend(_format_metric_block(doc, technical))
    lines.append("")
    return "\n".join(lines)


def _format_metric_block(doc: MetricDoc, technical: bool) -> list[str]:
    """Format one metric's documentation block."""
    lines: list[str] = []
    lines.append("")
    lines.append(f"  {_BOLD}{doc.name}{_RESET}")
    lines.append(f"    {doc.explanation}")
    lines.append(f"    {_GREEN}Good range:{_RESET} {doc.good_range}")
    if doc.genre_notes:
        lines.append(f"    {_YELLOW}Genre:{_RESET} {doc.genre_notes}")
    if technical:
        lines.append(f"    {_DIM}Standard/Method:{_RESET} {doc.technical}")
    return lines


def _format_duration(seconds: float) -> str:
    """Convert seconds to m:ss string."""
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def _format_value(key: str, value: Any) -> str:
    """Format a metric value for display based on its key suffix."""
    if isinstance(value, str):
        return value
    if isinstance(value, float):
        if key.endswith("_bpm"):
            return f"{value:.1f} BPM"
        if "cents" in key:
            return f"{value:+.1f} cents"
        if "hz" in key.lower():
            return f"{value:,.1f} Hz"
        if "db" in key.lower() or "lufs" in key or "lu" in key:
            return f"{value:+.1f}"
        return f"{value:.4f}"
    return str(value)


def format_dir_summary(
    file_data: list[dict],
    directory: str,
    errors: list[tuple[str, str]] | None = None,
    stage: str = "master",
    genre=None,
) -> str:
    """Format a summary table for batch directory analysis."""
    lines: list[str] = []
    total_files = len(file_data) + (len(errors) if errors else 0)

    lines.append("")
    lines.append(f"{_BOLD}{'═' * 60}{_RESET}")
    stage_label = " (Pre-Master Mix)" if stage == "mix" else ""
    lines.append(f"{_BOLD}  DIRECTORY SUMMARY{stage_label} ({total_files} files){_RESET}")
    if genre is not None:
        tag = " (provisional targets)" if genre.provisional else ""
        lines.append(f"{_DIM}  Genre targets: {genre.display_name}{tag}{_RESET}")
    lines.append(f"{_BOLD}{'═' * 60}{_RESET}")
    lines.append("")

    lines.append(f"  {'File':<24} {'LUFS':>6} {'Peak':>6} {'Crest':>6} {'W':>3} {'F':>3}  Status")
    lines.append(f"  {'─' * 56}")

    total_warns = 0
    total_fails = 0

    for data in file_data:
        filename = Path(data["path"]).name
        if len(filename) > 22:
            filename = filename[:19] + "..."

        lufs = ""
        peak = ""
        crest = ""
        for r in data["results"]:
            if r.module == "loudness":
                lufs_val = r.metrics.get("integrated_lufs")
                peak_val = r.metrics.get("true_peak_dbtp") or r.metrics.get("sample_peak_dbfs")
                crest_val = r.metrics.get("crest_factor_db")
                if lufs_val is not None:
                    lufs = f"{lufs_val:+.1f}"
                if peak_val is not None:
                    peak = f"{peak_val:+.1f}"
                if crest_val is not None:
                    crest = f"{crest_val:.1f}"
                break

        file_warns = 0
        file_fails = 0
        for r in data["results"]:
            for a in r.assessments:
                if a.status == "warn":
                    file_warns += 1
                elif a.status == "fail":
                    file_fails += 1

        total_warns += file_warns
        total_fails += file_fails

        if file_fails > 0:
            status_color = _RED
            status_label = "FAIL"
        elif file_warns > 0:
            status_color = _YELLOW
            status_label = "WARN"
        else:
            status_color = _GREEN
            status_label = "PASS"

        lines.append(
            f"  {filename:<24} {lufs:>6} {peak:>6} {crest:>6} {file_warns:>3} {file_fails:>3}  "
            f"{status_color}{status_label}{_RESET}"
        )

    if errors:
        for err_file, err_msg in errors:
            filename = err_file
            if len(filename) > 22:
                filename = filename[:19] + "..."
            lines.append(
                f"  {filename:<24} {'—':>6} {'—':>6} {'—':>6} {'—':>3} {'—':>3}  "
                f"{_RED}ERROR{_RESET}  {_DIM}{err_msg}{_RESET}"
            )

    lines.append("")
    lines.append(f"{_BOLD}{'═' * 60}{_RESET}")
    lines.append(f"  {total_warns} warning(s), {total_fails} failure(s) across {total_files} files")
    lines.append(f"{_BOLD}{'═' * 60}{_RESET}")
    lines.append("")

    return "\n".join(lines)


def format_dir_json(
    file_data: list[dict],
    directory: str,
    errors: list[tuple[str, str]] | None = None,
    stage: str = "master",
    genre=None,
) -> str:
    """Format batch directory results as JSON."""
    files_output = []
    total_warns = 0
    total_fails = 0

    for data in file_data:
        entry: dict[str, Any] = {
            "file": data["path"],
            "format": data["file_info"],
        }

        file_assessments: list[dict] = []
        for result in data["results"]:
            entry[result.module] = result.metrics
            for a in result.assessments:
                file_assessments.append(
                    {
                        "metric": a.metric,
                        "value": a.value,
                        "status": a.status,
                        "message": a.message,
                        "reference": a.reference,
                    }
                )

        file_warns = sum(1 for a in file_assessments if a["status"] == "warn")
        file_fails = sum(1 for a in file_assessments if a["status"] == "fail")
        total_warns += file_warns
        total_fails += file_fails

        entry["assessments"] = file_assessments
        entry["summary"] = {"warnings": file_warns, "failures": file_fails}

        if data.get("diagnoses"):
            entry["diagnostics"] = [
                {
                    "pattern": d.pattern,
                    "name": d.name,
                    "severity": d.severity,
                    "diagnosis": d.diagnosis,
                    "advice": d.advice,
                    "matched_conditions": d.matched_conditions,
                    "total_conditions": d.total_conditions,
                }
                for d in data["diagnoses"]
            ]

        files_output.append(entry)

    skipped = [{"file": name, "error": message} for name, message in (errors or [])]

    output = {
        "schema_version": _SCHEMA_VERSION,
        "directory": directory,
        "stage": stage,
        "genre": genre.name if genre is not None else None,
        "genre_provisional": genre.provisional if genre is not None else None,
        "files": files_output,
        "skipped": skipped,
        "summary": {
            "total_files": len(file_data),
            "total_skipped": len(skipped),
            "total_warnings": total_warns,
            "total_failures": total_fails,
        },
    }

    return json.dumps(_sanitize(output), indent=2, allow_nan=False)


def _diff_line(change: MetricChange, color: str) -> str:
    arrow = "↑" if change.delta > 0 else "↓"
    status = ""
    if change.old_status and change.new_status and change.old_status != change.new_status:
        status = f"  {change.old_status.upper()} → {change.new_status.upper()}"
    return (
        f"  {color}{arrow}{_RESET} {change.module}.{change.metric:<28}"
        f" {change.old:+.2f} → {change.new:+.2f} ({change.delta:+.2f}){status}"
    )


def format_diff_terminal(diff: BounceDiff, old_path: str, new_path: str, genre=None) -> str:
    lines: list[str] = [""]
    lines.append(f"{_BOLD}{'═' * 60}{_RESET}")
    lines.append(f"{_BOLD}  BOUNCE DIFF{_RESET}")
    lines.append(f"{_DIM}  {old_path} → {new_path}{_RESET}")
    if genre is not None:
        tag = " (provisional targets)" if genre.provisional else ""
        lines.append(f"{_DIM}  Genre targets: {genre.display_name}{tag}{_RESET}")
    lines.append(f"{_BOLD}{'═' * 60}{_RESET}")

    if diff.improvements:
        lines.append("")
        lines.append(f"{_BOLD}── Improved {'─' * 47}{_RESET}")
        lines.extend(_diff_line(c, _GREEN) for c in diff.improvements)
    if diff.regressions:
        lines.append("")
        lines.append(f"{_BOLD}── Regressed {'─' * 46}{_RESET}")
        lines.extend(_diff_line(c, _RED) for c in diff.regressions)
    if diff.changes:
        lines.append("")
        lines.append(f"{_BOLD}── Changed {'─' * 48}{_RESET}")
        lines.extend(_diff_line(c, _YELLOW) for c in diff.changes)

    if diff.diagnostics_resolved or diff.diagnostics_introduced:
        lines.append("")
        lines.append(f"{_BOLD}── Diagnostics {'─' * 44}{_RESET}")
        for name in diff.diagnostics_resolved:
            lines.append(f"  {_GREEN}resolved{_RESET}   {name}")
        for name in diff.diagnostics_introduced:
            lines.append(f"  {_RED}introduced{_RESET} {name}")

    lines.append("")
    lines.append(f"{_BOLD}{'═' * 60}{_RESET}")
    lines.append(
        f"  {len(diff.improvements)} improved, {len(diff.regressions)} regressed,"
        f" {len(diff.changes)} changed, {diff.unchanged_count} unchanged"
    )
    lines.append(f"{_BOLD}{'═' * 60}{_RESET}")
    lines.append("")
    return "\n".join(lines)


def format_diff_json(diff: BounceDiff, old_path: str, new_path: str, genre=None) -> str:
    def _encode(change: MetricChange) -> dict:
        return {
            "module": change.module,
            "metric": change.metric,
            "old": change.old,
            "new": change.new,
            "delta": change.delta,
            "old_status": change.old_status,
            "new_status": change.new_status,
        }

    output = {
        "schema_version": _SCHEMA_VERSION,
        "old": old_path,
        "new": new_path,
        "genre": genre.name if genre is not None else None,
        "genre_provisional": genre.provisional if genre is not None else None,
        "improvements": [_encode(c) for c in diff.improvements],
        "regressions": [_encode(c) for c in diff.regressions],
        "changes": [_encode(c) for c in diff.changes],
        "diagnostics_resolved": diff.diagnostics_resolved,
        "diagnostics_introduced": diff.diagnostics_introduced,
        "unchanged_count": diff.unchanged_count,
    }
    return json.dumps(_sanitize(output), indent=2, allow_nan=False)
