#!/usr/bin/env python3
"""Canonical Mastery V2 Registry: 12 Hook/Motion Formats, 8 Subtitle Formats, Anti-Repeat Router & 2-4 Keyframe Stack Builder.

Shared across `storyboard.py`, `variants.py`, `render_hooks_chromium.py`, `caption_words.py`,
`validate_edl.py`, and `kz_lint.py` so every component agrees on preset names, layer roles,
and anti-repeat constraints.
"""

import re

CAPTION_FORMATS = (
    'asymmetric_bento_stack',
    'graffiti_underline_strike',
    'tilted_pill_badge',
    'behind_head_giant',
    'word_by_word_pop',
    'split_left_right_dialogue',
    'slot_machine_counter',
    'whisper_glitch_box',
)

CAMERA_PRESETS = (
    'punch_in',
    'slow_push_in',
    'dramatic_pull_out',
    'speaker_whip_pan',
    'handheld_breathing',
)

VALID_CAMERA_EFFECTS = set(CAMERA_PRESETS) | {
    'zoom_in', 'zoom_out', 'zoom_push', 'smooth_pan', 'whip_pan', 'micro_shake', 'snap_punch',
}

BANNED_PLACEHOLDERS = (
    '88%', 'негізгі көрсеткіш', 'жасырын кейс #01', 'рекордтық динамика',
    'күшті инсайт', 'алгоритм және процесс', 'өсім динамикасы',
    'todo', 'placeholder', 'lorem ipsum', 'live simulation',
)

LAYER_ROLES = ('camera', 'depth', 'graphic', 'type_audio')

