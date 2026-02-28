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


class TestEvaluateDiagnostics:
    """Test pattern matching with min_match logic."""

    def _make_results(self, **overrides):
        """Build a full set of AnalysisResult objects with controllable metrics."""
        loudness = {
            "integrated_lufs": -12.0,
            "true_peak_dbtp": -1.5,
            "loudness_range_lu": 8.0,
            "crest_factor_db": 14.0,
        }
        spectrum = {
            "centroid_hz": 2000.0,
            "bandwidth_hz": 2500.0,
            "rolloff_hz": 6000.0,
            "flatness": 0.15,
            "bands": {
                "sub_bass": -30.0, "bass": -20.0, "low_mid": -18.0,
                "mid": -15.0, "upper_mid": -17.0, "presence": -22.0,
                "brilliance": -25.0,
            },
        }
        stereo = {
            "phase_correlation": 0.5,
            "stereo_width": 0.25,
            "min_block_correlation": 0.3,
            "balance_db": 0.1,
            "frequency_width": {
                "sub_bass": 0.95, "low_mid": 0.85,
                "mid": 0.6, "upper_mid": 0.4, "air": 0.3,
            },
        }
        perceptual = {
            "brightness": 0.15,
            "warmth": 0.15,
        }
        # Apply overrides: keys like "loudness.integrated_lufs" -> -5.0
        for path, val in overrides.items():
            parts = path.split(".", 2)
            module_metrics = {"loudness": loudness, "spectrum": spectrum,
                              "stereo": stereo, "perceptual": perceptual}[parts[0]]
            if len(parts) == 3:
                module_metrics[parts[1]][parts[2]] = val
            else:
                module_metrics[parts[1]] = val

        return [
            AnalysisResult(module="loudness", metrics=loudness),
            AnalysisResult(module="spectrum", metrics=spectrum),
            AnalysisResult(module="stereo", metrics=stereo),
            AnalysisResult(module="perceptual", metrics=perceptual),
        ]

    def test_healthy_mix_no_diagnostics(self):
        results = self._make_results()
        diagnoses = evaluate_diagnostics(results)
        assert diagnoses == []

    def test_over_compressed_detected(self):
        results = self._make_results(**{
            "loudness.crest_factor_db": 4.0,
            "loudness.integrated_lufs": -6.0,
            "loudness.loudness_range_lu": 3.0,
        })
        diagnoses = evaluate_diagnostics(results)
        patterns = [d.pattern for d in diagnoses]
        assert "over_compressed" in patterns

    def test_over_compressed_one_condition_not_enough(self):
        """Only crest_factor is bad — should NOT fire (min_match=2)."""
        results = self._make_results(**{
            "loudness.crest_factor_db": 4.0,
        })
        diagnoses = evaluate_diagnostics(results)
        patterns = [d.pattern for d in diagnoses]
        assert "over_compressed" not in patterns

    def test_muddy_mix_detected(self):
        results = self._make_results(**{
            "spectrum.centroid_hz": 1200.0,
            "perceptual.warmth": 0.30,
            "perceptual.brightness": 0.05,
        })
        diagnoses = evaluate_diagnostics(results)
        patterns = [d.pattern for d in diagnoses]
        assert "muddy_mix" in patterns

    def test_harsh_mix_detected(self):
        results = self._make_results(**{
            "spectrum.centroid_hz": 3200.0,
            "perceptual.brightness": 0.25,
            "perceptual.warmth": 0.05,
        })
        diagnoses = evaluate_diagnostics(results)
        patterns = [d.pattern for d in diagnoses]
        assert "harsh_mix" in patterns

    def test_mono_incompatible_detected(self):
        results = self._make_results(**{
            "stereo.phase_correlation": 0.05,
            "stereo.stereo_width": 0.35,
            "stereo.frequency_width.sub_bass": 0.5,
        })
        diagnoses = evaluate_diagnostics(results)
        patterns = [d.pattern for d in diagnoses]
        assert "mono_incompatible" in patterns

    def test_streaming_unfriendly_detected(self):
        results = self._make_results(**{
            "loudness.integrated_lufs": -5.0,
            "loudness.true_peak_dbtp": -0.3,
            "loudness.loudness_range_lu": 3.0,
        })
        diagnoses = evaluate_diagnostics(results)
        patterns = [d.pattern for d in diagnoses]
        assert "streaming_unfriendly" in patterns

    def test_diagnosis_has_advice(self):
        results = self._make_results(**{
            "loudness.crest_factor_db": 4.0,
            "loudness.integrated_lufs": -6.0,
            "loudness.loudness_range_lu": 3.0,
        })
        diagnoses = evaluate_diagnostics(results)
        over = [d for d in diagnoses if d.pattern == "over_compressed"][0]
        assert len(over.advice) > 20
        assert over.severity == "fail"
        assert over.matched_conditions >= 2

    def test_multiple_patterns_can_fire(self):
        """Over-compressed AND streaming-unfriendly overlap."""
        results = self._make_results(**{
            "loudness.crest_factor_db": 4.0,
            "loudness.integrated_lufs": -5.0,
            "loudness.loudness_range_lu": 3.0,
            "loudness.true_peak_dbtp": -0.3,
        })
        diagnoses = evaluate_diagnostics(results)
        patterns = [d.pattern for d in diagnoses]
        assert "over_compressed" in patterns
        assert "streaming_unfriendly" in patterns


