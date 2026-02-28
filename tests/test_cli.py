"""Tests for CLI argument parsing and full dispatch."""

import json
from bounce_house.cli import create_parser, main


class TestParser:
    def test_analyze_requires_file(self):
        parser = create_parser()
        args = parser.parse_args(["analyze", "mix.wav"])
        assert args.command == "analyze"
        assert args.file == "mix.wav"
        assert args.reference is None
        assert args.json is False

    def test_analyze_with_reference(self):
        parser = create_parser()
        args = parser.parse_args(["analyze", "mix.wav", "--reference", "ref.wav"])
        assert args.reference == "ref.wav"

    def test_analyze_with_json(self):
        parser = create_parser()
        args = parser.parse_args(["analyze", "mix.wav", "--json"])
        assert args.json is True

    def test_loudness_subcommand(self):
        parser = create_parser()
        args = parser.parse_args(["loudness", "mix.wav"])
        assert args.command == "loudness"

    def test_spectrum_subcommand(self):
        parser = create_parser()
        args = parser.parse_args(["spectrum", "mix.wav"])
        assert args.command == "spectrum"

    def test_stereo_subcommand(self):
        parser = create_parser()
        args = parser.parse_args(["stereo", "mix.wav"])
        assert args.command == "stereo"

    def test_compare_subcommand(self):
        parser = create_parser()
        args = parser.parse_args(["compare", "mix.wav", "ref.wav"])
        assert args.command == "compare"
        assert args.file == "mix.wav"
        assert args.reference == "ref.wav"

    def test_no_command_returns_1(self):
        assert main([]) == 1


class TestFullAnalysis:
    def test_analyze_runs_successfully(self, tmp_wav):
        result = main(["analyze", str(tmp_wav)])
        assert result == 0

    def test_analyze_json_output(self, tmp_wav, capsys):
        main(["analyze", str(tmp_wav), "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "loudness" in data
        assert "spectrum" in data
        assert "stereo" in data

    def test_loudness_subcommand_runs(self, tmp_wav):
        result = main(["loudness", str(tmp_wav)])
        assert result == 0

    def test_spectrum_subcommand_runs(self, tmp_wav):
        result = main(["spectrum", str(tmp_wav)])
        assert result == 0

    def test_stereo_subcommand_runs(self, tmp_wav):
        result = main(["stereo", str(tmp_wav)])
        assert result == 0

    def test_compare_runs(self, tmp_wav, tmp_reference_wav):
        result = main(["compare", str(tmp_wav), str(tmp_reference_wav)])
        assert result == 0

    def test_compare_json_output(self, tmp_wav, tmp_reference_wav, capsys):
        main(["compare", str(tmp_wav), str(tmp_reference_wav), "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "loudness" in data
        assert "band_differences" in data.get("spectrum", {})

    def test_nonexistent_file_returns_1(self):
        result = main(["analyze", "/nonexistent/file.wav"])
        assert result == 1

    def test_analyze_with_reference(self, tmp_wav, tmp_reference_wav):
        result = main(["analyze", str(tmp_wav), "--reference", str(tmp_reference_wav)])
        assert result == 0
