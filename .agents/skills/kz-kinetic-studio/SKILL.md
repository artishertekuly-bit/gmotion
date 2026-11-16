---
name: kz-kinetic-studio
description: >-
  High-craft vertical 9:16 Kazakh kinetic motion studio ("80% Multi-Font Kinetic Subtitle Choreography +
  20% (strictly 2-3) High-Craft Transparent Composite Hero Hooks + Zero Black Screen"). Keeps the speaker's
  live 9:16 video as the 100% continuous spine (with subtle bokeh blur/dim behind frosted Hero cards,
  never opaque #000000/#05070a black screens), renders 2-3 compact WebM VP9-alpha Hero Hooks
  (hero_editorial_collage, hero_glass_kpi_counter, hero_3d_totem_badge, hero_incoming_ui_alert) via
  image2pipe + Chromium, drives kinetic retention subtitles in the locked safe zone (y = 1280..1520) with
  contrasting font switches, 1.35x keyword explosions, graffiti underlines, clean inter-word spacing, and
  outputs a clean 15-25 MB MP4 with automatic temp/cache cleanup. Trigger on: "/kz-kinetic-studio",
  "talking head", "сөйлеп тұрған видео", "камераға сөйлеген видео", "рилс монтаж", "қазақша субтитр",
  "хук", "кинетикалық субтитр".
---

# `kz-kinetic-studio` — 80% Кинетикалық Субтитр Хореографиясы + 20% (2–3) Композиттік Hero Hook

**Негізгі Философия:**
> **"80% Көпшрифтті Кинетикалық Субтитр Хореографиясы + 20% (тек 2–3 рет) Жоғары Сапалы Композиттік Hero Hook + 0% Қара Экран"**

Адаммен сөйлесу — **тек қазақша**, қарапайым, нақты тілде. Барлық техникалық файлдар ағылшынша, ал экрандағы барлық жазу — мінсіз қазақ орфографиясымен (транскрипт түбірімен сәйкес).

---

## 5 Бұзылмайтын Студия Заңы (Unbreakable Laws)

`engine/scripts/validate_edl.py` әр `kz_edl.json` жоспарын қатаң тексереді (ереже бұзылса рендерге жібермейді):

1. **Zero Black Screen Law (`100%` Live Speaker Spine):**
   - Қара фонды (`#000000`, `#05070a`, `#0B0B0E`) `split` және `full` экрандарға **МҮЛДЕМ ТЫЙЫМ САЛЫНАДЫ!**
   - Спикердің 9:16 видеосы бүкіл **100% уақыт бойы** негізгі тірі фон болып қалады. Hero Hook шыққан сәтте спикердің үстіне мөлдір альфа-композит ретінде қойылады (`blur_bg: true` болса, спикердің кадры `backdrop-filter: blur` сияқты жұмсақ бұлдыратылып тереңдік береді, бірақ экран ешқашан қараймайды).
2. **Strictly 2–3 High-Craft Hero Hooks (`2 <= total_hooks <= 3`):**
   - 45–60 секундтық видеоға 7 сапасыз карточка тықпалауға тыйым салынады!
   - Бүкіл видеода **кемінде 2, ЕҢ КӨБІ 3** қана премиум Hero Hook болады, тек **4 Ультра-Сапалы Компоненттен**:
     1. `hero_editorial_collage` *(920×520 WebM alpha)* — нағыз қағаз текстурасы (`torn_paper_strip.png`, `frazix_dossier_card.png`), мөр (`badge_fakt.png`/`badge_erezhe.png`), көлеңке және серіппелі физикамен шығатын редакциялық коллаж.
     2. `hero_glass_kpi_counter` *(880×420 WebM alpha)* — Rossark frosted glassmorphism плашка (`rgba(255,255,255,0.12)`, ақ шыны жиек), ішінде `0 -> 160 000 000 ₸` слот-санағыш және `frazix_sparkle_gold.png` жарқылы.
     3. `hero_3d_totem_badge` *(880×460 WebM alpha)* — спикер иығы/жоғарғы аймағында (`y=340..480`) қалқып тұратын `card_3d_bakyt.png` / `compass_3d_gold.png` 3D объектісі + `arrow_yellow_down.png`.
     4. `hero_incoming_ui_alert` *(880×360 WebM alpha)* — жоғарыдан iOS Dynamic Island / Apple Glass Banner стилінде сырғып түсетін хабарлама/қоңырау баннері және дыбыс толқыны.
3. **80% Kinetic Subtitle Choreography (`caption_words.py` + `textass.py`):**
   - Көрерменнің назарын бастың артындағы жасырын сөз емес, **сөйленіп жатқан субтитрдің өзі** ұстайды!
   - **Locked Safe Zone (`y = 1280..1520`):** Барлық субтитрлер тек төменгі кеуде/мойын аймағында (`y = 1380` әдепкі) ойнайды. Экран ортасында (`y=960`) немесе бет/микрофон үстінде секірмейді!
   - **No Space Swallowing:** Шрифт (`word_fonts`) немесе өлшем ауысқанда сөздер арасында міндетті түрде қатты бос орын (`\h` + `\fsp0`) сақталады (`тауып ЖАТТЫ`, ешқашан `тауыпЖАТТЫ` емес!).
   - **No Orphan Syllables / Mini-Tokens (`min_token_len >= 3`):** `3` әріптен қысқа сөздер (`те`, `ол`, `ал`), жалғаулар және көмекші етістіктер (`жатты`, `қалды`, `екен`, `дейді`) ешқашан жеке кадрға немесе жалғыз жолға бөлінбейді — әрдайым `2–4` сөздік фразамен бірге шығады. `glitch`/`terminal` анимациясы сөзді әріптеп үзбей, **бүтін сөзбен** ашады!
   - **In-Line Keyword Explosion:** «ФЕНОМЕН», «160 МИЛЛИОН», «ШОК», «ҚАТЕЛІК» сияқты кілт сөздер бастың артына жасырылмай, субтитр жолының **дәл ішінде** `impact`/`editorial` шрифтіне ауысып, **`1.35x` масштабпен** жарып шығады + астынан `underline_yellow.png`/`underline_red.png` немесе `-3°` контрастты Pill + `pop.wav` дыбысы қосылады.
4. **Dynamic Multi-Speaker Camera (`vision_py.py` + `render_reel.py`):**
   - 3 спикерге дейін MAR ерін-қимылы бойынша автофокус + 5 камера динамикасы (`punch_in`, `slow_push_in`, `dramatic_pull_out`, `speaker_whip_pan`, `handheld_breathing`).
   - Әр битте `2 <= animations <= 4` қабаты болады.
5. **Zero-Placeholder & Kazakh Orthography Audit (`kz_lint.py`):**
   - Транскриптте жоқ жасанды заглушкалар (`88%`, `НЕГІЗГІ КӨРСЕТКІШ`, `TODO`) және орфографиялық қателер (`КӨРЕМЕН` -> `КӨРЕРМЕН`) қатаң блокталады.

---

## Жеңіл Әрі Таза Рендер Пайплайны (Zero 1 GB Bloat)

1. **Ешқандай мыңдаған PNG немесе 1080×1920 бос `.mov` жоқ!**
   - `scripts/render_hooks_chromium.py` тек **2–3 Hero Hook**-ты шағын карточка өлшемінде (`880×420` / `920×520`, 30 fps) Playwright буферінен тікелей FFmpeg `image2pipe`-қа жіберіп, жеңіл **WebM (VP9 alpha, `yuva420p`)** форматында (`~0.3–1 МБ`) рендерлейді.
2. **Барлық граффити акценттер мен 80% кинетикалық субтитрлер** браузерсіз, тікелей **FFmpeg + libass** арқылы салынады.
3. **Қоқысты автоматты тазалау:**
   - Маска қажет емес жобаларда `presenter_mattes.py --faces-only` тек жылдам `faces.jsonl` жасайды (19 минуттық `rembg` мен жүздеген МБ `.mov` жасамайды).
   - `render_reel.py --crf 20 --cleanup` аяқталғанда барлық `work/` / `reel_*` кэштері мен `hooks_rendered/` уақытша файлдары `shutil.rmtree`-мен өшіріліп, тек **`15–25 МБ`** таза финалдық `.mp4` қалады!

---

## Жергілікті Ноутбукті Қорғау және Авто-Бұлттық Рендер (GitHub Actions)

- **Жергілікті компьютерде (8GB RAM, HDD):** ТЕК `fetch_to_context.py`, `caption_words.py`, `storyboard.py --plan-only`, `validate_edl.py`, `kz_lint.py`, `sfx_from_edl.py --dry`, `py_compile` іске қосылады.
- **ЕШҚАШАН жергілікті ауыр MP4/Chromium/rembg рендер жасама!**
- `validate_edl.py` (0 қате) және `kz_lint.py` (85+, 0 FAIL) өткен бойда рұқсат сұрамай-ақ `git add` → `git commit` → `git push` жасап, [render-master-reel.yml](file:///c:/Users/Artur/Gmotion/.github/workflows/render-master-reel.yml) бұлттық рендерін іске қос және дайын жеңіл `.mp4` нәтижені `gh run download` арқылы жүктеп, кадрларды тексер.

---

## Жұмыс Қадамдары

`E` = `engine/scripts`, `K` = `scripts`, `DIR` = жоба папкасы:

1. **YouTube / Видео талдау:**
   ```bash
   python -X utf8 K/fetch_to_context.py YOUTUBE_URL --project DIR
   python -X utf8 E/cut_pauses.py DIR
   python -X utf8 E/master_audio.py DIR
   ```
2. **80% Кинетикалық Субтитр + 2–3 Hero Hook EDL құру:**
   ```bash
   python -X utf8 K/caption_words.py DIR --from 0.45 --to DUR --mode 60-40 --y 1380 --merge DIR/kz_edl.json
   python -X utf8 K/storyboard.py DIR/kz_edl.json --plan-only --enrich-edl
   ```
3. **Валидация (Strict Gate):**
   ```bash
   python -X utf8 E/validate_edl.py DIR/kz_edl.json
   python -X utf8 K/kz_lint.py DIR/kz_edl.json
   ```
4. **Бұлттық Рендер + QA Тексеріс (`15–25 МБ` MP4):**
   GitHub Actions ішінде: `presenter_mattes.py --faces-only` → `render_hooks_chromium.py` (2–3 compact WebM VP9 alpha) → `sfx_from_edl.py` → `render_reel.py --crf 20 --cleanup` → `review_render.py`.

## Файлдар Құрылымы

| Жол | Мақсаты |
|---|---|
| `assets/hooks/_hook_core.js` | Мөлдір альфа сахна, серіппелі физика, Glassmorphism/қағаз текстура көмекшілері (0% қара фон/неон) |
| `assets/hooks/hero_*.html` | Тек 4 премиум Hero Hook: `hero_editorial_collage`, `hero_glass_kpi_counter`, `hero_3d_totem_badge`, `hero_incoming_ui_alert` |
| `scripts/hook_registry.py` | 4 Hero Hook реестрі, `2 <= hooks <= 3` квота роутері, `[2..4]` қабатты стек |
| `scripts/render_hooks_chromium.py` | `image2pipe` → `WebM VP9 alpha` (дискіге PNG жазбайды, шағын карточка өлшемінде) |
| `scripts/caption_words.py` | `y=1380` safe zone, `>=3` әріп ережесі, `1.35x` сөзді жарып шығару, 8 субтитр стилі |
| `engine/scripts/textass.py` | `\h\fsp0` бос орын кепілі, `word_scales`, сөзбе-сөз reveal (буын үзбейді) |
| `engine/scripts/render_reel.py` | Тірі спикер үстіне WebM alpha + bokeh blur композитинг, `--crf 20`, `--cleanup` (`shutil.rmtree`) |
| `engine/scripts/validate_edl.py` | 6 қатаң ереже (`2 <= hooks <= 3`, `0` қара экран, safe zone, орфография, камера) |
| `scripts/kz_lint.py` | Қазақша орфография, түбір тексеру (`КӨРЕРМЕН`), `0` жетім буын, ритм бағалау |
| `assets/examples/kz_edl.json` | `kz-kinetic-studio` стандартымен жасалған эталон EDL (2–3 Hero Hook + 80% кинетика) |
