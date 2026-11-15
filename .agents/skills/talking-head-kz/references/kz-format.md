# The format - clean minimalist retention edit, in Kazakh

## Contents
1. Where it comes from
2. The grammar of the edit
3. Motion rules
4. Kazakh language rules
5. Type: roles, sizes, widths
6. Placement and the crosshair
7. EDL recipes
8. Beat sheet for a 25-30 s reel
9. Variants: three ways to open
10. Sound
11. Hook and CTA bank
12. Packaging
13. Review checklist and honest statuses

## 1. Where it comes from

Three sources, each with one job:

| source | what was taken |
|---|---|
| the analysed editor account (`C:\Users\Artur\Motion\materials\ref\cyl-creations\ANALYSIS.md`) | the structure: two caption modes, colour cards, cadence, packaging |
| the `saas-animation` skill | how things move and sound: storyboard first, shots that grow out of each other, one anchor point, soft word-by-word text, sound that means something |
| the `vizavi-motion` skill | how the work is run: 3-5 variants per key beat, the first build is a draft, check the decoded file, say honestly what was not checked |

Findings from the account that shape everything below:
- The edit changes something every ~2.5 s (10 visual states in 25 s) and adds a word every 0.3-0.5 s in between.
- 23-30 % of the running time is full-screen graphics (colour cards), the rest is the speaker with type.
- The same 24.7 s edit got 2.0 K views posted alone, 60.9 K as "After vs Before" and 120 K as a price comparison:
  the packaging decided the reach, not the edit.

Take the structure. Never reuse that account's wording, graphics or footage, and never name it in a reel.

## 2. The grammar of the edit

**Two caption modes that alternate** - this is the core of the look:

| mode | when | what is on screen |
|---|---|---|
| pill | connective speech, lists of small words | ONE word at a time, lower case, white on a rounded pill at chest height, swapped on every spoken word |
| stack | the loaded phrase of a beat | 2-3 lines: small lead-in (white) + BIG key word (red or white) and/or an italic serif accent (red) |

Never run the pill for more than ~6 s without a stack or a card; never two stacks in a row with the same layout.

**Full-screen cards** carry the idea the speaker is naming - a question, a contrast, a number:
- a solid colour (red, off-white, near-black, or the one colour sampled from the footage) with a 2-3 line stack;
- 1.4-2.8 s each, 3-5 of them in a 25-30 s reel, the first one inside the first 3-4 s;
- neighbouring cards differ in colour; one red word per screen (on a red card the words are white).

**The speaker** alternates `wide` and `tight` at beat boundaries (hides the jump cuts), tight on the hook and on
emphasis. No framing shorter than 1 s.

**Palette**: white, one red (`#E02B20`; darker `#C4151C` for a full red card), near-black `#161216`, off-white
`#F4F1EC`, plus ONE colour picked from the footage (the reference took dark green from the microphone: `#2F3E2E`).
That sampled colour goes on the pills and on one card. Nothing else.

**Length**: 20-35 s after tightening. One idea per reel.

## 3. Motion rules

These came from the two motion skills; `scripts/kz_lint.py` checks the ones a machine can check.

1. **Frame 0 is the cover.** The hook word is already settled on the very first frame: give it `"t0": -0.4`.
   An entrance animation that starts at 0 leaves the first frame empty - and that frame is the thumbnail.
2. **Text rises in, it does not pop.** The default entrance is `rise`: word by word, from blurred to sharp, with a
   small lift, ~0.075 s between words, fast at first and then slow for longer. It leaves the same way. No bounces, no
   scale pops, no letter-by-letter reveals. `pop` is only for pill captions (they swap in 0.08 s); `build` (letters
   assembling) at most twice in a reel, and never on the first frame.
3. **Something is always moving.** A `rise` line keeps a slow 3 % push while it holds; the speaker has a slow push
   inside every framing. A card must never sit as a still picture: its lines arrive one after another, on the words.
4. **One anchor - the invisible crosshair.** The big word of every speaker beat sits at one height (y ~1235), the big
   word of every card at one height (y ~965). The eye never has to hunt. Lead-ins go above it, tails below.
5. **Shots grow out of each other.** A card that follows pill captions enters with `"trans": "flood"`: the pill of
   the last word swells and fills the frame, first in the pill's colour, then the card's own colour follows inside
   it. A card that follows a stack enters with a camera move (`zoom`, `whip`). A one-word punch card cuts in with an
   invert flash. No cross-dissolves anywhere.
