"""Genre target profiles — data-only overlays on stage profiles.

PROVISIONAL: every value below is an engineering prior, not a measured target.
A deferred eval stage will calibrate these against a corpus of real reference
songs per genre and replace the numbers (mechanism stays). Until then every
genre carries provisional=True and all output is labeled accordingly.

Target format: module -> metric -> ((pass_lo, pass_hi), (warn_lo, warn_hi)).
Loudness targets apply only at master stage (pre-master headroom is
genre-independent); spectrum/stereo targets apply at every stage.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from bounce_house.profiles import Profile, _make_range_rule

_Range = tuple[float, float]
_Target = tuple[_Range, _Range]  # (pass_range, warn_range)

# Display metadata per overridable metric: unit and message subject
_METRIC_DISPLAY: dict[str, tuple[str, str]] = {
    "integrated_lufs": (" LUFS", "Integrated loudness"),
    "loudness_range_lu": (" LU", "Loudness range"),
    "crest_factor_db": (" dB", "Crest factor"),
    "stereo_width": ("", "Stereo width"),
    "centroid_hz": (" Hz", "Spectral centroid"),
}


@dataclass(frozen=True)
class GenreProfile:
    name: str
    display_name: str
    provisional: bool
    targets: dict[str, dict[str, _Target]]


_GENRES: dict[str, GenreProfile] = {
    g.name: g
    for g in [
        GenreProfile(
            name="pop",
            display_name="Pop",
            provisional=True,
            targets={
                "loudness": {
                    "integrated_lufs": ((-10.0, -7.0), (-12.0, -6.0)),
                    "loudness_range_lu": ((4.0, 8.0), (3.0, 10.0)),
                    "crest_factor_db": ((5.0, 10.0), (4.0, 14.0)),
                },
                "spectrum": {"centroid_hz": ((1800.0, 3200.0), (1400.0, 3800.0))},
                "stereo": {"stereo_width": ((0.15, 0.40), (0.08, 0.50))},
            },
        ),
        GenreProfile(
            name="rock",
            display_name="Rock",
            provisional=True,
            targets={
                "loudness": {
                    "integrated_lufs": ((-11.0, -8.0), (-13.0, -7.0)),
                    "loudness_range_lu": ((5.0, 10.0), (4.0, 12.0)),
                    "crest_factor_db": ((7.0, 12.0), (5.0, 15.0)),
                },
                "spectrum": {"centroid_hz": ((1500.0, 3000.0), (1200.0, 3600.0))},
                "stereo": {"stereo_width": ((0.12, 0.35), (0.06, 0.45))},
            },
        ),
        GenreProfile(
            name="edm",
            display_name="EDM",
            provisional=True,
            targets={
                "loudness": {
                    "integrated_lufs": ((-8.0, -5.0), (-10.0, -4.0)),
                    "loudness_range_lu": ((3.0, 6.0), (2.0, 8.0)),
                    "crest_factor_db": ((4.0, 7.0), (3.0, 9.0)),
                },
                "spectrum": {"centroid_hz": ((1500.0, 3000.0), (1100.0, 3600.0))},
                "stereo": {"stereo_width": ((0.20, 0.45), (0.12, 0.55))},
            },
        ),
        GenreProfile(
            name="hip_hop",
            display_name="Hip-Hop",
            provisional=True,
            targets={
                "loudness": {
                    "integrated_lufs": ((-10.0, -6.0), (-12.0, -5.0)),
                    "loudness_range_lu": ((4.0, 8.0), (3.0, 10.0)),
                    "crest_factor_db": ((5.0, 9.0), (4.0, 12.0)),
                },
                "spectrum": {"centroid_hz": ((1200.0, 2600.0), (900.0, 3200.0))},
                "stereo": {"stereo_width": ((0.10, 0.35), (0.05, 0.45))},
            },
        ),
        GenreProfile(
            name="metal",
            display_name="Metal",
            provisional=True,
            targets={
                "loudness": {
                    "integrated_lufs": ((-9.0, -6.0), (-11.0, -5.0)),
                    "loudness_range_lu": ((3.0, 7.0), (2.0, 9.0)),
                    "crest_factor_db": ((5.0, 8.0), (4.0, 11.0)),
                },
                "spectrum": {"centroid_hz": ((1800.0, 3400.0), (1400.0, 4000.0))},
                "stereo": {"stereo_width": ((0.12, 0.35), (0.06, 0.45))},
            },
        ),
        GenreProfile(
            name="folk",
            display_name="Folk / Acoustic",
            provisional=True,
            targets={
                "loudness": {
                    "integrated_lufs": ((-16.0, -10.0), (-19.0, -8.0)),
                    "loudness_range_lu": ((8.0, 15.0), (6.0, 18.0)),
                    "crest_factor_db": ((10.0, 16.0), (8.0, 20.0)),
                },
                "spectrum": {"centroid_hz": ((1200.0, 2600.0), (900.0, 3200.0))},
                "stereo": {"stereo_width": ((0.08, 0.30), (0.04, 0.40))},
            },
        ),
    ]
}

GENRE_NAMES: tuple[str, ...] = tuple(_GENRES)


def get_genre(name: str) -> GenreProfile:
    """Look up a genre by name. Raises ValueError listing valid names."""
    if name not in _GENRES:
        raise ValueError(f"Unknown genre '{name}'. Valid genres: {', '.join(_GENRES)}")
    return _GENRES[name]


def apply_genre(profile: Profile, genre: GenreProfile) -> Profile:
    """Return a new Profile with the genre's targets overlaid on the stage rules.

    Loudness overrides apply only at master stage; other modules always apply.
    Existing rules for a targeted metric are replaced; missing ones are added.
    """
    new_rules: dict = {}
    for module, rules in profile.rules.items():
        new_rules[module] = list(rules)

    for module, metric_targets in genre.targets.items():
        if module == "loudness" and profile.name != "master":
            continue  # pre-master headroom targets are genre-independent
        module_rules = new_rules.setdefault(module, [])
        for metric, (pass_range, warn_range) in metric_targets.items():
            unit, subject = _METRIC_DISPLAY[metric]
            rule = _make_range_rule(metric, pass_range, warn_range, unit, subject)
            module_rules[:] = [r for r in module_rules if r["metric"] != metric]
            module_rules.append(rule)

    return replace(profile, rules=new_rules)
