# TODO

## Open

### Multi-metric diagnostic pattern engine
- 8 patterns: muddy, harsh, thin, over-compressed, flat, mono-incompatible, wide-bass, streaming-unfriendly
- Data-driven pattern table in `diagnostics.py` with min_match threshold logic
- Layers on top of existing single-metric rules (additive, not replacement)
- New "Mix Diagnostics" section at bottom of report output
- PLR (Peak-to-Loudness Ratio) derived metric added to loudness analyzer
- Design: `docs/plans/2026-02-28-diagnostics-design.md`

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

### Batch analysis / CI integration (future)
- Analyze multiple files in one command
- Exit codes based on worst severity for CI/CD gating
- Summary table across files

## Done

### Add metric documentation / help page
- Implemented as `bounce-house explain` subcommand
- Three drill-down levels: overview, module, single metric
- Fuzzy matching on metric names and aliases
- `--technical` flag for measurement standards and methods
- Inline genre-specific context for all relevant metrics
- 21 metrics documented across 4 modules