HOOK_CATALOG = {
    'frazix_dossier_hook': {
        'source': 'rossark + frazix',
        'html': 'assets/hooks/frazix_dossier_hook.html',
        'assets': ['assets/frazix/frazix_dossier_card.png', 'assets/frazix/frazix_barcode.png', 'assets/frazix/frazix_dotgrid.png'],
        'depth': 'full',
        'layout_default': 'split',
        'default_sfx': 'whoosh',
        'keywords': ('тұлға', 'құпия', 'кейс', 'факт', 'досье', 'кім', 'директор', 'актриса', 'продюсер', 'хабарлас', 'кісі', 'личность', 'секрет'),
        'camera_default': 'slow_push_in',
    },
    'graffiti_fact_explosion': {
        'source': 'rossark + graffiti',
        'html': 'assets/hooks/graffiti_fact_explosion.html',
        'assets': ['assets/graffiti/badge_fakt.png', 'assets/graffiti/badge_erezhe.png', 'assets/graffiti/torn_paper_strip.png', 'assets/graffiti/arrow_red_loop.png'],
        'depth': 'full',
        'layout_default': 'full',
        'default_sfx': 'pop',
        'keywords': ('ереже', 'факт', 'заң', 'шындық', 'қағида', 'бірінші рет', 'правило', 'доказано'),
        'camera_default': 'punch_in',
    },
    'threejs_3d_floating_totem': {
        'source': 'three.js + 3d',
        'html': 'assets/hooks/threejs_3d_floating_totem.html',
        'assets': ['assets/3d/card_3d_bakyt.png', 'assets/3d/compass_3d_gold.png', 'assets/frazix/frazix_sparkle_gold.png'],
        'depth': 'full',
        'layout_default': 'full',
        'default_sfx': 'hit',
        'keywords': ('бағыт', 'арман', 'бақыт', 'жол', 'мақсат', 'направление', 'компас', 'болашақ'),
        'camera_default': 'speaker_whip_pan',
    },
    'lemo_ink_wash_history': {
        'source': 'lemo-opuscar',
        'html': 'assets/hooks/lemo_ink_wash_history.html',
        'assets': ['engine/assets/textures/halftone_1080x1920.png'],
        'depth': 'full',
        'layout_default': 'full',
        'default_sfx': 'thud',
        'keywords': ('тарих', 'мәдениет', 'жыл', 'ғасыр', 'балалық', 'жоқшылық', 'естелік', 'философия', 'ой', 'история'),
        'camera_default': 'dramatic_pull_out',
    },
    'lemo_isometric_system': {
        'source': 'lemo-opuscar + opus-video-prompts',
        'html': 'assets/hooks/lemo_isometric_system.html',
        'assets': ['assets/frazix/frazix_dotgrid.png'],
        'depth': 'full',
        'layout_default': 'split',
        'default_sfx': 'tick',
        'keywords': ('жүйе', 'бизнес', 'алгоритм', 'процесс', 'схема', 'жоба', 'технология', 'механизм', 'система', 'касса'),
        'camera_default': 'slow_push_in',
    },
    'reanimate_state_morph': {
        'source': 'reanimate',
        'html': 'assets/hooks/reanimate_state_morph.html',
        'assets': [],
        'depth': 'full',
        'layout_default': 'split',
        'default_sfx': 'whoosh',
        'keywords': ('бұрын', 'қазір', 'қате', 'дұрыс', 'салыстыр', 'теңге', 'доллар', 'шаққанда', 'қарсы', 'өзгер', 'было', 'стало'),
        'camera_default': 'punch_in',
    },
    'pixelfx_energy_shader': {
        'source': 'pixelfx',
        'html': 'assets/hooks/pixelfx_energy_shader.html',
        'assets': ['assets/frazix/frazix_sparkle_red.png'],
        'depth': 'full',
        'layout_default': 'full',
        'default_sfx': 'hit',
        'keywords': ('шок', 'страх', 'қорқыныш', 'найзағай', 'жарылыс', 'эмоция', 'күй', 'феномен', 'инсайт', 'қатты'),
        'camera_default': 'punch_in',
    },
    'opus_bento_grid_stats': {
        'source': 'awesome-opus5-5-videos + opus-video-prompts',
        'html': 'assets/hooks/opus_bento_grid_stats.html',
        'assets': ['assets/frazix/frazix_dotgrid.png'],
        'depth': 'full',
        'layout_default': 'split',
        'default_sfx': 'pop',
        'keywords': ('миллион', 'миллиард', 'млн', 'млрд', 'пайыз', '%', 'ақша', 'табыс', 'күніне', 'сана', 'қанша'),
        'camera_default': 'slow_push_in',
    },
    'halftone_cutout_backsplash': {
        'source': 'presenter_mattes + halftone',
        'html': 'assets/hooks/halftone_cutout_backsplash.html',
        'assets': ['engine/assets/textures/halftone_1080x1920.png'],
        'depth': 'behind_speaker',
        'layout_default': 'behind_speaker',
        'default_sfx': 'hit',
        'keywords': ('рекорд', 'неге', 'қалай', 'маңызды', 'назар', 'басты', 'ұмытпа', 'қазақ', 'кино'),
        'camera_default': 'handheld_breathing',
    },
    'graffiti_circle_callout': {
        'source': 'graffiti',
        'html': 'assets/hooks/graffiti_circle_callout.html',
        'assets': ['assets/graffiti/oval_red.png', 'assets/graffiti/oval_cyan.png', 'assets/graffiti/underline_yellow.png'],
        'depth': 'full',
        'layout_default': 'split',
        'default_sfx': 'tick',
        'keywords': ('қара', 'мына', 'дәл', 'нақты', 'ерекше', 'көр', 'қымбат', 'не алу', 'келеді'),
        'camera_default': 'speaker_whip_pan',
    },
    'split_60_40_simulation': {
        'source': 'three.js + reanimate',
        'html': 'assets/hooks/split_60_40_simulation.html',
        'assets': [],
        'depth': 'full',
        'layout_default': 'split',
        'default_sfx': 'whoosh',
        'keywords': ('өсім', 'график', 'тренд', 'симуляция', 'динамика', 'статистика', 'нәтиже', 'бірте'),
        'camera_default': 'dramatic_pull_out',
    },
    'retro_terminal_decrypt': {
        'source': 'lemo-opuscar + frazix',
        'html': 'assets/hooks/retro_terminal_decrypt.html',
        'assets': ['assets/frazix/frazix_barcode.png'],
        'depth': 'full',
        'layout_default': 'split',
        'default_sfx': 'glitch',
        'keywords': ('код', 'шифр', 'дерек', 'құпия', 'жасырын', 'терминал', 'білмеймін', 'түсінбед', 'вообще', 'секрет'),
        'camera_default': 'handheld_breathing',
    },
}

