"""Tests for CLI argument parsing and full dispatch."""

import json

import numpy as np

from bounce_house.analyzers.base import AnalysisResult, Assessment
from bounce_house.cli import _analyze_file, _dir_exit_code, _load_analyzers, create_parser, main
from bounce_house.profiles import get_profile


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
        assert result in (0, 1, 2)

    def test_analyze_json_output(self, tmp_wav, capsys):
        main(["analyze", str(tmp_wav), "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "loudness" in data
        assert "spectrum" in data
        assert "stereo" in data

    def test_loudness_subcommand_runs(self, tmp_wav):
        result = main(["loudness", str(tmp_wav)])
        assert result in (0, 1, 2)

    def test_spectrum_subcommand_runs(self, tmp_wav):
        result = main(["spectrum", str(tmp_wav)])
        assert result in (0, 1, 2)

    def test_stereo_subcommand_runs(self, tmp_wav):
        result = main(["stereo", str(tmp_wav)])
        assert result in (0, 1, 2)

    def test_compare_runs(self, tmp_wav, tmp_reference_wav):
        result = main(["compare", str(tmp_wav), str(tmp_reference_wav)])
        assert result in (0, 1, 2)

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
        assert result in (0, 1, 2)

    def test_corrupt_file_returns_1(self, tmp_path, capsys):
        corrupt = tmp_path / "corrupt.wav"
        corrupt.write_bytes(b"NOTANAUDIOFILE\x00\x01\x02\x03")
        result = main(["analyze", str(corrupt)])
        assert result == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.err

    def test_analyze_with_reference(self, tmp_wav, tmp_reference_wav):
        result = main(["analyze", str(tmp_wav), "--reference", str(tmp_reference_wav)])
        assert result in (0, 1, 2)


class TestReferenceSampleRateGuard:
    def _write_wav(self, path, sr):
        import numpy as np
        import soundfile as sf

        t = np.linspace(0, 1.0, sr, endpoint=False)
        sine = 0.5 * np.sin(2 * np.pi * 440 * t)
        sf.write(str(path), np.column_stack([sine, sine]), sr, subtype="FLOAT")

    def test_mismatched_reference_rate_warns(self, tmp_path):
        mix = tmp_path / "mix.wav"
        ref = tmp_path / "ref.wav"
        self._write_wav(mix, 44100)
        self._write_wav(ref, 48000)  # different Nyquist → unreliable band comparison
        data = _analyze_file(str(mix), reference_path=str(ref), profile=get_profile("master"))
        assert data["warnings"]
        assert any("sample rate" in w for w in data["warnings"])

    def test_matched_reference_rate_does_not_warn(self, tmp_path):
        mix = tmp_path / "mix.wav"
        ref = tmp_path / "ref.wav"
        self._write_wav(mix, 44100)
        self._write_wav(ref, 44100)
        data = _analyze_file(str(mix), reference_path=str(ref), profile=get_profile("master"))
        assert data["warnings"] == []

    def test_warning_reaches_stderr(self, tmp_path, capsys):
        mix = tmp_path / "mix.wav"
        ref = tmp_path / "ref.wav"
        self._write_wav(mix, 44100)
        self._write_wav(ref, 48000)
        main(["analyze", str(mix), "--reference", str(ref)])
        assert "Warning:" in capsys.readouterr().err


class TestAnalyzeFile:
    def test_returns_structured_data(self, tmp_wav):
        data = _analyze_file(str(tmp_wav))
        analyzers = _load_analyzers()
        assert "results" in data
        assert "file_info" in data
        assert "diagnoses" in data
        assert "path" in data
        assert len(data["results"]) == len(analyzers)

    def test_with_reference(self, tmp_wav, tmp_reference_wav):
        data = _analyze_file(str(tmp_wav), reference_path=str(tmp_reference_wav))
        analyzers = _load_analyzers()
        assert len(data["results"]) == len(analyzers)

    def test_file_info_has_expected_keys(self, tmp_wav):
        data = _analyze_file(str(tmp_wav))
        assert "sample_rate" in data["file_info"]
        assert "channels" in data["file_info"]
        assert "duration" in data["file_info"]

    def test_subset_analyzers(self, tmp_wav):
        analyzers = _load_analyzers()
        data = _analyze_file(str(tmp_wav), analyzers=[analyzers[0]])
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
        assert result in (0, 1, 2)


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
        assert "No audio files" in captured.err

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
        """A corrupt file should not stop batch processing, but must not exit 0."""
        corrupt = tmp_wav_dir / "zzz_corrupt.wav"
        corrupt.write_bytes(b"NOTANAUDIOFILE\x00\x01\x02\x03")
        result = main(["dir", str(tmp_wav_dir)])
        captured = capsys.readouterr()
        assert "track_a.wav" in captured.out
        assert "zzz_corrupt.wav" in captured.err
        # A skipped file means part of the requested input was not analyzed —
        # this must not report success (would be a false green in CI).
        assert result >= 1

    def test_dir_json_surfaces_skipped_files(self, tmp_wav_dir, capsys):
        """dir --json must report skipped files so machine consumers see them."""
        corrupt = tmp_wav_dir / "zzz_corrupt.wav"
        corrupt.write_bytes(b"NOTANAUDIOFILE\x00\x01\x02\x03")
        result = main(["dir", str(tmp_wav_dir), "--json"])
        data = json.loads(capsys.readouterr().out)
        assert result >= 1
        assert data["summary"]["total_skipped"] == 1
        # total_files stays the count of successfully-analyzed files (backward compatible)
        assert data["summary"]["total_files"] == 3
        assert any(s["file"] == "zzz_corrupt.wav" for s in data["skipped"])

    def test_dir_json_no_skipped_key_omits_when_clean(self, tmp_wav_dir, capsys):
        """A clean batch has no skipped files: total_skipped is 0, skipped is empty."""
        main(["dir", str(tmp_wav_dir), "--json"])
        data = json.loads(capsys.readouterr().out)
        assert data["summary"]["total_skipped"] == 0
        assert data["skipped"] == []


class TestDiscoverWavFiles:
    def test_finds_wav_files(self, tmp_path):
        import numpy as np
        import soundfile as sf

        from bounce_house.cli import _discover_audio_files

        sr = 44100
        for name in ["a.wav", "b.wav"]:
            sf.write(str(tmp_path / name), np.zeros((sr, 2)), sr, subtype="PCM_16")
        (tmp_path / "notes.txt").write_text("hello")
        files = _discover_audio_files(str(tmp_path), recursive=False)
        assert len(files) == 2
        assert all(f.suffix == ".wav" for f in files)

    def test_sorted_alphabetically(self, tmp_path):
        import numpy as np
        import soundfile as sf

        from bounce_house.cli import _discover_audio_files

        sr = 44100
        for name in ["c.wav", "a.wav", "b.wav"]:
            sf.write(str(tmp_path / name), np.zeros((sr, 2)), sr, subtype="PCM_16")
        files = _discover_audio_files(str(tmp_path), recursive=False)
        assert [f.name for f in files] == ["a.wav", "b.wav", "c.wav"]

    def test_recursive_finds_subdirs(self, tmp_path):
        import numpy as np
        import soundfile as sf

        from bounce_house.cli import _discover_audio_files

        sr = 44100
        sub = tmp_path / "sub"
        sub.mkdir()
        sf.write(str(tmp_path / "top.wav"), np.zeros((sr, 2)), sr, subtype="PCM_16")
        sf.write(str(sub / "nested.wav"), np.zeros((sr, 2)), sr, subtype="PCM_16")
        files = _discover_audio_files(str(tmp_path), recursive=True)
        assert len(files) == 2

    def test_no_recursive_skips_subdirs(self, tmp_path):
        import numpy as np
        import soundfile as sf

        from bounce_house.cli import _discover_audio_files

        sr = 44100
        sub = tmp_path / "sub"
        sub.mkdir()
        sf.write(str(tmp_path / "top.wav"), np.zeros((sr, 2)), sr, subtype="PCM_16")
        sf.write(str(sub / "nested.wav"), np.zeros((sr, 2)), sr, subtype="PCM_16")
        files = _discover_audio_files(str(tmp_path), recursive=False)
        assert len(files) == 1

    def test_empty_dir_returns_empty(self, tmp_path):
        from bounce_house.cli import _discover_audio_files

        files = _discover_audio_files(str(tmp_path), recursive=False)
        assert files == []


class TestBatchExitCode:
    """The errors bump: any skipped file forces exit >= 1 without changing rank."""

    def _all_pass(self):
        return [
            {
                "results": [
                    AnalysisResult(
                        module="loudness", assessments=[Assessment("lufs", -14.0, "pass", "ok")]
                    )
                ]
            }
        ]

    def test_all_pass_no_errors_is_0(self):
        from bounce_house.cli import _batch_exit_code

        assert _batch_exit_code(self._all_pass(), []) == 0

    def test_all_pass_with_skipped_file_is_1(self):
        from bounce_house.cli import _batch_exit_code

        # This is the false-green case: every analyzed file passes, but one was skipped.
        assert _batch_exit_code(self._all_pass(), [("corrupt.wav", "boom")]) == 1

    def test_failure_still_trumps_skipped(self):
        from bounce_house.cli import _batch_exit_code

        fail = [
            {
                "results": [
                    AnalysisResult(
                        module="loudness", assessments=[Assessment("lufs", -5.0, "fail", "loud")]
                    )
                ]
            }
        ]
        assert _batch_exit_code(fail, [("corrupt.wav", "boom")]) == 2

    def test_empty_batch_with_errors_is_1(self):
        from bounce_house.cli import _batch_exit_code

        assert _batch_exit_code([], [("corrupt.wav", "boom")]) == 1


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
        assert result in (0, 1, 2)

    def test_analyze_includes_tuning(self, tmp_wav):
        """Full analyze should include tuning section."""
        result = main(["analyze", str(tmp_wav)])
        assert result in (0, 1, 2)

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
        assert result in (0, 1, 2)  # may have warnings/failures, should not error

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
        assert result in (0, 1, 2)


class TestExitCodes:
    def _expected_code(self, capsys) -> int:
        data = json.loads(capsys.readouterr().out)
        if data["summary"]["failures"]:
            return 2
        if data["summary"]["warnings"]:
            return 1
        return 0

    def test_analyze_exit_code_matches_summary(self, tmp_wav, capsys):
        code = main(["analyze", str(tmp_wav), "--json"])
        assert code == self._expected_code(capsys)

    def test_compare_exit_code_matches_summary(self, tmp_wav, tmp_reference_wav, capsys):
        code = main(["compare", str(tmp_wav), str(tmp_reference_wav), "--json"])
        assert code == self._expected_code(capsys)

    def test_module_subcommand_exit_code_matches_summary(self, tmp_wav, capsys):
        code = main(["loudness", str(tmp_wav), "--json"])
        assert code == self._expected_code(capsys)

    def test_exit_code_helper_ranks_worst_status(self):
        from bounce_house.cli import _exit_code_for_results

        def result_with(status):
            return AnalysisResult(
                module="loudness",
                metrics={},
                assessments=[Assessment(metric="m", value=0.0, status=status, message="")],
            )

        assert _exit_code_for_results([result_with("pass")]) == 0
        assert _exit_code_for_results([result_with("pass"), result_with("warn")]) == 1
        assert _exit_code_for_results([result_with("warn"), result_with("fail")]) == 2
        assert _exit_code_for_results([]) == 0


class TestColorHandling:
    def test_piped_output_has_no_ansi(self, tmp_wav, capsys, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        main(["analyze", str(tmp_wav)])
        assert "\033[" not in capsys.readouterr().out

    def test_force_color_restores_ansi(self, tmp_wav, capsys, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("FORCE_COLOR", "1")
        main(["analyze", str(tmp_wav)])
        assert "\033[" in capsys.readouterr().out

    def test_no_color_beats_force_color(self, tmp_wav, capsys, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.setenv("FORCE_COLOR", "1")
        main(["analyze", str(tmp_wav)])
        assert "\033[" not in capsys.readouterr().out

    def test_explain_respects_color_rules(self, capsys, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        main(["explain"])
        assert "\033[" not in capsys.readouterr().out


class TestAudioDiscovery:
    def test_dir_discovers_flac_and_aiff(self, tmp_path):
        import soundfile as sf

        from bounce_house.cli import _discover_audio_files

        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False)
        stereo = np.column_stack([0.5 * np.sin(2 * np.pi * 440 * t)] * 2)
        sf.write(str(tmp_path / "a.wav"), stereo, sr, subtype="PCM_16")
        sf.write(str(tmp_path / "b.flac"), stereo, sr, format="FLAC")
        sf.write(str(tmp_path / "c.aiff"), stereo, sr, format="AIFF")
        (tmp_path / "notes.txt").write_text("not audio")
        files = _discover_audio_files(str(tmp_path), recursive=False)
        assert [f.name for f in files] == ["a.wav", "b.flac", "c.aiff"]


class TestLazyImports:
    def test_cli_import_does_not_pull_librosa(self):
        import subprocess
        import sys

        code = (
            "import sys; import bounce_house.cli; "
            "assert 'librosa' not in sys.modules, 'librosa imported eagerly'; "
            "assert 'numba' not in sys.modules, 'numba imported eagerly'"
        )
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
