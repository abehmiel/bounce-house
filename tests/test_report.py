"""Tests for report formatting."""

import json

from bounce_house.analyzers.base import AnalysisResult, Assessment
from bounce_house.report import format_dir_json, format_dir_summary, format_json, format_terminal


def _make_results():
    return [
        AnalysisResult(
            module="loudness",
            metrics={"integrated_lufs": -12.0, "true_peak_dbtp": -1.5},
            assessments=[
                Assessment(
                    "integrated_lufs",
                    -12.0,
                    "pass",
                    "Integrated loudness is -12.0 LUFS — within target range",
                ),
            ],
        ),
        AnalysisResult(
            module="stereo",
            metrics={"phase_correlation": 0.62, "stereo_width": 0.31},
        ),
    ]


class TestTerminalFormat:
    def test_returns_string(self):
        output = format_terminal(
            _make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4}
        )
        assert isinstance(output, str)

    def test_contains_file_name(self):
        output = format_terminal(
            _make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4}
        )
        assert "mix.wav" in output

    def test_contains_module_sections(self):
        output = format_terminal(
            _make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4}
        )
        assert "Loudness" in output
        assert "Stereo" in output

    def test_contains_pass_indicator(self):
        output = format_terminal(
            _make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4}
        )
        assert "PASS" in output

    def test_contains_summary(self):
        output = format_terminal(
            _make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4}
        )
        assert "warning" in output.lower() or "failure" in output.lower() or "0" in output


def test_unknown_metric_is_auto_formatted():
    """A metric not in _METRIC_NAMES should auto-format, not vanish."""
    result = AnalysisResult(
        module="loudness",
        metrics={"integrated_lufs": -12.0, "my_new_metric_db": -3.5},
        assessments=[],
    )
    output = format_terminal(
        [result], "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 60.0}
    )
    assert "My New Metric Db" in output


def test_none_value_not_displayed_as_string():
    """A metric with value None must not display as 'None'."""
    result = AnalysisResult(
        module="loudness",
        metrics={"integrated_lufs": -12.0, "crest_factor_db": None},
        assessments=[],
    )
    output = format_terminal(
        [result], "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 60.0}
    )
    assert "None" not in output


class TestJsonFormat:
    def test_returns_valid_json(self):
        output = format_json(
            _make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4}
        )
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_has_file_key(self):
        output = format_json(
            _make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4}
        )
        data = json.loads(output)
        assert data["file"] == "mix.wav"

    def test_has_module_keys(self):
        output = format_json(
            _make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4}
        )
        data = json.loads(output)
        assert "loudness" in data
        assert "stereo" in data

    def test_has_summary(self):
        output = format_json(
            _make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4}
        )
        data = json.loads(output)
        assert "summary" in data


from bounce_house.diagnostics import Diagnosis  # noqa: E402


class TestDiagnosticsTerminal:
    def test_diagnostics_section_shown(self):
        results = _make_results()
        diagnoses = [
            Diagnosis(
                pattern="over_compressed",
                name="Over-Compressed",
                severity="fail",
                diagnosis="Over-compressed master; dynamics crushed",
                advice="Reduce bus compressor ratio.",
                matched_conditions=3,
                total_conditions=3,
            ),
        ]
        output = format_terminal(
            results,
            "mix.wav",
            {"sample_rate": 44100, "channels": 2, "duration": 222.4},
            diagnoses=diagnoses,
        )
        assert "Mix Diagnostics" in output
        assert "Over-Compressed" in output
        assert "FAIL" in output
        assert "Reduce bus compressor" in output

    def test_no_diagnostics_section_when_empty(self):
        results = _make_results()
        output = format_terminal(
            results,
            "mix.wav",
            {"sample_rate": 44100, "channels": 2, "duration": 222.4},
            diagnoses=[],
        )
        assert "Mix Diagnostics" not in output

    def test_diagnostics_backwards_compatible(self):
        """Calling without diagnoses param still works."""
        results = _make_results()
        output = format_terminal(
            results,
            "mix.wav",
            {"sample_rate": 44100, "channels": 2, "duration": 222.4},
        )
        assert isinstance(output, str)
        assert "Mix Diagnostics" not in output


