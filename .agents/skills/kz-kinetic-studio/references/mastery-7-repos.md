# 7-Repo Motion Graphics & High-Edit Mastery Reference (`talking-head-kz`)

Distilled concrete math, shaders, prompts, design tokens, and architectural patterns extracted directly from the 7 reference repositories into `talking-head-kz` for Context-First 60/40 Kazakh Reels (1080×1920).

---

## 1. `lemo-opuscar` — Film Styles, Procedural Curves, WebGL2 CRT & Three.js Post-Processing

### Core Procedural Math (`core/lib.js`)
- **Fritsch–Carlson Monotone Cubic Spline (`monotone(pts, t)`)**: Smooth keyframe interpolation that *never* overshoots flat holds between `[t_i, v_i]` pairs (`d[i] = 0` on sign change, harmonic mean `w1/m0 + w2/m1` otherwise). Use for camera dolly, exposure ramps, and typography holds.
- **Analytic Damped Spring (`spring(t, k=180, z=0.6)`)**:
  $$\omega = \sqrt{k}, \quad \omega_d = \omega\sqrt{1 - z^2}$$
  Underdamped ($z < 1$): $1 - e^{-z\omega t}\left(\cos(\omega_d t) + \frac{z\omega}{\omega_d}\sin(\omega_d t)\right)$.
  Critically/overdamped ($z \ge 1$): $1 - e^{-\omega t}(1 + \omega t)$.
- **Attack–Hold–Release Envelope (`env(t, t0, t1, a=0.25, r=0.35)`)**: Clean smoothstep gate for transient overlays and cards.
- **Deterministic PRNG & Value Noise (`mulberry(seed)`, `vnoise(x, y, z, seed)`)**: Bitwise hash `(n ^ (n >> 16))` ensures identical noise across parallel cloud Chromium workers (`seek(t)` purity).

### WebGL2 CRT / VHS Post Pass (`core/post/crt.js`)
For `whisper_terminal`, retro tech hooks, or `ascii-crt` inserts:
1. Horizontal chromatic channel offset (`chroma` bleed on R/B UV channels).
2. Phosphor bloom / halation (`bright` threshold mix).
3. Scanline modulation: `0.5 + 0.5 * cos(uv.y * uResolution.y * PI)` mixed cleanly (`0.12–0.22` depth, never washed out).
4. Animated film grain seeded by frame time (`hash12(gl_FragCoord.xy + t)`).

### Three.js Physical DoF + AO + Bloom Pipeline (`core/three/post.js`)
Order of passes in `EffectComposer`:
1. `RenderPass(scene, camera)`
2. `GTAOPass` (subtle contact ambient occlusion on 3D cards/ui planes)
3. Depth-of-Field CoC spiral gather shader (`abs(depth - focus) / depth`, golden-angle sample ring for creamy bokeh behind speaker/hero 3D objects)
4. `UnrealBloomPass(res, strength=0.35, radius=0.4, threshold=0.88)` (restrained glow only on emissive accents)
5. Vignette + ACES Filmic output pass.

### Styleboard Design Discipline (`styleboard/DESIGN.md`, 99 styles in `catalog.json`)
- **Color**: 1 dominant dark ground (`#0B0B0B` / `#0E0C0E` / `#161216`) + 1 crisp neutral paper (`#EDE6DE` / `#FFFFFF`) + **at most 1 accent per beat** (`#ED3B22`, `#FFD600`, or `#00E676`).
- **Key styles matched to Talking-Head KZ hooks**:
  - `dark-keynote`: Obsidian ground, razor-sharp bold statement center-punch + subtle rim highlight.
  - `swiss-motion`: Asymmetric grid hairlines (`1px` ticks), tabular counters, rigid typographic hierarchy.
  - `ascii-crt`: Monospace monospace reveal (`whisper_terminal`), amber/phosphor green accents, scanline texture.
  - `text-flash-cuts`: Rapid 3–5 frame cadence keyword hits (`kinetic_stack`) on downbeats.
  - `hologram-hud`: Precision corner reticles (`crosshair`), HUD bracket counters around speaker insights.
  - `caption-news`: Documentary lower-third badge (`rossark_pill`) + citation proof card.

---

## 2. `rossark-motion-skill` — High-Edit Reels & Physical UI Choreography

