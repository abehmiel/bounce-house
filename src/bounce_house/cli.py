"""CLI entry point for bounce-house."""

import argparse
import sys


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bounce-house",
        description="Analyze audio mixes for loudness, spectral balance, stereo imaging, and more.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_get_version()}")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze — full report
    analyze_parser = subparsers.add_parser("analyze", help="Run full analysis on a mix")
    analyze_parser.add_argument("file", help="Path to .wav file")
    analyze_parser.add_argument("--reference", help="Path to reference .wav file")
    analyze_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # loudness
    loudness_parser = subparsers.add_parser("loudness", help="Loudness and dynamics analysis")
    loudness_parser.add_argument("file", help="Path to .wav file")
    loudness_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # spectrum
    spectrum_parser = subparsers.add_parser("spectrum", help="Spectral analysis")
    spectrum_parser.add_argument("file", help="Path to .wav file")
    spectrum_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # stereo
    stereo_parser = subparsers.add_parser("stereo", help="Stereo imaging and phase analysis")
    stereo_parser.add_argument("file", help="Path to .wav file")
    stereo_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # compare
    compare_parser = subparsers.add_parser("compare", help="Compare mix against a reference track")
    compare_parser.add_argument("file", help="Path to .wav file")
    compare_parser.add_argument("reference", help="Path to reference .wav file")
    compare_parser.add_argument("--json", action="store_true", help="Output as JSON")

    return parser


def _get_version() -> str:
    from bounce_house import __version__
    return __version__


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    print(f"Command: {args.command}, File: {args.file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
