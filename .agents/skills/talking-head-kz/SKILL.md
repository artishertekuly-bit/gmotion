---
name: talking-head-kz
description: Turn a talking-head recording in Kazakh (or Russian) into a finished vertical 9:16 Reel / TikTok / Short in the "clean minimalist retention edit" style - tightened pauses, single-word pill captions, a big red key word with an italic serif accent, full-screen colour cards that grow out of the captions, a counter, punch-in zooms, soft synthesised SFX, voice at -14 LUFS, plus the "Кейін / Дейін" side-by-side packaging. Works storyboard-first with a scored self-check and a review of the decoded file. Rendered by code (Python + ffmpeg/libass) on this Windows PC with fonts that contain every Kazakh letter. Use it whenever someone wants to edit, subtitle or "make a reel" from a video of a person speaking to camera - "talking head", "сөйлеп тұрған видео", "камераға сөйлеген видео", "говорящая голова", "рилс монтаж", "субтитр қой", "қазақша субтитр", "хук", "дейін/кейін", "в стиле cyl.creations" - even if they never say EDL or render. The base engine is the talking-head-reels skill; this one is its Kazakh + Windows version and should be preferred on this machine.
---

# Talking-head reels in Kazakh (Mastery 60/40 High-Edit + Cloud Render)

Turn a Kazakh/Russian talking-head clip or full YouTube podcast into a finished High-Edit vertical 9:16 Reel (1080×1920): **60% dynamic retention subtitles** across 5 distinct modes + **40% contextual 3D/Canvas/UI motion hooks & overlays** with 3-layer depth behind/around the speaker, powered by patterns distilled from 7 reference motion repos (`references/mastery-7-repos.md`) and cloud-rendered in GitHub Actions.

| layer | where | what |
|---|---|---|
| Mastery reference | `references/mastery-7-repos.md` | Distilled curves, shaders, springs, CRT/DoF, Three.js & UI patterns from 7 repos |
| Context extractor | `scripts/fetch_to_context.py` | YouTube transcript + "Most Replayed" heatmap -> Context Window (no HD video download) |
| Engine | `engine/` | Pause cutting, mastering, cross-platform `vision_py.py` (`mediapipe`+`rembg`), EDL compositor |
| Kazakh + 60/40 layer | `scripts/`, `references/kz-format.md`, `assets/hooks/` | 5-mode 60% captions, HTML/Three.js hook renderer, `./kzfonts/` + `./soundeffects/` SFX |
| Cloud render | `.github/workflows/render-master-reel.yml` | Ubuntu 16GB CI: `yt-dlp --download-sections`, `rembg`, Chromium 60fps, `render_reel.py` |

**Read `references/kz-format.md` and `references/mastery-7-repos.md` before planning any edit.**

Talk to the person in Kazakh, in plain words. Project files stay in English; everything on screen is in the spoken language.

## Core Architecture: 60 / 40 High-Edit + Context-First

1. **Context-First YouTube Podcast Intake (`scripts/fetch_to_context.py`)**:
   - Never generate blindly and never download full multi-hour videos locally.
   - Fetch subtitles (`kk,ru,en`) + YouTube Heatmap (`Most Replayed`) into `context_prompt.md` + `context_packet.json`.
   - Read the transcript in Context Window, pick the sharpest 45–60 s `[start, end]` viral slice, and write `podcast_source.json`.
2. **60% — Dynamic Retention Subtitles (`caption_words.py --mode 60-40` + `textass.py`)**:
   Rotate dynamically by semantics & cadence instead of flat single-style subtitles:
   - **`word_pop` (30%)**: 2–3 word chunks, active spoken word springs (`122% -> 100%`) and lights up `#FFD600` or `#00E676`.
   - **`rossark_pill` (10%)**: Key nouns/terms spawn a contrast UI pill + `sfx: "pop"` (`./soundeffects/pop.wav`).
   - **`kinetic_stack` (10%)**: 3-line bold Anton/`./kzfonts/` stack during hooks and vocal peaks.
   - **`reanimate_counter` (5%)**: Automatic `0 -> N` animated numeric counters (`counter: [a0, a1, v0, v1, suf]`) when stats/money/% appear.
   - **`whisper_terminal` (5%)**: Monospace `mono` (`terminal` anim) typewriter reveal on pauses/intrigues.
