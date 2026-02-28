# Design: `bounce-house explain` Command

## Overview

Add an `explain` subcommand that provides metric documentation directly in the CLI. Engineers can look up what each metric measures, why it matters for mixing, what good/bad values look like, and how they vary by genre.

## User Interface

Three levels of drill-down:

```
bounce-house explain              # overview: 1-line summary per metric, grouped by module
bounce-house explain loudness     # module: full explanation of each metric in that module
bounce-house explain lufs         # single metric: deep dive on one metric
```

A `--technical` flag adds measurement method, standard references, and formulas:

```
bounce-house explain lufs --technical
```

Fuzzy matching on metric names: `cent`, `centroid`, or `spectral_centroid` all resolve to `centroid_hz`. If no match, suggest closest candidates.

## Audience

Both working audio engineers and home studio producers. Default explanations are plain-language and practical. The `--technical` flag adds standards references (ITU-R BS.1770, EBU R128, etc.) and measurement details.

## Data Model

New module: `src/bounce_house/metric_docs.py`

```python
@dataclass
class MetricDoc:
    key: str                  # internal key matching analyzer output, e.g. "integrated_lufs"
    name: str                 # display name, e.g. "Integrated LUFS"
    module: str               # "loudness", "spectrum", "stereo", "perceptual"
    summary: str              # 1-line plain-language summary
    explanation: str           # 2-3 sentences: why it matters for mixing
    good_range: str           # human-readable range string
    genre_notes: str          # inline genre context (EDM vs jazz vs pop etc.)
    technical: str            # measurement method, standard, formula
    aliases: list[str]        # fuzzy match targets: ["lufs", "loudness_units"]
```

All metrics stored in a `METRICS: dict[str, MetricDoc]` keyed by internal key. A `MODULES: dict[str, list[str]]` maps module name to ordered list of metric keys.

### Fuzzy Matching

No external dependencies. Resolution order:
1. Exact match on metric key or module name
2. Exact match on any alias
3. Case-insensitive substring match on key, name, or alias
4. If no match, suggest closest candidates (by substring overlap)

## Metrics Covered

### Loudness Module
- `integrated_lufs` — Integrated loudness per ITU-R BS.1770
- `loudness_range_lu` — Loudness range per EBU Tech 3342
- `true_peak_dbtp` — True peak level
- `sample_peak_dbfs` — Maximum sample value
- `rms_db` — RMS level
- `crest_factor_db` — Peak-to-RMS ratio

### Spectrum Module
- `centroid_hz` — Spectral centroid (perceived brightness)
- `bandwidth_hz` — Spectral bandwidth (spectral spread)
- `rolloff_hz` — Spectral rolloff (high-frequency edge)
- `flatness` — Spectral flatness (tonality vs noise)
- `bands` — 7-band energy distribution (sub-bass through brilliance)

### Stereo Module
- `phase_correlation` — L/R correlation (mono compatibility)
- `mid_rms_db` / `side_rms_db` / `ms_ratio_db` — Mid/Side decomposition
- `stereo_width` — Side-to-total energy ratio
- `balance_db` — L/R channel balance
- `min_block_correlation` — Worst-case temporal phase correlation
- `frequency_width` — Per-band stereo correlation

### Perceptual Module
- `brightness` — High-frequency energy ratio (or timbral_models output)
- `warmth` — Low-mid energy ratio (or timbral_models output)

## Output Formatting

Reuses ANSI color palette from `report.py`. No pager integration — output goes directly to stdout (users can pipe through `less -R` if needed).

### Overview mode (`bounce-house explain`)

```
BOUNCE HOUSE — Metric Reference
════════════════════════════════════════════════════════════

── Loudness & Dynamics ─────────────────────────────────────
  Integrated LUFS     Perceived loudness of the full mix (ITU-R BS.1770)
  Loudness Range      Dynamic spread from quiet to loud passages (EBU R128)
  True Peak           Maximum reconstructed waveform level
  ...

── Spectral Balance ────────────────────────────────────────
  Centroid            Spectral "center of mass" — correlates with brightness
  ...
```

### Module mode (`bounce-house explain loudness`)

```
── Loudness & Dynamics ─────────────────────────────────────

  Integrated LUFS
    Measures the perceived loudness of your mix over its full duration.
    Streaming platforms normalize to target loudness (-14 LUFS on
    Spotify/YouTube, -16 on Apple Music). Masters louder than the
    target get turned down, wasting headroom and dynamics.
    Good range: -16 to -8 LUFS
    Genre: EDM often -6 to -9 LUFS; jazz -12 to -18 LUFS

  Loudness Range (LRA)
    ...
```

### Metric mode (`bounce-house explain lufs`)

Same as module mode but for a single metric. With `--technical`:

```
  Integrated LUFS
    Measures the perceived loudness of your mix over its full duration.
    ...
    Standard: ITU-R BS.1770-5, EBU R128
    Method: K-weighted loudness measurement using a two-stage filter
            (high-shelf pre-filter + low-frequency weighting) with
            absolute gate at -70 LUFS and relative gate at -10 LU.
            Integrated over the full program duration.
```

## File Changes

### New files
- `src/bounce_house/metric_docs.py` — MetricDoc dataclass, METRICS dict, MODULES mapping, fuzzy lookup
- `tests/test_explain.py` — completeness, fuzzy matching, CLI integration, output format

### Modified files
- `src/bounce_house/cli.py` — add `explain` subparser, wire dispatch
- `src/bounce_house/report.py` — add `format_explain_*()` functions

### No new dependencies

## Content Sources

Metric documentation content sourced from:
- ITU-R BS.1770-5 (loudness measurement)
- EBU R128 (broadcast loudness normalization)
- EBU Tech 3342 (loudness range)
- AES TD1004 (loudness measurement)
- Streaming platform documentation (Spotify, Apple Music, YouTube)
- iZotope, Sound on Sound, Sweetwater educational references
- librosa documentation (spectral features)
- CCRMA / ScienceDirect (spectral descriptors)