class TestDiagnosticsJson:
    def test_diagnostics_in_json(self):
        results = _make_results()
        diagnoses = [
            Diagnosis(
                pattern="muddy_mix",
                name="Muddy Mix",
                severity="warn",
                diagnosis="Low-mid buildup",
                advice="Cut 200-500 Hz",
                matched_conditions=2,
                total_conditions=4,
            ),
        ]
        output = format_json(
            results,
            "mix.wav",
            {"sample_rate": 44100, "channels": 2, "duration": 222.4},
            diagnoses=diagnoses,
        )
        data = json.loads(output)
        assert "diagnostics" in data
        assert len(data["diagnostics"]) == 1
        assert data["diagnostics"][0]["pattern"] == "muddy_mix"
        assert data["diagnostics"][0]["matched_conditions"] == 2

    def test_json_no_diagnostics_key_when_empty(self):
        results = _make_results()
        output = format_json(
            results,
            "mix.wav",
            {"sample_rate": 44100, "channels": 2, "duration": 222.4},
            diagnoses=[],
        )
        data = json.loads(output)
        assert "diagnostics" not in data

    def test_json_backwards_compatible(self):
        results = _make_results()
        output = format_json(
            results,
            "mix.wav",
            {"sample_rate": 44100, "channels": 2, "duration": 222.4},
        )
        data = json.loads(output)
        assert "diagnostics" not in data


def _make_file_data():
    """Create mock batch data for 2 files."""
    return [
        {
            "path": "track_a.wav",
            "file_info": {"sample_rate": 44100, "channels": 2, "duration": 180.0},
            "results": [
                AnalysisResult(
                    module="loudness",
                    metrics={
                        "integrated_lufs": -14.2,
                        "true_peak_dbtp": -0.3,
                        "crest_factor_db": 8.1,
                    },
                    assessments=[
                        Assessment("integrated_lufs", -14.2, "pass", "Loudness OK"),
                        Assessment("true_peak_dbtp", -0.3, "warn", "Peak too hot"),
                    ],
                ),
            ],
            "diagnoses": [],
        },
        {
            "path": "track_b.wav",
            "file_info": {"sample_rate": 44100, "channels": 2, "duration": 240.0},
            "results": [
                AnalysisResult(
                    module="loudness",
                    metrics={
                        "integrated_lufs": -11.8,
                        "true_peak_dbtp": -0.1,
                        "crest_factor_db": 5.2,
                    },
                    assessments=[
                        Assessment("integrated_lufs", -11.8, "fail", "Too loud"),
                    ],
                ),
            ],
            "diagnoses": [],
        },
    ]


class TestDirSummary:
    def test_returns_string(self):
        output = format_dir_summary(_make_file_data(), "./masters", [])
        assert isinstance(output, str)

    def test_contains_directory_summary_header(self):
        output = format_dir_summary(_make_file_data(), "./masters", [])
        assert "DIRECTORY SUMMARY" in output

    def test_contains_file_names(self):
        output = format_dir_summary(_make_file_data(), "./masters", [])
        assert "track_a.wav" in output
        assert "track_b.wav" in output

    def test_contains_file_count(self):
        output = format_dir_summary(_make_file_data(), "./masters", [])
        assert "2 files" in output

    def test_contains_totals(self):
        output = format_dir_summary(_make_file_data(), "./masters", [])
        assert "1 warning" in output.lower() or "1 warn" in output.lower()
        assert "1 failure" in output.lower() or "1 fail" in output.lower()

    def test_shows_worst_status_per_file(self):
        output = format_dir_summary(_make_file_data(), "./masters", [])
        assert "WARN" in output
        assert "FAIL" in output

    def test_shows_errors(self):
        errors = [("corrupt.wav", "Cannot read audio file")]
        output = format_dir_summary(_make_file_data(), "./masters", errors)
        assert "corrupt.wav" in output
        assert "Cannot read" in output


