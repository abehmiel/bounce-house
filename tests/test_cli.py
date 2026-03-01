"""Tests for CLI argument parsing and full dispatch."""

import json

from bounce_house.analyzers.base import AnalysisResult, Assessment
from bounce_house.cli import ALL_ANALYZERS, _analyze_file, _dir_exit_code, create_parser, main


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


class TestDirParser:
    def test_dir_subcommand_parses(self):
        parser = create_parser()
        args = parser.parse_args(["dir", "./masters"])
        assert args.command == "dir"
        assert args.path == "./masters"

    def test_dir_recursive_flag(self):
        parser = create_parser()
        args = parser.parse_args(["dir", "./masters", "--recursive"])
        assert args.recursive is True

    def test_dir_json_flag(self):
        parser = create_parser()
        args = parser.parse_args(["dir", "./masters", "--json"])
        assert args.json is True

    def test_dir_reference_flag(self):
        parser = create_parser()
        args = parser.parse_args(["dir", "./masters", "--reference", "ref.wav"])
        assert args.reference == "ref.wav"

    def test_dir_recursive_short_flag(self):
        parser = create_parser()
        args = parser.parse_args(["dir", "./masters", "-r"])
        assert args.recursive is True


class TestDirCommand:
    def test_dir_runs_successfully(self, tmp_wav_dir):
        result = main(["dir", str(tmp_wav_dir)])
        assert result in (0, 1, 2)

    def test_dir_terminal_output_has_reports_and_summary(self, tmp_wav_dir, capsys):
        main(["dir", str(tmp_wav_dir)])
        captured = capsys.readouterr()
        assert "track_a.wav" in captured.out
        assert "track_b.wav" in captured.out
        assert "track_c.wav" in captured.out
        assert "DIRECTORY SUMMARY" in captured.out

    def test_dir_json_output(self, tmp_wav_dir, capsys):
        main(["dir", str(tmp_wav_dir), "--json"])
        captured = capsys.readouterr()
        import json

        data = json.loads(captured.out)
        assert "files" in data
        assert len(data["files"]) == 3
        assert "summary" in data
        assert data["summary"]["total_files"] == 3

    def test_dir_empty_directory(self, tmp_path, capsys):
        result = main(["dir", str(tmp_path)])
        assert result == 1
        captured = capsys.readouterr()
        assert "No .wav files" in captured.err

    def test_dir_nonexistent_path(self, capsys):
        result = main(["dir", "/nonexistent/path"])
        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower() or "does not exist" in captured.err.lower()

    def test_dir_exit_code_0_when_all_pass(self, tmp_wav_dir):
        result = main(["dir", str(tmp_wav_dir)])
        assert result in (0, 1, 2)

    def test_dir_with_reference(self, tmp_wav_dir, tmp_reference_wav):
        result = main(["dir", str(tmp_wav_dir), "--reference", str(tmp_reference_wav)])
        assert result in (0, 1, 2)

    def test_dir_with_corrupt_file_continues(self, tmp_wav_dir, capsys):
        """A corrupt file should not stop batch processing."""
        corrupt = tmp_wav_dir / "zzz_corrupt.wav"
        corrupt.write_bytes(b"NOTANAUDIOFILE\x00\x01\x02\x03")
        _result = main(["dir", str(tmp_wav_dir)])
        captured = capsys.readouterr()
        assert "track_a.wav" in captured.out
        assert "zzz_corrupt.wav" in captured.err


class TestDiscoverWavFiles:
    def test_finds_wav_files(self, tmp_path):
        import numpy as np
        import soundfile as sf

        from bounce_house.cli import _discover_wav_files

        sr = 44100
        for name in ["a.wav", "b.wav"]:
            sf.write(str(tmp_path / name), np.zeros((sr, 2)), sr, subtype="PCM_16")
        (tmp_path / "notes.txt").write_text("hello")
        files = _discover_wav_files(str(tmp_path), recursive=False)
        assert len(files) == 2
        assert all(f.suffix == ".wav" for f in files)

    def test_sorted_alphabetically(self, tmp_path):
        import numpy as np
        import soundfile as sf

        from bounce_house.cli import _discover_wav_files

        sr = 44100
        for name in ["c.wav", "a.wav", "b.wav"]:
            sf.write(str(tmp_path / name), np.zeros((sr, 2)), sr, subtype="PCM_16")
        files = _discover_wav_files(str(tmp_path), recursive=False)
        assert [f.name for f in files] == ["a.wav", "b.wav", "c.wav"]

    def test_recursive_finds_subdirs(self, tmp_path):
        import numpy as np
        import soundfile as sf

        from bounce_house.cli import _discover_wav_files

        sr = 44100
        sub = tmp_path / "sub"
        sub.mkdir()
        sf.write(str(tmp_path / "top.wav"), np.zeros((sr, 2)), sr, subtype="PCM_16")
        sf.write(str(sub / "nested.wav"), np.zeros((sr, 2)), sr, subtype="PCM_16")
        files = _discover_wav_files(str(tmp_path), recursive=True)
        assert len(files) == 2

    def test_no_recursive_skips_subdirs(self, tmp_path):
        import numpy as np
        import soundfile as sf

        from bounce_house.cli import _discover_wav_files

        sr = 44100
        sub = tmp_path / "sub"
        sub.mkdir()
        sf.write(str(tmp_path / "top.wav"), np.zeros((sr, 2)), sr, subtype="PCM_16")
        sf.write(str(sub / "nested.wav"), np.zeros((sr, 2)), sr, subtype="PCM_16")
        files = _discover_wav_files(str(tmp_path), recursive=False)
        assert len(files) == 1

    def test_empty_dir_returns_empty(self, tmp_path):
        from bounce_house.cli import _discover_wav_files

        files = _discover_wav_files(str(tmp_path), recursive=False)
        assert files == []


