# TODO

## Open

### Genre reference profiles (future)
- Built-in JSON profiles for common genres (hip-hop, EDM, pop, indie rock, etc.)
- Expected ranges for LUFS, LRA, crest factor, spectral centroid, band energies, stereo width
- `--genre` flag to calibrate pass/warn/fail thresholds per genre
- Inspired by iZotope Tonal Balance Control's 12 genre target curves

### Frequency-dependent stereo rules (future)
- Rules evaluating `frequency_width` per band (currently computed but not assessed)
- Sub-bass correlation < 0.7 warning for "wide bass" problem
- Could fold into diagnostic patterns or standalone rules

### Band energy ratio metrics (future)
- Derived ratios like low_mid/mid, brilliance/bass for tilt-independent diagnostics
- More robust than absolute band energies for detecting mud/harshness without a reference


## Done

### Mix vs. master stage profiles
- `--stage mix|master` flag on `analyze`, `dir`, and single-module subcommands
- Mix stage: LUFS targets -24 to -14, peak threshold -3 dBFS, lenient crest factor
- Master stage (default): existing thresholds unchanged (-16 to -8 LUFS, -1 dBTP peak)
- Streaming-readiness diagnostic disabled in mix mode
- Headroom and bus limiter diagnostics added for mix mode
- Stage-aware rules via `StageProfile` dataclass in `rules.py`

### Batch analysis / CI integration
- `dir` subcommand: `bounce-house dir ./masters/` analyzes all WAV files in a directory
- `--recursive` flag to include subdirectories, `--json` for machine-readable output, `--reference` for comparison
- Rich progress bars: nested file + module bars for batch mode, single module bar for file analysis
- Exit codes for CI/CD gating: 0=all pass, 1=warnings, 2=failures
- Summary table with per-file LUFS, peak, crest factor, warn/fail counts, worst-status badge
- Error resilience: corrupt/unreadable files logged to stderr, processing continues

### Multi-metric diagnostic pattern engine
- 8 patterns: muddy, harsh, thin, over-compressed, flat, mono-incompatible, wide-bass, streaming-unfriendly
- Data-driven pattern table in `diagnostics.py` with min_match threshold logic
- Layers on top of existing single-metric rules (additive, not replacement)
- New "Mix Diagnostics" section at bottom of report output
- PLR (Peak-to-Loudness Ratio) derived metric added to loudness analyzer
- PLR metric docs, rule (pass/warn/fail), and explain command support
- 22 metrics documented across 4 modules (up from 21)

### Add metric documentation / help page
- Implemented as `bounce-house explain` subcommand
- Three drill-down levels: overview, module, single metric
- Fuzzy matching on metric names and aliases
- `--technical` flag for measurement standards and methods
- Inline genre-specific context for all relevant metrics
- 21 metrics documented across 4 modules