class TestDirJson:
    def test_returns_valid_json(self):
        output = format_dir_json(_make_file_data(), "./masters")
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_has_files_array(self):
        output = format_dir_json(_make_file_data(), "./masters")
        data = json.loads(output)
        assert "files" in data
        assert len(data["files"]) == 2

    def test_has_directory_key(self):
        output = format_dir_json(_make_file_data(), "./masters")
        data = json.loads(output)
        assert data["directory"] == "./masters"

    def test_has_summary(self):
        output = format_dir_json(_make_file_data(), "./masters")
        data = json.loads(output)
        assert data["summary"]["total_files"] == 2
        assert data["summary"]["total_warnings"] == 1
        assert data["summary"]["total_failures"] == 1

    def test_each_file_has_standard_structure(self):
        output = format_dir_json(_make_file_data(), "./masters")
        data = json.loads(output)
        for f in data["files"]:
            assert "file" in f
            assert "format" in f
            assert "assessments" in f
            assert "summary" in f


def _make_tuning_result():
    return AnalysisResult(
        module="tuning",
        metrics={
            "tuning_deviation_cents": 3.5,
            "estimated_a_hz": 440.9,
            "closest_standard": "A=440",
            "pitch_drift_std_cents": 1.2,
            "pitch_drift_range_cents": 2.8,
            "pitch_drift_trend_cents_per_min": 0.3,
            "chroma_sharpness": 0.82,
        },
    )


class TestTuningInTerminal:
    def test_tuning_section_header(self):
        results = _make_results() + [_make_tuning_result()]
        output = format_terminal(
            results, "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 60}
        )
        assert "Tuning" in output

    def test_tuning_deviation_displayed(self):
        results = _make_results() + [_make_tuning_result()]
        output = format_terminal(
            results, "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 60}
        )
        assert "cents" in output

    def test_estimated_a_displayed(self):
        results = _make_results() + [_make_tuning_result()]
        output = format_terminal(
            results, "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 60}
        )
        assert "440" in output


class TestTuningInJson:
    def test_json_has_tuning_key(self):
        results = _make_results() + [_make_tuning_result()]
        output = format_json(
            results, "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 60}
        )
        data = json.loads(output)
        assert "tuning" in data
        assert "tuning_deviation_cents" in data["tuning"]

    def test_json_tuning_has_all_metrics(self):
        results = _make_results() + [_make_tuning_result()]
        output = format_json(
            results, "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 60}
        )
        data = json.loads(output)
        assert data["tuning"]["chroma_sharpness"] == 0.82
        assert data["tuning"]["estimated_a_hz"] == 440.9


class TestStageInReport:
    def _make_results(self):
        from bounce_house.analyzers.base import AnalysisResult

        return [AnalysisResult(module="loudness", metrics={"integrated_lufs": -12.0})]

    def test_terminal_header_shows_master_by_default(self):
        from bounce_house.report import format_terminal

        output = format_terminal(
            self._make_results(), "test.wav", {"sample_rate": 44100, "channels": 2, "duration": 60}
        )
        assert "Master Analysis Report" in output

    def test_terminal_header_shows_mix_stage(self):
        from bounce_house.report import format_terminal

        output = format_terminal(
            self._make_results(),
            "test.wav",
            {"sample_rate": 44100, "channels": 2, "duration": 60},
            stage="mix",
        )
        assert "Pre-Master Mix" in output

    def test_json_includes_stage(self):
        import json

        from bounce_house.report import format_json

        output = format_json(
            self._make_results(),
            "test.wav",
            {"sample_rate": 44100, "channels": 2, "duration": 60},
            stage="mix",
        )
        data = json.loads(output)
        assert data["stage"] == "mix"

    def test_json_default_stage_is_master(self):
        import json

        from bounce_house.report import format_json

        output = format_json(
            self._make_results(), "test.wav", {"sample_rate": 44100, "channels": 2, "duration": 60}
        )
        data = json.loads(output)
        assert data["stage"] == "master"


