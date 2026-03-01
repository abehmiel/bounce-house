"""Tests for rule-based advice engine."""

from bounce_house.analyzers.base import AnalysisResult
from bounce_house.profiles import get_profile
from bounce_house.rules import evaluate_rules


class TestRuleEngine:
    def test_loudness_pass(self):
        result = AnalysisResult(
            module="loudness",
            metrics={
                "integrated_lufs": -12.0,
                "true_peak_dbtp": -1.5,
                "loudness_range_lu": 8.0,
                "crest_factor_db": 14.0,
            },
        )
        assessments = evaluate_rules(result)
        statuses = [a.status for a in assessments]
        assert all(s == "pass" for s in statuses)

    def test_loudness_too_hot(self):
        result = AnalysisResult(
            module="loudness",
            metrics={
                "integrated_lufs": -5.0,
                "true_peak_dbtp": 0.2,
                "loudness_range_lu": 2.0,
                "crest_factor_db": 4.0,
            },
        )
        assessments = evaluate_rules(result)
        fails = [a for a in assessments if a.status == "fail"]
        assert len(fails) >= 2  # LUFS and true peak should fail

    def test_stereo_phase_warning(self):
        result = AnalysisResult(
            module="stereo",
            metrics={"phase_correlation": 0.1, "min_block_correlation": -0.1, "balance_db": 0.2},
        )
        assessments = evaluate_rules(result)
        warns = [a for a in assessments if a.status == "warn"]
        assert len(warns) >= 1

    def test_stereo_out_of_phase_fail(self):
        result = AnalysisResult(
            module="stereo",
            metrics={"phase_correlation": -0.5, "min_block_correlation": -0.8, "balance_db": 0.1},
        )
        assessments = evaluate_rules(result)
        fails = [a for a in assessments if a.status == "fail"]
        assert len(fails) >= 1

    def test_reference_band_deviation(self):
        result = AnalysisResult(
            module="spectrum",
            metrics={"bands": {}, "band_differences": {"low_mid": 5.0, "bass": 1.0}},
        )
        assessments = evaluate_rules(result)
        warns_or_fails = [a for a in assessments if a.status in ("warn", "fail")]
        assert any("low_mid" in a.metric for a in warns_or_fails)

    def test_assessments_have_messages(self):
        result = AnalysisResult(
            module="loudness",
            metrics={
                "integrated_lufs": -5.0,
                "true_peak_dbtp": 0.2,
                "loudness_range_lu": 2.0,
                "crest_factor_db": 4.0,
            },
        )
        assessments = evaluate_rules(result)
        for a in assessments:
            assert isinstance(a.message, str)
            assert len(a.message) > 0

    def test_unknown_module_returns_empty(self):
        result = AnalysisResult(module="unknown", metrics={})
        assessments = evaluate_rules(result)
        assert assessments == []

    def test_missing_metrics_skipped_gracefully(self):
        result = AnalysisResult(module="loudness", metrics={"integrated_lufs": -12.0})
        assessments = evaluate_rules(result)
        # Should only assess metrics that are present, not crash
        assert isinstance(assessments, list)

    def test_plr_pass(self):
        result = AnalysisResult(
            module="loudness",
            metrics={"plr_db": 12.0},
        )
        assessments = evaluate_rules(result)
        plr = [a for a in assessments if a.metric == "plr_db"]
        assert len(plr) == 1
        assert plr[0].status == "pass"

    def test_plr_fail(self):
        result = AnalysisResult(
            module="loudness",
            metrics={"plr_db": 6.0},
        )
        assessments = evaluate_rules(result)
        plr = [a for a in assessments if a.metric == "plr_db"]
        assert len(plr) == 1
        assert plr[0].status == "fail"


class TestRulesWithProfile:
    def test_evaluate_rules_accepts_profile(self):
        profile = get_profile("master")
        result = AnalysisResult(
            module="loudness",
            metrics={
                "integrated_lufs": -12.0,
                "true_peak_dbtp": -1.5,
                "loudness_range_lu": 8.0,
                "crest_factor_db": 14.0,
            },
        )
        assessments = evaluate_rules(result, profile)
        assert all(a.status == "pass" for a in assessments)

    def test_mix_profile_lufs_pass(self):
        """A -18 LUFS mix should pass in mix mode but warn in master mode."""
        result = AnalysisResult(
            module="loudness",
            metrics={"integrated_lufs": -18.0},
        )
        mix_assessments = evaluate_rules(result, get_profile("mix"))
        master_assessments = evaluate_rules(result, get_profile("master"))

        mix_lufs = [a for a in mix_assessments if a.metric == "integrated_lufs"][0]
        master_lufs = [a for a in master_assessments if a.metric == "integrated_lufs"][0]

        assert mix_lufs.status == "pass"
        assert master_lufs.status == "warn"

    def test_backward_compat_no_profile(self):
        """evaluate_rules still works without a profile (uses master default)."""
        result = AnalysisResult(
            module="loudness",
            metrics={"integrated_lufs": -12.0},
        )
        assessments = evaluate_rules(result)
        assert len(assessments) >= 1