6. **A move never reverses.** Do not zoom in and straight back out on the same subject; do not flip the framing
   faster than once a second.
7. **Fast, then slow for longer.** First drafts are too quick. A stack needs ~0.5 s to arrive and at least 0.6 s
   to be read; a three-line card needs 1.6 s or more.
8. **Polish, in one place only.** `"gradient": true` shades the lower half of a white big word towards cool grey -
   use it on white words over dark footage or a black card, never on a colour card (it vanishes there) and never
   on red.
9. **Every change lands on a word.** `t0` of every insert and every stack is a word start from
   `analysis/program_words.json`; the voice is the clock.

## 4. Kazakh language rules

1. **The verb comes last.** In English the punch word opens the sentence ("NEVER post..."); in Kazakh it closes it
   ("...видео салма"). So for the hook only, the punch word is on screen from frame 0 and the voice arrives at
   it ~2 s later. Everywhere else a word appears when spoken.
   Better still, write hooks that start with the punch: "Тоқта.", "Жоқ.", a number, a question word.
2. **The meaning sits in the ending.** The negation (-ма/-ме, -ба/-бе, -па/-пе, емес, жоқ) is the word to make big
   and red: САЛМА, ІСТЕМЕ, ЕМЕС, ЖОҚ. Do not split a word to colour only its suffix - colour the whole word.
3. **Particles never stand alone.** ма/ме/ба/бе/па/пе, да/де/та/те, ғой, қой, ше, екен, еді, емес, деп, үшін join
   the word before them in one pill ("келдің бе?", "жақсы ғой"), or the word after them when they open a stretch
   ("деп сұрайсың"). `caption_words.py` does this.
4. **Words are long, speech is slower.** Count on ~2 words per second (the English reference reels run at 3.2-3.7).
   One Kazakh word per pill reads well; a pill stays 0.4-0.7 s. A 25 s reel is 45-55 words: write the script to that.
5. **Long key words.** Prefer the short root or a synonym for the big word (ҚАЛАЙ, НЕГЕ, ТОҚТА, ҚАТЕ, ТЕГІН).
   A long word is fine as the serif accent or on a card, where the renderer shrinks it to the frame.
6. **Questions.** The question word (қалай, неге, қашан, кім, не, қанша) is the big word; the verb with "?" is the
   accent line under it.
7. **Capitals with tails.** Қ, Ң, Ғ, Ұ, Ү, Ә are taller or deeper than Latin capitals: keep two-line leading at
   1.2 x size or more and never tuck a line closer than ~115 px under a big word.
8. **Loan words** are written as spoken: видео, контент, алгоритм, клиент, лайк.
9. **Numbers and money**: digits, a space between thousands (1 000 000), the tenge sign after the number (2 000 ₸).
10. **Quote marks**: «...», not "...".
11. **Spelling check.** Scribe confuses і/и, ұ/ү/у, қ/к, ң/н, ә/а. `kz_lint.py` compares every on-screen word with
    the transcript, so fix the transcript first (`analysis/asr.json`, then re-run `cut_pauses.py`) - a wrong letter
    in a 200 px word is the first thing a Kazakh viewer sees.

## 5. Type: roles, sizes, widths

| role (`font`) | font on this PC | used for | size (px) | case | default entrance |
|---|---|---|---|---|---|
| `anton` | Segoe UI Black | the key word of a beat, numbers, the CTA word | 170-240 | CAPITALS | `rise` |
| `serif` | Times New Roman Bold Italic | the softer / ironic half, the accent | 130-160 | lower case | `rise` |
| `sub` | Segoe UI Semibold | pills, lead-in labels, subtitles | pill 76, label 80-96, subtitle 62-70 | lower case | `rise` (pills: `pop`) |
| `didot` | Times New Roman Italic | a rare thin accent | 110-150 | lower case | `rise` |

The role names are the engine's and must stay (`anton` gets the red glow and holds to the end of its shot).

Width guide (measured; the frame allows ~960 px per line, the renderer shrinks anything wider and prints a note):

| font | px per character | fits in one line |
|---|---|---|
| Segoe UI Black, capitals | ~0.70 x size | 6 letters at 220, 7 at 200, 8 at 170, 9 at 150 |
| Times Bold Italic, lower case | ~0.50 x size | 12 letters at 150 |
| Segoe UI Semibold, lower case | ~0.48 x size | 26 characters at 76 |