HOOK_ORDER = list(HOOK_CATALOG.keys())


def pick_hook_preset(text='', beat_name='', last_used_styles=None, fallback_idx=0):
    """Select the best matching hook preset from all 12 formats while obeying the Anti-Repeat Law.

    `last_used_styles` maintains the recent style queue; this function NEVER picks the
    immediately preceding style (and avoids repeating the last 2 styles when possible),
    appending the chosen style to `last_used_styles` if a list is provided.
    """
    hay = ('%s %s' % (beat_name or '', text or '')).lower()
    hist = list(last_used_styles or [])
    last = hist[-1] if hist else None
    recent = set(hist[-2:])

    scored = []
    for idx, preset in enumerate(HOOK_ORDER):
        kws = HOOK_CATALOG[preset]['keywords']
        hits = sum(2 if (' ' in kw and kw in hay) else (1 if kw in hay else 0) for kw in kws)
        scored.append((hits, -((idx - fallback_idx) % len(HOOK_ORDER)), preset))

    scored.sort(reverse=True)
    # 1. Strongest semantic match not in recent-2 (and never == last)
    chosen = None
    for hits, _, preset in scored:
        if hits > 0 and preset != last and preset not in recent:
            chosen = preset
            break
    # 2. Semantic match different from immediate last
    if not chosen:
        for hits, _, preset in scored:
            if hits > 0 and preset != last:
                chosen = preset
                break
    # 3. Deterministic rotation across unused presets
    if not chosen:
        for step in range(len(HOOK_ORDER)):
            cand = HOOK_ORDER[(fallback_idx + step) % len(HOOK_ORDER)]
            if cand != last and cand not in recent:
                chosen = cand
                break
    if not chosen:
        chosen = next((p for p in HOOK_ORDER if p != last), HOOK_ORDER[0])

    if isinstance(last_used_styles, list):
        last_used_styles.append(chosen)
    return chosen


def extract_transcript_metaphor(said='', beat_name=''):
    """Transcript Metaphor Extraction: turn exact Kazakh spoken tokens into non-placeholder scene payload."""
    txt = (said or '').strip()
    low = (beat_name + ' ' + txt).lower()
    words = [w.strip('.,!?;:«»"()') for w in txt.split() if w.strip('.,!?;:«»"()')]
    nums = [float(n.replace(',', '.')) for n in re.findall(r'\d+(?:[.,]\d+)?', txt)]
    headline = (beat_name or ' '.join(words[:3])).strip()
    subtitle = ' '.join(words[:5]) if words else headline

    # Detect metaphor from spoken words
    if any(k in low for k in ('хабарлас', 'қоңырау', 'звон', 'телефон', 'айтты', 'сұра')):
        metaphor = 'call_ui'
    elif any(k in low for k in ('доллар', 'теңге', 'валют', 'курс', 'шаққанда', 'қымбат')):
        metaphor = 'currency_compare'
    elif nums or any(k in low for k in ('миллион', 'миллиард', 'млн', 'млрд', 'пайыз', '%', 'ақша', 'табыс')):
        metaphor = 'number_stats'
    elif any(k in low for k in ('бұрын', 'қазір', 'бірақ', 'ал ', 'не ', 'қарсы', 'алуға')):
        metaphor = 'state_contrast'
    elif any(k in low for k in ('страх', 'қорқыныш', 'шок', 'жоқшылық', 'ашу', 'эмоция', 'феномен')):
        metaphor = 'emotion_shock'
    else:
        metaphor = 'process_steps'

    val_to = int(nums[0]) if nums and nums[0].is_integer() else (nums[0] if nums else 0)
    suf = ' МЛН ₸' if any(k in low for k in ('миллион', 'млн')) else ('%' if '%' in txt else (' ₸' if 'теңге' in low else ''))
    # Pull up to 3 meaningful tokens (>3 chars) for step/item displays
    key_tokens = [w.upper() for w in words if len(w) >= 4][:3] or [w.upper() for w in words[:3]]
    kpis = []
    if val_to:
        kpis.append({'label': words[0].upper() if words else headline[:10].upper(), 'val': f'{val_to}{suf}'})
    for kt in key_tokens:
        if len(kpis) < 3:
            kpis.append({'label': kt[:12], 'val': kt[:8]})
    return dict(
        metaphor=metaphor,
        title=headline[:28],
        subtitle=subtitle[:42],
        label=(beat_name or (words[0] if words else '')).upper()[:24],
        spoken_words=txt,
        **{'from': 0},
        to=val_to,
        suffix=suf,
        kpis=kpis,
        items=key_tokens,
        left_label=(words[0].upper() if words else ''),
        right_label=(words[-1].upper() if len(words) > 1 else ''),
    )


