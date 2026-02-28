# CLI tools for analyzing audio mixes on macOS

**No single CLI tool covers every mixing and mastering analysis need, but a powerful stack of free, open-source tools can.** The strongest combination for a Python-savvy Logic Pro user is **ffmpeg** (loudness, dynamics, phase), **pyloudnorm** (Python-native LUFS), **librosa** or **essentia** (spectral analysis), and custom **numpy** scripts (stereo imaging) — all installable via Homebrew or pip. For AI-powered feedback, the **ai-music-mix-analyzer** project pairs DSP analysis with GPT-4o, while **matchering** handles automated reference-based mastering. Below is a deep guide to every tool worth knowing.

---

## Dynamics and loudness: ffmpeg, SoX, and pyloudnorm lead the pack

### ffmpeg — the most versatile single tool

Install with `brew install ffmpeg`. Three filters matter most:

**`loudnorm`** measures integrated loudness, true peak, and loudness range, and outputs parseable JSON:

```bash
ffmpeg -i mix.wav -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json -f null -
```

This prints to stderr with keys like `input_i` (integrated LUFS), `input_tp` (true peak dBTP), `input_lra` (loudness range LU), and `input_thresh` (gating threshold). The `input_*` fields are your raw measurements; the `output_*` fields show what normalization *would* produce. Add `print_format=summary` for human-readable output instead.

**`ebur128`** provides continuous momentary/short-term/integrated loudness logging at 10 Hz, plus a final summary with per-channel true peak:

```bash
ffmpeg -nostats -i mix.wav -filter_complex ebur128=peak=true -f null -
```

**`astats`** is arguably the most powerful single-command option for time-domain analysis — it reports **peak level dB, RMS level dB, crest factor, dynamic range, zero crossings, entropy, bit depth, flat factor, and noise floor** per channel and overall:

```bash
ffmpeg -i mix.wav -af astats -f null -
```

For dynamic range specifically, the **`drmeter`** filter computes a DR value similar to the Pleasurize Music Foundation algorithm:

```bash
ffmpeg -i mix.wav -af drmeter -f null -
```

Batch processing is straightforward in shell:

```bash
for f in *.wav; do
  echo "=== $f ==="
  ffmpeg -i "$f" -af loudnorm=print_format=json -f null - 2>&1 | tail -12
done
```

**Key gotcha**: All ffmpeg analysis output goes to **stderr**, not stdout. The `loudnorm` filter internally resamples to 192 kHz, so always specify `-ar 48000` if producing output files.

### SoX — fast RMS, peak, and crest factor from the terminal

Install with `brew install sox`. The `stats` effect gives per-channel and overall metrics:

```bash
sox mix.wav -n stats
```

This reports **peak level dB, RMS level dB, RMS peak/trough dB, crest factor (linear), flat factor, peak count, effective bit depth**, and DC offset. The older `stat` command adds rough frequency and volume adjustment factor. SoX does **not** measure LUFS — it uses simple RMS without K-weighting. Its crest factor is linear (a value of ~7.7 equals ~17.7 dB peak-to-RMS). Last major release was 14.4.2 in 2015, but it remains rock-solid and available via Homebrew.

### pyloudnorm — Python-native ITU-R BS.1770-4

Install with `pip install pyloudnorm soundfile`. Fully compliant with ITU-R BS.1770-4 within **±0.1 dB** tolerance:

```python
import soundfile as sf
import pyloudnorm as pyln
import numpy as np, glob, json

results = []
for path in glob.glob("*.wav"):
    data, rate = sf.read(path)
    meter = pyln.Meter(rate)
    loudness = meter.integrated_loudness(data)
    lra = meter.loudness_range(data)
    peak = 20 * np.log10(np.max(np.abs(data)) + 1e-10)
    results.append({"file": path, "lufs": round(loudness, 1),
                     "lra": round(lra, 1), "peak_dbfs": round(peak, 1)})

print(json.dumps(results, indent=2))
```

pyloudnorm does **not** include true peak measurement (only sample peak via numpy). For ITU-compliant true peak, use ffmpeg's `loudnorm` or oversample with scipy. Pure Python makes it ~3× slower than libebur128's C implementation, but fast enough for batch work.