class TestEdgeCases:
    """Boundary conditions and edge cases for diagnostic patterns."""

    def _make_results(self, **overrides):
        """Reuse the helper from TestEvaluateDiagnostics."""
        return TestEvaluateDiagnostics._make_results(
            TestEvaluateDiagnostics(), **overrides
        )

    def test_thin_mix_detected(self):
        results = self._make_results(**{
            "perceptual.warmth": 0.04,
            "spectrum.bands.bass": -35.0,
            "spectrum.centroid_hz": 3000.0,
        })
        diagnoses = evaluate_diagnostics(results)
        patterns = [d.pattern for d in diagnoses]
        assert "thin_mix" in patterns

    def test_flat_lifeless_detected(self):
        results = self._make_results(**{
            "stereo.stereo_width": 0.05,
            "loudness.loudness_range_lu": 3.0,
            "stereo.phase_correlation": 0.95,
        })
        diagnoses = evaluate_diagnostics(results)
        patterns = [d.pattern for d in diagnoses]
        assert "flat_lifeless" in patterns

    def test_wide_bass_detected(self):
        results = self._make_results(**{
            "stereo.frequency_width.sub_bass": 0.4,
        })
        diagnoses = evaluate_diagnostics(results)
        patterns = [d.pattern for d in diagnoses]
        assert "wide_bass" in patterns

    def test_exact_threshold_does_not_fire(self):
        """Conditions use strict < and >, so values at the boundary should not match."""
        results = self._make_results(**{
            "loudness.crest_factor_db": 6.0,  # threshold is < 6
            "loudness.integrated_lufs": -8.0,  # threshold is > -8
            "loudness.loudness_range_lu": 4.0,  # threshold is < 4
        })
        diagnoses = evaluate_diagnostics(results)
        patterns = [d.pattern for d in diagnoses]
        assert "over_compressed" not in patterns

    def test_missing_module_does_not_crash(self):
        """If an analyzer didn't run (e.g., single-module command), patterns should not crash."""
        results = [
            AnalysisResult(module="loudness", metrics={
                "integrated_lufs": -12.0,
                "crest_factor_db": 14.0,
                "loudness_range_lu": 8.0,
            }),
        ]
        diagnoses = evaluate_diagnostics(results)
        assert isinstance(diagnoses, list)

    def test_none_metric_value_handled(self):
        """A metric with value None (e.g., crest_factor for silence) should not crash."""
        results = [
            AnalysisResult(module="loudness", metrics={
                "integrated_lufs": -12.0,
                "crest_factor_db": None,
                "loudness_range_lu": 8.0,
            }),
        ]
        diagnoses = evaluate_diagnostics(results)
        assert isinstance(diagnoses, list)

    def test_all_patterns_have_required_fields(self):
        """Verify every pattern in _PATTERNS has the required keys."""
        from bounce_house.diagnostics import _PATTERNS
        required = {"pattern", "name", "conditions", "min_match", "severity", "diagnosis", "advice"}
        for p in _PATTERNS:
            assert required.issubset(p.keys()), f"Pattern {p.get('pattern')} missing keys: {required - p.keys()}"
            assert p["severity"] in ("warn", "fail")
            assert p["min_match"] >= 1
            assert p["min_match"] <= len(p["conditions"])


from bounce_house.profiles import get_profile


class TestDiagnosticsWithProfile:
    def _make_results(self, **overrides):
        return TestEvaluateDiagnostics._make_results(
            TestEvaluateDiagnostics(), **overrides
        )

    def test_evaluate_diagnostics_accepts_profile(self):
        profile = get_profile("master")
        results = self._make_results()
        diagnoses = evaluate_diagnostics(results, profile)
        assert diagnoses == []

    def test_mix_profile_skips_streaming_unfriendly(self):
        """streaming_unfriendly should not fire in mix mode even with matching metrics."""
        results = self._make_results(**{
            "loudness.integrated_lufs": -5.0,
            "loudness.true_peak_dbtp": -0.3,
            "loudness.loudness_range_lu": 3.0,
        })
        mix_diagnoses = evaluate_diagnostics(results, get_profile("mix"))
        master_diagnoses = evaluate_diagnostics(results, get_profile("master"))

        mix_patterns = [d.pattern for d in mix_diagnoses]
        master_patterns = [d.pattern for d in master_diagnoses]

        assert "streaming_unfriendly" not in mix_patterns
        assert "streaming_unfriendly" in master_patterns

    def test_mix_headroom_insufficient_fires(self):
        """headroom_insufficient should fire in mix mode when peaks are hot."""
        results = self._make_results(**{
            "loudness.sample_peak_dbfs": -1.5,
        })
        diagnoses = evaluate_diagnostics(results, get_profile("mix"))
        patterns = [d.pattern for d in diagnoses]
        assert "headroom_insufficient" in patterns

    def test_mix_bus_limiter_detected_fires(self):
        """bus_limiter_detected fires when all 3 conditions match."""
        results = self._make_results(**{
            "loudness.crest_factor_db": 3.0,
            "loudness.sample_peak_dbfs": -0.5,
            "loudness.integrated_lufs": -10.0,
        })
        diagnoses = evaluate_diagnostics(results, get_profile("mix"))
        patterns = [d.pattern for d in diagnoses]
        assert "bus_limiter_detected" in patterns

    def test_master_no_headroom_check(self):
        """headroom_insufficient should not exist in master mode."""
        results = self._make_results(**{
            "loudness.sample_peak_dbfs": -1.5,
        })
        diagnoses = evaluate_diagnostics(results, get_profile("master"))
        patterns = [d.pattern for d in diagnoses]
        assert "headroom_insufficient" not in patterns

    def test_backward_compat_no_profile(self):
        """evaluate_diagnostics still works without a profile."""
        results = self._make_results()
        diagnoses = evaluate_diagnostics(results)
        assert isinstance(diagnoses, list)
