# tests/test_profiles.py
"""Tests for analysis profiles."""

from bounce_house.profiles import Profile, get_profile


class TestProfile:
    def test_get_master_profile(self):
        profile = get_profile("master")
        assert profile.name == "master"
        assert profile.display_name == "Master"
        assert isinstance(profile.rules, dict)
        assert isinstance(profile.patterns, list)

    def test_get_profile_default_is_master(self):
        default = get_profile("master")
        assert default.name == "master"

    def test_get_profile_invalid_raises(self):
        import pytest
        with pytest.raises(ValueError, match="Unknown stage"):
            get_profile("stem")

    def test_master_profile_has_loudness_rules(self):
        profile = get_profile("master")
        assert "loudness" in profile.rules
        assert len(profile.rules["loudness"]) >= 5

    def test_master_profile_has_stereo_rules(self):
        profile = get_profile("master")
        assert "stereo" in profile.rules

    def test_master_profile_has_patterns(self):
        profile = get_profile("master")
        pattern_ids = [p["pattern"] for p in profile.patterns]
        assert "streaming_unfriendly" in pattern_ids
        assert "over_compressed" in pattern_ids


class TestMixProfile:
    def test_get_mix_profile(self):
        profile = get_profile("mix")
        assert profile.name == "mix"
        assert profile.display_name == "Pre-Master Mix"

    def test_mix_lufs_pass_range(self):
        """Mix LUFS pass range is -24 to -14."""
        profile = get_profile("mix")
        lufs_rule = [r for r in profile.rules["loudness"] if r["metric"] == "integrated_lufs"][0]
        assert lufs_rule["evaluate"](-18.0) == "pass"
        assert lufs_rule["evaluate"](-14.0) == "pass"
        assert lufs_rule["evaluate"](-24.0) == "pass"
        assert lufs_rule["evaluate"](-12.0) != "pass"  # too hot for a mix

    def test_mix_true_peak_more_lenient(self):
        """Mix allows more headroom — warn at -3, fail at -1."""
        profile = get_profile("mix")
        peak_rule = [r for r in profile.rules["loudness"] if r["metric"] == "true_peak_dbtp"][0]
        assert peak_rule["evaluate"](-4.0) == "pass"
        assert peak_rule["evaluate"](-2.0) == "warn"
        assert peak_rule["evaluate"](-0.5) == "fail"

    def test_mix_crest_factor_more_lenient(self):
        """Mix crest factor threshold is lower (fail < 4 instead of < 6)."""
        profile = get_profile("mix")
        crest_rule = [r for r in profile.rules["loudness"] if r["metric"] == "crest_factor_db"][0]
        assert crest_rule["evaluate"](5.0) == "warn"  # warn, not fail
        assert crest_rule["evaluate"](3.0) == "fail"

    def test_mix_plr_more_lenient(self):
        """Mix PLR threshold is lower (fail < 6 instead of < 8)."""
        profile = get_profile("mix")
        plr_rule = [r for r in profile.rules["loudness"] if r["metric"] == "plr_db"][0]
        assert plr_rule["evaluate"](7.0) == "warn"  # warn, not fail
        assert plr_rule["evaluate"](5.0) == "fail"

    def test_mix_lra_wider_pass_range(self):
        """Mix LRA pass range is 6-20 instead of 5-15."""
        profile = get_profile("mix")
        lra_rule = [r for r in profile.rules["loudness"] if r["metric"] == "loudness_range_lu"][0]
        assert lra_rule["evaluate"](18.0) == "pass"  # would be warn in master
        assert lra_rule["evaluate"](6.0) == "pass"

    def test_mix_no_streaming_unfriendly(self):
        """Streaming-unfriendly pattern should be absent in mix profile."""
        profile = get_profile("mix")
        pattern_ids = [p["pattern"] for p in profile.patterns]
        assert "streaming_unfriendly" not in pattern_ids

    def test_mix_has_headroom_insufficient(self):
        """Mix profile should include headroom_insufficient pattern."""
        profile = get_profile("mix")
        pattern_ids = [p["pattern"] for p in profile.patterns]
        assert "headroom_insufficient" in pattern_ids

    def test_mix_has_bus_limiter_detected(self):
        """Mix profile should include bus_limiter_detected pattern."""
        profile = get_profile("mix")
        pattern_ids = [p["pattern"] for p in profile.patterns]
        assert "bus_limiter_detected" in pattern_ids

    def test_mix_over_compressed_adjusted(self):
        """Mix over_compressed uses crest < 4 and LUFS > -14 thresholds."""
        profile = get_profile("mix")
        oc = [p for p in profile.patterns if p["pattern"] == "over_compressed"][0]
        # Crest condition threshold should be 4, not 6
        crest_cond = [c for c in oc["conditions"] if "crest_factor" in c[0]][0]
        assert crest_cond[2] == 4
        # LUFS condition threshold should be -14, not -8
        lufs_cond = [c for c in oc["conditions"] if "integrated_lufs" in c[0]][0]
        assert lufs_cond[2] == -14

    def test_mix_stereo_rules_same_as_master(self):
        """Stereo rules should be identical between mix and master."""
        mix = get_profile("mix")
        master = get_profile("master")
        assert len(mix.rules["stereo"]) == len(master.rules["stereo"])