### High-Edit Motion Rules (`SKILL.md`, `MOTION.md`)
- **Asymmetric Timing**: Exits are **faster** than entrances (~60–75% of enter duration).
- **Never Scale From `0`**: UI cards, pills, and kinetic blocks enter from `scale: 0.90–0.97` with `opacity` + `translateY` + subtle `blur -> 0`. Only micro-highlights (`word_pop` / `rossark_pill`) pop with overshoot (`118%–126% -> 100%`).
- **Volume Preservation (`squash & stretch`)**: When stretching on `y` during fast vertical whips/bounces, set `sx = 1.0 / (sy ** 0.6)` so typography & cards retain mass.
- **Easing Pairings**:
  - Sharp UI Snap (`EASE_OUT`): `cubic-bezier(0.23, 1.0, 0.32, 1.0)`
  - Camera / Card Sweep (`EASE_IN_OUT`): `cubic-bezier(0.77, 0.0, 0.175, 1.0)`
- **Procedural Helpers (`motion.ts`)**: `flow()` (piecewise monotone), `track()`, `seg(t, a, b)` normalized phase `0..1`, `wave(t, freq, amp)`, `bell(u)` (`sin(pi * u)^p` symmetric pulse).
- **Pacing Rule**: Something visual shifts every **1.5–3.0 s** — zoom step (`wide <-> tight`), UI pill popup (`rossark_pill` + `pop.wav`), or 40% B-roll / card / 3D overlay.

---

## 3. `reanimate` — State Morphing, Analytic Springs & Virtual-Clock Determinism

### Closed-Form Spring Sizing (`references/implementation.md`)
- Damping ratio:
  $$\zeta = \frac{\text{damping}}{2\sqrt{\text{stiffness}\cdot\text{mass}}}$$
- Target overshoot heuristic:
  $$\text{overshoot} \approx \exp\!\left(\frac{-\pi\zeta}{\sqrt{1-\zeta^2}}\right)$$
  ($\zeta \approx 0.59 \rightarrow 10\%$ overshoot; $\zeta \approx 0.69 \rightarrow 5\%$ overshoot; $\zeta \approx 0.46 \rightarrow 20\%$ overshoot).
- Approx settle time: $t_{\text{settle}} \approx \frac{4}{\zeta\sqrt{\text{stiffness}/\text{mass}}}$.

### Morphing & Perceptual Color Blending (`motion.js`)
- **SVG Path String Morph (`mixString(a, b, u)`)**: Tokenizes numeric sequences inside SVG `d="..."` or CSS transform strings and interpolates pairs element-wise — zero DOM thrash.
- **Perceptual Gamma-Squared Color Mixing (`mixColor(c1, c2, u)`)**: Blend in squared RGB ($c^2$) then take $\sqrt{\cdot}$ so `#ED3B22 -> #00E676` never dips into muddy brown midpoints!
- **OKLab Linear Shader Blending (`shaders.js`)**: `labToLinear()` matrix converts perceptual OKLab trail colors to linear GPU RGB cleanly.
- **Deterministic Headless Rendering (`references/webgl.md`)**:
  - Single-file HTML with `window.seek(t)` computing *100% of DOM/Canvas/WebGL state from `t`*.
  - No `setTimeout`/`setInterval`/unseeded `Math.random()`. Wait for `await document.fonts.ready` before frame 0!
  - In Chromium/SwiftShader cloud renders, enforce virtual clock stepping (`dt = 1/fps`) so 60fps capture has 0% frame jitter.

---

## 4. `pixelfx` — Deterministic Particles, Ordered Dither & Shader Layers

### Core Primitives (`src/core/math.js`, `src/core/particles.js`, `src/core/painter.js`)
- **Closed-Form Ballistics (`fly`, `flyV` with drag $k$ & gravity $g$)**:
  - Position & velocity integrated analytically in time $t$ so particles/sparks evaluate deterministically at any random-access seek `t` without stepping physics history from $t=0$!
- **Seamless Looping Noise (`tileNoise`, `tileFbm`, `loopNoise`)**: Toroidal 4D/repeating lattice sampling so embers, rain, or dust loops seamlessly with zero jump.
- **Dual-Buffer Painter (`color` + `light`)**:
  - 4×4 Bayer ordered dithering for crisp retro pixel dissolves (`whisper_terminal` / `ascii-crt` transitions).
  - Separate additive glow buffer (`light`) composited over the base frame so sparks/lightning stay punchy without muddy alpha fringes.
