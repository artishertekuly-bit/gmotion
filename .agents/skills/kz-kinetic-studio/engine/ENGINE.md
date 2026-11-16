---
name: kz-kinetic-studio
description: Core video assembly and kinetic typography engine behind kz-kinetic-studio. Keeps the speaker's live 9:16 footage as the continuous spine (100%), overlays 2-3 compact WebM VP9-alpha Hero Hooks (never black split/full screens), draws 80% multi-font kinetic ASS subtitles in the locked chest/neck safe zone (y = 1280..1520) with hard inter-word spacing, 1.35x inline keyword bursts, and outputs a clean 15-25 MB H.264 MP4 (--crf 20 --cleanup) with zero temp bloat.
---

# `kz-kinetic-studio` Engine

Core renderer & EDL validation engine for Kazakh 9:16 vertical retention reels.

## Architecture Laws

1. **80% Kinetic Subtitles + 20% (2–3) Composite Hero Hooks:**
   - No opaque black (`#000000` / `#05070a`) `split` or `full` screens — speaker video stays live 100% of the runtime.
   - Optional `blur_bg: true` on a Hero Hook overlay applies smooth gaussian bokeh blur/dim to the live speaker frame behind the floating frosted/paper card without ever cutting away to black.
   - Total Hero Hook overlays per reel: strictly **`2 <= total_hooks <= 3`**.
2. **Locked Subtitle Safe Zone (`y = 1280..1520`):**
   - Subtitles never jump to mid-screen (`y=960`) or behind the head. Default baseline anchor is `y = 1380`.
   - `textass.py` enforces `\h` hard non-breaking spaces across font switches (`word_fonts`) and `1.35x` inline word scales (`word_scales`), and reveals typewriter beats word-by-word rather than chopping mid-word syllables.
3. **Zero 1 GB Disk Bloat:**
   - `render_hooks_chromium.py` pipes Chromium RGBA screenshots directly via `image2pipe` into compact VP9 alpha `.webm` files (compact card dimensions `880x420` or `920x520` — zero full-frame PNG/qtrle `.mov` dumps).
   - `presenter_mattes.py --faces-only` produces fast MediaPipe multi-speaker `analysis/faces.jsonl` without heavy `rembg` `.mov` mattes unless an EDL explicitly requests matte cutouts.
   - `render_reel.py` defaults to `--crf 20` (`15–25 MB` output) and automatically cleans temporary `work/`/`reel_*` caches and intermediate renders (`--cleanup`).

## Core Scripts

- `scripts/reel_plan.py` — Builds normalized timeline, multi-speaker MAR focus keys (`0.35s whip_pan` vs scene-cut jump), camera curves, and subtitle placement (`y=1280..1520`).
- `scripts/textass.py` — ASS frame renderer with `word_fonts`, `word_scales`, uncollapsible `\h\fsp0` spaces, word-by-word reveal, pills, and glow/shadow passes.
- `scripts/render_reel.py` — Multi-process compositor supporting VP9 alpha `.webm` floating cards, live `blur_bg`, graffiti PNG accents (`underline_yellow`, `badge_fakt`), `--crf 20`, and `shutil.rmtree` cleanup.
- `scripts/validate_edl.py` — Strict compiler gate (`2 <= hooks <= 3`, zero black/placeholder/orphan errors, camera motion on every beat, `2 <= animations <= 4`).
- `scripts/vision_py.py` & `scripts/presenter_mattes.py` — Cross-platform MediaPipe multi-face MAR tracker (`--faces-only` fast mode or full guided-filter mattes when requested).