def build_compound_keyframes(t0, t1, preset=None, caption_format='word_by_word_pop', sfx='pop', role_index=0, include_depth=True):
    """Build a valid 2..4 layer Compound Keyframe Stack with explicit Module 3 camera presets."""
    cam = (HOOK_CATALOG.get(preset, {}).get('camera_default') if preset else None) or CAMERA_PRESETS[role_index % len(CAMERA_PRESETS)]
    cam_anim = {'layer': 'camera', 'effect': cam, 't0': round(t0, 3), 't1': round(t1, 3)}
    if cam == 'punch_in':
        cam_anim.update({'from': 1.0, 'to': 1.24})
    elif cam == 'slow_push_in':
        cam_anim.update({'from': 1.0, 'to': 1.18})
    elif cam == 'dramatic_pull_out':
        cam_anim.update({'from': 1.24, 'to': 1.00})
    elif cam == 'speaker_whip_pan':
        cam_anim.update({'from': 1.08, 'to': 1.16, 'pan_px': 28 if role_index % 2 == 0 else -28})
    else:
        cam_anim.update({'from': 1.0, 'to': 1.03})

    stack = [cam_anim]
    if include_depth:
        stack.append({
            'layer': 'depth',
            'effect': 'matte_backsplash' if role_index % 2 == 0 else 'halftone_drift',
            't0': round(t0, 3),
            't1': round(t1, 3),
        })
    if preset:
        stack.append({
            'layer': 'graphic',
            'preset': preset,
            'spring': {'stiffness': 220, 'damping': 18},
            't0': round(t0, 3),
            't1': round(t1, 3),
        })
    stack.append({
        'layer': 'type_audio',
        'caption_format': caption_format,
        'sfx': sfx or HOOK_CATALOG.get(preset, {}).get('default_sfx', 'pop'),
        't0': round(t0, 3),
        't1': round(t1, 3),
    })
    return stack[:4]


def balance_keyframe_stack(animations, t0=0.0, t1=2.0, role_index=0):
    """Enforce `2 <= len(animations) <= 4` on any beat/keyframe while preserving unique layer roles."""
    items = [dict(a) for a in (animations or []) if isinstance(a, dict)]
    notes = []

    if len(items) > 4:
        kept, seen = [], set()
        for a in items:
            role = a.get('layer', 'graphic')
            if role not in seen:
                seen.add(role)
                kept.append(a)
        for a in items:
            if len(kept) >= 4:
                break
            if a not in kept:
                kept.append(a)
        notes.append('clamped %d -> %d layers (max 4)' % (len(items), len(kept[:4])))
        items = kept[:4]

    if len(items) < 2:
        existing_roles = {a.get('layer') for a in items}
        if 'camera' not in existing_roles:
            cam = CAMERA_PRESETS[role_index % len(CAMERA_PRESETS)]
            items.insert(0, {'layer': 'camera', 'effect': cam, 'from': 1.0, 'to': 1.18 if cam == 'slow_push_in' else 1.24, 't0': round(t0, 3), 't1': round(t1, 3)})
        if len(items) < 2 and 'type_audio' not in existing_roles:
            items.append({'layer': 'type_audio', 'caption_format': 'word_by_word_pop', 'sfx': 'pop', 't0': round(t0, 3), 't1': round(t1, 3)})
        if len(items) < 2 and 'depth' not in existing_roles:
            items.append({'layer': 'depth', 'effect': 'halftone_drift', 't0': round(t0, 3), 't1': round(t1, 3)})
        notes.append('expanded <2 -> %d layers (min 2)' % len(items))

    return items, notes
