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
        "Standard: ITU-R BS.1770-4 Annex 2 (approximated). Method: 4x polyphase "
        "FIR oversampling (2x at >=96 kHz sample rates) via scipy.signal."
        "resample_poly, then peak magnitude in dBTP. Measured natively — no "
        "external tools required."
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
        "Method: 20 * log10(max(|samples|)) on the delivered waveform, measured "
        "before DC removal so any DC offset counts against headroom. This is the "
        "standard digital peak measurement without oversampling; it does not "
        "account for inter-sample peaks that occur during D/A reconstruction."
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
        "Method: per-channel 20*log10(peak/RMS), averaged over channels with "
        "signal (silent channels excluded so hard-panned content is not "
        "diluted). Related to PSR (Peak-to-Short-term Loudness Ratio) which "
        "uses a 3s BS.1770 window instead of RMS, and PLR (Peak-to-Loudness "
        "Ratio) which uses integrated loudness."
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

_DC_OFFSET = MetricDoc(
    key="dc_offset_db",
    name="DC Offset",
    module="loudness",
    summary="Constant (0 Hz) offset detected and removed before analysis.",
    explanation=(
        "A DC offset is a constant shift of the whole waveform away from zero, "
        "usually introduced by cheap audio interfaces or buggy plugins. It "
        "wastes headroom, can cause clicks at edit points, and skews level "
        "measurements. Bounce House removes it before analysis and reports "
        "the removed amount here."
    ),
    good_range="Below -60 dBFS (effectively none)",
    genre_notes=(
        "Genre-independent. Anything above -40 dBFS is worth fixing at the "
        "source: check plugin chains and enable your DAW's DC-removal filter "
        "on the master bus."
    ),
    technical=(
        "Method: per-channel arithmetic mean of all samples, subtracted at "
        "load; reported as 20*log10(max(|mean|)) in dBFS. LUFS is unaffected "
        "either way (K-weighting removes DC); RMS, crest factor, and band "
        "energies are measured on the DC-free signal."
    ),
    aliases=["dc", "dc_offset", "offset"],
)

_DR_SCORE = MetricDoc(
    key="dr_score",
    name="DR (Dynamic Range)",
    module="loudness",
    summary="Loud-passage dynamic range in the TT/Pleasurize DR convention.",
    explanation=(
        "The DR value compares the loudest 20% of 3-second passages against "
        "their peaks — the number mixing communities trade in ('this master "
        "is DR6'). Unlike crest factor (instantaneous) or LRA (quiet-to-loud "
        "spread), DR asks whether your LOUD sections still breathe."
    ),
    good_range="Above 7",
    genre_notes=(
        "Loud modern masters: DR5-7. Dynamic rock/indie: DR8-12. "
        "Acoustic/jazz/classical: DR12+. Below DR5 almost always sounds "
        "fatiguing on repeat listens."
    ),
    technical=(
        "Method: per channel, 3 s blocks; block RMS = sqrt(2*mean(x^2)) per "
        "the DR convention; DR = 20*log10(second-highest block peak / "
        "quadratic mean of loudest 20% of block RMS values), averaged over "
        "channels. Files under 3 s report no DR."
    ),
    aliases=["dr", "dr14", "dynamic_range"],
)

