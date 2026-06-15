# StemDeck — Technical: Waveform Acquisition & Rendering

## 1. Data Source: `peaks.json`

The backend produces a JSON file at `/api/jobs/{jobId}/stems/peaks.json` containing signed `[min, max]` peak pairs for each stem. Each stem gets `N` peak pairs, computed server-side from the decoded WAV.

```json
{
  "vocals":  [[-0.12, 0.15], [-0.08, 0.09], ...],
  "drums":   [[-0.45, 0.50], [-0.38, 0.42], ...],
  "bass":    [[-0.21, 0.19], [-0.15, 0.17], ...],
  "other":   [[-0.05, 0.06], [-0.03, 0.04], ...]
}
```

This file is fetched **in parallel with the job-data fetch** (`peaksPromise`), gated by a 3-second AbortController timeout so it never blocks playback even if the file is missing or slow.

---

## 2. Two Playback/Rendering Paths

StemDeck supports two audio backends. The waveform visuals differ depending on which path is active:

| Path | Trigger | Waveform Renderer |
|------|---------|-------------------|
| **Streaming** (`useEngine=false`) | Feature flag off, or decoded PCM >1.2 GB | WaveSurfer.js canvas (`barWidth:3`, `barGap:2`, `barRadius:2`) |
| **Web Audio Engine** (`useEngine=true`) | Default; decodes AudioBuffers in memory | SVG overview layer (`<rect>` bars via `renderOverviewWaveformPath`) |

When the **engine is active**, the multitrack (WaveSurfer) is instantiated with `null` URLs so it never fetches audio — it exists only for the layout container. The CSS class `engine-waveforms` is toggled on `.app` to show the SVG overlay and hide the WaveSurfer canvas.

### 2.1. WaveSurfer Canvas (Streaming Path)

- `Multitrack.create()` with `barWidth: 3, barGap: 2, barRadius: 2` per track
- Wave color: `STEM_COLORS[name]`
- Progress color: `PROGRESS_COLOR` (gold)
- Cursor hidden (`cursorWidth: 0`)
- Tracks normalized to container width (`minPxPerSec: 0`), zero scroll
- `minPxPerSec: 0` keeps the inner waveform at container width, so ruler ticks, playhead, and loop region stay aligned without scroll-position math

### 2.2. SVG Overview Layer (Engine Path + After Peaks Arrive)

Used by both paths as the **primary overview waveform** once `peaks.json` resolves. On the streaming path, it overlays the WaveSurfer canvas (when present); on the engine path, it is the only waveform.

**Architecture**: A single `.stem-waveform-layer` div is inserted as a sibling of `.multitrack-container`. Inside it, one `.stem-waveform-row[data-stem]` per lane, each containing an `<svg>` with `<rect>` bars.

**Layout**:
```
.stem-waveform-layer (absolute positioned, covers multitrack area)
  ├── .stem-waveform-row[data-stem="original"]
  │     └── svg.stem-waveform-svg (viewBox="0 0 {bars} 48")
  │           └── rect × bars
  ├── .stem-waveform-row[data-stem="vocals"]
  │     └── svg.stem-waveform-svg
  ...
```

- 5px bar slot = 3px bar + 2px gap (matching WaveSurfer defaults)
- Bar width ratio: `0.6` of slot (3/5)
- ViewBox width = `barCount`, height = `48`
- `preserveAspectRatio="none"` so SVG stretches horizontally
- Bars rendered centered vertically (y centers around 24), with minimum height 0.7 so silent regions show a faint dotted line instead of vanishing

**Bar count**: `laneWidth / 5`, clamped to minimum 40.

**Normalization**: Cross-stem (shared global max), preserving real amplitude relationships (drums tall, piano short). The single `norm` factor is `1 / globalMax` across all stems.

**CSS styling**:
```css
.stem-waveform-svg rect {
  fill: var(--stem-color);
  opacity: 0.78;
  filter: drop-shadow(0 0 3px color-mix(in srgb, var(--stem-color) 40%, transparent));
}
```

---

## 3. Footer Waveform (Canvas 2D)

Always present in the transport footer bar, rendered on a `<canvas id="footer-waveform">`.

**Data flow**:
1. From `peaks.json`: the first stem's peak pairs are downsampled to 300 bars (`_FOOTER_BARS`). A step filter picks every Nth pair.
2. Fallback: if no `peaks.json`, the first stem WAV is fetched, decoded via `AudioContext.decodeAudioData()`, and peak pairs computed via `bufferMinMaxPeaks(buf, 300)`.

**Rendering** (`_drawFooterWave`):
- Canvas sized at `devicePixelRatio` for HiDPI
- 300 bars with 1px gap
- Each bar spans from sample `mn` to `mx`, normalized to the global per-frame max
- Color: **gold** (`#f4b740`) for played portion (index < `progress × 300`), **dim white** (`rgba(255,255,255,0.13)`) for unplayed
- A gold dot is drawn at the progress position (when `0.001 < progress < 0.999`)
- Redraws on `ResizeObserver` to fill the container

Placeholder fallback (`_drawPlaceholderWave`): 300 bars of synthetic sine-sum amplitudes (`sin(t×3.7) + sin(t×9.1) + sin(t×21.3)`) at opacity `rgba(255,255,255,0.07)`.

