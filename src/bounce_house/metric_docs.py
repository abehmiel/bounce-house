"""Metric documentation for the explain command.

Each MetricDoc describes one metric: what it measures, why it matters,
good/bad value ranges, genre context, and technical measurement details.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MetricDoc:
    """Documentation for a single analysis metric."""

    key: str
    name: str
    module: str
    summary: str
    explanation: str
    good_range: str
    genre_notes: str
    technical: str
    aliases: list[str] = field(default_factory=list)


# --- Loudness metrics ---

_INTEGRATED_LUFS = MetricDoc(
    key="integrated_lufs",
    name="Integrated LUFS",
    module="loudness",
    summary="Perceived loudness of the full mix (ITU-R BS.1770).",
    explanation=(
        "Measures perceived loudness over the entire track using K-weighted "
        "filtering. Streaming platforms normalize to a target loudness — "
        "-14 LUFS on Spotify/YouTube, -16 on Apple Music. If your master is "
        "louder than the target, the platform turns it down, wasting your "
        "headroom and dynamics."
    ),
    good_range="-16 to -8 LUFS",
    genre_notes=(
        "EDM/hip-hop masters often land at -6 to -9 LUFS (turned down 5-8 dB "
        "on streaming). Pop typically -8 to -12. Jazz -12 to -18, preserving "
        "natural dynamics. Classical -18 to -24."
    ),
    technical=(
        "Standard: ITU-R BS.1770-5, EBU R128. K-weighted loudness using a "
        "two-stage filter (high-shelf pre-filter + low-frequency weighting) "
        "with absolute gate at -70 LUFS and relative gate at -10 LU. "
        "Integrated over the full program duration."
    ),
    aliases=["lufs", "loudness", "integrated", "loudness_units"],
)

_LOUDNESS_RANGE = MetricDoc(
    key="loudness_range_lu",
    name="Loudness Range (LRA)",
    module="loudness",
    summary="Dynamic spread from quiet to loud passages (EBU R128).",
    explanation=(
        "Measures the statistical spread of loudness over time — the difference "
        "between the 10th and 95th percentile of short-term loudness. Too low "
        "means the mix sounds flat and fatiguing. Too high means it's hard to "
        "listen to in noisy environments without constant volume adjustment."
    ),
    good_range="5 to 15 LU",
    genre_notes=(
        "EDM/trap: 3-6 LU (heavy compression). Pop: 5-7 LU. Rock: 5-9 LU. "
        "Jazz: 8-15 LU. Classical: 10-25 LU. Within each genre, variation is "
        "enormous — the EBU found pop songs ranging from 3.7 to 12 LU."
    ),
    technical=(
        "Standard: EBU Tech 3342. Uses BS.1770 short-term loudness "
        "(3s window, 100ms overlap) with absolute gate at -70 LUFS and "
        "relative gate at -20 LU. LRA = P95 - P10 of the gated distribution."
    ),
    aliases=["lra", "loudness_range", "dynamic_range"],
)

_TRUE_PEAK = MetricDoc(
    key="true_peak_dbtp",
    name="True Peak",
    module="loudness",
    summary="Maximum reconstructed waveform level (inter-sample peaks).",
    explanation=(
        "The maximum level of the continuous waveform reconstructed between "
        "samples. Sample-peak meters miss inter-sample peaks that cause "
        "clipping during D/A conversion and lossy codec encoding (AAC, Ogg, "
        "MP3). The -1.0 dBTP ceiling leaves headroom for codec reconstruction."
    ),
    good_range="Below -1.0 dBTP",
    genre_notes=(
        "The -1.0 dBTP ceiling applies to all genres — it's a technical "
        "safety margin for codec conversion, not an aesthetic choice. Some "
        "mastering engineers use -1.5 dBTP for extra safety."
    ),
    technical=(
        "Standard: ITU-R BS.1770-5. Measured using minimum 4x oversampling. "
        "bounce-house uses ffmpeg's loudnorm filter for true peak measurement, "
        "falling back to sample peak when ffmpeg is unavailable. "
        "EBU R128 specifies max -1.0 dBTP. Apple Music requires -1.0 dBTP."
    ),
    aliases=["true_peak", "tp", "dbtp", "peak", "inter_sample"],
)

_SAMPLE_PEAK = MetricDoc(
    key="sample_peak_dbfs",
    name="Sample Peak",
    module="loudness",
    summary="Maximum absolute sample value in the digital signal.",
    explanation=(
        "The highest individual sample value in the waveform, in dBFS. "
        "Unlike true peak, this only measures the discrete sample values "
        "and may miss inter-sample peaks. Useful as a quick check but "
        "true peak is the more reliable ceiling measurement."
    ),
    good_range="Below -0.3 dBFS",
    genre_notes="Applies equally to all genres.",
    technical=(
        "Method: 20 * log10(max(|samples|)). This is the standard digital "
        "peak measurement without oversampling. Does not account for "
        "inter-sample peaks that occur during D/A reconstruction."
    ),
    aliases=["sample_peak", "dbfs", "digital_peak"],
)

_RMS = MetricDoc(
    key="rms_db",
    name="RMS Level",
    module="loudness",
    summary="Root mean square energy level of the signal.",
    explanation=(
        "The average power of the signal, expressed in dB. RMS correlates "
        "roughly with perceived loudness for simple signals but LUFS is more "
        "perceptually accurate for complex mixes. RMS is still useful as a "
        "component of crest factor calculation."
    ),
    good_range="-20 to -10 dB (varies widely by genre)",
    genre_notes=(
        "RMS targets vary widely. Heavy EDM may have RMS near -8 dB; "
        "classical recordings often sit at -25 dB or lower. LUFS is the "
        "better metric for loudness comparison across genres."
    ),
    technical=(
        "Method: 20 * log10(sqrt(mean(samples^2))). Computed over all "
        "samples in the file. No frequency weighting or gating is applied, "
        "unlike LUFS measurement."
    ),
    aliases=["rms", "rms_level", "average_level"],
)

_CREST_FACTOR = MetricDoc(
    key="crest_factor_db",
    name="Crest Factor",
    module="loudness",
    summary="Peak-to-RMS ratio — reveals how much transient headroom exists.",
    explanation=(
        "The ratio of peak level to RMS level in dB. Indicates how much "
        "transient punch exists above the sustained energy. Low crest factor "
        "means heavily compressed/limited audio. High crest factor means "
        "strong transients with lower sustained energy — more natural and "
        "punchy but quieter on average."
    ),
    good_range="8 to 14 dB",
    genre_notes=(
        "EDM/trap: 3-5 dB (extremely compressed). Pop: 5-8 dB. Rock: 8-12 dB. "
        "Jazz: 8-14 dB. Classical: 14-20+ dB. Below 6 dB generally sounds "
        "squashed; above 18 dB is likely unprocessed."
    ),
    technical=(
        "Method: sample_peak_dBFS - RMS_dB. Related to PSR (Peak-to-Short-term "
        "Loudness Ratio) which uses a 3s BS.1770 window instead of RMS, and "
        "PLR (Peak-to-Loudness Ratio) which uses integrated loudness."
    ),
    aliases=["crest", "crest_factor", "dynamics", "transients"],
)

_PLR = MetricDoc(
    key="plr_db",
    name="Peak-to-Loudness Ratio (PLR)",
    module="loudness",
    summary="True peak minus integrated LUFS — over-compression indicator.",
    explanation=(
        "The difference between the true peak level and the integrated "
        "loudness. Low PLR indicates the limiter ceiling is very close to "
        "the average loudness, meaning the audio has been pushed hard "
        "against the limiter. Well-mastered audio typically has PLR above "
        "10 dB. Below 8 dB suggests excessive limiting."
    ),
    good_range="Above 10 dB",
    genre_notes=(
        "EDM/hip-hop: PLR 8-12 dB. Pop: 10-14 dB. Rock: 10-16 dB. "
        "Jazz/classical: 14-20+ dB. Below 8 dB in any genre likely "
        "indicates audible limiting artifacts."
    ),
    technical=(
        "Method: true_peak_dBTP - integrated_LUFS. Related to PSR "
        "(Peak-to-Short-term Loudness Ratio) which uses a 3s BS.1770 "
        "window. PLR is the simplest useful over-compression indicator."
    ),
    aliases=["plr", "peak_to_loudness", "peak_loudness_ratio"],
)

# --- Spectrum metrics ---

_CENTROID = MetricDoc(
    key="centroid_hz",
    name="Spectral Centroid",
    module="spectrum",
    summary="Spectral 'center of mass' — correlates with perceived brightness.",
    explanation=(
        "The weighted mean frequency of the spectrum. Perceptually, it "
        "correlates strongly with brightness: a high centroid sounds bright or "
        "harsh, a low centroid sounds dark or muddy. Useful for comparing "
        "tonal balance against reference tracks."
    ),
    good_range="1500 to 3500 Hz (balanced mix)",
    genre_notes=(
        "Dark/warm mixes (classical, ambient, lo-fi): 800-2000 Hz. "
        "Balanced mixes (pop, rock, jazz): 1500-3500 Hz. "
        "Bright/aggressive mixes (EDM, metal): 2500-5000+ Hz."
    ),
    technical=(
        "Method: centroid = sum(f * |X(f)|) / sum(|X(f)|). Computed frame-wise "
        "using librosa.feature.spectral_centroid, then averaged across frames. "
        "Depends heavily on instrumentation — solo cello ~300-800 Hz; "
        "hi-hat-heavy loop >6000 Hz."
    ),
    aliases=["centroid", "center", "brightness_freq", "spectral_centroid"],
)

_BANDWIDTH = MetricDoc(
    key="bandwidth_hz",
    name="Spectral Bandwidth",
    module="spectrum",
    summary="How spread out the spectral energy is around the centroid.",
    explanation=(
        "The magnitude-weighted standard deviation of frequencies around the "
        "centroid. Narrow bandwidth means energy concentrated in a few "
        "frequencies (tonal). Wide bandwidth means energy spread broadly "
        "(complex arrangement or noise). Helps identify if a mix is "
        "spectrally 'thin' or 'full'."
    ),
    good_range="1500 to 4000 Hz (complex arrangement)",
    genre_notes=(
        "Simple/tonal sounds: 500-1500 Hz. Full arrangements: 1500-4000+ Hz. "
        "Very high bandwidth can indicate noise issues."
    ),
    technical=(
        "Method: magnitude-weighted standard deviation around centroid. "
        "Computed via librosa.feature.spectral_bandwidth, averaged across "
        "frames."
    ),
    aliases=["bandwidth", "spectral_bandwidth", "spread"],
)

_ROLLOFF = MetricDoc(
    key="rolloff_hz",
    name="Spectral Rolloff (85%)",
    module="spectrum",
    summary="Frequency below which 85% of spectral energy is contained.",
    explanation=(
        "Approximates the upper edge of significant spectral energy. A low "
        "rolloff means the mix lacks high-frequency content (dull). A very "
        "high rolloff suggests lots of energy in upper frequencies (bright, "
        "possibly harsh or noisy)."
    ),
    good_range="4000 to 8000 Hz (at 85%)",
    genre_notes=(
        "Dark/muffled mixes: 2000-4000 Hz. Balanced: 4000-8000 Hz. "
        "Bright/airy: 8000-12000+ Hz."
    ),
    technical=(
        "Method: frequency at which cumulative spectral energy reaches 85% "
        "of total. Computed via librosa.feature.spectral_rolloff with "
        "roll_percent=0.85, averaged across frames."
    ),
    aliases=["rolloff", "spectral_rolloff", "high_freq_edge"],
)

_FLATNESS = MetricDoc(
    key="flatness",
    name="Spectral Flatness",
    module="spectrum",
    summary="Tonality vs. noise — 0.0 is pure tone, 1.0 is white noise.",
    explanation=(
        "The ratio of geometric mean to arithmetic mean of the power spectrum. "
        "Low flatness indicates strong tonal content (pitched instruments). "
        "High flatness indicates noise-like energy. Useful for identifying "
        "congested or noisy frequency regions."
    ),
    good_range="0.1 to 0.4 (typical mixed music)",
    genre_notes=(
        "Sustained pitched instruments: 0.0-0.1. Typical mixes: 0.1-0.4. "
        "Percussion-heavy: 0.3-0.6. Noise/texture: 0.8-1.0."
    ),
    technical=(
        "Method: geometric_mean(S) / arithmetic_mean(S) where S is the power "
        "spectrum. Also known as Wiener entropy. Computed via "
        "librosa.feature.spectral_flatness, averaged across frames."
    ),
    aliases=["flatness", "spectral_flatness", "tonality", "wiener_entropy"],
)

_BANDS = MetricDoc(
    key="bands",
    name="Band Energies",
    module="spectrum",
    summary="Energy distribution across 7 mixing-relevant frequency bands.",
    explanation=(
        "Measures average energy in sub-bass (20-60 Hz), bass (60-250 Hz), "
        "low-mid (250-500 Hz), mid (500-2000 Hz), upper-mid (2000-4000 Hz), "
        "presence (4000-6000 Hz), and brilliance (6000-20000 Hz). Reveals "
        "where your mix is heavy or thin relative to a balanced spectrum "
        "or reference track."
    ),
    good_range="Relative — compare against reference tracks in your genre",
    genre_notes=(
        "EDM/hip-hop: strong sub-bass and bass energy. Rock: emphasis on "
        "upper-mid and presence. Jazz: relatively flat with gentle rolloff. "
        "Use the compare command with a reference track for meaningful "
        "band-by-band comparison."
    ),
    technical=(
        "Method: STFT with n_fft=4096, then mean power in each band "
        "converted to dB. Bands: sub-bass (20-60 Hz), bass (60-250 Hz), "
        "low-mid (250-500 Hz), mid (500-2 kHz), upper-mid (2-4 kHz), "
        "presence (4-6 kHz), brilliance (6-20 kHz)."
    ),
    aliases=["bands", "band_energies", "frequency_bands", "eq", "spectrum_bands"],
)

# --- Stereo metrics ---

_PHASE_CORRELATION = MetricDoc(
    key="phase_correlation",
    name="Phase Correlation",
    module="stereo",
    summary="L/R channel correlation — measures mono compatibility.",
    explanation=(
        "The Pearson correlation between left and right channels. +1.0 means "
        "identical channels (mono). 0.0 means no correlation (widest safe "
        "stereo). Below 0.0 means phase cancellation — elements will disappear "
        "or thin out when summed to mono (Bluetooth speakers, PA systems, "
        "club subs)."
    ),
    good_range="+0.3 to +0.7",
    genre_notes=(
        "All genres benefit from correlation above +0.3 for safe mono "
        "playback. Ambient/electronic can work at 0.0-0.3 but should be "
        "checked in mono. Any sustained reading below 0.0 needs fixing."
    ),
    technical=(
        "Method: Pearson correlation coefficient r = sum(L*R) / "
        "sqrt(sum(L^2) * sum(R^2)) computed over the full signal. "
        "Equivalent to a goniometer's vertical vs horizontal energy ratio."
    ),
    aliases=["phase", "correlation", "mono_compat", "goniometer"],
)

_MID_RMS = MetricDoc(
    key="mid_rms_db",
    name="Mid RMS",
    module="stereo",
    summary="RMS level of the mid (center) signal in M/S decomposition.",
    explanation=(
        "The energy in the mid (mono-sum) channel: (L+R)/2. This is "
        "everything centered in the stereo image — lead vocals, bass, kick, "
        "snare center. High mid energy relative to side means a focused, "
        "mono-compatible mix."
    ),
    good_range="Relative to side RMS — see M/S Ratio",
    genre_notes="Varies with mix width. See M/S Ratio and Stereo Width.",
    technical=(
        "Method: mid = (L+R)/2, then 20*log10(rms(mid)). Part of the "
        "mid/side decomposition commonly used in mastering."
    ),
    aliases=["mid", "mid_rms", "center", "mid_channel"],
)

_SIDE_RMS = MetricDoc(
    key="side_rms_db",
    name="Side RMS",
    module="stereo",
    summary="RMS level of the side (difference) signal in M/S decomposition.",
    explanation=(
        "The energy in the side (difference) channel: (L-R)/2. This is "
        "everything panned or different between channels — stereo reverbs, "
        "wide synths, hard-panned guitars. High side energy means a wide "
        "stereo image but potential mono compatibility issues."
    ),
    good_range="Relative to mid RMS — see M/S Ratio",
    genre_notes="Varies with mix width. See M/S Ratio and Stereo Width.",
    technical=(
        "Method: side = (L-R)/2, then 20*log10(rms(side)). Part of the "
        "mid/side decomposition."
    ),
    aliases=["side", "side_rms", "difference", "side_channel"],
)

_MS_RATIO = MetricDoc(
    key="ms_ratio_db",
    name="M/S Ratio",
    module="stereo",
    summary="Mid-to-side energy balance — higher means narrower stereo image.",
    explanation=(
        "The difference between mid and side RMS levels in dB. A large "
        "positive ratio means the mix is mostly center-focused (narrow). "
        "A small or negative ratio means lots of side energy (wide or "
        "potentially problematic)."
    ),
    good_range="3 to 12 dB (mid louder than side)",
    genre_notes=(
        "Mono-heavy genres (hip-hop, classical): 8-15+ dB. "
        "Wide mixes (ambient, EDM): 3-6 dB. "
        "Negative M/S ratio indicates more side than mid — unusual and "
        "likely problematic."
    ),
    technical=(
        "Method: mid_rms_db - side_rms_db. A positive value means mid "
        "dominates; negative means side dominates."
    ),
    aliases=["ms_ratio", "mid_side_ratio", "ms"],
)

_STEREO_WIDTH = MetricDoc(
    key="stereo_width",
    name="Stereo Width",
    module="stereo",
    summary="Side-to-total energy ratio — 0.0 is mono, 0.5 is equal M/S.",
    explanation=(
        "The ratio of side RMS to (mid RMS + side RMS). 0.0 means purely "
        "mono. 0.5 means equal mid and side energy (extremely wide). "
        "Typical mixes sit between 0.2 and 0.4."
    ),
    good_range="0.2 to 0.4",
    genre_notes=(
        "Mono/narrow: 0.0-0.1. Normal stereo: 0.2-0.4. Wide: 0.4-0.6 "
        "(ambient, cinematic). Above 0.5: more side than mid, likely has "
        "severe mono compatibility issues."
    ),
    technical=(
        "Method: side_rms / (mid_rms + side_rms) where mid=(L+R)/2 and "
        "side=(L-R)/2. Ranges from 0.0 (mono) to 0.5 (equal mid/side)."
    ),
    aliases=["width", "stereo_width", "image_width"],
)

_BALANCE = MetricDoc(
    key="balance_db",
    name="Channel Balance",
    module="stereo",
    summary="L/R level difference — 0 dB means perfectly centered.",
    explanation=(
        "The RMS level difference between left and right channels in dB. "
        "Positive means left is louder; negative means right is louder. "
        "Significant imbalance indicates a panning issue or accidental "
        "gain offset."
    ),
    good_range="Within +/- 0.5 dB",
    genre_notes="Applies to all genres. Imbalance above 1.5 dB is audible.",
    technical=(
        "Method: 20*log10(rms(L)) - 20*log10(rms(R)). A simple left-right "
        "energy comparison."
    ),
    aliases=["balance", "pan", "channel_balance", "lr_balance"],
)

_MIN_BLOCK_CORR = MetricDoc(
    key="min_block_correlation",
    name="Min Block Correlation",
    module="stereo",
    summary="Worst-case phase correlation in any 50ms window.",
    explanation=(
        "The minimum phase correlation found in any 50ms block of the signal. "
        "Even if the overall correlation is healthy, individual sections with "
        "negative correlation will cause audible phase cancellation in mono. "
        "Identifies problematic stereo effects, flanger sweeps, or "
        "polarity-inverted sections."
    ),
    good_range="Above 0.0",
    genre_notes=(
        "Brief dips below 0.0 during transitions or effects may be acceptable "
        "in electronic music. Sustained negative correlation in any section "
        "is problematic for all genres."
    ),
    technical=(
        "Method: signal split into 50ms blocks (block_size = sr * 0.05). "
        "Pearson correlation computed per block. Returns the minimum value. "
        "Blocks with near-zero standard deviation are skipped."
    ),
    aliases=["min_corr", "min_block", "worst_correlation", "block_correlation"],
)

_FREQ_WIDTH = MetricDoc(
    key="frequency_width",
    name="Frequency-Dependent Width",
    module="stereo",
    summary="Per-band stereo correlation across frequency ranges.",
    explanation=(
        "Stereo correlation measured separately in sub-bass (20-120 Hz), "
        "low-mid (120-500 Hz), mid (500-2000 Hz), upper-mid (2-8 kHz), "
        "and air (8-20 kHz). Low frequencies should be highly correlated "
        "(near mono). Higher frequencies can be wider. Reveals frequency "
        "regions with phase problems."
    ),
    good_range="Sub-bass >0.9, lows >0.5, mids/highs >0.0",
    genre_notes=(
        "Bass below 120 Hz should always be mono (correlation near 1.0) — "
        "out-of-phase bass causes cancellation on subs, PA systems, and "
        "vinyl. Higher frequency bands can be wider for all genres."
    ),
    technical=(
        "Method: STFT-based L/R correlation per frequency band. Bands: "
        "sub-bass (20-120 Hz), low-mid (120-500 Hz), mid (500-2 kHz), "
        "upper-mid (2-8 kHz), air (8-20 kHz). Uses scipy.signal.stft "
        "with nperseg=4096."
    ),
    aliases=["freq_width", "frequency_correlation", "band_width", "freq_stereo"],
)

# --- Perceptual metrics ---

_BRIGHTNESS = MetricDoc(
    key="brightness",
    name="Brightness",
    module="perceptual",
    summary="High-frequency energy ratio — how bright or dark the mix sounds.",
    explanation=(
        "The ratio of energy above 4 kHz to total energy (proxy mode), or a "
        "perceptual brightness score (timbral_models mode). Higher values "
        "mean a brighter, more airy mix. Lower values mean a darker, warmer "
        "tone. Complements the spectral centroid with a single perceptual "
        "number."
    ),
    good_range="0.1 to 0.3 (proxy mode, genre-dependent)",
    genre_notes=(
        "Bright genres (EDM, pop): higher brightness values. "
        "Dark genres (lo-fi, ambient, dub): lower values. "
        "Compare against reference tracks in your genre rather than "
        "targeting absolute values."
    ),
    technical=(
        "Proxy method: sum(S[f >= 4kHz]) / sum(S). When timbral_models is "
        "installed, uses AudioCommons timbral brightness model instead. "
        "STFT with n_fft=4096."
    ),
    aliases=["brightness", "bright", "air", "high_freq_energy"],
)

_WARMTH = MetricDoc(
    key="warmth",
    name="Warmth",
    module="perceptual",
    summary="Low-mid energy ratio — how warm or thin the mix sounds.",
    explanation=(
        "The ratio of energy in the 200-500 Hz range to total energy "
        "(proxy mode), or a perceptual warmth score (timbral_models mode). "
        "Higher values mean a warmer, fuller low-mid character. Very high "
        "values may indicate muddiness."
    ),
    good_range="0.1 to 0.3 (proxy mode, genre-dependent)",
    genre_notes=(
        "Warm genres (R&B, soul, jazz): higher values. "
        "Thin/bright genres (some electronic): lower values. "
        "Compare against reference tracks rather than targeting absolutes."
    ),
    technical=(
        "Proxy method: sum(S[200Hz <= f < 500Hz]) / sum(S). When "
        "timbral_models is installed, uses AudioCommons timbral warmth "
        "model. STFT with n_fft=4096."
    ),
    aliases=["warmth", "warm", "body", "low_mid_energy"],
)

# --- Registry ---

METRICS: dict[str, MetricDoc] = {
    doc.key: doc
    for doc in [
        _INTEGRATED_LUFS, _LOUDNESS_RANGE, _TRUE_PEAK, _SAMPLE_PEAK,
        _RMS, _CREST_FACTOR, _PLR,
        _CENTROID, _BANDWIDTH, _ROLLOFF, _FLATNESS, _BANDS,
        _PHASE_CORRELATION, _MID_RMS, _SIDE_RMS, _MS_RATIO,
        _STEREO_WIDTH, _BALANCE, _MIN_BLOCK_CORR, _FREQ_WIDTH,
        _BRIGHTNESS, _WARMTH,
    ]
}

MODULES: dict[str, list[str]] = {
    "loudness": [
        "integrated_lufs", "loudness_range_lu", "true_peak_dbtp",
        "sample_peak_dbfs", "rms_db", "crest_factor_db", "plr_db",
    ],
    "spectrum": [
        "centroid_hz", "bandwidth_hz", "rolloff_hz", "flatness", "bands",
    ],
    "stereo": [
        "phase_correlation", "mid_rms_db", "side_rms_db", "ms_ratio_db",
        "stereo_width", "balance_db", "min_block_correlation",
        "frequency_width",
    ],
    "perceptual": ["brightness", "warmth"],
}

# Module display names (shared with report.py)
MODULE_TITLES: dict[str, str] = {
    "loudness": "Loudness & Dynamics",
    "spectrum": "Spectral Balance",
    "stereo": "Stereo & Phase",
    "perceptual": "Perceptual Quality",
}


def resolve_topic(query: str) -> tuple[str, str | list[str]]:
    """Resolve a user query to a module name or metric key.

    Returns:
        ("module", module_name) -- if query matches a module
        ("metric", metric_key) -- if query matches a metric key or alias
        ("none", [suggestions]) -- if no match found
    """
    q = query.lower().strip()

    # 1. Exact module match
    if q in MODULES:
        return ("module", q)

    # 2. Exact metric key match
    if q in METRICS:
        return ("metric", q)

    # 3. Exact alias match
    for key, doc in METRICS.items():
        if q in [a.lower() for a in doc.aliases]:
            return ("metric", key)

    # 4. Case-insensitive substring match on key, name, or alias
    for key, doc in METRICS.items():
        searchable = [key.lower(), doc.name.lower()] + [a.lower() for a in doc.aliases]
        for s in searchable:
            if q in s:
                return ("metric", key)

    # 5. No match — suggest candidates
    suggestions = _suggest(q)
    return ("none", suggestions)


def _suggest(query: str, max_suggestions: int = 3) -> list[str]:
    """Find closest metric/module names for a failed query."""
    q = query.lower()
    scored: list[tuple[int, str]] = []

    for name in list(MODULES.keys()) + list(METRICS.keys()):
        # Score by longest common substring length
        score = _longest_common_substring_len(q, name.lower())
        if score > 0:
            scored.append((score, name))

    for key, doc in METRICS.items():
        for alias in doc.aliases:
            score = _longest_common_substring_len(q, alias.lower())
            if score > 0:
                scored.append((score, key))

    scored.sort(key=lambda x: -x[0])
    seen: list[str] = []
    for _, name in scored:
        if name not in seen:
            seen.append(name)
        if len(seen) >= max_suggestions:
            break
    return seen


def _longest_common_substring_len(a: str, b: str) -> int:
    """Length of the longest common substring between a and b."""
    if not a or not b:
        return 0
    m, n = len(a), len(b)
    prev = [0] * (n + 1)
    best = 0
    for i in range(1, m + 1):
        curr = [0] * (n + 1)
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                curr[j] = prev[j - 1] + 1
                if curr[j] > best:
                    best = curr[j]
        prev = curr
    return best