### Other loudness/dynamics tools worth knowing

- **rsgain** (`brew install rsgain`) — modern, actively maintained ReplayGain 2.0 scanner built on libebur128. Reports integrated loudness, LRA, and true peak. Multithreaded batch scanning built in.
- **loudgain** (`brew install loudgain`) — similar to rsgain, outputs tab-delimited tables suitable for CSV parsing.
- **DR14 T.meter** (`pip install DR14-T.meter`) — computes DR14 dynamic range per track and album average, outputs `dr14.txt` and `dr14.html` reports. Last release 2015 but still functional on Python 3.
- **ffmpeg-normalize** (`pip install ffmpeg-normalize`) — wraps ffmpeg's two-pass loudnorm for batch normalization. Not an analysis tool per se, but useful for normalizing bounces to target LUFS.
- **r128gain** — archived since August 2023; use rsgain instead.

### Dynamics tools comparison

| Tool | LUFS (I) | True peak | LRA | RMS | Crest factor | DR | JSON output | Install |
|------|:--------:|:---------:|:---:|:---:|:------------:|:--:|:-----------:|---------|
| ffmpeg `loudnorm` | ✅ | ✅ | ✅ | — | — | — | ✅ | `brew install ffmpeg` |
| ffmpeg `astats` | — | sample | — | ✅ | ✅ | ✅ | metadata | `brew install ffmpeg` |
| SoX `stats` | — | sample | — | ✅ | ✅ | — | — | `brew install sox` |
| pyloudnorm | ✅ | — | ✅ | — | — | — | script | `pip install pyloudnorm` |
| rsgain | ✅ | ✅ | ✅ | — | — | — | — | `brew install rsgain` |
| DR14 T.meter | — | — | — | ✅ | ✅ | ✅ | HTML | `pip install DR14-T.meter` |

---

## Spectral analysis: librosa and essentia are the heavy hitters

### librosa — the de facto Python audio analysis library

Install with `pip install librosa` (v0.11.0, March 2025, **8,100+ GitHub stars**). Computes spectral centroid, bandwidth, rolloff, flatness, contrast, MFCCs, mel spectrograms, chroma, and tonnetz. Here's a complete octave-band energy analysis:

```python
import librosa
import numpy as np

y, sr = librosa.load('mix.wav', sr=None, mono=True)

# Spectral shape descriptors (frame-wise, then averaged)
centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
bandwidth = np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr))
rolloff = np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85))
flatness = np.mean(librosa.feature.spectral_flatness(y=y))

print(f"Centroid: {centroid:.0f} Hz | Bandwidth: {bandwidth:.0f} Hz")
print(f"Rolloff (85%): {rolloff:.0f} Hz | Flatness: {flatness:.4f}")

# Energy per mixing-relevant frequency band
S = np.abs(librosa.stft(y, n_fft=4096))**2
freqs = librosa.fft_frequencies(sr=sr, n_fft=4096)

bands = [("Sub-bass", 20, 60), ("Bass", 60, 250), ("Low-mid", 250, 500),
         ("Mid", 500, 2000), ("Upper-mid", 2000, 4000),
         ("Presence", 4000, 6000), ("Brilliance", 6000, 20000)]

for name, lo, hi in bands:
    mask = (freqs >= lo) & (freqs < hi)
    db = 10 * np.log10(np.mean(S[mask, :]) + 1e-10)
    print(f"  {name} ({lo}-{hi} Hz): {db:+.1f} dB")
```

### essentia — the most comprehensive single tool

Install with `pip install essentia` (supports macOS ARM64 and x86_64). Essentia's standout feature is its **CLI extractor** that computes dozens of descriptors in one pass and outputs JSON:

```bash
essentia_streaming_extractor_music mix.wav output.json
```

The output JSON includes mean/var/min/max/median for spectral centroid, spread, skewness, kurtosis, complexity, rolloff, contrast, flux, flatness, HPCP (chroma), key/scale detection, chord progressions, BPM, beat positions, loudness, dynamic complexity, and more. For batch processing entire catalogs, this is unmatched — point it at a directory and get structured JSON for every file.