- Red big words get a soft red glow by default; white big words: `"glow": false`.
- Text over the speaker: `"shadow": true` on labels, accents and subtitles. On cards no shadow is needed.
- On an off-white card use `#161216` for the label and the accent, red for the key word only.

## 6. Placement and the crosshair (1080x1920, x centred at 540)

| context | lead-in | big word (the anchor) | line under |
|---|---|---|---|
| over the speaker ("under the neck", never on the face) | y 1075-1150 | **y 1215-1240** | y 1345-1355 |
| pill captions over the speaker | - | y 1290 | - |
| full-screen card, big word in the middle | y 800-810 | **y 960-965** | y 1125-1140 |
| full-screen card, big word last | y 735 and y 850 | **y 965** | - |

Nothing below y 1500 (platform buttons and the caption cover it), nothing above y 300, nothing between y 520 and
y 1040 while the speaker is on screen (that is the face).

## 7. EDL recipes

All times are program seconds from `analysis/program_words.json`. A full, rendered example: `assets/examples/kz_edl.json`.
`"anim"` can be left out - `rise` is the default, `pop` for pills.

Hook stack - the punch word on the cover frame, the accent rises when spoken:
```json
{"font": "anton", "text": "САЛМА", "t0": -0.4, "t1": 3.13, "y": 1240, "size": 210, "color": "#E02B20", "keep_t1": true},
{"font": "serif", "text": "бір қатені", "t0": 0.47, "t1": 3.13, "y": 1070, "size": 135, "color": "#FFFFFF", "shadow": true}
```

Pill run - generate it, do not type it:
```bash
python -X utf8 scripts/caption_words.py DIR --from 13.8 --to 16.5 --pill "#2F3E2E" --merge DIR/edl.json
```
```json
{"font": "sub", "text": "деп сұрайсың", "t0": 13.8, "t1": 15.06, "y": 1290, "size": 76, "anim": "pop", "fadeout": false, "pill": "#2F3E2E"}
```
Pill options: `pill_opacity` (0.92), `pill_pad` (0.42 x size each side), `pill_h` (1.42 x size), `pill_radius`
(0.5 = round ends). One line only.

Label + accent over the speaker (an item in a list, an excuse, a name):
```json
{"font": "sub", "text": "алгоритм", "t0": 5.38, "t1": 6.6, "y": 1150, "size": 80, "shadow": true},
{"font": "serif", "text": "кінәлі", "t0": 6.0, "t1": 6.6, "y": 1265, "size": 140, "color": "#E02B20", "shadow": true}
```

Card that grows out of the last pill (`flood`), with a three-line stack on the anchor:
```json
{"id": "wrong_q", "t0": 11.87, "t1": 13.8, "kind": "solid", "trans": "flood", "flash": null, "bg": "#C4151C", "flood_color": "#2F3E2E"}
```
```json
{"font": "sub", "text": "қаралымды", "t0": 11.87, "t1": 13.8, "y": 800, "size": 96},
{"font": "anton", "text": "ҚАЛАЙ", "t0": 12.5, "t1": 13.8, "y": 965, "size": 220, "color": "#FFFFFF", "keep_t1": true, "glow": false},
{"font": "serif", "text": "көбейтемін?", "t0": 13.0, "t1": 13.8, "y": 1140, "size": 150, "color": "#FFFFFF"}
```
`flood_from` ([x, y], default 540, 1290 - the pill) and `flood_size` ([w, h] of the seed, default 300 x 108) move
the starting point; `flood_color` is the pill's colour. Other entries: `zoom` or `whip` after a stack; `cut` +
`"flash": "invert"` for a one-word punch card of 0.6-0.8 s.
Card backgrounds: red `#C4151C`, off-white `#F4F1EC`, near-black `#0B0B0B`, the sampled colour.

One-word punch card with the gradient (white on black, quick rise so it reads at once):
```json
{"id": "no", "t0": 9.39, "t1": 10.06, "kind": "solid", "trans": "cut", "flash": "invert", "bg": "#0B0B0B"}
{"font": "anton", "text": "ЖОҚ.", "t0": 9.39, "t1": 10.03, "y": 960, "size": 240, "keep_t1": true, "glow": false, "rise_d": 0.12, "gradient": true}
```
Gradient options: `"gradient": "#8E96A3"` (the foot colour), `gradient_amount` (0.8). One line only.

