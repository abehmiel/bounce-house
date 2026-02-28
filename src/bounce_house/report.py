"""Report formatting — terminal (ANSI) and JSON output."""

from __future__ import annotations

import json
from typing import Any

from bounce_house.analyzers.base import AnalysisResult, Assessment


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
    "perceptual": "Perceptual Quality",
}

# Display-friendly metric names
_METRIC_NAMES = {
    "integrated_lufs": "Integrated LUFS",
    "true_peak_dbtp": "True Peak",
    "true_peak_available": None,  # skip display
    "loudness_range_lu": "Loudness Range",
    "sample_peak_dbfs": "Sample Peak",
    "rms_db": "RMS Level",
    "crest_factor_db": "Crest Factor",
    "centroid_hz": "Centroid",
    "bandwidth_hz": "Bandwidth",
    "rolloff_hz": "Rolloff (85%)",
    "flatness": "Flatness",
    "phase_correlation": "Phase Correlation",
    "min_block_correlation": "Min Block Corr",
    "mid_rms_db": "Mid RMS",
    "side_rms_db": "Side RMS",
    "ms_ratio_db": "M/S Ratio",
    "stereo_width": "Stereo Width",
    "balance_db": "Balance",
    "brightness": "Brightness",
    "warmth": "Warmth",
    "hardness": "Hardness",
    "roughness": "Roughness",
    "timbral_models_available": None,
    "proxy_metrics": None,
    "mono_file": None,
}


def format_terminal(
    results: list[AnalysisResult],
    filename: str,
    file_info: dict[str, Any],
) -> str:
    """Format analysis results as rich terminal output.

    Args:
        results: List of analysis results from each module.
        filename: Name of the analyzed audio file.
        file_info: Dict with keys 'sample_rate', 'channels', 'duration'.

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
    lines.append(f"{_BOLD}  BOUNCE HOUSE — Mix Analysis Report{_RESET}")
    lines.append(f"{_DIM}  {filename} ({sr} Hz, {ch_str}, {duration_str}){_RESET}")
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
            display_name = _METRIC_NAMES.get(key)
            if display_name is None:
                continue
            if key in ("bands", "band_differences", "reference_bands", "frequency_width"):
                continue
            # Skip reference/diff keys in main display
            if key.startswith("reference_") or key.endswith("_difference"):
                continue

            assessment = assessment_map.get(key)
            status_str = ""
            if assessment:
                color = _STATUS_COLORS[assessment.status]
                label = _STATUS_LABELS[assessment.status]
                status_str = f"  {color}{label}{_RESET}"

            value_str = _format_value(key, value)
            lines.append(f"  {display_name:<22} {value_str}{status_str}")

        # Band energies
        if bands:
            lines.append("")
            for band_name, energy in bands.items():
                label = band_name.replace("_", "-")
                diff_str = ""
                if band_diffs and band_name in band_diffs:
                    diff = band_diffs[band_name]
                    if abs(diff) > 3.0:
                        color = _YELLOW if abs(diff) <= 6.0 else _RED
                        diff_str = f"  {color}{diff:+.1f} dB vs ref{_RESET}"
                lines.append(f"  {label:<22} {energy:>8.1f} dB{diff_str}")

        # Frequency-dependent stereo width
        if freq_width:
            lines.append("")
            lines.append(f"  {_DIM}Frequency-dependent correlation:{_RESET}")
            for band_name, corr in freq_width.items():
                label = band_name.replace("_", "-")
                lines.append(f"    {label:<18} {corr:+.3f}")

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
) -> str:
    """Format analysis results as JSON.

    Args:
        results: List of analysis results from each module.
        filename: Name of the analyzed audio file.
        file_info: Dict with keys 'sample_rate', 'channels', 'duration'.

    Returns:
        A JSON-encoded string with file info, per-module metrics,
        all assessments, and a summary of warnings/failures.
    """
    output: dict[str, Any] = {
        "file": filename,
        "format": file_info,
    }

    all_assessments: list[dict] = []

    for result in results:
        output[result.module] = result.metrics
        for a in result.assessments:
            all_assessments.append({
                "metric": a.metric,
                "value": a.value,
                "status": a.status,
                "message": a.message,
                "reference": a.reference,
            })

    warns = sum(1 for a in all_assessments if a["status"] == "warn")
    fails = sum(1 for a in all_assessments if a["status"] == "fail")

    output["assessments"] = all_assessments
    output["summary"] = {"warnings": warns, "failures": fails}

    return json.dumps(output, indent=2)


def _format_duration(seconds: float) -> str:
    """Convert seconds to m:ss string."""
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def _format_value(key: str, value: Any) -> str:
    """Format a metric value for display based on its key suffix."""
    if isinstance(value, float):
        if "hz" in key.lower():
            return f"{value:,.0f} Hz"
        if "db" in key.lower() or "lufs" in key or "lu" in key:
            return f"{value:+.1f}"
        return f"{value:.4f}"
    return str(value)
