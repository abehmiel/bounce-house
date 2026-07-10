"""CLI entry point for bounce-house."""

from __future__ import annotations

import argparse
import os
import re
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
from bounce_house.audio import load_audio
from bounce_house.diagnostics import evaluate_diagnostics
from bounce_house.genres import GENRE_NAMES  # top-level import is fine: genres.py is light
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

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def _use_color() -> bool:
    """NO_COLOR wins, then FORCE_COLOR, then TTY detection (https://no-color.org)."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return sys.stdout.isatty() and os.environ.get("TERM") != "dumb"


def _print_report(text: str) -> None:
    """Print human-facing report text, stripping ANSI codes when color is inappropriate."""
    if not _use_color():
        text = _ANSI_RE.sub("", text)
    print(text)


# Analyzer subcommand names — must not import the analyzers (librosa is slow to load)
MODULE_COMMANDS: tuple[str, ...] = (
    "loudness",
    "spectrum",
    "stereo",
    "translation",
    "perceptual",
    "tuning",
    "qc",
)


def _load_analyzers() -> list:
    """Import and instantiate all analyzers. Deferred: pulls the librosa/numba chain."""
    from bounce_house.analyzers.loudness import LoudnessAnalyzer
    from bounce_house.analyzers.perceptual import PerceptualAnalyzer
    from bounce_house.analyzers.qc import QcAnalyzer
    from bounce_house.analyzers.spectrum import SpectrumAnalyzer
    from bounce_house.analyzers.stereo import StereoAnalyzer
    from bounce_house.analyzers.translation import TranslationAnalyzer
    from bounce_house.analyzers.tuning import TuningAnalyzer

    return [
        LoudnessAnalyzer(),
        SpectrumAnalyzer(),
        StereoAnalyzer(),
        TranslationAnalyzer(),
        PerceptualAnalyzer(),
        TuningAnalyzer(),
        QcAnalyzer(),
    ]


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
    stage_parent.add_argument(
        "--genre",
        choices=list(GENRE_NAMES),
        default=None,
        help="Calibrate targets for a genre (provisional targets pending real-song evals)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze — full report
    analyze_parser = subparsers.add_parser(
        "analyze", help="Run full analysis on a mix", parents=[stage_parent]
    )
    analyze_parser.add_argument("file", help="Path to an audio file (wav/flac/aiff/ogg)")
    analyze_parser.add_argument(
        "--reference", help="Path to a reference audio file (wav/flac/aiff/ogg)"
    )
    analyze_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Individual module subcommands
    module_descriptions = {
        "loudness": "Loudness and dynamics analysis",
        "spectrum": "Spectral analysis",
        "stereo": "Stereo imaging and phase analysis",
        "translation": "Mono and small-speaker translation check",
        "perceptual": "Perceptual quality analysis",
        "tuning": "Tuning and pitch stability analysis",
        "qc": "Quality control — clipping and edge silence",
    }
    for name in MODULE_COMMANDS:
        sub = subparsers.add_parser(name, help=module_descriptions[name], parents=[stage_parent])
        sub.add_argument("file", help="Path to an audio file (wav/flac/aiff/ogg)")
        sub.add_argument("--json", action="store_true", help="Output as JSON")

    # compare
    compare_parser = subparsers.add_parser(
        "compare", help="Compare mix against a reference track", parents=[stage_parent]
    )
    compare_parser.add_argument("file", help="Path to an audio file (wav/flac/aiff/ogg)")
    compare_parser.add_argument(
        "reference", help="Path to a reference audio file (wav/flac/aiff/ogg)"
    )
    compare_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # diff — bounce-over-bounce comparison
    diff_parser = subparsers.add_parser(
        "diff",
        help="Diff two bounces of the same mix — what improved, what regressed",
        parents=[stage_parent],
    )
    diff_parser.add_argument("old", help="Previous bounce (audio file)")
    diff_parser.add_argument("new", help="New bounce (audio file)")
    diff_parser.add_argument("--json", action="store_true", help="Output as JSON")

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
        "dir", help="Analyze all audio files in a directory", parents=[stage_parent]
    )
    dir_parser.add_argument("path", help="Directory to scan for audio files")
    dir_parser.add_argument("-r", "--recursive", action="store_true", help="Include subdirectories")
    dir_parser.add_argument("--json", action="store_true", help="Output as JSON")
    dir_parser.add_argument(
        "--reference", help="Path to a reference audio file (wav/flac/aiff/ogg)"
    )

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
    warnings: list[str] = []
    if reference_path:
        reference = load_audio(Path(reference_path))
        if reference.sample_rate != audio.sample_rate:
            # Band energies are normalized per file over 20 Hz–Nyquist, so a
            # different Nyquist shifts the reference's broadband baseline and
            # produces spurious per-band differences. Resampling to a common
            # rate is deferred (Stage 3); warn so the comparison isn't trusted blindly.
            warnings.append(
                f"Reference sample rate ({reference.sample_rate} Hz) differs from "
                f"the mix ({audio.sample_rate} Hz); spectral band comparisons may be "
                "unreliable until both are at the same rate."
            )
    if analyzers is None:
        analyzers = _load_analyzers()
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
        "warnings": warnings,
    }


def _run_analysis(
    file_path: str,
    reference_path: str | None = None,
    analyzers: list | None = None,
    use_json: bool = False,
    profile=None,
    genre=None,
) -> int:
    """Run analysis and print report. Returns exit code."""
    active_analyzers = analyzers if analyzers is not None else _load_analyzers()
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
    for warning in data.get("warnings", []):
        print(f"Warning: {warning}", file=sys.stderr)
    if use_json:
        print(
            format_json(
                data["results"],
                data["path"],
                data["file_info"],
                diagnoses=data["diagnoses"],
                stage=profile.name,
                genre=genre,
            )
        )
    else:
        _print_report(
            format_terminal(
                data["results"],
                data["path"],
                data["file_info"],
                diagnoses=data["diagnoses"],
                stage=profile.name,
                genre=genre,
            )
        )
    return _exit_code_for_results(data["results"])


def _discover_audio_files(directory: str, recursive: bool = False) -> list[Path]:
    """Find supported audio files in a directory, sorted alphabetically."""
    from bounce_house.audio import SUPPORTED_EXTENSIONS

    dir_path = Path(directory)
    candidates = dir_path.rglob("*") if recursive else dir_path.glob("*")
    files = [p for p in candidates if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
    return sorted(files, key=lambda p: p.name.lower())


def _run_dir(
    directory: str,
    recursive: bool = False,
    reference_path: str | None = None,
    use_json: bool = False,
    profile=None,
    genre=None,
) -> int:
    """Analyze all audio files in a directory. Returns exit code."""
    dir_path = Path(directory)
    if not dir_path.is_dir():
        print(f"Error: Directory does not exist: {directory}", file=sys.stderr)
        return 1

    wav_files = _discover_audio_files(directory, recursive)
    if not wav_files:
        print(f"Error: No audio files found in {directory}", file=sys.stderr)
        return 1

    analyzer_list = _load_analyzers()
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
        module_task = progress.add_task("Modules", total=len(analyzer_list), visible=False)

        for wav_path in wav_files:
            progress.update(file_task, description=f"Analyzing {wav_path.name}")
            progress.update(module_task, completed=0, total=len(analyzer_list), visible=True)

            def on_module(name: str):
                progress.update(module_task, description=f"  {name}")
                progress.advance(module_task)

            try:
                data = _analyze_file(
                    str(wav_path),
                    reference_path,
                    analyzers=analyzer_list,
                    on_module=on_module,
                    profile=profile,
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
        print(format_dir_json(file_data, directory, errors, stage=profile.name, genre=genre))
    else:
        for data in file_data:
            _print_report(
                format_terminal(
                    data["results"],
                    data["path"],
                    data["file_info"],
                    diagnoses=data["diagnoses"],
                    stage=profile.name,
                    genre=genre,
                )
            )
        _print_report(
            format_dir_summary(file_data, directory, errors, stage=profile.name, genre=genre)
        )

    return _batch_exit_code(file_data, errors)


def _run_diff(old_path: str, new_path: str, use_json: bool = False, profile=None) -> int:
    """Diff two bounces. Exit 0 = no regressions, 1 = regressions or new diagnostics."""
    from bounce_house.bounce_diff import compute_diff
    from bounce_house.report import format_diff_json, format_diff_terminal

    try:
        old_data = _analyze_file(old_path, profile=profile)
        new_data = _analyze_file(new_path, profile=profile)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    diff = compute_diff(old_data, new_data)
    if use_json:
        print(format_diff_json(diff, old_path, new_path))
    else:
        _print_report(format_diff_terminal(diff, old_path, new_path))

    if diff.regressions or diff.diagnostics_introduced:
        return 1
    return 0


def _exit_code_for_results(results: list[AnalysisResult]) -> int:
    """Exit code from assessments: 0 = all pass, 1 = warnings, 2 = failures."""
    statuses = {a.status for r in results for a in r.assessments}
    if "fail" in statuses:
        return 2
    if "warn" in statuses:
        return 1
    return 0


def _dir_exit_code(file_data: list[dict]) -> int:
    """Determine exit code from batch results. 0=pass, 1=warn, 2=fail."""
    return max((_exit_code_for_results(data["results"]) for data in file_data), default=0)


def _batch_exit_code(file_data: list[dict], errors: list[tuple[str, str]]) -> int:
    """Batch exit code including skipped files.

    Same 0/1/2 assessment ranking as `_dir_exit_code`, but any skipped
    (unreadable/corrupt) file forces at least exit 1 — otherwise a batch that
    silently drops inputs could report success and become a false green in CI.
    """
    return max(_dir_exit_code(file_data), 1 if errors else 0)


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    use_json = getattr(args, "json", False)
    profile = get_profile(getattr(args, "stage", "master"))

    genre_name = getattr(args, "genre", None)
    genre = None
    if genre_name:
        from bounce_house.genres import apply_genre, get_genre

        genre = get_genre(genre_name)
        profile = apply_genre(profile, genre)

    if args.command == "analyze" or args.command == "compare":
        return _run_analysis(
            args.file, args.reference, None, use_json, profile=profile, genre=genre
        )
    elif args.command == "explain":
        return _run_explain(args.topic, getattr(args, "technical", False))
    elif args.command == "dir":
        return _run_dir(
            args.path,
            getattr(args, "recursive", False),
            getattr(args, "reference", None),
            use_json,
            profile=profile,
            genre=genre,
        )
    elif args.command == "diff":
        return _run_diff(args.old, args.new, use_json, profile=profile)
    elif args.command in MODULE_COMMANDS:
        analyzer = next(a for a in _load_analyzers() if a.name == args.command)
        return _run_analysis(args.file, None, [analyzer], use_json, profile=profile, genre=genre)
    else:
        parser.print_help()
        return 1


def _run_explain(topic: str | None, technical: bool) -> int:
    """Print metric documentation. Returns exit code."""
    if topic is None:
        _print_report(format_explain_overview())
        return 0

    kind, result = resolve_topic(topic)

    if kind == "module":
        assert isinstance(result, str)
        _print_report(format_explain_module(result, technical=technical))
        return 0
    elif kind == "metric":
        assert isinstance(result, str)
        _print_report(format_explain_metric(result, technical=technical))
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
