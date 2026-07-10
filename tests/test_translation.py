"""Tests for the translation analyzer — mono and small-speaker survival."""

import numpy as np
import pytest
import soundfile as sf

from bounce_house.analyzers.translation import TranslationAnalyzer
from bounce_house.audio import load_audio


def _write(tmp_path, name, stereo, sr=44100):
    sf.write(str(tmp_path / name), stereo, sr, subtype="FLOAT")
    return tmp_path / name


class TestMonoLoss:
    def test_identical_channels_lose_nothing(self, tmp_path):
        sr = 44100
        t = np.linspace(0, 2.0, 2 * sr, endpoint=False)
        mono = 0.5 * np.sin(2 * np.pi * 440 * t)
        path = _write(tmp_path, "center.wav", np.column_stack([mono, mono]))
        result = TranslationAnalyzer().analyze(load_audio(path))
        assert result.metrics["mono_loss_db"] == pytest.approx(0.0, abs=0.1)

    def test_antiphase_cancels_completely(self, tmp_path):
        sr = 44100
        t = np.linspace(0, 2.0, 2 * sr, endpoint=False)
        tone = 0.5 * np.sin(2 * np.pi * 440 * t)
        path = _write(tmp_path, "antiphase.wav", np.column_stack([tone, -tone]))
        result = TranslationAnalyzer().analyze(load_audio(path))
        assert result.metrics["mono_loss_db"] < -30.0
        assert result.metrics["worst_band"] == "low_mid"  # 440 Hz lives in 120-500

    def test_hard_panned_element_loses_3db(self, tmp_path):
        sr = 44100
        t = np.linspace(0, 2.0, 2 * sr, endpoint=False)
        tone = 0.5 * np.sin(2 * np.pi * 440 * t)
        path = _write(tmp_path, "panned.wav", np.column_stack([tone, np.zeros_like(tone)]))
        result = TranslationAnalyzer().analyze(load_audio(path))
        assert result.metrics["mono_loss_db"] == pytest.approx(-3.0, abs=0.3)

    def test_mono_file_translates_perfectly(self, tmp_mono_wav):
        result = TranslationAnalyzer().analyze(load_audio(tmp_mono_wav))
        assert result.metrics["mono_loss_db"] == 0.0


class TestLowEndReliance:
    def test_sub_heavy_signal_flagged(self, tmp_path):
        sr = 44100
        t = np.linspace(0, 2.0, 2 * sr, endpoint=False)
        sub = 0.8 * np.sin(2 * np.pi * 50 * t)
        mids = 0.1 * np.sin(2 * np.pi * 1000 * t)
        signal = sub + mids
        path = _write(tmp_path, "subby.wav", np.column_stack([signal, signal]))
        result = TranslationAnalyzer().analyze(load_audio(path))
        assert result.metrics["low_end_reliance"] > 0.5

    def test_midrange_signal_not_flagged(self, tmp_wav):
        result = TranslationAnalyzer().analyze(load_audio(tmp_wav))
        assert result.metrics["low_end_reliance"] < 0.35