---

## 4. Mixer Mini-Wave (SVG)

Each horizontal mixer lane gets a 40-bar SVG thumbnail (`viewBox="0 0 80 26"`).

**Before decode**: Seeded pseudo-random bars shaped by a sine envelope (attack/decay curve):
```js
const env = Math.sin((i / 40) * Math.PI) * 0.7 + 0.3;
const h = env * (rng() * 0.6 + 0.25) * 26;
```
Opacity 0.6, fill = stem color.

**After decode**: Real peaks computed in `renderRealMiniWave`:
1. Read `getChannelData(0)` from the decoded AudioBuffer
2. Divide into 40 bins
3. Peak-find per bin (absolute max)
4. Normalize to per-stem max (each mini-wave fills its own box)
5. Replace SVG children with `<rect>` bars, opacity 0.95

Triggered from:
- **Engine path**: `eng.ready` → `eng.getBuffers()` → `renderDecodedStemVisuals`
- **Streaming path**: `ws.getDecodedData()` in `renderAllMiniWaves`

---

## 5. VU Meter Envelope (Float32Array)

Pre-computed per stem at load time (`buildStemVuEnvelope`) for real-time animation without sample-level processing during playback.

| Parameter | Value |
|-----------|-------|
| FPS | 30 |
| Window | 45 ms (≈1.98 samples at 44.1 kHz) |
| Level formula | `rms × 0.78 + peak × 0.22` |
| Final | `sqrt(level / maxLoudest)` |

The envelope is indexed by `Math.floor(time × 30)` and scaled by the stem's effective gain (volume × mute/solo). Rendered on a `requestAnimationFrame` loop (`startStemVuLoop`) into two DOM targets:
- **Mini meter** (sidebar stem list): CSS `--vu-scale` drives a height-animated bar
- **Lane VU** (mixer column): CSS `--vu-level` drives the meter fill width  

Peak hold decays at 0.025/frame over 28 frames.

---

## 6. Stem Energy Baseline (RMS Bars)

Displayed in the "Stem Energy" panel before playback starts. Computed from the decoded AudioBuffer's global RMS per stem, then normalized so the loudest stem is 100%.

```js
const rms = sqrt(sum(samples²) / sampleCount);
// Normalize: pct = (rms / maxRms) × 100
```

Rendered as CSS `--v` percentage on each `.energy-row b` bar. Overwritten per-frame by the VU loop once playback starts.

---

## 7. Data Flow Summary

```
Backend processing
  │
  ├── WAV files (stems/*.wav)
  │
  ├── peaks.json (pre-computed [min,max] pairs)
  │     │
  │     ├── → footer waveform (canvas, 300 bars)
  │     │     └── _drawFooterWave(progress)
  │     │
  │     └── → overview SVG layer (~1500 → viewBox-width bars)
  │           └── renderAllOverviewWaveformsFromPeaks(stems, peaks)
  │
  └── [Engine path] decode WAVs → AudioBuffers
        │
        ├── → overview SVG layer (from AudioBuffer peaks)
        │     └── renderAllOverviewWaveforms(stems, decodedMap)
        │
        ├── → mixer mini-wave SVGs (40 bars)
        │     └── renderRealMiniWave(name, buffer, color)
        │
        ├── → VU meter envelopes (Float32Array, 30 FPS)
        │     └── startStemVuLoop(stems, decodedMap, token)
        │
        ├── → stem energy baseline (global RMS %)
        │     └── renderStemEnergyBaseline(stems, decodedMap)
        │
        └── → playback: AudioBufferSourceNode → GainNode → AnalyserNode → destination
              └── tick() on requestAnimationFrame drives onTime callback → UI updates
```

### Visual difference between paths

```
Streaming path (WaveSurfer canvas)     Engine path (SVG overview)
┌──────────────────────────────────┐   ┌──────────────────────────────────┐
│ Canvas  │ Canvas  │ Canvas       │   │ SVG rects │ SVG rects │ SVG rects │
│ (orig)  │ (vocals)│ (drums)      │   │ (orig)    │ (vocals)  │ (drums)   │
│ barWidth:3, barGap:2             │   │ 3px bar + 2px gap, drop-shadow  │
│ progressColor: gold              │   │ opacity:0.78, --stem-color      │
└──────────────────────────────────┘   └──────────────────────────────────┘
         Both aligned in .multitrack-container, same lane positions
          CSS .engine-waveforms hides canvas, shows SVG; reverse for streaming
```

---

## 8. Key Constants

| Constant | Value | Location |
|----------|-------|----------|
| `OVERVIEW_WAVE_POINTS` | 1500 | player.js:194 |
| `OVERVIEW_BAR_SLOT_PX` | 5 | player.js:274 |
| `OVERVIEW_BAR_FRAC` | 0.6 | player.js:275 |
| `MINI_WAVE_BARS` | 40 | mixer.js:177 |
| `MINI_WAVE_VIEWBOX_H` | 26 | mixer.js:178 |
| `_FOOTER_BARS` | 300 | player.js:204 |
| `STEM_VU_FPS` | 30 | player.js:195 |
| `MAX_ENGINE_DECODED_BYTES` | 1.2e9 | player.js:61 |
| `WAVEFORM_LANE_HEIGHT` | 70 | player.js:196 |