_RMS_CURVE = MetricDoc(
    key="rms_curve_db",
    name="Level Over Time",
    module="loudness",
    summary="RMS level curve across the track (up to 50 points).",
    explanation=(
        "A coarse loudness contour: spot sections that are much louder/quieter "
        "than intended, missing dynamics between verse and chorus, or an export "
        "that faded early."
    ),
    good_range="Informational",
    genre_notes="Genre-independent.",
    technical=(
        "Method: RMS in dB over up to 50 equal time segments, floor -100 dB. "
        "Also intended for external plotting via --json."
    ),
    aliases=["level_curve", "loudness_curve"],
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
        "Dark/muffled mixes: 2000-4000 Hz. Balanced: 4000-8000 Hz. Bright/airy: 8000-12000+ Hz."
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
        "Energy in seven mixing-relevant frequency bands, each expressed in "
        "dB relative to the file's own broadband average — positive means "
        "the band sits above the mix's average spectral density, negative "
        "below. Because values are relative, they are comparable between "
        "files regardless of overall level."
    ),
    good_range="Relative — compare against reference tracks in your genre",
    genre_notes=(
        "EDM/hip-hop: strong sub-bass and bass energy. Rock: emphasis on "
        "upper-mid and presence. Jazz: relatively flat with gentle rolloff. "
        "Use the compare command with a reference track for meaningful "
        "band-by-band comparison."
    ),
    technical=(
        "Method: mean STFT power (n_fft=4096) per band, in dB relative to "
        "the mean power density across 20 Hz-20 kHz of the same file. Bands: "
        "sub-bass 20-60, bass 60-250, low-mid 250-500, mid 500-2000, "
        "upper-mid 2000-4000, presence 4000-6000, brilliance 6000-20000 Hz."
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
    good_range="+0.5 to +1.0 for a full mix",
    genre_notes=(
        "Finished mixes typically read +0.5 to +1.0 broadband. Ambient and "
        "wide electronic productions may dip toward +0.1-0.5 — acceptable if "
        "a mono check confirms nothing disappears. Below +0.1 means real "
        "mono cancellation risk on Bluetooth speakers, phones, and PA subs."
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
        "Method: side = (L-R)/2, then 20*log10(rms(side)). Part of the mid/side decomposition."
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
    summary="L/R decorrelation, balance-compensated — 0 is mono/panned, 0.5 independent.",
    explanation=(
        "How decorrelated the left and right channels are, after compensating "
        "for level imbalance: 0 means the two channels carry the same signal "
        "(even if panned), 0.5 means fully independent content. Pure panning "
        "does not count as width — check Channel Balance for that. Width is "
        "undefined (not reported) when one channel is silent."
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
        " Channels are normalized to equal RMS before the M/S split so panning "
        "does not register as width."
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
        "Method: 20*log10(rms(L)) - 20*log10(rms(R)). A simple left-right energy comparison."
    ),
    aliases=["balance", "pan", "channel_balance", "lr_balance"],
)

_LOW_BLOCK_CORR = MetricDoc(
    key="low_block_correlation",
    name="Block Correlation (5th Percentile)",
    module="stereo",
    summary="5th percentile phase correlation across 50ms blocks.",
    explanation=(
        "The 5th percentile of per-block phase correlation values. Unlike the "
        "minimum, this metric ignores isolated one-off dips (e.g. a single drum "
        "hit or transient) and instead indicates whether phase issues are sustained "
        "across multiple sections of the signal."
    ),
    good_range="Above 0.0",
    genre_notes=(
        "Electronic music with heavy stereo processing may show lower values. "
        "Sustained negative correlation is problematic for all genres."
    ),
    technical=(
        "Method: signal split into 50ms blocks (block_size = sr * 0.05). "
        "Pearson correlation computed per block. Returns the 5th percentile "
        "(numpy.percentile with p=5). Blocks with near-zero standard deviation "
        "are skipped."
    ),
    aliases=["low_corr", "low_block", "p5_correlation", "block_corr_p5"],
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

_CORRELATION_CURVE = MetricDoc(
    key="correlation_curve",
    name="Correlation Over Time",
    module="stereo",
    summary="Stereo correlation curve across the track (up to 50 points).",
    explanation=(
        "Shows WHERE phase problems live: a dip to negative values in one "
        "section points at a specific stereo effect or layered part, which a "
        "single whole-track number hides."
    ),
    good_range="Informational",
    genre_notes="Genre-independent.",
    technical=(
        "Method: 50 ms Pearson block correlations averaged into up to 50 "
        "buckets; silent buckets are null."
    ),
    aliases=["corr_curve", "phase_curve"],
)

# --- Translation metrics ---

_MONO_LOSS = MetricDoc(
    key="mono_loss_db",
    name="Mono Loss",
    module="translation",
    summary="Energy lost when the mix is summed to mono.",
    explanation=(
        "Phones, Bluetooth speakers, club PA subs, and many cafe systems play "
        "your mix in mono. This measures how much energy disappears when L and "
        "R are summed: 0 dB means nothing lost, -3 dB is a hard-panned "
        "element's pan-law drop, and larger losses mean anti-phase content is "
        "cancelling itself."
    ),
    good_range="0 to -1 dB",
    genre_notes=(
        "Genre-independent. Wide electronic mixes tolerate up to ~-2 dB if a "
        "mono listen confirms nothing vital vanishes."
    ),
    technical=(
        "Method: 10*log10(mean(((L+R)/2)^2) / mean of per-channel power). "
        "Per-band version uses STFT (nperseg=4096) over the same five bands "
        "as the stereo analyzer."
    ),
    aliases=["mono_loss", "mono", "translation"],
)

_BAND_MONO_LOSS = MetricDoc(
    key="band_mono_loss",
    name="Mono Loss by Band",
    module="translation",
    summary="Where in the spectrum mono summing cancels energy.",
    explanation=(
        "Localizes mono cancellation: a big low-mid loss usually means "
        "stereo-widened guitars/synths; sub-bass loss means stereo bass (see "
        "the Wide Bass diagnostic)."
    ),
    good_range="Each band 0 to -1 dB",
    genre_notes="Genre-independent.",
    technical=(
        "Method: per-band mono-sum STFT power vs per-channel average power, "
        "bands 20-120/120-500/500-2k/2k-8k/8k-20k Hz."
    ),
    aliases=["band_loss"],
)

_LOW_END_RELIANCE = MetricDoc(
    key="low_end_reliance",
    name="Low-End Reliance",
    module="translation",
    summary="Fraction of the mix's energy below 120 Hz.",
    explanation=(
        "Small speakers reproduce almost nothing below ~120 Hz. If most of "
        "your energy lives down there, the mix collapses on a phone: quiet, "
        "thin, and unbalanced. Give melodic low-end parts harmonics "
        "(saturation) so they read on small speakers."
    ),
    good_range="0.05 to 0.35",
    genre_notes=(
        "Bass-heavy genres (hip-hop, EDM) run higher by design — check the "
        "mix on a phone speaker anyway; saturation on the bass keeps it "
        "audible."
    ),
    technical=("Method: STFT power below 120 Hz over total power, computed on the mono sum."),
    aliases=["low_end", "sub_reliance", "small_speaker"],
)

# --- Perceptual metrics ---

_BRIGHTNESS = MetricDoc(
    key="brightness",
    name="Brightness",
    module="perceptual",
    summary="High-frequency energy ratio — how bright or dark the mix sounds.",
    explanation=(
        "The ratio of energy above 4 kHz to total energy, on a 0-1 scale. "
        "This proxy is always computed, regardless of whether the optional "
        "timbral_models extra is installed — diagnostics thresholds are "
        "calibrated to its 0-1 range. Higher values mean a brighter, more "
        "airy mix; lower values mean a darker, warmer tone. When the "
        "perceptual extra is installed, a separate AudioCommons perceptual "
        "score is also reported under timbral_brightness."
    ),
    good_range="0.1 to 0.3 (genre-dependent)",
    genre_notes=(
        "Bright genres (EDM, pop): higher brightness values. "
        "Dark genres (lo-fi, ambient, dub): lower values. "
        "Compare against reference tracks in your genre rather than "
        "targeting absolute values."
    ),
    technical=(
        "Method: sum(S[f >= 4kHz]) / sum(S), STFT with n_fft=4096. Always "
        "computed and always the authoritative 0-1 value used by rules and "
        "diagnostics — see timbral_brightness for the separate ~0-100 "
        "AudioCommons model score."
    ),
    aliases=["brightness", "bright", "air", "high_freq_energy"],
)

_WARMTH = MetricDoc(
    key="warmth",
    name="Warmth",
    module="perceptual",
    summary="Low-mid energy ratio — how warm or thin the mix sounds.",
    explanation=(
        "The ratio of energy in the 200-500 Hz range to total energy, on a "
        "0-1 scale. This proxy is always computed, regardless of whether the "
        "optional timbral_models extra is installed — diagnostics thresholds "
        "are calibrated to its 0-1 range. Higher values mean a warmer, "
        "fuller low-mid character; very high values may indicate muddiness. "
        "When the perceptual extra is installed, a separate AudioCommons "
        "perceptual score is also reported under timbral_warmth."
    ),
    good_range="0.1 to 0.3 (genre-dependent)",
    genre_notes=(
        "Warm genres (R&B, soul, jazz): higher values. "
        "Thin/bright genres (some electronic): lower values. "
        "Compare against reference tracks rather than targeting absolutes."
    ),
    technical=(
        "Method: sum(S[200Hz <= f < 500Hz]) / sum(S), STFT with n_fft=4096. "
        "Always computed and always the authoritative 0-1 value used by "
        "rules and diagnostics — see timbral_warmth for the separate "
        "~0-100 AudioCommons model score."
    ),
    aliases=["warmth", "warm", "body", "low_mid_energy"],
)

_TIMBRAL_BRIGHTNESS = MetricDoc(
    key="timbral_brightness",
    name="Timbral Brightness (AudioCommons)",
    module="perceptual",
    summary="AudioCommons perceptual brightness model score.",
    explanation=(
        "A perceptual brightness score from the AudioCommons timbral_models "
        "library, available only when the optional `perceptual` extra is "
        "installed. Reported alongside — not instead of — the always-on "
        "brightness proxy ratio; it uses a different (~0-100) scale and is "
        "not used by the rules or diagnostics engines."
    ),
    good_range="No fixed range — compare relative to reference tracks",
    genre_notes="See brightness for genre-specific guidance on the proxy scale.",
    technical=(
        "Computed via timbral_models.timbral_brightness(filepath). Returns "
        "None if the model raises on this file. Requires `uv sync --extra "
        "perceptual`."
    ),
    aliases=["timbral_brightness", "audiocommons_brightness"],
)

_TIMBRAL_WARMTH = MetricDoc(
    key="timbral_warmth",
    name="Timbral Warmth (AudioCommons)",
    module="perceptual",
    summary="AudioCommons perceptual warmth model score.",
    explanation=(
        "A perceptual warmth score from the AudioCommons timbral_models "
        "library, available only when the optional `perceptual` extra is "
        "installed. Reported alongside — not instead of — the always-on "
        "warmth proxy ratio; it uses a different (~0-100) scale and is not "
        "used by the rules or diagnostics engines."
    ),
    good_range="No fixed range — compare relative to reference tracks",
    genre_notes="See warmth for genre-specific guidance on the proxy scale.",
    technical=(
        "Computed via timbral_models.timbral_warmth(filepath). Returns None "
        "if the model raises on this file. Requires `uv sync --extra "
        "perceptual`."
    ),
    aliases=["timbral_warmth", "audiocommons_warmth"],
)

# --- Tuning metrics ---

_TUNING_DEVIATION = MetricDoc(
    key="tuning_deviation_cents",
    name="Tuning Deviation",
    module="tuning",
    summary="Offset from A440 concert pitch in cents.",
    explanation=(
        "Measures how far the overall tuning of the recording deviates from "
        "the standard A=440 Hz reference. Positive values mean sharp, negative "
        "means flat. Some orchestras tune to A=442 or A=443. Older recordings "
        "or analog tape transfers may show arbitrary tuning offsets."
    ),
    good_range="Within ±8 cents of A440",
    genre_notes=(
        "Classical orchestras commonly tune to A=441-443. Baroque period "
        "instruments may use A=415. Some genres deliberately use A=432."
    ),
    technical=(
        "Estimated via librosa.estimate_tuning() which builds a histogram of "
        "spectral peak deviations from the equal-tempered grid. Resolution: "
        "1 cent. Works on polyphonic content. Note: the estimate is modulo "
        "one semitone (±50 cents) — a mix tuned a full half-step down (e.g., "
        "A=415) wraps toward zero and cannot be distinguished from concert "
        "pitch by this method."
    ),
    aliases=["tuning", "pitch", "concert_pitch", "a440"],
)

_ESTIMATED_A = MetricDoc(
    key="estimated_a_hz",
    name="Concert Pitch (A)",
    module="tuning",
    summary="Estimated frequency of concert A in Hz.",
    explanation=(
        "The estimated absolute frequency of the note A above middle C. "
        "Standard tuning is A=440 Hz. This is derived from the tuning "
        "deviation measurement."
    ),
    good_range="435-445 Hz",
    genre_notes="See tuning_deviation_cents for genre context.",
    technical="Computed as 440 * 2^(deviation_cents / 1200).",
    aliases=["concert_a", "a_hz"],
)

_PITCH_DRIFT_RANGE = MetricDoc(
    key="pitch_drift_range_cents",
    name="Pitch Drift Range",
    module="tuning",
    summary="Total pitch excursion over the track duration.",
    explanation=(
        "Measures how much the overall tuning varies from start to finish. "
        "A high range indicates pitch drift — the recording drifting sharp or "
        "flat over time. Common in analog tape transfers, poorly calibrated "
        "instruments, or recordings with temperature-induced tuning drift."
    ),
    good_range="Under 8 cents",
    genre_notes=(
        "Live recordings may show more drift than studio recordings. "
        "Analog tape wow can produce 5-20 cents of drift."
    ),
    technical=(
        "Computed by running librosa.estimate_tuning() on overlapping 10-second "
        "windows with 5-second hop, then taking max - min of the resulting curve."
    ),
    aliases=["drift", "pitch_drift", "wow"],
)

_CHROMA_SHARPNESS = MetricDoc(
    key="chroma_sharpness",
    name="Chroma Sharpness",
    module="tuning",
    summary="How well-defined the pitch content is (0-1 scale).",
    explanation=(
        "Measures whether pitch energy concentrates cleanly in individual "
        "chroma bins or spreads diffusely across them. Well-tuned recordings "
        "produce sharp chroma peaks; detuned or poorly intonated recordings "
        "produce broad, smeared distributions."
    ),
    good_range="Above 0.6",
    genre_notes=(
        "Noise-heavy genres (industrial, lo-fi) will naturally score lower. "
        "Highly pitched content (piano, strings) scores higher."
    ),
    technical=(
        "Computed from librosa.feature.chroma_cqt() with forced A440 alignment "
        "(tuning=0). Per-frame peak-to-mean ratio of the 12-bin chroma vector, "
        "normalized to a 0-1 scale where 1.0 = all energy in a single bin."
    ),
    aliases=["chroma", "intonation"],
)

_CLOSEST_STANDARD = MetricDoc(
    key="closest_standard",
    name="Closest Standard Pitch",
    module="tuning",
    summary="Named concert pitch standard nearest to the detected tuning.",
    explanation=(
        "Identifies which named concert pitch standard (A=432, A=440, A=442, etc.) "
        "is closest to the detected tuning. Useful for quickly seeing whether "
        "a recording uses a non-standard reference pitch."
    ),
    good_range="A=440 (standard)",
    genre_notes="See tuning_deviation_cents for genre context.",
    technical=(
        "Computed by finding the minimum distance between the "
        "measured deviation and known standards."
    ),
    aliases=["standard", "reference_pitch"],
)

_PITCH_DRIFT_STD = MetricDoc(
    key="pitch_drift_std_cents",
    name="Pitch Drift (std dev)",
    module="tuning",
    summary="Standard deviation of tuning across time windows.",
    explanation=(
        "Measures tuning consistency over time. A low standard deviation means "
        "the tuning stays stable throughout the track. Higher values indicate "
        "tuning instability — the recording wobbles in pitch over its duration."
    ),
    good_range="Under 3 cents",
    genre_notes=(
        "Live recordings may show more variation than studio recordings. "
        "Analog tape wow produces periodic pitch instability."
    ),
    technical=(
        "Standard deviation of librosa.estimate_tuning() values computed on "
        "overlapping time windows (10-second windows, 5-second hop for long audio)."
    ),
    aliases=["drift_std", "pitch_stability"],
)

_PITCH_DRIFT_TREND = MetricDoc(
    key="pitch_drift_trend_cents_per_min",
    name="Pitch Trend",
    module="tuning",
    summary="Linear pitch drift rate in cents per minute.",
    explanation=(
        "Shows whether pitch is systematically drifting sharp or flat over time. "
        "Positive values mean the recording gets sharper; negative means flatter. "
        "Common in analog tape transfers where speed stability degrades."
    ),
    good_range="Within ±2 cents/min",
    genre_notes=(
        "Vintage recordings transferred from tape may show consistent drift. "
        "Digital recordings should show near-zero trend."
    ),
    technical=(
        "Linear regression slope of the windowed tuning curve, converted to cents per minute."
    ),
    aliases=["pitch_trend", "drift_trend"],
)

# --- Rhythm metrics ---

_TEMPO_BPM = MetricDoc(
    key="tempo_bpm",
    name="Tempo",
    module="rhythm",
    summary="Estimated tempo in beats per minute.",
    explanation=(
        "The rate a listener would tap along at. Tempo itself is never a mix "
        "defect — its value is what it unlocks. Knowing the tempo turns vague "
        "settings into arithmetic: delay times that lock to the grid, "
        "compressor release times short enough to recover before the next "
        "transient, reverb pre-delay measured in note values rather than "
        "guesses. See note_ms for the table."
    ),
    good_range="No good or bad value — informational",
    genre_notes=(
        "House 120-130, techno 125-150, hip-hop 80-100 (often heard at half "
        "time), drum & bass 170-180, ballads 60-80. Genre expectations matter "
        "mainly because they tell you which octave of an ambiguous estimate is "
        "the musically sensible one."
    ),
    technical=(
        "Estimated from a librosa tempogram (onset-strength autocorrelation). "
        "Each lag is scored by autocorrelation strength times a log-normal "
        "prior centred on 120 BPM with a one-octave sigma, restricted to "
        "40-260 BPM. The highest-scoring lag is reported. Those prior "
        "parameters are librosa's own defaults for tempo estimation "
        "(start_bpm=120, std_bpm=1.0, the Ellis approach), not values tuned "
        "here. The prior breaks octave ties toward the rate a listener would "
        "tap without hard-coding a range that would mangle drum & bass or "
        "downtempo."
    ),
    aliases=["bpm", "tempo", "beats_per_minute", "speed"],
)

_TEMPO_CONFIDENCE = MetricDoc(
    key="tempo_confidence",
    name="Tempo Confidence",
    module="rhythm",
    summary="How strongly the reported tempo beat its rivals, 0 to 1.",
    explanation=(
        "Tempo estimation's dominant failure is the octave error — reporting "
        "174 BPM for an 87 BPM track. This is not a bug but genuine ambiguity: "
        "a hi-hat layer on eighth notes really does create a pulse at twice "
        "the beat rate. This value is the winning candidate's share of the "
        "total score. A low value means the metrical level is contested, not "
        "that the music is bad. Read tempo_candidates when it is low."
    ),
    good_range=(
        "Above 0.40 means the top candidate is less contested, not that it is "
        "correct — an octave-wrong estimate can still score above 0.40. Read "
        "tempo_candidates either way"
    ),
    genre_notes=(
        "Rigid programmed material (house, techno) scores high. Rubato, live "
        "playing, ambient, and anything with a busy syncopated top layer "
        "scores lower — correctly."
    ),
    technical=(
        "The top candidate's prior-weighted tempogram score divided by the sum "
        "of the top three candidates' scores. Candidates must be more than "
        "0.05 octaves apart. That is about one tempogram bin wide, so two "
        "candidates can still land at the same metrical level rather than "
        "distinct ones — when that happens, the score splits between them "
        "and this value reads lower than the estimate's real certainty."
    ),
    aliases=["tempo_certainty", "bpm_confidence"],
)

_TEMPO_STABILITY = MetricDoc(
    key="tempo_stability",
    name="Tempo Stability",
    module="rhythm",
    summary="Whether the tempo holds steady: constant, varying, ambiguous, or unmeasurable.",
    explanation=(
        "'constant' means one tempo throughout. 'varying' means the track "
        "changes tempo — expected in live or through-composed material, but a "
        "red flag in programmed music, where it usually means a tempo map got "
        "edited or a bounce drifted. 'ambiguous' means the metrical level is "
        "contested and the number should be read with tempo_candidates. "
        "'unmeasurable' means the file is too short or has too few onsets."
    ),
    good_range="'constant' for programmed material; 'varying' is normal live",
    genre_notes=(
        "Any grid-programmed genre should read 'constant'. Orchestral, jazz, "
        "and singer-songwriter material often reads 'varying' with no fault."
    ),
    technical=(
        "Derived from the number of merged tempo segments and the confidence "
        "value. Confidence below 0.40 forces 'ambiguous' regardless of "
        "segmentation."
    ),
    aliases=["tempo_drift", "stability"],
)

_TEMPO_CANDIDATES = MetricDoc(
    key="tempo_candidates",
    name="Tempo Candidates",
    module="rhythm",
    summary="Top three competing tempo estimates with their normalized scores.",
    explanation=(
        "The alternates the estimator considered, usually related by a factor "
        "of two or three — different metrical levels of the same pulse. When "
        "the top pick looks wrong, the right answer is very often the second "
        "entry. Exposing the list is deliberate: presenting a single number "
        "for a genuinely ambiguous measurement would misrepresent it."
    ),
    good_range="No good or bad value — informational",
    genre_notes=(
        "Half-time hip-hop and drum & bass are the classic cases where the "
        "second candidate is the one a musician would name."
    ),
    technical=(
        "The three highest-scoring tempogram lags after prior weighting, "
        "separated by more than 0.05 octaves, with scores normalized to sum "
        "to 1.0. That separation is about one tempogram bin wide, so two "
        "candidates can still land at the same metrical level rather than "
        "distinct ones — when that happens, the score is split between them "
        "and tempo_confidence reads lower than the estimate's real certainty."
    ),
    aliases=["tempo_alternates", "bpm_candidates", "octave_alternates"],
)

_TEMPO_SEGMENTS = MetricDoc(
    key="tempo_segments",
    name="Tempo Segments",
    module="rhythm",
    summary="Contiguous spans of near-constant tempo, with start and end times.",
    explanation=(
        "Shows where the tempo changed and roughly when. A track that reads as "
        "one segment held one tempo throughout. Two or more segments means "
        "something moved — deliberate in live and through-composed material, "
        "usually an accident in programmed music."
    ),
    good_range="One segment for programmed material",
    genre_notes=(
        "Multiple segments are unremarkable in orchestral and jazz recordings "
        "and worth investigating in anything sequenced to a grid."
    ),
    technical=(
        "Tempo is estimated in overlapping 12-second windows with a 4-second "
        "hop, then each window is compared against the BPM that started its "
        "run and merged in if it agrees within 3 percent — so a segment ends "
        "on drift away from its own anchor, not from the previous window. "
        "What this reports reliably is WHERE the tempo changed; the BPM "
        "inside each segment carries the same octave ambiguity as the global "
        "estimate. A 12-second window cannot localize a change more "
        "precisely than its own length."
    ),
    aliases=["tempo_map", "tempo_track", "segments"],
)

_SWING_RATIO = MetricDoc(
    key="swing_ratio",
    name="Swing Ratio",
    module="rhythm",
    summary="Where offbeats sit, as a ratio of the straight midpoint.",
    explanation=(
        "1.0 is dead-straight eighth notes; about 1.33 is triplet swing. This "
        "is the most directly actionable rhythm metric: a swung performance "
        "against a straight-quantized delay or a straight sample layer is an "
        "audible fight, and hearing it is easier once you can see the number. "
        "If the mix is swung, set delays by ear or to triplet values rather "
        "than straight ones."
    ),
    good_range="No good or bad value — match your delays and samples to it",
    genre_notes=(
        "Blues, jazz, shuffle-based rock, and much UK garage sit near 1.3-1.5. "
        "House, techno, and most pop sit near 1.0. Trap hi-hats often swing "
        "slightly, around 1.05-1.15."
    ),
    technical=(
        "Onset-strength-weighted mean phase within the beat, restricted to the "
        "offbeat region (0.25 to 0.9 of the beat) so the downbeat transient "
        "does not dominate, divided by 0.5. Verified separation on synthetic "
        "material: straight 1.11, triplet-swung 1.42. Reported only when "
        "tempo_confidence is at least 0.40 — swing is phase within the beat, "
        "so an octave-wrong tempo would make it meaningless."
    ),
    aliases=["swing", "shuffle", "groove", "swing_amount"],
)

_SUBDIVISION = MetricDoc(
    key="subdivision",
    name="Subdivision",
    module="rhythm",
    summary="Whether offbeats read as straight or shuffled.",
    explanation=(
        "A plain-language reading of swing_ratio: 'straight' below 1.20, "
        "'shuffled' at or above it. Use it as a quick check that any "
        "programmed layer you add matches the feel of what is already there."
    ),
    good_range="No good or bad value — informational",
    genre_notes="See swing_ratio for genre context.",
    technical="Thresholded swing_ratio at 1.20.",
    aliases=["feel", "straight_or_swung"],
)

_NOTE_MS = MetricDoc(
    key="note_ms",
    name="Note Lengths",
    module="rhythm",
    summary="Millisecond length of each note value at the detected tempo.",
    explanation=(
        "The table that makes tempo useful at the desk. Set a delay to the "
        "1/8d value for the classic dotted-eighth slap; set a compressor "
        "release shorter than the 1/16 value so it recovers before the next "
        "transient; set reverb pre-delay to 1/16 or 1/8t to keep the tail off "
        "the attack. A 400 ms release at 160 BPM is eating the next hit, and "
        "this table is how you see that at a glance."
    ),
    good_range="No good or bad value — a reference table",
    genre_notes=(
        "Dotted eighth is the signature delay of stadium rock and much modern "
        "pop. Triplet-eighth delays suit shuffled material — cross-check "
        "swing_ratio before choosing."
    ),
    technical=(
        "60000 / tempo_bpm gives the quarter-note length in milliseconds; the "
        "rest are exact multiples. Empty when tempo is unmeasurable. This "
        "table inherits the tempo estimate, so if tempo_bpm is octave-wrong "
        "every value here is wrong by the same factor of two — check "
        "tempo_candidates if the numbers do not match what you hear."
    ),
    aliases=["delay_times", "note_lengths", "delay_ms", "ms"],
)

# --- QC metrics ---

_CLIP_EVENTS = MetricDoc(
    key="clip_events",
    name="Clip Events",
    module="qc",
    summary="Count of hard-clipped sample runs (≥3 consecutive samples at −0.1 dBFS).",
    explanation=(
        "Runs of consecutive full-scale samples mean the waveform was flattened — "
        "digital clipping. A handful may be an intentional loudness aesthetic; "
        "dozens mean your limiter ceiling or export gain staging is wrong."
    ),
    good_range="0",
    genre_notes=(
        "Aggressive EDM/metal masters sometimes clip deliberately; anything else "
        "should be clean. If you didn't choose clipping, fix it."
    ),
    technical=(
        "Method: per channel, count runs of ≥3 consecutive samples with "
        "|x| ≥ 10^(−0.1/20). DC offset is removed before detection."
    ),
    aliases=["clipping", "clip", "clipped"],
)

_LONGEST_CLIP_RUN = MetricDoc(
    key="longest_clip_run",
    name="Longest Clip Run",
    module="qc",
    summary="Length in samples of the longest flattened run.",
    explanation=(
        "Longer runs are more audible: 3–5 samples may pass unnoticed; runs "
        "above ~20 samples (0.5 ms) produce audible distortion on transients."
    ),
    good_range="0 samples",
    genre_notes="Genre-independent.",
    technical="Method: max run length among detected clip runs across channels.",
    aliases=["clip_run"],
)

_LEADING_SILENCE = MetricDoc(
    key="leading_silence_sec",
    name="Leading Silence",
    module="qc",
    summary="Silence before the audio starts.",
    explanation=(
        "Dead air at the start of a bounce usually means the export region "
        "included empty bars. Streaming platforms and CD pressing both want "
        "tight heads."
    ),
    good_range="0 to 0.5 s",
    genre_notes="Genre-independent; leave heads tight and let the platform handle gaps.",
    technical="Method: 10 ms peak-envelope windows below −60 dBFS from the start.",
    aliases=["leading_silence", "head_silence"],
)

_TRAILING_SILENCE = MetricDoc(
    key="trailing_silence_sec",
    name="Trailing Silence",
    module="qc",
    summary="Silence after the audio ends.",
    explanation=(
        "A long silent tail inflates track length and can be an export-region "
        "mistake. Reverb tails that decay below −60 dBFS count as silence here."
    ),
    good_range="0 to 5 s",
    genre_notes="Genre-independent.",
    technical="Method: 10 ms peak-envelope windows below −60 dBFS from the end.",
    aliases=["trailing_silence", "tail_silence"],
)

# --- Registry ---

METRICS: dict[str, MetricDoc] = {
    doc.key: doc
    for doc in [
        _INTEGRATED_LUFS,
        _LOUDNESS_RANGE,
        _TRUE_PEAK,
        _SAMPLE_PEAK,
        _RMS,
        _CREST_FACTOR,
        _PLR,
        _DC_OFFSET,
        _DR_SCORE,
        _RMS_CURVE,
        _CENTROID,
        _BANDWIDTH,
        _ROLLOFF,
        _FLATNESS,
        _BANDS,
        _PHASE_CORRELATION,
        _MID_RMS,
        _SIDE_RMS,
        _MS_RATIO,
        _STEREO_WIDTH,
        _BALANCE,
        _LOW_BLOCK_CORR,
        _FREQ_WIDTH,
        _CORRELATION_CURVE,
        _MONO_LOSS,
        _BAND_MONO_LOSS,
        _LOW_END_RELIANCE,
        _BRIGHTNESS,
        _WARMTH,
        _TIMBRAL_BRIGHTNESS,
        _TIMBRAL_WARMTH,
        _TUNING_DEVIATION,
        _ESTIMATED_A,
        _PITCH_DRIFT_RANGE,
        _CHROMA_SHARPNESS,
        _CLOSEST_STANDARD,
        _PITCH_DRIFT_STD,
        _PITCH_DRIFT_TREND,
        _TEMPO_BPM,
        _TEMPO_CONFIDENCE,
        _TEMPO_STABILITY,
        _TEMPO_CANDIDATES,
        _TEMPO_SEGMENTS,
        _SWING_RATIO,
        _SUBDIVISION,
        _NOTE_MS,
        _CLIP_EVENTS,
        _LONGEST_CLIP_RUN,
        _LEADING_SILENCE,
        _TRAILING_SILENCE,
    ]
}

MODULES: dict[str, list[str]] = {
    "loudness": [
        "integrated_lufs",
        "loudness_range_lu",
        "true_peak_dbtp",
        "sample_peak_dbfs",
        "rms_db",
        "crest_factor_db",
        "plr_db",
        "dc_offset_db",
        "dr_score",
        "rms_curve_db",
    ],
    "spectrum": [
        "centroid_hz",
        "bandwidth_hz",
        "rolloff_hz",
        "flatness",
        "bands",
    ],
    "stereo": [
        "phase_correlation",
        "mid_rms_db",
        "side_rms_db",
        "ms_ratio_db",
        "stereo_width",
        "balance_db",
        "low_block_correlation",
        "frequency_width",
        "correlation_curve",
    ],
    "translation": ["mono_loss_db", "band_mono_loss", "low_end_reliance"],
    "perceptual": ["brightness", "warmth", "timbral_brightness", "timbral_warmth"],
    "tuning": [
        "tuning_deviation_cents",
        "estimated_a_hz",
        "closest_standard",
        "pitch_drift_range_cents",
        "pitch_drift_std_cents",
        "pitch_drift_trend_cents_per_min",
        "chroma_sharpness",
    ],
    "rhythm": [
        "tempo_bpm",
        "tempo_confidence",
        "tempo_stability",
        "tempo_candidates",
        "tempo_segments",
        "swing_ratio",
        "subdivision",
        "note_ms",
    ],
    "qc": [
        "clip_events",
        "longest_clip_run",
        "leading_silence_sec",
        "trailing_silence_sec",
    ],
}

# Module display names (shared with report.py)
MODULE_TITLES: dict[str, str] = {
    "loudness": "Loudness & Dynamics",
    "spectrum": "Spectral Balance",
    "stereo": "Stereo & Phase",
    "translation": "Translation (Mono & Small Speakers)",
    "perceptual": "Perceptual Quality",
    "tuning": "Tuning & Pitch",
    "rhythm": "Rhythm & Groove",
    "qc": "Quality Control",
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
