# src/bounce_house/profiles.py
"""Analysis profiles for different production stages.

Each profile bundles rules thresholds and diagnostic patterns appropriate
for a specific stage (e.g., master vs. pre-master mix).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Profile:
    """A set of rules and diagnostic patterns for a production stage."""

    name: str
    display_name: str
    description: str
    rules: dict
    patterns: list


def get_profile(stage: str) -> Profile:
    """Look up a profile by stage name. Raises ValueError for unknown stages."""
    if stage not in _PROFILES:
        raise ValueError(f"Unknown stage '{stage}'. Valid stages: {', '.join(_PROFILES)}")
    return _PROFILES[stage]


# --- Master profile (current defaults) ---


def _lufs_status(value: float) -> str:
    if -16 <= value <= -8:
        return "pass"
    if -20 <= value < -16 or -8 < value <= -6:
        return "warn"
    return "fail"


def _true_peak_status(value: float) -> str:
    if value <= -0.9:
        return "pass"
    if value <= -0.5:
        return "warn"
    return "fail"


def _lra_status(value: float) -> str:
    if 5 <= value <= 15:
        return "pass"
    if 3 <= value < 5 or 15 < value <= 20:
        return "warn"
    return "fail"


def _crest_status(value: float) -> str:
    if value > 10:
        return "pass"
    if value >= 6:
        return "warn"
    return "fail"


def _plr_status(value: float) -> str:
    if value > 10:
        return "pass"
    if value >= 8:
        return "warn"
    return "fail"


def _correlation_status(value: float) -> str:
    if value >= 0.5:
        return "pass"
    if value >= 0.1:
        return "warn"
    return "fail"


def _min_block_corr_status(value: float) -> str:
    if value > 0.0:
        return "pass"
    if value >= -0.3:
        return "warn"
    return "fail"


def _balance_status(value: float) -> str:
    v = abs(value)
    if v <= 0.5:
        return "pass"
    if v <= 1.5:
        return "warn"
    return "fail"


def _tuning_deviation_status(value: float) -> str:
    if abs(value) < 8:
        return "pass"
    if abs(value) < 20:
        return "warn"
    return "fail"


def _pitch_drift_status(value: float) -> str:
    if value < 8:
        return "pass"
    if value < 20:
        return "warn"
    return "fail"


def _chroma_sharpness_status(value: float) -> str:
    if value > 0.4:
        return "pass"
    if value > 0.2:
        return "warn"
    return "fail"


def _qc_clip_status(value: float) -> str:
    if value == 0:
        return "pass"
    if value <= 20:
        return "warn"
    return "fail"


def _qc_leading_silence_status(value: float) -> str:
    if value <= 0.5:
        return "pass"
    if value <= 5.0:
        return "warn"
    return "fail"


def _qc_trailing_silence_status(value: float) -> str:
    if value <= 5.0:
        return "pass"
    if value <= 30.0:
        return "warn"
    return "fail"


def _dc_offset_status(value: float) -> str:
    if value < -40.0:
        return "pass"
    if value <= -20.0:
        return "warn"
    return "fail"


def _dr_status(value: float) -> str:
    if value >= 7:
        return "pass"
    if value >= 4:
        return "warn"
    return "fail"


def _range_status(
    value: float, pass_range: tuple[float, float], warn_range: tuple[float, float]
) -> str:
    """Grade a value against nested pass/warn ranges (inclusive)."""
    if pass_range[0] <= value <= pass_range[1]:
        return "pass"
    if warn_range[0] <= value <= warn_range[1]:
        return "warn"
    return "fail"


def _make_range_rule(
    metric: str,
    pass_range: tuple[float, float],
    warn_range: tuple[float, float],
    unit: str,
    subject: str,
) -> dict:
    """Build a data-driven rule dict from pass/warn ranges."""
    lo, hi = pass_range
    return {
        "metric": metric,
        "evaluate": lambda v, p=pass_range, w=warn_range: _range_status(v, p, w),
        "messages": {
            "pass": f"{subject} is {{value:.2f}}{unit} — within the {lo}-{hi}{unit} target",
            "warn": f"{subject} is {{value:.2f}}{unit} — outside the {lo}-{hi}{unit} target",
            "fail": f"{subject} is {{value:.2f}}{unit} — far outside the {lo}-{hi}{unit} target",
        },
    }


_MASTER_RULES: dict[str, list[dict]] = {
    "loudness": [
        {
            "metric": "integrated_lufs",
            "evaluate": _lufs_status,
            "messages": {
                "pass": "Integrated loudness is {value:.1f} LUFS — within target range",
                "warn": (
                    "Integrated loudness is {value:.1f} LUFS — outside typical -16 to -8 range"
                ),
                "fail": (
                    "Integrated loudness is {value:.1f} LUFS"
                    " — significantly outside target range,"
                    " check your gain staging"
                ),
            },
        },
        {
            "metric": "true_peak_dbtp",
            "evaluate": _true_peak_status,
            "messages": {
                "pass": "True peak is {value:.1f} dBTP — safe headroom",
                "warn": (
                    "True peak is {value:.1f} dBTP — close to clipping,"
                    " consider lowering limiter ceiling to -1.0 dBTP"
                ),
                "fail": (
                    "True peak is {value:.1f} dBTP — risk of inter-sample"
                    " peaks on codec conversion,"
                    " add a limiter ceiling at -1.0 dBTP"
                ),
            },
        },
        {
            "metric": "loudness_range_lu",
            "evaluate": _lra_status,
            "messages": {
                "pass": "Loudness range is {value:.1f} LU — healthy dynamics",
                "warn": (
                    "Loudness range is {value:.1f} LU — dynamics may be too compressed or too wide"
                ),
                "fail": (
                    "Loudness range is {value:.1f} LU"
                    " — extreme dynamics, review compressor/limiter settings"
                ),
            },
        },
        {
            "metric": "crest_factor_db",
            "evaluate": _crest_status,
            "messages": {
                "pass": "Crest factor is {value:.1f} dB — good transient headroom",
                "warn": "Crest factor is {value:.1f} dB — transients may be over-compressed",
                "fail": (
                    "Crest factor is {value:.1f} dB"
                    " — heavily squashed, reduce limiting or compression"
                ),
            },
        },
        {
            "metric": "plr_db",
            "evaluate": _plr_status,
            "messages": {
                "pass": "Peak-to-Loudness Ratio is {value:.1f} dB — healthy headroom",
                "warn": "PLR is {value:.1f} dB — approaching over-limited territory",
                "fail": "PLR is {value:.1f} dB — heavily limited, consider backing off the limiter",
            },
        },
        {
            "metric": "dc_offset_db",
            "evaluate": _dc_offset_status,
            "messages": {
                "pass": "DC offset negligible ({value:.1f} dBFS)",
                "warn": (
                    "DC offset of {value:.1f} dBFS removed before analysis"
                    " — check plugin chains and interface"
                ),
                "fail": (
                    "Large DC offset ({value:.1f} dBFS) removed — a plugin or interface"
                    " is broken, fix at the source"
                ),
            },
        },
        {
            "metric": "dr_score",
            "evaluate": _dr_status,
            "messages": {
                "pass": "DR {value:.1f} — healthy loud-passage dynamics",
                "warn": (
                    "DR {value:.1f} — loud passages are dense;"
                    " typical of loud modern masters, verify it's intentional"
                ),
                "fail": (
                    "DR {value:.1f} — loud passages are crushed flat;"
                    " ease off bus compression/limiting"
                ),
            },
        },
    ],
    "stereo": [
        {
            "metric": "phase_correlation",
            "evaluate": _correlation_status,
            "messages": {
                "pass": "Phase correlation is {value:+.3f} — good mono compatibility",
                "warn": ("Phase correlation is {value:+.3f} — may lose energy in mono playback"),
                "fail": (
                    "Phase correlation is {value:+.3f}"
                    " — significant phase cancellation, check stereo effects"
                ),
            },
        },
        {
            "metric": "low_block_correlation",
            "evaluate": _min_block_corr_status,
            "messages": {
                "pass": (
                    "Block correlation (5th percentile) is {value:+.3f} — no sustained phase issues"
                ),
                "warn": (
                    "Block correlation (5th percentile) is {value:+.3f}"
                    " — sustained sections with near-zero or negative correlation"
                ),
                "fail": (
                    "Block correlation (5th percentile) is {value:+.3f}"
                    " — sustained phase cancellation across multiple sections"
                ),
            },
        },
        {
            "metric": "balance_db",
            "evaluate": _balance_status,
            "messages": {
                "pass": "Channel balance is {value:+.1f} dB — centered",
                "warn": ("Channel balance is {value:+.1f} dB — slight imbalance, check panning"),
                "fail": (
                    "Channel balance is {value:+.1f} dB"
                    " — significant imbalance, review pan positions"
                ),
            },
        },
        _make_range_rule("stereo_width", (0.08, 0.45), (0.03, 0.55), "", "Stereo width"),
        _make_range_rule("ms_ratio_db", (3.0, 12.0), (0.0, 18.0), " dB", "M/S ratio"),
    ],
    "translation": [
        _make_range_rule("mono_loss_db", (-1.0, 0.5), (-3.0, 0.5), " dB", "Mono energy loss"),
        _make_range_rule("low_end_reliance", (0.0, 0.35), (0.0, 0.50), "", "Low-end reliance"),
    ],
    "tuning": [
        {
            "metric": "tuning_deviation_cents",
            "evaluate": _tuning_deviation_status,
            "messages": {
                "pass": "Tuning deviation is {value:+.1f} cents from A440 — within tolerance",
                "warn": "Tuning deviation is {value:+.1f} cents from A440 — check reference pitch",
                "fail": (
                    "Tuning deviation is {value:+.1f} cents from A440 — significant, check tuning"
                ),
            },
        },
        {
            "metric": "pitch_drift_range_cents",
            "evaluate": _pitch_drift_status,
            "messages": {
                "pass": "Pitch stability: {value:.1f} cents range — stable",
                "warn": (
                    "Pitch stability: {value:.1f} cents range"
                    " — moderate drift, consider pitch correction"
                ),
                "fail": (
                    "Pitch stability: {value:.1f} cents range"
                    " — significant drift, re-record or apply pitch correction"
                ),
            },
        },
        {
            "metric": "chroma_sharpness",
            "evaluate": _chroma_sharpness_status,
            "messages": {
                "pass": "Chroma definition: {value:.2f} — well-defined pitch content",
                "warn": "Chroma definition: {value:.2f} — somewhat diffuse pitch content",
                "fail": (
                    "Chroma definition: {value:.2f} — very diffuse pitch content, check intonation"
                ),
            },
        },
        _make_range_rule(
            "pitch_drift_std_cents", (0.0, 5.0), (0.0, 12.0), " cents", "Pitch drift (std)"
        ),
    ],
    "qc": [
        {
            "metric": "clip_events",
            "evaluate": _qc_clip_status,
            "messages": {
                "pass": "No hard clipping detected",
                "warn": (
                    "{value:.0f} clipped run(s) detected — fine if intentional,"
                    " otherwise lower your limiter ceiling"
                ),
                "fail": (
                    "{value:.0f} clipped runs detected — audible distortion likely,"
                    " check export gain staging and limiter ceiling"
                ),
            },
        },
        {
            "metric": "leading_silence_sec",
            "evaluate": _qc_leading_silence_status,
            "messages": {
                "pass": "Head is tight ({value:.2f} s of leading silence)",
                "warn": "{value:.2f} s of leading silence — trim the export region start",
                "fail": "{value:.2f} s of leading silence — export region includes empty bars",
            },
        },
        {
            "metric": "trailing_silence_sec",
            "evaluate": _qc_trailing_silence_status,
            "messages": {
                "pass": "Tail is clean ({value:.2f} s of trailing silence)",
                "warn": "{value:.2f} s of trailing silence — check the export region end",
                "fail": "{value:.2f} s of trailing silence — export region far too long",
            },
        },
    ],
}

_MASTER_PATTERNS: list[dict] = [
    {
        "pattern": "muddy_mix",
        "name": "Muddy Mix",
        "conditions": [
            ("spectrum.centroid_hz", "<", 1500),
            ("perceptual.warmth", ">", 0.25),
            ("spectrum.band_ratios.low_mid_minus_mid", ">", 8.0),
            ("perceptual.brightness", "<", 0.08),
        ],
        "min_match": 2,
        "severity": "warn",
        "diagnosis": "Low-mid buildup causing muddy mix",
        "advice": (
            "Cut 2-4 dB in the 200-500 Hz range. Check for overlapping bass, "
            "guitar body, and vocal chest resonance. Use a high-pass filter on "
            "non-bass instruments to remove unnecessary low-mid energy."
        ),
    },
    {
        "pattern": "harsh_mix",
        "name": "Harsh / Brittle Mix",
        "conditions": [
            ("spectrum.centroid_hz", ">", 2800),
            ("perceptual.brightness", ">", 0.20),
            ("perceptual.warmth", "<", 0.10),
            ("spectrum.band_ratios.upper_mid_minus_mid", ">", 0.0),
        ],
        "min_match": 2,
        "severity": "warn",
        "diagnosis": "Excessive high-mid energy causing harshness",
        "advice": (
            "Check for resonant peaks in the 2-5 kHz range on vocals and guitars. "
            "Apply narrow-Q cuts of -2 to -4 dB at problem frequencies. Consider "
            "a de-esser on vocals targeting 5-8 kHz. Rather than boosting highs, "
            "try cutting low-mids to improve clarity."
        ),
    },
    {
        "pattern": "thin_mix",
        "name": "Thin / Weak Mix",
        "conditions": [
            ("perceptual.warmth", "<", 0.08),
            ("spectrum.band_ratios.bass_minus_mid", "<", 2.0),
            ("spectrum.band_ratios.low_mid_minus_mid", "<", 2.0),
            ("spectrum.centroid_hz", ">", 2500),
        ],
        "min_match": 2,
        "severity": "warn",
        "diagnosis": "Insufficient low-frequency energy; mix sounds thin",
        "advice": (
            "Check if high-pass filters are set too high. Typical HPF for vocals "
            "is 80-120 Hz, not 200+ Hz. Verify your monitoring: untreated rooms "
            "can cause phantom bass buildup that leads to over-cutting. Compare "
            "your bass/low-mid levels against a reference track."
        ),
    },
    {
        "pattern": "over_compressed",
        "name": "Over-Compressed",
        "conditions": [
            ("loudness.crest_factor_db", "<", 6),
            ("loudness.integrated_lufs", ">", -8),
            ("loudness.loudness_range_lu", "<", 4),
        ],
        "min_match": 2,
        "severity": "fail",
        "diagnosis": "Over-compressed master; dynamics crushed",
        "advice": (
            "Reduce bus compressor ratio or increase threshold. Ease off the "
            "limiter — aim for at least 8 dB crest factor. Target LRA above "
            "5 LU for streaming. Spotify normalizes to -14 LUFS, so pushing "
            "beyond -8 gains nothing and costs dynamics."
        ),
    },
    {
        "pattern": "flat_lifeless",
        "name": "Flat / Lifeless Mix",
        "conditions": [
            ("stereo.stereo_width", "<", 0.08),
            ("loudness.loudness_range_lu", "<", 5),
            ("stereo.phase_correlation", ">", 0.9),
        ],
        "min_match": 2,
        "severity": "warn",
        "diagnosis": "Mix lacks spatial depth and dynamic variation",
        "advice": (
            "Add spatial depth with reverb and delay. Vary dynamics between "
            "sections (quieter verses, louder choruses). Check panning — "
            "spreading instruments across the stereo field adds life. Even small "
            "stereo width differences between verse and chorus create perceived energy."
        ),
    },
    {
        "pattern": "mono_incompatible",
        "name": "Mono Incompatible",
        "conditions": [
            ("stereo.phase_correlation", "<", 0.1),
            ("stereo.stereo_width", ">", 0.30),
            ("stereo.frequency_width.sub_bass", "<", 0.7),
        ],
        "min_match": 2,
        "severity": "fail",
        "diagnosis": "Wide stereo image with poor mono compatibility",
        "advice": (
            "Bass frequencies below 200 Hz should be summed to mono. Check stereo "
            "widening plugins for phase issues. Test your mix in mono — any "
            "element that disappears or gets quieter has a phase problem. Bluetooth "
            "speakers, phone speakers, and PA mono subs will expose this."
        ),
    },
    {
        "pattern": "wide_bass",
        "name": "Wide Bass",
        "conditions": [
            ("stereo.frequency_width.sub_bass", "<", 0.6),
            ("stereo.frequency_width.low_mid", "<", 0.7),
        ],
        "min_match": 1,
        "severity": "warn",
        "diagnosis": "Stereo bass causing energy loss and muddiness",
        "advice": (
            "Apply a mid/side EQ to mono everything below 150-200 Hz. Check that "
            "kick and bass are panned center. Stereo bass sounds wide on headphones "
            "but loses power on mono playback systems (phones, clubs, PA centers)."
        ),
    },
    {
        "pattern": "detuned_mix",
        "name": "Detuned Mix",
        "conditions": [
            ("tuning.tuning_deviation_cents", "abs>", 15),
            ("tuning.pitch_drift_range_cents", ">", 15),
            ("tuning.chroma_sharpness", "<", 0.25),
        ],
        "min_match": 2,
        "severity": "warn",
        "diagnosis": "Possible tuning issues — pitch instability or non-standard tuning",
        "advice": (
            "Check instrument tuning against a reference. If pitch drifts over "
            "time, re-record or apply pitch correction. If the concert pitch is "
            "intentionally non-440, this warning can be ignored."
        ),
    },
    {
        "pattern": "streaming_unfriendly",
        "name": "Streaming-Unfriendly Master",
        "conditions": [
            ("loudness.integrated_lufs", ">", -7),
            ("loudness.true_peak_dbtp", ">", -1.0),
            ("loudness.loudness_range_lu", "<", 4),
        ],
        "min_match": 2,
        "severity": "fail",
        "diagnosis": "Master too hot for streaming platforms",
        "advice": (
            "Spotify normalizes to -14 LUFS, Apple Music to -16 LUFS. Your track "
            "will be turned down, and the aggressive limiting will be audible. "
            "Consider mastering to -9 to -12 LUFS with a -1.0 dBTP ceiling. The "
            "quieter version will actually sound better after platform "
            "normalization because it retains more dynamics."
        ),
    },
]

MASTER_PROFILE = Profile(
    name="master",
    display_name="Master",
    description="Mastered audio — streaming-ready loudness and peak targets",
    rules=_MASTER_RULES,
    patterns=_MASTER_PATTERNS,
)

# --- Mix profile (pre-master) ---


def _mix_lufs_status(value: float) -> str:
    if -24 <= value <= -14:
        return "pass"
    if -28 <= value < -24 or -14 < value <= -12:
        return "warn"
    return "fail"


def _mix_true_peak_status(value: float) -> str:
    if value < -3.0:
        return "pass"
    if value <= -1.0:
        return "warn"
    return "fail"


def _mix_lra_status(value: float) -> str:
    if 6 <= value <= 20:
        return "pass"
    if 4 <= value < 6 or 20 < value <= 25:
        return "warn"
    return "fail"


def _mix_crest_status(value: float) -> str:
    if value > 10:
        return "pass"
    if value >= 4:
        return "warn"
    return "fail"


def _mix_plr_status(value: float) -> str:
    if value > 10:
        return "pass"
    if value >= 6:
        return "warn"
    return "fail"


_MIX_RULES: dict[str, list[dict]] = {
    "loudness": [
        {
            "metric": "integrated_lufs",
            "evaluate": _mix_lufs_status,
            "messages": {
                "pass": (
                    "Integrated loudness is {value:.1f} LUFS — good level for a pre-master mix"
                ),
                "warn": (
                    "Integrated loudness is {value:.1f} LUFS — outside typical -24 to -14 mix range"
                ),
                "fail": (
                    "Integrated loudness is {value:.1f} LUFS"
                    " — check gain staging before sending to mastering"
                ),
            },
        },
        {
            "metric": "true_peak_dbtp",
            "evaluate": _mix_true_peak_status,
            "messages": {
                "pass": ("True peak is {value:.1f} dBTP — good headroom for mastering"),
                "warn": (
                    "True peak is {value:.1f} dBTP — consider pulling"
                    " mix bus down 3-6 dB for mastering headroom"
                ),
                "fail": (
                    "True peak is {value:.1f} dBTP — insufficient headroom,"
                    " pull mix bus fader down before sending to mastering"
                ),
            },
        },
        {
            "metric": "loudness_range_lu",
            "evaluate": _mix_lra_status,
            "messages": {
                "pass": ("Loudness range is {value:.1f} LU — healthy dynamics for a mix"),
                "warn": (
                    "Loudness range is {value:.1f} LU — dynamics may be"
                    " too compressed or too wide for mastering"
                ),
                "fail": (
                    "Loudness range is {value:.1f} LU"
                    " — extreme dynamics, review compressor settings"
                ),
            },
        },
        {
            "metric": "crest_factor_db",
            "evaluate": _mix_crest_status,
            "messages": {
                "pass": ("Crest factor is {value:.1f} dB — good transient preservation"),
                "warn": (
                    "Crest factor is {value:.1f} dB — bus compression may be"
                    " limiting dynamics available for mastering"
                ),
                "fail": (
                    "Crest factor is {value:.1f} dB — heavily squashed"
                    " for a pre-master mix, ease off bus compression"
                ),
            },
        },
        {
            "metric": "plr_db",
            "evaluate": _mix_plr_status,
            "messages": {
                "pass": ("Peak-to-Loudness Ratio is {value:.1f} dB — healthy headroom"),
                "warn": ("PLR is {value:.1f} dB — mix may be too loud for mastering"),
                "fail": (
                    "PLR is {value:.1f} dB — remove any mix bus limiting"
                    " before sending to mastering"
                ),
            },
        },
        {
            "metric": "dc_offset_db",
            "evaluate": _dc_offset_status,
            "messages": {
                "pass": "DC offset negligible ({value:.1f} dBFS)",
                "warn": (
                    "DC offset of {value:.1f} dBFS removed before analysis"
                    " — check plugin chains and interface"
                ),
                "fail": (
                    "Large DC offset ({value:.1f} dBFS) removed — a plugin or interface"
                    " is broken, fix at the source"
                ),
            },
        },
        {
            "metric": "dr_score",
            "evaluate": _dr_status,
            "messages": {
                "pass": "DR {value:.1f} — healthy loud-passage dynamics",
                "warn": (
                    "DR {value:.1f} — loud passages are dense;"
                    " typical of loud modern masters, verify it's intentional"
                ),
                "fail": (
                    "DR {value:.1f} — loud passages are crushed flat;"
                    " ease off bus compression/limiting"
                ),
            },
        },
    ],
    "stereo": _MASTER_RULES["stereo"],  # identical
    "translation": _MASTER_RULES["translation"],  # identical
    "tuning": _MASTER_RULES["tuning"],  # identical
    "qc": _MASTER_RULES["qc"],  # identical
}

_MIX_PATTERNS: list[dict] = [p for p in _MASTER_PATTERNS if p["pattern"] != "streaming_unfriendly"]
# Replace over_compressed with mix-adjusted version
_MIX_PATTERNS = [p for p in _MIX_PATTERNS if p["pattern"] != "over_compressed"] + [
    {
        "pattern": "over_compressed",
        "name": "Over-Compressed Mix",
        "conditions": [
            ("loudness.crest_factor_db", "<", 4),
            ("loudness.integrated_lufs", ">", -14),
            ("loudness.loudness_range_lu", "<", 4),
        ],
        "min_match": 2,
        "severity": "fail",
        "diagnosis": "Over-compressed pre-master mix; dynamics crushed before mastering",
        "advice": (
            "Ease off bus compression and remove any mix bus limiter. The mastering "
            "engineer needs dynamic range to work with. Aim for at least 6 dB crest "
            "factor in your mix bounce."
        ),
    },
]
# Add mix-only patterns
_MIX_PATTERNS.extend(
    [
        {
            "pattern": "headroom_insufficient",
            "name": "Insufficient Headroom",
            "conditions": [
                ("loudness.sample_peak_dbfs", ">", -3.0),
                ("loudness.true_peak_dbtp", ">", -2.0),
            ],
            "min_match": 1,
            "severity": "warn",
            "diagnosis": "Mix peaks too close to 0 dBFS for mastering headroom",
            "advice": (
                "Pull mix bus fader down 3-6 dB to leave headroom for mastering. "
                "Mastering engineers need room to work — peaks near 0 dBFS "
                "limit their options."
            ),
        },
        {
            "pattern": "bus_limiter_detected",
            "name": "Bus Limiter Detected",
            "conditions": [
                ("loudness.crest_factor_db", "<", 5),
                ("loudness.sample_peak_dbfs", ">", -1.5),
                ("loudness.integrated_lufs", ">", -12),
            ],
            "min_match": 3,
            "severity": "warn",
            "diagnosis": "Mix bus limiter detected — dynamics decisions baked in",
            "advice": (
                "This mix appears to have a limiter on the mix bus. Remove limiting "
                "before sending to mastering — it bakes in dynamics decisions that "
                "the mastering engineer should control."
            ),
        },
    ]
)

MIX_PROFILE = Profile(
    name="mix",
    display_name="Pre-Master Mix",
    description="Pre-master mix — headroom and balance checks for mastering readiness",
    rules=_MIX_RULES,
    patterns=_MIX_PATTERNS,
)

_PROFILES: dict[str, Profile] = {
    "master": MASTER_PROFILE,
    "mix": MIX_PROFILE,
}