- **Signature Recipe Patterns**:
  - `lightning/lightning-strike.js`: Stepped zigzag leader + branching cracks + 3-pulse flicker array `[1, 0.72, 0.3, 0.95, 0.5, 0.8, 0.22]` + short white peak frame.
  - `weather/rain.js`: 4 depth planes (far thin/dim streaks -> near bright streaks + impact splashes + wind gust noise field).
  - `explosions/big-explosion.js`: 3-beat staggered bursts (`t = 0, 0.13, 0.25`) + heat-cooled color ramp (`white -> gold -> ember -> charcoal smoke`).

---

## 5. `opus-video-prompts` & `awesome-opus5-5-videos` — Prompt Engineering & Viral Structure

### Production Prompt Architecture (`prompts/10`, `15`, `16`, `18`)
Every contextual HTML/Three.js hook prompt uses 5 strict blocks:
1. `<inputs>`: Beat topic, spoken Kazakh quote, exact duration (`dur`), dominant accent (`#FFD600` / `#00E676` / `#ED3B22`), canvas `1080x1920`.
2. `<direction>`: Visual metaphor (1 clear idea per shot), typography lock (`./kzfonts/` or Cyrillic Google Font), **Banned List** (no generic purple gradients, no unmotivated lens flares, no text collisions in face band `y 520..1040`).
3. `<structure>`: Exact timecoded beats aligned to spoken words & audio peaks.
4. `<build>`: Pure function `window.seek(t)` (zero CSS transitions/timers), transparent background (`alpha: true`) when rendered as overlay over `presenter_mattes.py`, or opaque/halftone background when rendered as 3-layer backplate behind the speaker cutout.
5. `<gotchas>`:
   - Never apply `will-change: transform` on scaled containers (causes blurry bitmap rasterization in Chromium).
   - Never put `opacity`/`filter` directly on `preserve-3d` ancestors (flattens 3D planes); wrap and fade outer container instead.
   - Always check `1080x1920` safe zones (`y: 300..1500` content, face kept clear `y: 520..1040` unless `behind_speaker` matte layer is active).

### Talking-Head B-Roll Synthesis (`10-talking-head-to-lineart.md`, `15-ui-morph-loop.md`, `16-high-end-product-video.md`)
- Match spoken concepts immediately: speaker stays crisp in foreground or circular PiP / 60-40 bottom split while upper/background layer morphs dynamically (`button -> chart -> 3D prism -> terminal insight`).
- Peak-aligned SFX: Every UI state change / morph snap places its audio transient peak (`argmax(|x|)`) on the exact video frame of visual impact.

---

## 6. `three.js` — 3D Camera, Particle Clouds & Depth Compositing (`src/` + `examples/jsm/`)

- **Vertical 9:16 Camera (`PerspectiveCamera`)**:
  - `fov = 38–45°` (less wide-angle distortion on 9:16 portrait), `aspect = 1080 / 1920`, `near = 0.1`, `far = 200`.
  - Smooth dolly/orbit driven purely by `monotone()` / `spring(t)`: subtle `z` push-in + `2–4°` parallax sway so 3D props feel anchored behind the speaker matte.
- **High-Impact Data / Concept Particles (`Points` + `BufferGeometry` + `ShaderMaterial`)**:
  - Pack `position`, `aTarget`, `aSeed`, `aSize` attributes once; morph smoothly `mix(position, aTarget, smoothstep(...))` in vertex shader for instant point-cloud transitions (`0ms` CPU frame rebuild overhead).
- **Alpha Overlays (`WebGLRenderer({ alpha: true, antialias: true, preserveDrawingBuffer: true })`)**:
  - Set `renderer.setClearColor(0x000000, 0)` to export clean premultiplied/straight alpha RGBA overlays for 3-layer compositing behind (`matte_body`) or in front of the speaker in `render_reel.py`!
- **Cloud Compatibility (Ubuntu + SwiftShader)**:
  - Launch Headless Chromium with `--use-angle=swiftshader --enable-webgl --ignore-gpu-blocklist`. Keep post-processing lightweight (`BokehShader` or single-pass bloom) so 60fps frame capture finishes fast inside GitHub Actions without OOM.