class TestStrictJson:
    @staticmethod
    def _strict_loads(text: str):
        def _reject(name):
            raise AssertionError(f"non-RFC-8259 JSON constant emitted: {name}")

        return json.loads(text, parse_constant=_reject)

    def test_silent_file_json_is_strict(self, tmp_silent_wav, capsys):
        from bounce_house.cli import main

        main(["analyze", str(tmp_silent_wav), "--json"])
        data = self._strict_loads(capsys.readouterr().out)
        # Silence → integrated LUFS is -inf internally → must serialize as null
        assert data["loudness"]["integrated_lufs"] is None
        assert data["schema_version"] == 3

    def test_dir_json_is_strict_with_silent_file(self, tmp_path, capsys):
        import numpy as np
        import soundfile as sf

        from bounce_house.cli import main

        sr = 44100
        sf.write(str(tmp_path / "silent.wav"), np.zeros((sr, 2)), sr, subtype="PCM_16")
        main(["dir", str(tmp_path), "--json"])
        data = self._strict_loads(capsys.readouterr().out)
        assert data["schema_version"] == 3
        assert data["files"][0]["loudness"]["integrated_lufs"] is None

    def test_sanitize_replaces_non_finite(self):
        from bounce_house.report import _sanitize

        dirty = {"a": float("nan"), "b": [float("inf"), 1.5], "c": {"d": float("-inf")}}
        assert _sanitize(dirty) == {"a": None, "b": [None, 1.5], "c": {"d": None}}


class TestSparklines:
    def test_sparkline_maps_range(self):
        from bounce_house.report import _sparkline

        s = _sparkline([0.0, 0.5, 1.0], lo=0.0, hi=1.0)
        assert s[0] == "▁"
        assert s[-1] == "█"
        assert len(s) == 3

    def test_sparkline_handles_none(self):
        from bounce_house.report import _sparkline

        assert _sparkline([0.0, None, 1.0], lo=0.0, hi=1.0)[1] == " "

    def test_report_contains_level_sparkline(self, tmp_wav):
        from bounce_house.cli import _analyze_file
        from bounce_house.profiles import get_profile
        from bounce_house.report import format_terminal

        data = _analyze_file(str(tmp_wav), profile=get_profile("master"))
        out = format_terminal(
            data["results"], data["path"], data["file_info"], diagnoses=data["diagnoses"]
        )
        assert "Level" in out
        assert any(ch in out for ch in "▁▂▃▄▅▆▇█")

    def test_sparkline_survives_inverted_range(self):
        """Regression: lo > hi (e.g. clamped lo from an all-quiet curve) must not
        produce an out-of-range index into _SPARK_CHARS."""
        from bounce_house.report import _sparkline

        s = _sparkline([-80.0, -75.0, -70.0], lo=-60.0, hi=-70.0)
        assert len(s) == 3
        assert all(ch in "▁▂▃▄▅▆▇█" for ch in s)

    def test_report_handles_quiet_file_without_crashing(self, tmp_path):
        """Regression: a stereo file whose RMS curve is entirely below -60 dBFS
        used to crash format_terminal with an IndexError in _sparkline."""
        import numpy as np
        import soundfile as sf

        from bounce_house.cli import _analyze_file
        from bounce_house.profiles import get_profile
        from bounce_house.report import format_terminal

        sr = 44100
        duration = 1.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        # Amplitude well below -60 dBFS RMS (~0.0003 -> ~-70 dBFS).
        left = 0.0003 * np.sin(2 * np.pi * 440 * t)
        right = 0.0003 * np.sin(2 * np.pi * 440 * t + np.pi / 4)
        quiet = np.column_stack([left, right])
        path = tmp_path / "quiet.wav"
        sf.write(str(path), quiet, sr, subtype="PCM_16")

        data = _analyze_file(str(path), profile=get_profile("master"))
        out = format_terminal(
            data["results"], data["path"], data["file_info"], diagnoses=data["diagnoses"]
        )
        assert out
        assert "Level" in out

    def test_report_handles_silent_file_without_crashing(self, tmp_path):
        """Regression: an all-zeros (fully silent) file must not crash the
        terminal report either."""
        import numpy as np
        import soundfile as sf

        from bounce_house.cli import _analyze_file
        from bounce_house.profiles import get_profile
        from bounce_house.report import format_terminal

        sr = 44100
        duration = 1.0
        silence = np.zeros((int(sr * duration), 2))
        path = tmp_path / "silent.wav"
        sf.write(str(path), silence, sr, subtype="PCM_16")

        data = _analyze_file(str(path), profile=get_profile("master"))
        out = format_terminal(
            data["results"], data["path"], data["file_info"], diagnoses=data["diagnoses"]
        )
        assert out
        assert "Level" in out


