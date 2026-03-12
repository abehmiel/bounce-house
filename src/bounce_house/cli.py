"""CLI entry point for bounce-house."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from bounce_house.analyzers.base import AnalysisResult
from bounce_house.analyzers.loudness import LoudnessAnalyzer
from bounce_house.analyzers.perceptual import PerceptualAnalyzer
from bounce_house.analyzers.spectrum import SpectrumAnalyzer
from bounce_house.analyzers.stereo import StereoAnalyzer
from bounce_house.analyzers.tuning import TuningAnalyzer
from bounce_house.audio import load_audio
from bounce_house.diagnostics import evaluate_diagnostics
from bounce_house.metric_docs import resolve_topic
from bounce_house.profiles import get_profile
from bounce_house.report import (
    format_dir_json,
    format_dir_summary,
    format_explain_metric,
    format_explain_module,
    format_explain_overview,
    format_json,
    format_terminal,
)
from bounce_house.rules import evaluate_rules

_STDERR_CONSOLE = Console(stderr=True)


ALL_ANALYZERS = [
    LoudnessAnalyzer(),
    SpectrumAnalyzer(),
    StereoAnalyzer(),
    PerceptualAnalyzer(),
    TuningAnalyzer(),
]

ANALYZER_MAP = {a.name: a for a in ALL_ANALYZERS}


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bounce-house",
        description="Analyze audio mixes for loudness, spectral balance, stereo imaging, and more.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_get_version()}")

    # Shared parent parser for --stage flag (inherited by all subcommands)
    stage_parent = argparse.ArgumentParser(add_help=False)
    stage_parent.add_argument(
        "--stage",
        choices=["mix", "master"],
        default="master",
        help=(
            "Analysis stage: 'master' (default) or 'mix' (pre-master mix with adjusted thresholds)"
        ),
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze — full report
    analyze_parser = subparsers.add_parser(
        "analyze", help="Run full analysis on a mix", parents=[stage_parent]
    )
    analyze_parser.add_argument("file", help="Path to .wav file")
    analyze_parser.add_argument("--reference", help="Path to reference .wav file")
    analyze_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Individual module subcommands
    for name, desc in [
        ("loudness", "Loudness and dynamics analysis"),
        ("spectrum", "Spectral analysis"),
        ("stereo", "Stereo imaging and phase analysis"),
        ("perceptual", "Perceptual quality analysis"),
        ("tuning", "Tuning and pitch stability analysis"),
    ]:
        sub = subparsers.add_parser(name, help=desc, parents=[stage_parent])
        sub.add_argument("file", help="Path to .wav file")
        sub.add_argument("--json", action="store_true", help="Output as JSON")

    # compare
    compare_parser = subparsers.add_parser(
        "compare", help="Compare mix against a reference track", parents=[stage_parent]
    )
    compare_parser.add_argument("file", help="Path to .wav file")
    compare_parser.add_argument("reference", help="Path to reference .wav file")
    compare_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # explain — metric documentation
    explain_parser = subparsers.add_parser("explain", help="Explain analysis metrics")
    explain_parser.add_argument(
        "topic", nargs="?", default=None, help="Module or metric name (fuzzy matched)"
    )
    explain_parser.add_argument(
        "--technical", action="store_true", help="Include measurement standards and methods"
    )

    # dir — batch analysis
    dir_parser = subparsers.add_parser(
        "dir", help="Analyze all .wav files in a directory", parents=[stage_parent]
    )
    dir_parser.add_argument("path", help="Directory to scan for .wav files")
    dir_parser.add_argument("-r", "--recursive", action="store_true", help="Include subdirectories")
    dir_parser.add_argument("--json", action="store_true", help="Output as JSON")
    dir_parser.add_argument("--reference", help="Path to reference .wav file")

    return parser


def _get_version() -> str:
    from bounce_house import __version__

    return __version__


def _analyze_file(
    file_path: str,
    reference_path: str | None = None,
    analyzers: list | None = None,
    on_module: Callable[[str], None] | None = None,
    profile=None,
) -> dict:
    """Run all computation for a file and return structured data.

    Returns a dict with keys: path, results, file_info, diagnoses.
    Raises FileNotFoundError or ValueError on bad input.
    """
    path = Path(file_path)
    audio = load_audio(path)
    reference = None
    if reference_path:
        reference = load_audio(Path(reference_path))
    if analyzers is None:
        analyzers = ALL_ANALYZERS
    results: list[AnalysisResult] = []
    for analyzer in analyzers:
        if on_module:
            on_module(analyzer.name)
        if reference:  # noqa: SIM108
            result = analyzer.compare(audio, reference)
        else:
            result = analyzer.analyze(audio)
        assessments = evaluate_rules(result, profile)
        result.assessments = assessments
        results.append(result)
    diagnoses = evaluate_diagnostics(results, profile)
    file_info = {
        "sample_rate": audio.sample_rate,
        "channels": audio.channels,
        "duration": round(audio.duration, 1),
    }
    return {
        "path": str(path),
        "results": results,
        "file_info": file_info,
        "diagnoses": diagnoses,
    }


def _run_analysis(
    file_path: str,
    reference_path: str | None = None,
    analyzers: list | None = None,
    use_json: bool = False,
    profile=None,
) -> int:
    """Run analysis and print report. Returns exit code."""
    active_analyzers = analyzers if analyzers is not None else ALL_ANALYZERS
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=_STDERR_CONSOLE,
            transient=True,
        ) as progress:
            task = progress.add_task("Analyzing modules", total=len(active_analyzers))

            def on_module(name: str):
                progress.update(task, description=f"Analyzing {name}")
                progress.advance(task)

            data = _analyze_file(
                file_path, reference_path, active_analyzers, on_module=on_module, profile=profile
            )
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    if use_json:
        print(
            format_json(
                data["results"],
                data["path"],
                data["file_info"],
                diagnoses=data["diagnoses"],
                stage=profile.name,
            )
        )
    else:
        print(
            format_terminal(
                data["results"],
                data["path"],
                data["file_info"],
                diagnoses=data["diagnoses"],
                stage=profile.name,
            )
        )
    return 0


def _discover_wav_files(directory: str, recursive: bool = False) -> list[Path]:
    """Find .wav files in a directory, sorted alphabetically."""
    dir_path = Path(directory)
    if recursive:  # noqa: SIM108
        files = list(dir_path.rglob("*.wav"))
    else:
        files = list(dir_path.glob("*.wav"))
    return sorted(files, key=lambda p: p.name.lower())


def _run_dir(
    directory: str,
    recursive: bool = False,
    reference_path: str | None = None,
    use_json: bool = False,
    profile=None,
) -> int:
    """Analyze all .wav files in a directory. Returns exit code."""
    dir_path = Path(directory)
    if not dir_path.is_dir():
        print(f"Error: Directory does not exist: {directory}", file=sys.stderr)
        return 1

    wav_files = _discover_wav_files(directory, recursive)
    if not wav_files:
        print(f"Error: No .wav files found in {directory}", file=sys.stderr)
        return 1

    file_data: list[dict] = []
    errors: list[tuple[str, str]] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=_STDERR_CONSOLE,
        transient=True,
    ) as progress:
        file_task = progress.add_task("Analyzing files", total=len(wav_files))
        module_task = progress.add_task("Modules", total=len(ALL_ANALYZERS), visible=False)

        for wav_path in wav_files:
            progress.update(file_task, description=f"Analyzing {wav_path.name}")
            progress.update(module_task, completed=0, total=len(ALL_ANALYZERS), visible=True)

            def on_module(name: str):
                progress.update(module_task, description=f"  {name}")
                progress.advance(module_task)

            try:
                data = _analyze_file(
                    str(wav_path), reference_path, on_module=on_module, profile=profile
                )
                file_data.append(data)
            except (FileNotFoundError, ValueError) as e:
                errors.append((str(wav_path.name), str(e)))
                print(f"Error: {wav_path.name}: {e}", file=sys.stderr)

            progress.update(module_task, visible=False)
            progress.advance(file_task)

    if not file_data and errors:
        print("Error: All files failed to load.", file=sys.stderr)
        return 1

    if use_json:
        print(format_dir_json(file_data, directory, stage=profile.name))
    else:
        for data in file_data:
            print(
                format_terminal(
                    data["results"],
                    data["path"],
                    data["file_info"],
                    diagnoses=data["diagnoses"],
                    stage=profile.name,
                )
            )
        print(format_dir_summary(file_data, directory, errors, stage=profile.name))

    return _dir_exit_code(file_data)


def _dir_exit_code(file_data: list[dict]) -> int:
    """Determine exit code from batch results. 0=pass, 1=warn, 2=fail."""
    has_fail = False
    has_warn = False
    for data in file_data:
        for result in data["results"]:
            for a in result.assessments:
                if a.status == "fail":
                    has_fail = True
                elif a.status == "warn":
                    has_warn = True
    if has_fail:
        return 2
    if has_warn:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    use_json = getattr(args, "json", False)
    profile = get_profile(getattr(args, "stage", "master"))

    if args.command == "analyze" or args.command == "compare":
        return _run_analysis(args.file, args.reference, None, use_json, profile=profile)
    elif args.command == "explain":
        return _run_explain(args.topic, getattr(args, "technical", False))
    elif args.command == "dir":
        return _run_dir(
            args.path,
            getattr(args, "recursive", False),
            getattr(args, "reference", None),
            use_json,
            profile=profile,
        )
    elif args.command in ANALYZER_MAP:
        analyzer = ANALYZER_MAP[args.command]
        return _run_analysis(args.file, None, [analyzer], use_json, profile=profile)
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
        assert isinstance(result, str)
        print(format_explain_module(result, technical=technical))
        return 0
    elif kind == "metric":
        assert isinstance(result, str)
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
