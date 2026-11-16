# Planning the edit - from a talk to beats

The scripts handle the mechanics. What makes the reel work is the plan: which words become big
type, which sentences get footage, where the speaker's face is the best picture. Plan on the
program timeline (`analysis/program_words.json`), after the pauses are cut.

## 1. Read the talk as a story

Mark four parts:
- **Hook** (first 2-6 s): the promise or the provocation. It decides whether people keep watching.
- **Setup**: who/what/where, the rules of the situation.
- **Escalation**: the surprising turns - each turn deserves its own visual idea.
- **Payoff + call to action** (last 3-6 s): the conclusion and the ask.

## 2. Autonomous Expertise: Layout Quotas, Metaphor Extraction & 2–4 Layer Stacks

### A. Layout Quota Rule (Mandatory Balance)
Single-mode `overlay` / `behind_speaker` edits are **prohibited**. Balance beat screen time across:
- **`split` (50/50 or 45/55):** `30%–35%` of reel (minimum `2` inserts). Top (`y=0..920`) shows clean bespoke story visual / custom HTML animation; bottom (`y=920..1920`) frames the active speaker.
- **`full` (100% Full-Screen Visual Scene / B-Roll):** `25%–30%` (minimum `2` inserts). Speaker yields to full-bleed motion graphics or footage over voice.
- **`cards` / `cutout` / `flood`:** `20%–25%`. Speaker cut out or minimized so focus lands on interactive comparative cards.
- **`behind_speaker`:** `<= 15%` max (`> 20%` fails compiler validation!). **NEVER** put charts, Bento grids, or small multi-line widgets behind speaker (head occludes the center). Only `1–2` word giant headlines (`>= 160px`, top clear zone `y=120..320` or oversized behind-head typography) are allowed.

### B. Transcript Metaphor Extraction Algorithm (Zero-Placeholder Law)
Before writing any EDL insert or running `storyboard.py`, read `analysis/program_words.json` word by word and convert speech into concrete visual metaphors — **never** abstract placeholder widgets (`88%`, `НЕГІЗГІ КӨРСЕТКІШ`, `TODO`, `example`):
1. **Extract Tokens per Beat:** Identify exact spoken nouns (`телефон`, `ақша`, `доллар`, `үй`), numeric facts (`160 млн`, `3x`, `%`), contrasting turns (`бірақ`, `ал`, `қарсы`), and physical verbs (`хабарласу`, `өсу`, `салыстыру`).
2. **Bind Scene Metaphor (`custom_html_scene` / `EDL_PAYLOAD`):**
   - *Currency / Numbers / Growth* → animated financial chart / counter bento (`from`, `to`, `suffix`, `kpis`, real labels).
   - *Phone Call / Message / Social* → bespoke UI call card or decrypted terminal message with exact spoken words.
   - *Contrast / Choice / Dilemma* → `split` or dual `State A -> State B` comparison stage (`left_label`, `right_label`).
   - *Process / Rule / Breakdown* → isometric system flow or checklist / graffiti callout with exact spoken steps.
3. **Verify Compound Density (`2..4` animations):** Every active beat combines: `[1. camera_motion] + [2. story scene/insert] + [3. accent graffiti/3D/frazix] + [4. multi-font caption + SFX]`.

## 2.1. Split into beats

A beat is one thought, usually 1.5-4 s, ending at a natural pause or a full stop. For every beat
decide one primary visual:

| the words are about... | show |
|---|---|
| speaker emotion / oversized punch word (`<=15%`) | presenter + `behind_speaker` (`>=160px`, `y=120..320`) |
| a concrete thing, place, process, big metaphor (`25–30%`) | `full` bespoke HTML story scene or B-roll (`100%`) |
| comparison, metric reaction, dual focus (`30–35%`) | `split` (bespoke top visual `0..920`, presenter bottom) |
| numbers, multi-item facts, visual focus shift (`20–25%`) | `cards` / `cutout` / `flood` / `bar` / `number` |
| list / contrasting words | `vsplit` / `band` / `converge` |