3. **40% — Contextual Hook & 3-Layer Depth Overlays (`assets/hooks/`, `render_hooks_chromium.py`)**:
   - Write bespoke deterministic HTML/Canvas/SVG/Three.js `window.seek(t)` hooks inspired by `references/mastery-7-repos.md` (no ready-made stock hook library needed).
   - 3-Layer Depth compositing in `render_reel.py`: Background (halftone/dimmed studio) → Middle (`behind_speaker` HTML/3D overlay + `behind` big typography) → Foreground (`presenter_mattes.py` speaker cutout via `mediapipe`+`rembg` + `front` 60% subtitles).

## What is different from the base engine

- **Fonts (`./kzfonts/` + Windows + Ubuntu).** `textass.kz_font_sources()` auto-discovers `./kzfonts/`, Windows Kazakh fonts (`SegoeUIBlack`, `Consolas-Bold`, `TimesNewRomanPS-BoldItalicMT`), and Ubuntu Cloud fonts (`DejaVuSans-Bold`, `DejaVuSansMono-Bold`, `NotoSans`). Always check custom fonts with `scripts/font_check.py`.
- **SFX (`./soundeffects/` + synthesized fallback).** `scripts/sfx_from_edl.py` auto-checks `./soundeffects/` for matching stems (`pop`, `whoosh`, etc.) before falling back to numpy/scipy synthesis, aligning peaks cleanly to frame hits.
- **Cross-Platform Mattes (`vision_py.py`).** Uses `mediapipe` + `rembg` ONNX on Linux/Windows instead of macOS-only Swift (`tool_cmd` in `vision_tools.py` preserves macOS Swift fallback on Darwin).
- **Local Weak-PC Protection.** `storyboard.py` defaults to `--plan-only` on Windows; `render_reel.py` (full MP4) and `render_hooks_chromium.py` block accidental local runs on `<12 GB` RAM Windows laptops.

## This PC (8 GB RAM Laptop Safety Rule & Auto Cloud Render)

- **Locally ONLY run:** `fetch_to_context.py`, EDL/ASS/`storyboard.py --plan-only`, `caption_words.py`, `validate_edl.py`, `kz_lint.py`, `font_check.py`, `sfx_from_edl.py --dry`, and writing HTML `window.seek(t)` hook code.
- **NEVER run heavy video rendering locally** (`render_reel.py` full encode, Chromium frame capture, `rembg` matting).
- **Mandatory Auto-Push to Cloud Render (No Confirmation Pause):** Because the GitHub CLI connector (`gh`, scopes `repo` + `workflow`) is already authorized, **NEVER stop to ask the user for permission before committing, pushing to `git`, or launching cloud rendering**. As soon as `validate_edl.py` (0 errors), `kz_lint.py` (85+, 0 fail), and `storyboard.py --plan-only` pass:
  1. Immediately stage project files (`kz_edl.json`, `motion_hooks/*.html`, `podcast_source.json`, `analysis/program_words.json`, `analysis/cuts.json`), run `git commit` + `git push`, and trigger/watch `.github/workflows/render-master-reel.yml` (`gh workflow run render-master-reel.yml -f project_dir=...` or automatic push trigger).
  2. GitHub Actions (`ubuntu-latest` 16 GB RAM) downloads ONLY `--download-sections *START-END`, generates mattes, captures 60fps Chromium overlays, mixes audio, renders the Master + Phone MP4, and uploads artifacts for download (`gh run download`).
- Run every local Python script as `python -X utf8 ...` (cp1251 console crashes on Kazakh print output without `-X utf8`).
- `python -X utf8 scripts/check_setup_kz.py` verifies environment setup locally.

## Consent gates (stop and ask, with the price)

1. **Scribe transcription** - paid by audio length. One request per recording; never repeat it
   (`--from-json analysis/scribe_raw.json` rebuilds for free).
2. **Generated footage or pictures** (Flow, Higgsfield) - per `C:\Users\Artur\Motion\AGENTS.md`.
3. **Any download** (fonts, logos, stock clips, music) - say the file, the source and the size.

## Step 0 - intake

Ask only for what is missing, in one short message:
1. the recording (path) - vertical 1080x1920 or 4K horizontal, the speaker roughly centred, face in the upper half;
2. the script, if there is one (it catches mis-heard words);
3. the call to action for the end (for example: пікірге «ХУК» деп жаз);
4. one colour to take from the footage (clothes, wall, microphone) - or pick it yourself from a frame;
5. whether a "Кейін / Дейін" version is wanted as well, and whether they have music of their own.

