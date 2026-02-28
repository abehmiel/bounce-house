"""CLI entry point for bounce-house."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bounce_house.audio import load_audio
from bounce_house.analyzers.base import AnalysisResult
from bounce_house.analyzers.loudness import LoudnessAnalyzer
from bounce_house.analyzers.spectrum import SpectrumAnalyzer
from bounce_house.analyzers.stereo import StereoAnalyzer
from bounce_house.analyzers.perceptual import PerceptualAnalyzer
from bounce_house.rules import evaluate_rules
from bounce_house.metric_docs import resolve_topic
from bounce_house.report import format_terminal, format_json, format_explain_overview, format_explain_module, format_explain_metric


ALL_ANALYZERS = [
    LoudnessAnalyzer(),
    SpectrumAnalyzer(),
    StereoAnalyzer(),
    PerceptualAnalyzer(),
]

ANALYZER_MAP = {a.name: a for a in ALL_ANALYZERS}


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bounce-house",
        description="Analyze audio mixes for loudness, spectral balance, stereo imaging, and more.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_get_version()}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze — full report
    analyze_parser = subparsers.add_parser("analyze", help="Run full analysis on a mix")
    analyze_parser.add_argument("file", help="Path to .wav file")
    analyze_parser.add_argument("--reference", help="Path to reference .wav file")
    analyze_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Individual module subcommands
    for name, desc in [
        ("loudness", "Loudness and dynamics analysis"),
        ("spectrum", "Spectral analysis"),
        ("stereo", "Stereo imaging and phase analysis"),
    ]:
        sub = subparsers.add_parser(name, help=desc)
        sub.add_argument("file", help="Path to .wav file")
        sub.add_argument("--json", action="store_true", help="Output as JSON")

    # compare
    compare_parser = subparsers.add_parser("compare", help="Compare mix against a reference track")
    compare_parser.add_argument("file", help="Path to .wav file")
    compare_parser.add_argument("reference", help="Path to reference .wav file")
    compare_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # explain — metric documentation
    explain_parser = subparsers.add_parser("explain", help="Explain analysis metrics")
    explain_parser.add_argument("topic", nargs="?", default=None, help="Module or metric name (fuzzy matched)")
    explain_parser.add_argument("--technical", action="store_true", help="Include measurement standards and methods")

    return parser


def _get_version() -> str:
    from bounce_house import __version__
    return __version__


def _run_analysis(
    file_path: str,
    reference_path: str | None = None,
    analyzers: list | None = None,
    use_json: bool = False,
) -> int:
    """Run analysis and print report. Returns exit code."""
    path = Path(file_path)
    try:
        audio = load_audio(path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    reference = None
    if reference_path:
        try:
            reference = load_audio(Path(reference_path))
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    if analyzers is None:
        analyzers = ALL_ANALYZERS

    results: list[AnalysisResult] = []
    for analyzer in analyzers:
        if reference:
            result = analyzer.compare(audio, reference)
        else:
            result = analyzer.analyze(audio)

        # Apply rules
        assessments = evaluate_rules(result)
        result.assessments = assessments
        results.append(result)

    file_info = {
        "sample_rate": audio.sample_rate,
        "channels": audio.channels,
        "duration": round(audio.duration, 1),
    }

    if use_json:
        print(format_json(results, str(path), file_info))
    else:
        print(format_terminal(results, str(path), file_info))

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    use_json = getattr(args, "json", False)

    if args.command == "analyze":
        return _run_analysis(args.file, args.reference, None, use_json)
    elif args.command == "compare":
        return _run_analysis(args.file, args.reference, None, use_json)
    elif args.command == "explain":
        return _run_explain(args.topic, getattr(args, "technical", False))
    elif args.command in ANALYZER_MAP:
        analyzer = ANALYZER_MAP[args.command]
        return _run_analysis(args.file, None, [analyzer], use_json)
    else:
        parser.print_help()
        return 1


def _run_explain(topic: str | None, technical: bool) -> int:
    """Print metric documentation. Returns exit code."""
    if topic is None:
        print(format_explain_overview())
        return 0

    kind, result = resolve_topic(topic)

    if kind == "module":
        print(format_explain_module(result, technical=technical))
        return 0
    elif kind == "metric":
        print(format_explain_metric(result, technical=technical))
        return 0
    else:
        suggestions = result
        msg = f"Unknown topic '{topic}'."
        if suggestions:
            msg += f" Did you mean: {', '.join(suggestions)}?"
        print(msg, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
