"""Tests for genre target overlays (provisional values, real mechanism)."""

import json

import pytest

from bounce_house.cli import main
from bounce_house.genres import GENRE_NAMES, apply_genre, get_genre
from bounce_house.profiles import get_profile


class TestGenreData:
    def test_all_genres_resolvable_and_provisional(self):
        assert set(GENRE_NAMES) == {"pop", "rock", "edm", "hip_hop", "metal", "folk"}
        for name in GENRE_NAMES:
            genre = get_genre(name)
            assert genre.provisional is True  # flips only after the eval stage

    def test_unknown_genre_lists_valid_names(self):
        with pytest.raises(ValueError, match="pop"):
            get_genre("polka")


class TestGenreOverlay:
    def _evaluate(self, profile, module, metric, value):
        rule = next(r for r in profile.rules[module] if r["metric"] == metric)
        return rule["evaluate"](value)

    def test_edm_lufs_target_overrides_master(self):
        base = get_profile("master")
        edm = apply_genre(base, get_genre("edm"))
        # -6 LUFS: warn under generic master targets, pass for EDM
        assert self._evaluate(base, "loudness", "integrated_lufs", -6.0) == "warn"
        assert self._evaluate(edm, "loudness", "integrated_lufs", -6.0) == "pass"

    def test_folk_flags_edm_loudness(self):
        folk = apply_genre(get_profile("master"), get_genre("folk"))
        assert self._evaluate(folk, "loudness", "integrated_lufs", -6.0) == "fail"

    def test_genre_adds_centroid_rule(self):
        base = get_profile("master")
        assert not any(r["metric"] == "centroid_hz" for r in base.rules.get("spectrum", []))
        edm = apply_genre(base, get_genre("edm"))
        assert any(r["metric"] == "centroid_hz" for r in edm.rules["spectrum"])

    def test_mix_stage_keeps_its_loudness_rules(self):
        mix = apply_genre(get_profile("mix"), get_genre("edm"))
        # Mix headroom targets are genre-independent: -18 LUFS passes mix, would fail EDM master
        assert self._evaluate(mix, "loudness", "integrated_lufs", -18.0) == "pass"

    def test_base_profile_not_mutated(self):
        base = get_profile("master")
        before = self._evaluate(base, "loudness", "integrated_lufs", -6.0)
        apply_genre(base, get_genre("edm"))
        assert self._evaluate(base, "loudness", "integrated_lufs", -6.0) == before


class TestGenreCli:
    def test_genre_flag_labels_json(self, tmp_wav, capsys):
        main(["analyze", str(tmp_wav), "--genre", "edm", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert data["genre"] == "edm"
        assert data["genre_provisional"] is True

    def test_no_genre_is_null_in_json(self, tmp_wav, capsys):
        main(["analyze", str(tmp_wav), "--json"])
        data = json.loads(capsys.readouterr().out)
        assert data["genre"] is None

    def test_genre_shown_as_provisional_in_report(self, tmp_wav, capsys, monkeypatch):
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        main(["analyze", str(tmp_wav), "--genre", "edm"])
        out = capsys.readouterr().out
        assert "EDM" in out
        assert "provisional" in out.lower()