Project folder: `C:\Users\Artur\Motion\work\th\<name>_reel\` (finals are copied to `C:\Users\Artur\Motion\final\`).

## Step 1 - prepare and analyse

`E` = `engine/scripts`, `K` = `scripts` (both inside this skill's folder), `DIR` = the project folder.

```bash
python -X utf8 E/prepare_project.py VIDEO.mp4 --project DIR
python -X utf8 K/transcribe_scribe.py DIR            # PAID - only after consent
python -X utf8 E/cut_pauses.py DIR [--remove 2.40-2.72 ...]
python -X utf8 E/master_audio.py DIR
```

Read the transcript against the script. Fix mis-heard words in `analysis/asr.json` (keep the times), remove false
starts with `--remove`, re-run `cut_pauses.py`, and report how much was cut ("41,2 с → 33,8 с"). Everything later
uses program time (`analysis/program_words.json`).

## Step 2 - plan, variants, draft EDL

1. Decide the ending first: what should the viewer do after the last word (comment a word, save, follow)? The
   reel is planned backwards from that line. Then split the talk into beats (`kz-format.md`, section 8) and write
   them into the EDL as `"beats"`.
2. Write the EDL with **Mastery V2** mechanics (avoid single-effect flat frames):
   - **12 Hook Presets + Anti-Repeat** (`scripts/hook_registry.py`): choose distinct context-matched `preset` inserts across `frazix_dossier_hook`, `graffiti_fact_explosion`, `threejs_3d_floating_totem`, `lemo_ink_wash_history`, `lemo_isometric_system`, `reanimate_state_morph`, `pixelfx_energy_shader`, `opus_bento_grid_stats`, `halftone_cutout_backsplash`, `graffiti_circle_callout`, `split_60_40_simulation`, `retro_terminal_decrypt`; never repeat consecutive presets.
   - **Compound Keyframe Density `[2..4]`**: every active beat runs 2–4 layered animations across Camera (`zoom_push` / `smooth_pan` / `micro_shake`), Depth (`matte_backsplash` / `halftone_drift`), Graphic (`spring(k=220, d=18)`), and Type+SFX (`storyboard.py --enrich-edl` & `validate_edl.py` auto-balance `[2..4]`).
   - **4-Role Font Matrix + Mixed-Font Sentences**: map `impact`, `clean`, `editorial`, `tech` (verified via `font_check.py --roles`) and mix contrasting fonts inline via `"word_fonts": [...]`.
   - **8 Geometric Subtitle Formats**: generate dynamic subtitles rotating all 8 formats:
   ```bash
   python -X utf8 K/caption_words.py DIR --from 0.45 --to 51.65 --mode v2 --merge DIR/edl.json
   ```
3. Compare V2 variants on any beat cleanly (using `--plan-only` on low-RAM laptops):
   ```bash
   python -X utf8 K/variants.py DIR/edl.json --beat 1 --auto-v2 --plan-only --out-dir DIR/qa/variants_v2
   ```
4. Check the plan until it is clean:
   ```bash
   python -X utf8 E/validate_edl.py DIR/edl.json      # structure: fix every error
   python -X utf8 K/kz_lint.py DIR/edl.json           # format: 85+ and no FAIL before anything is shown
   ```
   A warning kept on purpose is fine - name it in the report.

## Step 3 - lightweight storyboard + automatic Cloud Render push (no stop)

```bash
python -X utf8 K/storyboard.py DIR/edl.json --out-dir DIR/qa/storyboard_v1
```

Verify `storyboard.md` / `storyboard.png` against `kz-format.md` (section 13) yourself. Do **NOT** stop and wait for user approval to push or render: proceed straight to `git add` → `git commit` → `git push` so `.github/workflows/render-master-reel.yml` starts rendering on GitHub Actions immediately (the user's GitHub connector grants standing permission). Track the workflow run with `gh run list` / `gh run watch` and download the finished MP4 artifacts when done.

## Step 4 - sound, render, review (runs in GitHub Actions Ubuntu CI)

```bash
python -X utf8 K/sfx_from_edl.py DIR/edl.json [--music FILE]     # then set "audio": "audio/program_sfx.wav" in the EDL
python -X utf8 E/render_reel.py DIR/edl.json --out DIR/render/NAME_v1.mp4 --workers 2      # in the background
python -X utf8 K/review_render.py DIR/render/NAME_v1.mp4 --edl DIR/edl.json --out-dir DIR/qa/review_v1
```

`review_render.py` decodes the finished file: frame count, every frame-to-frame jump (planned or not), frozen
stretches, loudness, and it saves `first.png`, `last.png` and `joins.png` - look at all three. Fix what it finds
(time → what is seen → cause → fix → re-check) and render again before the person sees it.

The master is heavy (near-lossless, with film grain). Always make the copy people actually post, and copy both to
`C:\Users\Artur\Motion\final\`:

```bash
ffmpeg -v error -y -i DIR/render/NAME_v1.mp4 -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart DIR/render/NAME_v1_phone.mp4
```

Report the numbers (size, fps, length, LUFS, lint score, worst SFX offset) and the statuses. Motion and sound are
not checked by Codex: ask the person to watch once and listen once. `--gain -4` makes every cue quieter.

## Step 5 - packaging (optional)

```bash
python -X utf8 K/compare_pack.py --main render/NAME_v1.mp4 --other render/NAME_raw.mp4 --out render/NAME_pack_v1.mp4 --brand "@name"
```

For the "before", render a copy of the EDL with empty `"inserts"` and `"text"` (same cuts, so both sides stay in sync).

## Step 6 - revisions

Number the notes, change nothing until the person says go, apply all of them in one pass, copy `edl.json` to
`edl_vN.json` first, render to a new `_vN.mp4`. Never overwrite a file the person has seen. A note that changes
beats, their order or a transition goes back to Step 3 (new storyboard, new yes); timing and styling notes do not.
A note that implies a rule ("субтитр үлкенірек") applies everywhere, not only in the screenshot.

## Files

| path | what |
|---|---|
| `references/kz-format.md` | the format: look, motion rules, Kazakh rules, EDL recipes, sound, hooks, checklist |
| `references/mastery-7-repos.md` | distilled curves, shaders, springs, 3D camera/particles & UI patterns from 7 repos |
| `scripts/fetch_to_context.py` | extract YouTube podcast transcript + heatmap into AI Context Window |
| `scripts/hook_registry.py` | Mastery V2 catalog: 12 hook presets, anti-repeat router, `[2..4]` compound layer builder |
| `scripts/render_hooks_chromium.py` | cloud 60fps SwiftShader Chromium renderer for all 12 HTML/Canvas/3D overlays (`assets/hooks/*.html`) |
| `assets/hooks/*.html` | 12 deterministic `window.seek(t)` hook templates (`_hook_core.js` spring physics + local PNG assets) |
| `assets/examples/kz_edl.json` | a complete Kazakh example EDL (27 s, lint 100/100, rendered and reviewed) |
| `assets/examples/kz_hook_variants.json` | five hook treatments (A-E) incl. 60/40 depth, `word_pop`, `terminal`, `counter` |
| `scripts/transcribe_scribe.py` | ElevenLabs Scribe -> `analysis/asr.json` (paid) |
| `scripts/caption_words.py` | `--mode v2` / `60-40` (8 geometric subtitle formats + mixed `word_fonts`) & classic Kazakh captions |
| `scripts/variants.py` | 3-5 treatments of one beat (`--auto-v2`, `--plan-only` low-RAM safe) |
| `scripts/kz_lint.py` | scored self-check of the EDL (language, rhythm, composition, motion, platform) |
| `scripts/storyboard.py` | lightweight storyboard (`--plan-only --enrich-edl` for `[2..4]` stacks) & real stills |
| `scripts/sfx_from_edl.py` | synthesised cues under the voice, frame-synced; optional music bed |
| `scripts/review_render.py` | review of the decoded MP4: jumps, frozen stretches, joins, loudness |
| `scripts/compare_pack.py` | "Кейін / Дейін" side-by-side packaging |
| `scripts/font_check.py` | checks Kazakh glyphs + `--roles` 4-role matrix (`impact`/`clean`/`editorial`/`tech`) |
| `scripts/check_setup_kz.py` | setup check for this PC |
| `engine/` | the patched talking-head-reels engine and its documents |

## Ground rules

- Footage: only material the person has rights to, or clips generated for them. The analysed account is a reference
  for structure only - never copy its texts, graphics or videos, and never name it in a reel.
- On-screen text quotes the speech. The one exception is the hook word, which is on the cover frame before it is spoken.
- Every render is a new file. Nothing is called checked that was not.
