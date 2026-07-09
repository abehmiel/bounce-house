"""Tests for the QC analyzer — clipping and edge-silence detection."""

import numpy as np
import pytest
import soundfile as sf

from bounce_house.analyzers.qc import QcAnalyzer
from bounce_house.audio import load_audio


def _write(tmp_path, name, data, sr=44100):
    sf.write(str(tmp_path / name), data, sr, subtype="FLOAT")
    return tmp_path / name


class TestClipping:
    def test_clean_sine_has_no_clip_events(self, tmp_wav):
        result = QcAnalyzer().analyze(load_audio(tmp_wav))
        assert result.metrics["clip_events"] == 0
        assert result.metrics["longest_clip_run"] == 0

    def test_flat_topped_signal_counts_events_and_runs(self, tmp_path):
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False)
        signal = np.clip(1.5 * np.sin(2 * np.pi * 100 * t), -1.0, 1.0)  # hard-clipped sine
        path = _write(tmp_path, "clipped.wav", np.column_stack([signal, signal]))
        result = QcAnalyzer().analyze(load_audio(path))
        # 100 Hz clipped sine: 200 flat tops/second, each a run of many samples
        assert result.metrics["clip_events"] > 100
        assert result.metrics["longest_clip_run"] >= 10

    def test_single_full_scale_sample_is_not_an_event(self, tmp_path):
        sr = 44100
        signal = np.zeros(sr)
        signal[1000] = 1.0  # one isolated peak — not a clip run
        path = _write(tmp_path, "spike.wav", np.column_stack([signal, signal]))
        result = QcAnalyzer().analyze(load_audio(path))
        assert result.metrics["clip_events"] == 0


class TestEdgeSilence:
    def test_leading_and_trailing_silence_measured(self, tmp_path):
        sr = 44100
        tone = 0.5 * np.sin(2 * np.pi * 440 * np.linspace(0, 1.0, sr, endpoint=False))
        signal = np.concatenate([np.zeros(sr), tone, np.zeros(2 * sr)])  # 1 s lead, 2 s tail
        path = _write(tmp_path, "padded.wav", np.column_stack([signal, signal]))
        result = QcAnalyzer().analyze(load_audio(path))
        assert result.metrics["leading_silence_sec"] == pytest.approx(1.0, abs=0.1)
        assert result.metrics["trailing_silence_sec"] == pytest.approx(2.0, abs=0.1)

    def test_fully_silent_file_reports_full_duration_lead(self, tmp_silent_wav):
        result = QcAnalyzer().analyze(load_audio(tmp_silent_wav))
        assert result.metrics["leading_silence_sec"] == pytest.approx(1.0, abs=0.05)