In Python, essentia provides frame-by-frame analysis with algorithms for Bark/Mel/ERB band energies, MFCCs, tonal descriptors (dissonance, inharmonicity), and even **TensorFlow model inference** for high-level features (`pip install essentia-tensorflow`).

### Building a tonal balance comparison tool

No widely-adopted open-source CLI replicates iZotope's Tonal Balance Control, but building one with librosa takes under 30 lines:

```python
import librosa, numpy as np

def spectral_profile(path, sr=44100, n_fft=4096):
    y, sr = librosa.load(path, sr=sr, mono=True)
    S = np.mean(np.abs(librosa.stft(y, n_fft=n_fft))**2, axis=1)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    return freqs, 10 * np.log10(S + 1e-10)

def compare_tonal_balance(mix_path, ref_path):
    freqs, mix_db = spectral_profile(mix_path)
    _, ref_db = spectral_profile(ref_path)
    mix_db -= np.max(mix_db)  # normalize
    ref_db -= np.max(ref_db)
    
    bands = {"Bass (<250 Hz)": (20, 250), "Low-Mid (250-2k)": (250, 2000),
             "Upper-Mid (2k-8k)": (2000, 8000), "Treble (>8k)": (8000, 20000)}
    
    for name, (lo, hi) in bands.items():
        mask = (freqs >= lo) & (freqs < hi)
        diff = np.mean(mix_db[mask]) - np.mean(ref_db[mask])
        print(f"{name}: {diff:+.1f} dB vs reference")
```

### Other spectral tools

- **scipy.signal.welch** — use Welch's method for smoothed power spectral density when you need low-level control over windowing and segment overlap.
- **SoX** — generates spectrogram PNGs (`sox mix.wav -n spectrogram -o spec.png`) and outputs raw power spectrum data (`sox mix.wav -n stat -freq 2> freq.txt`), but cannot compute high-level spectral descriptors.
- **ffmpeg** — the `showspectrumpic` filter generates spectrogram images: `ffmpeg -i mix.wav -lavfi showspectrumpic=s=1024x512 spectrogram.png`.
- **audioFlux** (`pip install audioflux`) — C-core with Python wrapper, significantly faster than librosa for mel spectrogram extraction, supports dozens of time-frequency transforms.
- **Spek** (`brew install --cask spek`) — free GUI spectrogram viewer, excellent for quick visual checks of lossy transcodes (shows hard frequency cutoffs).

---

## Stereo imaging and phase: ffmpeg's aphasemeter plus custom Python

### ffmpeg `aphasemeter` — phase correlation from the terminal

The **aphasemeter** filter outputs per-frame phase correlation values on a **-1 to +1** scale (where +1 = mono, 0 = uncorrelated stereo, -1 = out of phase):

```bash
# Write per-frame phase values to a text file
ffmpeg -i mix.wav -af "aphasemeter=video=0,ametadata=print:file=phase.txt" -f null -

# Quick average phase correlation (pipe through awk)
ffmpeg -i mix.wav -af "aphasemeter=video=0,ametadata=print:file=-" \
  -f null - 2>/dev/null | grep phase | awk -F= '{sum+=$2; n++} END {print "Avg phase:", sum/n}'
```

### ffmpeg `avectorscope` — goniometer/Lissajous visualization

Generate a static goniometer image or video directly from the command line:

```bash
# Single-frame goniometer PNG
ffmpeg -i mix.wav -filter_complex \
  "[0:a]avectorscope=s=800x800:zoom=1.5:mode=lissajous:draw=dot,format=rgb24[v]" \
  -map "[v]" -frames:v 1 goniometer.png

# Full goniometer video
ffmpeg -i mix.wav -filter_complex \
  "[0:a]avectorscope=s=800x800:zoom=1.5:mode=lissajous:draw=line[v]" \
  -map "[v]" -map 0:a goniometer.mp4
```

Modes include `lissajous` (rotated 45° — standard goniometer view), `lissajous_xy` (unrotated), and `polar`.

### Complete Python stereo analyzer

The **Pearson correlation coefficient** between L and R channels is mathematically identical to what DAW correlation meters display. Combined with M/S decomposition, this gives you everything a hardware goniometer shows:

```python
#!/usr/bin/env python3
"""Complete stereo imaging analyzer."""
import numpy as np
import soundfile as sf
import sys

def analyze_stereo(filepath):
    data, sr = sf.read(filepath, dtype='float64')
    if data.ndim == 1:
        print("Mono file — no stereo analysis possible.")
        return
    L, R = data[:, 0], data[:, 1]
    
    # Phase correlation (Pearson r) — identical to DAW correlation meter
    correlation = np.corrcoef(L, R)[0, 1]
    
    # Mid/Side decomposition
    mid = (L + R) / 2.0
    side = (L - R) / 2.0
    mid_rms = np.sqrt(np.mean(mid**2))
    side_rms = np.sqrt(np.mean(side**2))
    mid_db = 20 * np.log10(mid_rms + 1e-10)
    side_db = 20 * np.log10(side_rms + 1e-10)
    
    # Stereo width: 0 = mono, 0.5 = full width, >0.5 = more side than mid
    width = side_rms / (mid_rms + side_rms) if (mid_rms + side_rms) > 0 else 0
    
    # Channel balance
    l_db = 20 * np.log10(np.sqrt(np.mean(L**2)) + 1e-10)
    r_db = 20 * np.log10(np.sqrt(np.mean(R**2)) + 1e-10)
    
    # Windowed phase correlation (50ms blocks) — find minimum
    block = int(sr * 0.05)
    block_corrs = [np.corrcoef(L[i*block:(i+1)*block], R[i*block:(i+1)*block])[0, 1]
                   for i in range(len(L) // block)
                   if np.std(L[i*block:(i+1)*block]) > 1e-10]
    
    print(f"Phase Correlation:  {correlation:+.4f}  (+1=mono, 0=wide, -1=out of phase)")
    print(f"Min Block Corr:     {min(block_corrs):+.4f}  (worst-case 50ms window)")
    print(f"Mid RMS: {mid_db:.1f} dBFS | Side RMS: {side_db:.1f} dBFS")
    print(f"M/S Ratio: {mid_db - side_db:+.1f} dB  (positive = more mid)")
    print(f"Stereo Width: {width:.3f}  (0=mono, 0.5=full)")
    print(f"Balance: {l_db - r_db:+.1f} dB  (positive = left louder)")

if __name__ == "__main__":
    analyze_stereo(sys.argv[1])
```

### Frequency-dependent stereo width

This reveals which frequency ranges are panned wide versus narrow — critical for checking low-end mono compatibility:

```python
from scipy.signal import stft

def frequency_stereo_width(filepath, nperseg=4096):
    data, sr = sf.read(filepath, dtype='float64')
    f, t, Zl = stft(data[:, 0], sr, nperseg=nperseg)
    _, _, Zr = stft(data[:, 1], sr, nperseg=nperseg)
    
    bands = [(20, 120, "Sub/Bass"), (120, 500, "Low-Mid"),
             (500, 2000, "Mid"), (2000, 8000, "Upper-Mid"), (8000, 20000, "Air")]
    
    for lo, hi, name in bands:
        mask = (f >= lo) & (f < hi)
        l_energy = np.abs(Zl[mask, :]).flatten()
        r_energy = np.abs(Zr[mask, :]).flatten()
        corr = np.corrcoef(l_energy, r_energy)[0, 1]
        print(f"  {name} ({lo}-{hi} Hz): correlation {corr:+.3f}")
```

### Generating a matplotlib goniometer plot

```python
import matplotlib.pyplot as plt

def plot_goniometer(filepath, output="goniometer.png", max_samples=500000):
    data, sr = sf.read(filepath, dtype='float64')
    L, R = data[:max_samples, 0], data[:max_samples, 1]
    M = (L + R) / np.sqrt(2)
    S = (L - R) / np.sqrt(2)
    
    fig, ax = plt.subplots(figsize=(8, 8), facecolor='black')
    ax.set_facecolor('black')
    ax.scatter(S, M, s=0.1, c='lime', alpha=0.05)
    ax.set_xlim(-1, 1); ax.set_ylim(-1, 1); ax.set_aspect('equal')
    ax.set_xlabel('Side (L-R)', color='white')
    ax.set_ylabel('Mid (L+R)', color='white')
    plt.savefig(output, dpi=150, facecolor='black')
```

