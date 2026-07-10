"""Tests for bounce-over-bounce diffing."""

from bounce_house.analyzers.base import AnalysisResult, Assessment
from bounce_house.bounce_diff import compute_diff
from bounce_house.diagnostics import Diagnosis


def _data(lufs, lufs_status, corr=0.8, diagnoses=()):
    result = AnalysisResult(
        module="loudness",
        metrics={"integrated_lufs": lufs},
        assessments=[
            Assessment(metric="integrated_lufs", value=lufs, status=lufs_status, message="")
        ],
    )
    stereo = AnalysisResult(module="stereo", metrics={"phase_correlation": corr})
    return {
        "path": "x.wav",
        "results": [result, stereo],
        "file_info": {},
        "diagnoses": [
            Diagnosis(
                pattern=p,
                name=p,
                severity="warn",
                diagnosis="",
                advice="",
                matched_conditions=2,
                total_conditions=3,
            )
            for p in diagnoses
        ],
    }


class TestComputeDiff:
    def test_status_improvement_detected(self):
        diff = compute_diff(_data(-6.0, "warn"), _data(-9.0, "pass"))
        assert len(diff.improvements) == 1
        change = diff.improvements[0]
        assert change.metric == "integrated_lufs"
        assert change.old == -6.0 and change.new == -9.0
        assert not diff.regressions

    def test_status_regression_detected(self):
        diff = compute_diff(_data(-9.0, "pass"), _data(-5.0, "fail"))
        assert len(diff.regressions) == 1

    def test_insignificant_delta_ignored(self):
        diff = compute_diff(_data(-9.0, "pass"), _data(-9.1, "pass"))
        assert not diff.changes
        assert diff.unchanged_count >= 1

    def test_significant_delta_without_status_change(self):
        old = _data(-9.0, "pass", corr=0.9)
        new = _data(-9.0, "pass", corr=0.5)
        diff = compute_diff(old, new)
        assert any(c.metric == "phase_correlation" for c in diff.changes)

    def test_diagnostics_resolved_and_introduced(self):
        diff = compute_diff(
            _data(-9.0, "pass", diagnoses=("muddy_mix",)),
            _data(-9.0, "pass", diagnoses=("harsh_mix",)),
        )
        assert diff.diagnostics_resolved == ["muddy_mix"]
        assert diff.diagnostics_introduced == ["harsh_mix"]