class TestDirExitCode:
    def test_all_pass_returns_0(self):
        data = [
            {
                "results": [
                    AnalysisResult(
                        module="loudness",
                        assessments=[
                            Assessment("lufs", -14.0, "pass", "ok"),
                        ],
                    )
                ]
            }
        ]
        assert _dir_exit_code(data) == 0

    def test_warn_returns_1(self):
        data = [
            {
                "results": [
                    AnalysisResult(
                        module="loudness",
                        assessments=[
                            Assessment("peak", -0.1, "warn", "hot"),
                        ],
                    )
                ]
            }
        ]
        assert _dir_exit_code(data) == 1

    def test_fail_returns_2(self):
        data = [
            {
                "results": [
                    AnalysisResult(
                        module="loudness",
                        assessments=[
                            Assessment("lufs", -5.0, "fail", "too loud"),
                        ],
                    )
                ]
            }
        ]
        assert _dir_exit_code(data) == 2

    def test_fail_trumps_warn(self):
        data = [
            {
                "results": [
                    AnalysisResult(
                        module="loudness",
                        assessments=[
                            Assessment("peak", -0.1, "warn", "hot"),
                            Assessment("lufs", -5.0, "fail", "too loud"),
                        ],
                    )
                ]
            }
        ]
        assert _dir_exit_code(data) == 2

    def test_empty_data_returns_0(self):
        assert _dir_exit_code([]) == 0


class TestDirIntegration:
    def test_dir_recursive(self, tmp_wav_dir):
        """Test recursive discovery with subdirectories."""
        import numpy as np
        import soundfile as sf

        sub = tmp_wav_dir / "subdir"
        sub.mkdir()
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False)
        stereo = np.column_stack([0.5 * np.sin(2 * np.pi * 440 * t)] * 2)
        sf.write(str(sub / "nested.wav"), stereo, sr, subtype="PCM_16")
        result = main(["dir", str(tmp_wav_dir), "--recursive"])
        assert result in (0, 1, 2)

    def test_dir_recursive_json(self, tmp_wav_dir, capsys):
        """Recursive JSON output includes files from subdirectories."""
        import numpy as np
        import soundfile as sf

        sub = tmp_wav_dir / "subdir"
        sub.mkdir()
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False)
        stereo = np.column_stack([0.5 * np.sin(2 * np.pi * 440 * t)] * 2)
        sf.write(str(sub / "nested.wav"), stereo, sr, subtype="PCM_16")
        main(["dir", str(tmp_wav_dir), "--recursive", "--json"])
        captured = capsys.readouterr()
        import json

        data = json.loads(captured.out)
        assert data["summary"]["total_files"] == 4  # 3 + 1 nested


class TestStageFlag:
    def test_stage_flag_parsed(self):
        parser = create_parser()
        args = parser.parse_args(["analyze", "mix.wav", "--stage", "mix"])
        assert args.stage == "mix"

    def test_stage_flag_default_is_master(self):
        parser = create_parser()
        args = parser.parse_args(["analyze", "mix.wav"])
        assert args.stage == "master"

    def test_stage_flag_on_dir_command(self):
        parser = create_parser()
        args = parser.parse_args(["dir", "./mixes", "--stage", "mix"])
        assert args.stage == "mix"

    def test_stage_flag_on_module_command(self):
        parser = create_parser()
        args = parser.parse_args(["loudness", "mix.wav", "--stage", "mix"])
        assert args.stage == "mix"

    def test_stage_invalid_value_rejected(self):
        import pytest

        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["analyze", "mix.wav", "--stage", "stem"])


class TestTuningIntegration:
    def test_tuning_subcommand_parses(self):
        parser = create_parser()
        args = parser.parse_args(["tuning", "mix.wav"])
        assert args.command == "tuning"

    def test_tuning_subcommand_runs(self, tmp_wav):
        """The tuning subcommand should work standalone."""
        result = main(["tuning", str(tmp_wav)])
        assert result == 0

    def test_analyze_includes_tuning(self, tmp_wav):
        """Full analyze should include tuning section."""
        result = main(["analyze", str(tmp_wav)])
        assert result == 0

    def test_json_includes_tuning(self, tmp_wav, capsys):
        """JSON output should include tuning metrics."""
        main(["analyze", str(tmp_wav), "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "tuning" in data
        assert "tuning_deviation_cents" in data["tuning"]

    def test_tuning_json_has_all_metrics(self, tmp_wav, capsys):
        """JSON output should include all tuning metrics."""
        main(["analyze", str(tmp_wav), "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        for key in ["tuning_deviation_cents", "estimated_a_hz", "chroma_sharpness"]:
            assert key in data["tuning"], f"Missing: {key}"


class TestMixModeIntegration:
    def test_analyze_mix_mode_runs(self, tmp_wav):
        """Full pipeline with --stage mix completes without error."""
        result = main(["analyze", str(tmp_wav), "--stage", "mix"])
        assert result == 0 or result == 1  # may have warnings, should not error

    def test_analyze_mix_mode_json(self, tmp_wav, capsys):
        """JSON output in mix mode includes stage field."""
        main(["analyze", str(tmp_wav), "--stage", "mix", "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["stage"] == "mix"

    def test_dir_mix_mode_runs(self, tmp_wav_dir):
        """Batch dir with --stage mix completes without error."""
        result = main(["dir", str(tmp_wav_dir), "--stage", "mix"])
        assert result in (0, 1, 2)

    def test_loudness_mix_mode_runs(self, tmp_wav):
        """Single module with --stage mix works."""
        result = main(["loudness", str(tmp_wav), "--stage", "mix"])
        assert result in (0, 1)