A line that follows the voice word by word (a subtitle, the CTA tail): `"spoken": true` takes each word's time
from the transcript.
```json
{"font": "sub", "text": "деп жаз, үлгісін жіберемін", "t0": 24.6, "t1": 26.93, "y": 1352, "size": 62, "spoken": true, "shadow": true, "fadeout": false}
```
`rise` options: `rise_d` (0.28 s per word), `rise_stagger` (0.075 s), `rise_px` (lift, 0.16 x size), `drift` (3 %).

Counter card:
```json
{"id": "views", "t0": 19.02, "t1": 20.7, "kind": "number", "trans": "zoom", "flash": null,
 "label": "ҚАРАЛЫМ", "from": 0, "to": 1000000, "suffix": "", "count": [0.1, 1.2], "status": "0 КЛИЕНТ"}
```

Speaker inside a frame over a background (`pframe`), footage (`full` with `"color": true`), logos (`logo_flash`,
`converge`), a bar (`bar`) - as in `engine/references/edl-schema.md`.

CTA - always over the speaker, never over a card:
```json
{"font": "sub", "text": "пікірге", "t0": 23.7, "t1": 26.93, "y": 1075, "size": 90, "shadow": true},
{"font": "anton", "text": "«ХУК»", "t0": 24.3, "t1": 26.93, "y": 1215, "size": 210, "color": "#E02B20", "anim": "build", "keep_t1": true}
```

Top level for this look:
```json
"accent": "#E02B20",
"look": {"halftone_opacity": 0, "vignette": 26, "grain": 2},
"zoom": [[0, 3.18, "tight"], [3.18, 5.38, "wide"]],
"beats": [{"n": 1, "name": "Хук", "t0": 0, "t1": 3.18}, {"n": 2, "name": "Кім туралы", "t0": 3.18, "t1": 5.38}]
```
`beats` names the parts for the storyboard. Leave `"fonts"` out - the defaults are the Kazakh set.

## 8. Beat sheet for a 25-30 s reel

| # | part | share | on screen | entry |
|---|---|---|---|---|
| 1 | Hook - a ban, a wrong belief, a number | 0-3 s | speaker tight, hook stack, punch word on frame 0 | - |
| 2 | Who it is about | 3-5 s | first colour card (sampled colour): label + BIG + accent | `zoom` |
| 3 | What people usually think - a list of 2-3 | 5-9 s | speaker, label + red accent per item, tight / wide / tight | - |
| 4 | The turn ("Жоқ.") | 9-11 s | one-word black card with an invert flash, then label + accent | `cut` |
| 5 | The wrong way, said as a question | 11-15 s | pill, then a red card with a three-line stack | `flood` |
| 6 | The right way | 15-19 s | pills, then an off-white card: dark label + dark accent + red BIG | `flood` |
| 7 | Proof or price - a number | 19-23 s | counter card, then speaker with pills and a white BIG question | `zoom` |
| 8 | Call to action | last 3 s | speaker, label + red «WORD» + small spoken line | - |

For every beat fix in one line: the meaning, what is on screen, the exact words, the framing, how it enters from the
beat before, how it leaves into the next, the sound cue, and the one risk to check in a still.

## 9. Variants: three ways to open

Before the storyboard goes to the person, try 3-5 genuinely different treatments of the hook (and of any beat that
feels weak) with `scripts/variants.py`, pick the strongest for the whole reel, and say in one line why.
A different colour or font is not a variant; a different action, layout or transition is.
`assets/examples/kz_hook_variants.json` holds three for the demo:

| | idea | when it wins |
|---|---|---|
| A | stack under the neck: punch word on frame 0, accent rises when spoken | the face sells the hook; the default |
| B | card first: the red card names the problem, then the speaker gives the ban | the speaker's first second is weak or the room is busy |
| C | word above the head + the sentence in pills: the face stays fully open | expressive speaker; the sentence must be read as well as heard |

## 10. Sound

`scripts/sfx_from_edl.py` builds everything from the EDL, so re-timing the picture re-times the sound. Do sound
only after the storyboard is approved.

| what happens on screen | cue | why |
|---|---|---|
| an insert MOVES in (`zoom`, `whip`, `bulge`) | airy whoosh, loudest in the middle of the move | whooshes are for movement only |
| an insert cuts or morphs in (`cut`, `flood`) | soft thud / pop | a cut or a shape change is not a movement |
| a flash | shutter click | |
| a big word | pop | |
| an accent word | soft tick | |
| the first frame | soft low hit | marks the start |
| pill captions | nothing | 2-3 a second would become noise |

