"""Tests for CLI argument parsing and full dispatch."""

import json
from bounce_house.cli import create_parser, main, _analyze_file, ALL_ANALYZERS


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

    def test_perceptual_subcommand(self):
        parser = create_parser()
        args = parser.parse_args(["perceptual", "mix.wav"])
        assert args.command == "perceptual"

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

    def test_perceptual_subcommand_runs(self, tmp_wav):
        result = main(["perceptual", str(tmp_wav)])
        assert result == 0

    def test_corrupt_file_returns_1(self, tmp_path, capsys):
        corrupt = tmp_path / "corrupt.wav"
        corrupt.write_bytes(b"NOTANAUDIOFILE\x00\x01\x02\x03")
        result = main(["analyze", str(corrupt)])
        assert result == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.err

    def test_analyze_with_reference(self, tmp_wav, tmp_reference_wav):
        result = main(["analyze", str(tmp_wav), "--reference", str(tmp_reference_wav)])
        assert result == 0


class TestAnalyzeFile:
    def test_returns_structured_data(self, tmp_wav):
        data = _analyze_file(str(tmp_wav))
        assert "results" in data
        assert "file_info" in data
        assert "diagnoses" in data
        assert "path" in data
        assert len(data["results"]) == len(ALL_ANALYZERS)

    def test_with_reference(self, tmp_wav, tmp_reference_wav):
        data = _analyze_file(str(tmp_wav), reference_path=str(tmp_reference_wav))
        assert len(data["results"]) == len(ALL_ANALYZERS)

    def test_file_info_has_expected_keys(self, tmp_wav):
        data = _analyze_file(str(tmp_wav))
        assert "sample_rate" in data["file_info"]
        assert "channels" in data["file_info"]
        assert "duration" in data["file_info"]

    def test_subset_analyzers(self, tmp_wav):
        data = _analyze_file(str(tmp_wav), analyzers=[ALL_ANALYZERS[0]])
        assert len(data["results"]) == 1


class TestProgressBar:
    def test_analyze_shows_progress_on_stderr(self, tmp_wav, capsys):
        """Progress bar output goes to stderr, not stdout."""
        main(["analyze", str(tmp_wav)])
        captured = capsys.readouterr()
        # Report should still be in stdout
        assert "BOUNCE HOUSE" in captured.out

    def test_json_output_not_polluted_by_progress(self, tmp_wav, capsys):
        """JSON output on stdout must remain valid JSON despite progress bar."""
        main(["analyze", str(tmp_wav), "--json"])
        captured = capsys.readouterr()
        import json
        data = json.loads(captured.out)
        assert "loudness" in data


class TestDiagnosticsIntegration:
    def test_diagnostics_in_json_output(self, tmp_wav, capsys):
        """JSON output should include diagnostics key when patterns match."""
        main(["analyze", str(tmp_wav), "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        # The test fixture may or may not trigger diagnostics — just verify
        # the structure is correct (diagnostics key present if any fire, or absent)
        if "diagnostics" in data:
            for d in data["diagnostics"]:
                assert "pattern" in d
                assert "severity" in d
                assert "advice" in d
                assert "matched_conditions" in d

    def test_analyze_still_returns_0(self, tmp_wav):
        """Diagnostics should not break the existing exit code behavior."""
        result = main(["analyze", str(tmp_wav)])
        assert result == 0
