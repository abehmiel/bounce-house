"""Tests for the rhythm analyzer."""

from bounce_house.analyzers.rhythm import RhythmAnalyzer
from bounce_house.audio import load_audio


class TestTempoEstimation:
    def setup_method(self):
        self.analyzer = RhythmAnalyzer()

    def test_name(self):
        assert self.analyzer.name == "rhythm"

    def test_analyze_returns_result(self, tmp_tempo_120_wav):
        audio = load_audio(tmp_tempo_120_wav)
        result = self.analyzer.analyze(audio)
        assert result.module == "rhythm"

    def test_detects_120_bpm(self, tmp_tempo_120_wav):
        audio = load_audio(tmp_tempo_120_wav)
        result = self.analyzer.analyze(audio)
        assert abs(result.metrics["tempo_bpm"] - 120.0) < 3.0

    def test_confidence_in_unit_range(self, tmp_tempo_120_wav):
        audio = load_audio(tmp_tempo_120_wav)
        conf = self.analyzer.analyze(audio).metrics["tempo_confidence"]
        assert 0.0 <= conf <= 1.0

    def test_candidates_are_ranked_and_include_top_pick(self, tmp_tempo_120_wav):
        metrics = self.analyzer.analyze(load_audio(tmp_tempo_120_wav)).metrics
        cands = metrics["tempo_candidates"]
        assert 1 <= len(cands) <= 3
        assert cands[0]["bpm"] == metrics["tempo_bpm"]
        scores = [c["score"] for c in cands]
        assert scores == sorted(scores, reverse=True)

    def test_candidate_scores_sum_to_one(self, tmp_tempo_120_wav):
        cands = self.analyzer.analyze(load_audio(tmp_tempo_120_wav)).metrics["tempo_candidates"]
        assert abs(sum(c["score"] for c in cands) - 1.0) < 0.01

    def test_candidates_are_distinct_metrical_levels(self, tmp_tempo_120_wav):
        cands = self.analyzer.analyze(load_audio(tmp_tempo_120_wav)).metrics["tempo_candidates"]
        bpms = [c["bpm"] for c in cands]
        assert len(set(bpms)) == len(bpms)

    def test_short_file_is_unmeasurable_not_a_crash(self, tmp_wav):
        """The 1-second fixture is far too short for tempo — report None, do not guess."""
        metrics = self.analyzer.analyze(load_audio(tmp_wav)).metrics
        assert metrics["tempo_bpm"] is None
        assert metrics["tempo_confidence"] == 0.0

    def test_long_silence_is_unmeasurable_not_a_crash(self, tmp_long_silent_wav):
        """8 s of silence clears the duration guard and must exit via no-candidates."""
        metrics = self.analyzer.analyze(load_audio(tmp_long_silent_wav)).metrics
        assert metrics["tempo_bpm"] is None
        assert metrics["tempo_stability"] == "unmeasurable"

    def test_mono_file_detects_tempo(self, tmp_mono_tempo_wav):
        """Exercises the audio.samples[:, 0] branch, not just the duration guard."""
        metrics = self.analyzer.analyze(load_audio(tmp_mono_tempo_wav)).metrics
        assert abs(metrics["tempo_bpm"] - 120.0) < 3.0

    def test_octave_error_still_surfaces_true_tempo(self, tmp_tempo_90_wav):
        """The core claim of the candidate design: at 90 BPM the top pick is the
        octave-doubled 178, but the true tempo must still be in the list."""
        metrics = self.analyzer.analyze(load_audio(tmp_tempo_90_wav)).metrics
        bpms = [c["bpm"] for c in metrics["tempo_candidates"]]
        assert any(abs(b - 90.0) < 3.0 for b in bpms), f"90 BPM absent from {bpms}"

    def test_octave_ambiguity_lowers_confidence(self, tmp_tempo_90_wav, tmp_tempo_120_wav):
        """Contested metrical level must be reported as such, not as certainty.

        Asserted as a COMPARISON, not against the 0.40 constant: the measured
        values are 0.395 and 0.458, so a bare `< 0.40` would sit 1.3% from
        flipping on any librosa change. The threshold-crossing behaviour that
        actually matters downstream is pinned by the tempo_stability test in
        Task 2 and the swing-gate test in Task 3.
        """
        ambiguous = self.analyzer.analyze(load_audio(tmp_tempo_90_wav)).metrics
        confident = self.analyzer.analyze(load_audio(tmp_tempo_120_wav)).metrics
        assert confident["tempo_confidence"] - ambiguous["tempo_confidence"] > 0.03, (
            "octave-ambiguous material must score lower than unambiguous"
        )


class TestTempoSegments:
    def setup_method(self):
        self.analyzer = RhythmAnalyzer()

    def test_steady_tempo_is_one_segment(self, tmp_tempo_120_wav):
        metrics = self.analyzer.analyze(load_audio(tmp_tempo_120_wav)).metrics
        assert len(metrics["tempo_segments"]) == 1
        assert metrics["tempo_stability"] == "constant"

    def test_tempo_change_produces_multiple_segments(self, tmp_tempo_change_wav):
        metrics = self.analyzer.analyze(load_audio(tmp_tempo_change_wav)).metrics
        assert len(metrics["tempo_segments"]) >= 2

    def test_tempo_change_segments_differ_in_bpm(self, tmp_tempo_change_wav):
        segs = self.analyzer.analyze(load_audio(tmp_tempo_change_wav)).metrics["tempo_segments"]
        assert abs(segs[0]["bpm"] - segs[1]["bpm"]) > 5.0

    def test_segments_are_contiguous_and_non_overlapping(self, tmp_tempo_change_wav):
        segs = self.analyzer.analyze(load_audio(tmp_tempo_change_wav)).metrics["tempo_segments"]
        for a, b in zip(segs, segs[1:], strict=False):
            assert a["end_s"] == b["start_s"]

    def test_segments_span_the_file(self, tmp_tempo_change_wav):
        audio = load_audio(tmp_tempo_change_wav)
        segs = self.analyzer.analyze(audio).metrics["tempo_segments"]
        assert segs[0]["start_s"] == 0.0
        assert abs(segs[-1]["end_s"] - audio.duration) < 0.1

    def test_short_file_has_no_segments(self, tmp_wav):
        metrics = self.analyzer.analyze(load_audio(tmp_wav)).metrics
        assert metrics["tempo_segments"] == []
        assert metrics["tempo_stability"] == "unmeasurable"

    def test_ambiguous_confidence_forces_ambiguous_stability(self, tmp_tempo_90_wav):
        """Confidence below 0.40 overrides segmentation — see Task 1 for the
        confidence half of this pair."""
        metrics = self.analyzer.analyze(load_audio(tmp_tempo_90_wav)).metrics
        assert metrics["tempo_stability"] == "ambiguous"

    def test_stability_is_a_known_value(self, tmp_tempo_120_wav):
        stability = self.analyzer.analyze(load_audio(tmp_tempo_120_wav)).metrics["tempo_stability"]
        assert stability in {"constant", "varying", "ambiguous", "unmeasurable"}