Alternate: never two identical visual presets or caption formats back to back (`validate_edl.py` enforces this).

## 3. Choose the words

- **Big word (Anton)**: the single most loaded word of the beat - a verb, a number, a twist
  ("LYING", "15", "CHAOS", "LIED", "DRIFT"). One per beat, rarely two.
- **Serif accent (Didot Bold)**: the softer, ironic or elegant half ("I told you", "same town",
  "brutal", "copying"). Pairs well with an Anton word: serif above or below, both in the centre stack.
- **Subtitles (`sub`, words as spoken)**: the connective tissue between big words - short chunks
  of 2-4 words, 80-100 px, in the centre stack just under the big word (or alone where the big word
  would be). Not every sentence needs them; when a big word already says it, skip the subtitle.
- **Lead-in labels (`sub`, pop)**: a few words just above the big word ("you use", "the exact",
  "Emergence calls it").

Text should be quoted from the speech, not paraphrased. The viewer reads what they hear.

## 4. Pick footage per beat

Write the footage idea in one line: subject, action, mood, colour or B&W. Prefer concrete,
specific images that a viewer recognises instantly, with motion inside the shot. Then source it
(`broll-sourcing.md`). If nothing fits, stay on the presenter with a big word - that is better
than a generic clip.

## 5. Presenter framing plan

`zoom` in the EDL: a list of `[t0, t1, "wide"|"tight"]`. Switch at cuts (hides the jump) and on
emphasis. Hook and CTA usually tight. If you leave `zoom` out, the planner alternates at every cut.

## 6. Worked example (first 25 s of a real reel about an AI experiment)

| t (s) | words | on screen | text (font size, y) |
|---|---|---|---|
| 0.00-0.84 | "What if I told you" | presenter tight | `WHAT IF` (Anton 200, y 1122) + `I told you` (serif 150, y 1300) |
| 0.84-1.86 | "the safest AI" | `logo_flash`: 4 model logos on black/red, silhouette flash | `the safest` (Didot 120, y 1028) + `AI` (Anton 200, y 1203) |
| 1.86-3.16 | "you use every day" | `full`, colour shot: a phone in a shirt pocket | `you use` (label 100, y 847) + `EVERY DAY` (Anton 170, y 977) |
| 3.16-6.10 | "is actually lying to you?" | `frame` on red, split layout: three machine-eye close-ups, match cut | `LYING` (Anton 170, y 870) + `to you` (serif 150, on the seam) |
| 6.10-9.60 | "researchers took the four biggest models..." | `cards` (4 model cards, x10 agents) in split | subtitle on the seam (100, y ~960) |
| 9.60-12.32 | "...a 15-day survival test" | `full` in split: two clips stacked | `15` (Anton 224 red, y 843) + `DAY SURVIVAL TEST` (label 70, y 1010) |
| 12.32-14.70 | "things get weird very fast" | `full`: coloured characters on B&W | `WEIRD` (Anton 200 red, y 960) + `very fast.` (subtitle 100, y 1095) |
| 14.70-16.72 | "the exact same town" | `full`, colour | `the exact` (label 100) + `same town` (serif 150) |
| 16.72-19.20 | "same jobs and one brutal choice" | `full` | `brutal` (serif 150, y 828) + `CHOICE` (Anton 200 red, y 1008) |
| 19.20-20.74 | "work together to stay alive" | `band` in split | `WORK` (Anton 163, y 805) + `TOGETHER` (Anton 120 red, y 1063) |
| 20.74-23.36 | "or break the law to survive on your own" | `full` in split, colour street riot | `or` + `BREAK THE LAW` (Anton 109 red, on the seam) |

Ending of the same reel: presenter wide/tight, `If you want\nto watch` (label, two lines) +
`the full experiment\nyourself,` (serif, two lines) under the neck, then `COMMENT\n'TOWN'` (Anton
140 white, two lines) - CTA always in front of the presenter, never over B-roll.

## 7. Show the plan

Give the user the beat table (time, words, visual, text, footage idea) and wait for a go before
sourcing or generating footage. Adjust freely at this stage.
