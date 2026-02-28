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