class TestRhythmRendering:
    def test_terminal_shows_tempo(self, tmp_tempo_120_wav):
        from bounce_house.analyzers.rhythm import RhythmAnalyzer
        from bounce_house.audio import load_audio
        from bounce_house.report import format_terminal

        audio = load_audio(tmp_tempo_120_wav)
        result = RhythmAnalyzer().analyze(audio)
        out = format_terminal(
            [result],
            "tempo120.wav",
            {"sample_rate": 44100, "channels": 2, "duration": 16.0},
        )
        assert "Rhythm & Groove" in out
        assert "Tempo" in out
        assert "120" in out

    def test_terminal_renders_note_lengths(self, tmp_tempo_120_wav):
        from bounce_house.analyzers.rhythm import RhythmAnalyzer
        from bounce_house.audio import load_audio
        from bounce_house.report import format_terminal

        result = RhythmAnalyzer().analyze(load_audio(tmp_tempo_120_wav))
        out = format_terminal(
            [result],
            "tempo120.wav",
            {"sample_rate": 44100, "channels": 2, "duration": 16.0},
        )
        assert "1/8d" in out

    def test_terminal_omits_unmeasurable_tempo(self, tmp_wav):
        """A file too short to measure must not print a bogus BPM."""
        from bounce_house.analyzers.rhythm import RhythmAnalyzer
        from bounce_house.audio import load_audio
        from bounce_house.report import format_terminal

        result = RhythmAnalyzer().analyze(load_audio(tmp_wav))
        out = format_terminal(
            [result], "test.wav", {"sample_rate": 44100, "channels": 2, "duration": 1.0}
        )
        assert "Tempo  " not in out

    def test_terminal_shows_tempo_over_time_for_genuine_change(self, tmp_tempo_change_wav):
        from bounce_house.analyzers.rhythm import RhythmAnalyzer
        from bounce_house.audio import load_audio
        from bounce_house.report import format_terminal

        audio = load_audio(tmp_tempo_change_wav)
        result = RhythmAnalyzer().analyze(audio)
        out = format_terminal(
            [result],
            "change.wav",
            {"sample_rate": 44100, "channels": 2, "duration": audio.duration},
        )
        assert "Tempo over time:" in out

    def test_terminal_omits_tempo_over_time_for_jittering_constant_tempo(
        self, tmp_sparse_constant_wav
    ):
        from bounce_house.analyzers.rhythm import RhythmAnalyzer
        from bounce_house.audio import load_audio
        from bounce_house.report import format_terminal

        audio = load_audio(tmp_sparse_constant_wav)
        result = RhythmAnalyzer().analyze(audio)
        out = format_terminal(
            [result],
            "sparse.wav",
            {"sample_rate": 44100, "channels": 2, "duration": audio.duration},
        )
        assert "Tempo over time:" not in out