---

## AI-powered mix feedback and automated analysis tools

### ai-music-mix-analyzer — the closest thing to automated mix feedback

The most relevant open-source project is **owgit/ai-music-mix-analyzer** on GitHub (~31 stars, 141 commits, actively maintained). It combines DSP analysis across **7 frequency bands**, stereo field evaluation, dynamic range assessment, and phase correlation with **GPT-4o** (or alternative LLMs) to generate natural-language mixing suggestions. It's a Flask web app rather than a pure CLI tool, but its analysis engine is Python and could be adapted. Requires an OpenAI API key for AI-generated feedback.

### matchering — automated reference-based mastering

**sergree/matchering** (`pip install matchering`) is the standout tool for reference-based work. It analyzes a target mix and a reference track, then matches **RMS level, frequency response, peak amplitude, and stereo width** — pure DSP with no ML black boxes. While it performs *processing* rather than outputting an analysis report, its internal analysis pass effectively solves "how does my mix compare to this reference?"

```python
import matchering as mg
mg.process(
    target="my_mix.wav",
    reference="reference_track.wav",
    results=[mg.pcm24("mastered.wav")]
)
```

Also available as a CLI (`pip install matchering-cli`) and Docker web app. Hosted free at Songmastr.com.

### timbral_models — perceptual quality descriptors

**AudioCommons/timbral_models** computes perceptual indices including **Hardness, Depth, Brightness, Roughness, Warmth, Sharpness, and Boominess**. The Hardness metric specifically correlates with subjective mix quality assessments in published research (used in the `mastering_comparison` evaluation framework from ai-mastering). These descriptors answer questions like "does my mix sound harsh?" in a quantifiable way.

### RoEx Python SDK — cloud-based AI mix analysis

**roex-audio/roex-python** (`pip install roex-python`) provides an API for AI-powered mix analysis, automated mixing, and mastering. The analysis endpoint returns structured insights about a mix's characteristics. Requires an API key from roexaudio.com (likely paid for production use).

### Building your own rule-based analyzer

No single open-source project generates a report saying "your bass is +3 dB above reference, consider cutting 200 Hz." But combining the tools above, an expert Python developer can build one efficiently. The recommended stack:

- **pyloudnorm** → loudness and LRA targets (e.g., flag if LUFS is above -8 or below -16 for streaming)
- **librosa** → octave-band energy vs. reference curve (flag bands deviating >3 dB)
- **numpy** → phase correlation and M/S balance (flag if correlation drops below 0 or bass width > threshold)
- **ffmpeg astats** → crest factor and dynamic range (flag if DR < 6 dB)
- **timbral_models** → perceptual harshness/brightness checks
- **matplotlib** → generate spectrogram, goniometer, and loudness-over-time plots
- **Optional**: pipe the numerical analysis into GPT-4o via the OpenAI API for natural-language feedback

---

## The recommended toolchain for a Logic Pro workflow

For an expert Python developer on macOS doing mixing and mastering in Logic Pro, here is the optimal setup:

- **`brew install ffmpeg sox rsgain`** — covers loudness (LUFS/true peak/LRA), dynamics (RMS/crest/DR), phase correlation (`aphasemeter`), goniometer images (`avectorscope`), and spectrograms from the terminal
- **`pip install pyloudnorm librosa soundfile matchering`** — Python-native loudness measurement, spectral analysis, reference-based mastering
- **`pip install essentia`** — when you need the CLI extractor for batch JSON output of dozens of descriptors in one command
- **`pip install timbral_models`** — for perceptual quality metrics (hardness, brightness, warmth)
- **numpy/scipy/matplotlib** — already in any scientific Python environment; handles stereo analysis, custom FFT, and plot generation

This stack is entirely open-source, installable in minutes, and covers every analysis dimension: dynamics, spectral balance, stereo imaging, and mix quality assessment. The main gap in the ecosystem — a polished, all-in-one CLI that ingests a WAV and outputs a comprehensive mix report — remains an opportunity for a custom Python project combining these building blocks.