- Every cue's peak lands on the first frame that shows the change (the script prints the offset; over one frame is a bug).
- No sample twice in the same way: pitch and level vary a little by themselves.
- Levels stay under the voice: whoosh -27 dBFS, pop -20, tick -26; the voice stays at -14 LUFS.
- Music only if the person supplies a file: `--music FILE` puts it 20 dB under the voice with fades. To order one,
  give 2-3 prompts with the exact length and no drums that fight speech, for example: "minimal warm electronic bed,
  92 BPM, instrumental, soft plucks, airy pads, no lead, no vocals, 27 seconds, gentle lift at 0:19".
- Silent or not listened to are different things: say which.

## 11. Hook and CTA bank (write new ones in the same moulds; do not translate the reference's lines)

Hooks:
- Ban until fixed: «Мына бір қатені түземей, видео салма.»
- Wrong question -> right question: «"Қаралымды қалай көбейтемін?" - қате сұрақ.»
- Everyone does X: «Бәрі қаралымды қуып жүр. Ал ақша басқа жерде.»
- Price contrast: «2 000 теңгелік монтаж бен 30 000 теңгелік монтаж. Қайсысы жақсы?»
- Time or number: «Бір видеоға 5 сағат кетіп жүр ме? 30 минутта болады.»
- Stop word first: «Тоқта. Мынаны білмей тұрып, ... бастама.»

Calls to action (one per reel):
- keyword comment: «Пікірге "..." деп жаз - сілтемесін жіберемін.»
- save: «Сақтап қой, кейін керек болады.»
- send: «Осыны керек адамға жібер.»
- follow: «Жалғасын көргің келсе, жазыл.»
- for a comparison post, the question is the CTA: «Қайсысы жақсы? Пікірге жаз.»

## 12. Packaging (what to post, not only how to cut)

| post | build | why it worked on the reference account |
|---|---|---|
| "Кейін / Дейін" | `scripts/compare_pack.py`: big card = the edit, small card = the same cuts with no graphics | 60.9 K views, 2.3 % saves, 219 comments asking for the raw clip |
| "A vs B" with a provocative label (two prices, two tools) | the same script with `--label-main` / `--label-other` | 120 K views; the comments argued which side is better |
| the clean edit alone | the plain render | 48.9 K when the talk itself had a strong hook, 2.0 K when it did not |
| lead magnet, 10-12 s: one question + «пікірге ... деп жаз» | a short plain render | 190 comments on 2.4 K views |
| testimonial with a "мынадан → мынаған" strip | speaker + a `full` / `frame` insert in the lower third | pinned as proof, low reach |

Put the search words people would type in the post text, as that account did - the on-screen text stays clean.

## 13. Review checklist and honest statuses

Before showing anything: `kz_lint.py` at 85+ with no FAIL, then look at the storyboard yourself.

- [ ] Every Kazakh letter is right (ә ғ қ ң ө ұ ү һ і) and no word is in a fallback font.
- [ ] Frame 0 already shows the hook word.
- [ ] Nothing over the eyes or the mouth; pills at chest height; nothing below y 1500.
- [ ] Each beat looks different from the one before it; a change every 2-3 s.
- [ ] Big words sit on the two anchors; red is used for one word per screen.
- [ ] No particle alone in a pill; no more than three lines on a card.
- [ ] The first card arrives inside the first 3-4 s; the CTA is over the speaker.
- [ ] Mid-transition stills: the flood starts from the pill, nothing reveals black, no empty edges.
- [ ] Too-wide words were shrunk on purpose, not by accident (read the renderer's notes).

After the full render run `review_render.py` and look at `first.png`, `last.png` and `joins.png`. The first build
is a draft: write each finding as *time -> what is seen -> cause -> fix -> re-check*, fix, render again.

In the report to the person keep five statuses apart and never upgrade one into another:

| status | Kazakh | means |
|---|---|---|
| built | жасалды | the file or the code exists |
| run | іске қосып тексерілді | a script ran and printed numbers (lint score, frame count, LUFS, sync offsets) |
| seen in frames | кадрда көрінді | Claude looked at stills |
| watched in motion | қозғалыста қаралды | someone played the video at speed - Claude cannot |
| listened to | тыңдалды | someone heard the mix - Claude cannot |
