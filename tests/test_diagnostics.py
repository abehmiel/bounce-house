"""Tests for multi-metric diagnostic pattern engine."""

from bounce_house.analyzers.base import AnalysisResult
from bounce_house.diagnostics import Diagnosis, resolve_metric, evaluate_diagnostics


class TestResolveMetric:
    """Test the metric path resolver that extracts values from AnalysisResult lists."""

    def test_simple_metric(self):
        results = [
            AnalysisResult(module="loudness", metrics={"integrated_lufs": -12.0}),
        ]
        assert resolve_metric(results, "loudness.integrated_lufs") == -12.0

    def test_nested_metric(self):
        results = [
            AnalysisResult(module="stereo", metrics={
                "frequency_width": {"sub_bass": 0.95, "low_mid": 0.8},
            }),
        ]
        assert resolve_metric(results, "stereo.frequency_width.sub_bass") == 0.95

    def test_missing_module_returns_none(self):
        results = [
            AnalysisResult(module="loudness", metrics={"integrated_lufs": -12.0}),
        ]
        assert resolve_metric(results, "spectrum.centroid_hz") is None

    def test_missing_metric_returns_none(self):
        results = [
            AnalysisResult(module="loudness", metrics={"integrated_lufs": -12.0}),
        ]
        assert resolve_metric(results, "loudness.crest_factor_db") is None

    def test_band_energy_nested(self):
        results = [
            AnalysisResult(module="spectrum", metrics={
                "bands": {"low_mid": -15.0, "bass": -20.0},
            }),
        ]
        assert resolve_metric(results, "spectrum.bands.low_mid") == -15.0


class TestDiagnosisDataclass:
    def test_diagnosis_fields(self):
        d = Diagnosis(
            pattern="muddy_mix",
            name="Muddy Mix",
            severity="warn",
            diagnosis="Low-mid buildup",
            advice="Cut 200-500 Hz",
            matched_conditions=3,
            total_conditions=4,
        )
        assert d.pattern == "muddy_mix"
        assert d.severity == "warn"
        assert d.matched_conditions == 3
        assert d.total_conditions == 4
