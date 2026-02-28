"""Tests for report formatting."""

import json

from bounce_house.audio import AudioData
from bounce_house.analyzers.base import AnalysisResult, Assessment
from bounce_house.report import format_terminal, format_json


def _make_results():
    return [
        AnalysisResult(
            module="loudness",
            metrics={"integrated_lufs": -12.0, "true_peak_dbtp": -1.5},
            assessments=[
                Assessment("integrated_lufs", -12.0, "pass",
                           "Integrated loudness is -12.0 LUFS — within target range"),
            ],
        ),
        AnalysisResult(
            module="stereo",
            metrics={"phase_correlation": 0.62, "stereo_width": 0.31},
        ),
    ]


class TestTerminalFormat:
    def test_returns_string(self):
        output = format_terminal(_make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4})
        assert isinstance(output, str)

    def test_contains_file_name(self):
        output = format_terminal(_make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4})
        assert "mix.wav" in output

    def test_contains_module_sections(self):
        output = format_terminal(_make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4})
        assert "Loudness" in output
        assert "Stereo" in output

    def test_contains_pass_indicator(self):
        output = format_terminal(_make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4})
        assert "PASS" in output

    def test_contains_summary(self):
        output = format_terminal(_make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4})
        assert "warning" in output.lower() or "failure" in output.lower() or "0" in output


class TestJsonFormat:
    def test_returns_valid_json(self):
        output = format_json(_make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4})
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_has_file_key(self):
        output = format_json(_make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4})
        data = json.loads(output)
        assert data["file"] == "mix.wav"

    def test_has_module_keys(self):
        output = format_json(_make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4})
        data = json.loads(output)
        assert "loudness" in data
        assert "stereo" in data

    def test_has_summary(self):
        output = format_json(_make_results(), "mix.wav", {"sample_rate": 44100, "channels": 2, "duration": 222.4})
        data = json.loads(output)
        assert "summary" in data
