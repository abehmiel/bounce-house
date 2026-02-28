# Bounce House

CLI tool for analyzing audio mixes — loudness, spectral balance, stereo imaging, and actionable advice.

## Install

```bash
uv sync --dev
```

## Usage

```bash
# Full analysis
bounce-house analyze mix.wav

# JSON output
bounce-house analyze mix.wav --json

# Individual modules
bounce-house loudness mix.wav
bounce-house spectrum mix.wav
bounce-house stereo mix.wav

# Compare against a reference
bounce-house compare mix.wav reference.wav
```
