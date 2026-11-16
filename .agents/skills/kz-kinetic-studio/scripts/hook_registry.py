#!/usr/bin/env python3
"""Canonical kz-kinetic-studio Registry:
- Strictly 4 Ultra-Crafted Hero Hook Composites (Zero Black Screen, compact WebM VP9 alpha)
- Strictly 2 <= total_hooks <= 3 per reel
- 8 Kinetic Foreground Subtitle Formats (safe zone y=1280..1520, zero behind-hair hidden keywords)
- 2..4 Compound Animation Layers per beat
"""

import re

MIN_HERO_HOOKS = 2
MAX_HERO_HOOKS = 3

CAPTION_FORMATS = (
    'word_by_word_pop',
    'graffiti_underline_strike',
    'tilted_pill_badge',
    'keyword_spotlight_burst',
    'asymmetric_bento_stack',
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

COMMON_KZ_TYPOS = {
    'көремен': 'көрермен',
    'коркем': 'көркем',
    'жаксы': 'жақсы',
    'казақ': 'қазақ',
    'кажет': 'қажет',
    'акша': 'ақша',
    'тенге': 'теңге',
}

BANNED_DARK_BGS = {'#000000', '#05070A', '#0B0B0E', '#080A0E', '#0D0D12'}

LAYER_ROLES = ('camera', 'depth', 'graphic', 'type_audio')

HERO_CATALOG = {
    'hero_editorial_collage': {
        'source': 'lemo-opuscar + frazix + torn_paper',
        'html': 'assets/hooks/hero_editorial_collage.html',
        'assets': [
            'assets/frazix/frazix_dossier_card.png',
            'assets/frazix/frazix_dotgrid.png',
            'assets/frazix/frazix_barcode.png',
            'assets/graffiti/torn_paper_strip.png',
            'assets/graffiti/badge_fakt.png',
            'assets/graffiti/badge_erezhe.png',
        ],
        'width': 920,
        'height': 520,
        'x': 540,
        'y': 410,
        'blur_bg': True,
        'kind_default': 'overlay',
        'depth': 'front',
        'layout_default': 'full',
        'default_sfx': 'whoosh',
        'keywords': ('факт', 'досье', 'ереже', 'қағида', 'қымбат', 'тарих', 'дәлел', 'жаз', 'хроника'),
        'camera_default': 'slow_push_in',
    },
    'hero_glass_kpi_counter': {
        'source': 'rossark-glassmorphism + reanimate-counter',
        'html': 'assets/hooks/hero_glass_kpi_counter.html',
        'assets': ['assets/frazix/frazix_sparkle_gold.png'],
        'width': 880,
        'height': 420,
        'x': 540,
        'y': 380,
        'blur_bg': True,
        'kind_default': 'overlay',
        'depth': 'front',
        'layout_default': 'full',
        'default_sfx': 'pop',
        'keywords': ('миллион', 'миллиард', 'млн', 'млрд', 'пайыз', '%', 'ақша', 'теңге', 'доллар', 'күніне', 'табыс', '160'),
        'camera_default': 'punch_in',
    },
    'hero_3d_totem_badge': {
        'source': 'three.js + local-3d-assets + graffiti',
        'html': 'assets/hooks/hero_3d_totem_badge.html',
        'assets': [
            'assets/3d/compass_3d_gold.png',
            'assets/3d/card_3d_bakyt.png',
            'assets/frazix/frazix_sparkle_gold.png',
            'assets/graffiti/arrow_yellow_down.png',
        ],
        'width': 880,
        'height': 460,
        'x': 540,
        'y': 390,
        'blur_bg': False,
        'kind_default': 'overlay',
        'depth': 'front',
        'layout_default': 'full',
        'default_sfx': 'hit',
        'keywords': ('бақыт', 'арман', 'мақсат', 'бағыт', 'болашақ', 'жол', 'рекорд', 'феномен', 'жеңіс'),
        'camera_default': 'speaker_whip_pan',
    },
    'hero_incoming_ui_alert': {
        'source': 'ios-dynamic-island + telegram-glass',
        'html': 'assets/hooks/hero_incoming_ui_alert.html',
        'assets': [],
        'width': 880,
        'height': 360,
        'x': 540,
        'y': 320,
        'blur_bg': False,
        'kind_default': 'overlay',
        'depth': 'front',
        'layout_default': 'full',
        'default_sfx': 'pop',
        'keywords': ('хабарлас', 'қоңырау', 'звон', 'айтты', 'сұра', 'телефон', 'хат', 'сенбей'),
        'camera_default': 'dramatic_pull_out',
    },
}

HOOK_CATALOG = HERO_CATALOG
HOOK_ORDER = list(HERO_CATALOG.keys())


def pick_hook_preset(text='', beat_name='', last_used_styles=None, fallback_idx=0):
    """Select the best matching Hero Hook from the 4 high-craft composites while avoiding consecutive repeats."""
    hay = ('%s %s' % (beat_name or '', text or '')).lower()
    hist = list(last_used_styles or [])
    last = hist[-1] if hist else None

    scored = []
    for idx, preset in enumerate(HOOK_ORDER):
        kws = HERO_CATALOG[preset]['keywords']
        hits = sum(2 if (' ' in kw and kw in hay) else (1 if kw in hay else 0) for kw in kws)
        scored.append((hits, -((idx - fallback_idx) % len(HOOK_ORDER)), preset))

    scored.sort(reverse=True)
    chosen = None
    for hits, _, preset in scored:
        if hits > 0 and preset != last:
            chosen = preset
            break
    if not chosen:
        for step in range(len(HOOK_ORDER)):
            cand = HOOK_ORDER[(fallback_idx + step) % len(HOOK_ORDER)]
            if cand != last:
                chosen = cand
                break
    if not chosen:
        chosen = HOOK_ORDER[0]

    if isinstance(last_used_styles, list):
        last_used_styles.append(chosen)
    return chosen


def extract_transcript_metaphor(said='', beat_name=''):
    """Transcript Metaphor Extraction: real Kazakh tokens -> HERO_CATALOG EDL_PAYLOAD (zero placeholders)."""
    txt = (said or '').strip()
    low = (beat_name + ' ' + txt).lower()
    words = [w.strip('.,!?;:«»"()') for w in txt.split() if w.strip('.,!?;:«»"()')]
    nums = [float(n.replace(',', '.')) for n in re.findall(r'\d+(?:[.,]\d+)?', txt)]
    headline = (beat_name or ' '.join(words[:3])).strip()
    subtitle = ' '.join(words[:6]) if words else headline

    is_mln = any(k in low for k in ('миллион', 'млн'))
    is_mlrd = any(k in low for k in ('миллиард', 'млрд'))
    base_val = int(nums[0]) if nums and nums[0].is_integer() else (nums[0] if nums else 0)
    full_val = base_val * 1_000_000 if (base_val and is_mln and base_val < 10000) else (
        base_val * 1_000_000_000 if (base_val and is_mlrd and base_val < 10000) else base_val
    )
    suf = '₸' if any(k in low for k in ('теңге', 'млн', 'миллион', 'миллиард', 'ақша', 'табыс')) else ('%' if '%' in txt else '')

    if any(k in low for k in ('хабарлас', 'қоңырау', 'звон', 'телефон', 'сенбей')):
        hero = 'hero_incoming_ui_alert'
    elif nums or is_mln or is_mlrd or any(k in low for k in ('ақша', 'табыс', 'теңге', 'доллар')):
        hero = 'hero_glass_kpi_counter'
    elif any(k in low for k in ('бақыт', 'арман', 'бағыт', 'феномен', 'рекорд', 'жол')):
        hero = 'hero_3d_totem_badge'
    else:
        hero = 'hero_editorial_collage'

    return {
        'hero': hero,
        'title': headline[:24],
        'subtitle': subtitle[:38],
        'label': (words[0].upper() if words else headline[:18].upper()),
        'spoken_words': txt,
        'from': 0,
        'to': full_val,
        'suffix': suf,
        'asset': 'card' if 'бақыт' in low else 'compass',
        'stamp': (words[1].upper()[:14] if len(words) > 1 else ''),
    }


def build_compound_keyframes(t0, t1, preset=None, caption_format='word_by_word_pop', sfx='pop', role_index=0, include_depth=True):
    """Build a valid 2..4 layer Compound Keyframe Stack with explicit dynamic camera presets."""
    cam = (HERO_CATALOG.get(preset, {}).get('camera_default') if preset else None) or CAMERA_PRESETS[role_index % len(CAMERA_PRESETS)]
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
            'effect': 'bokeh_glass_dim' if HERO_CATALOG.get(preset, {}).get('blur_bg') else 'live_framing',
            't0': round(t0, 3),
            't1': round(t1, 3),
        })
    if preset:
        stack.append({
            'layer': 'graphic',
            'preset': preset,
            'spring': {'stiffness': 240, 'damping': 18},
            't0': round(t0, 3),
            't1': round(t1, 3),
        })
    stack.append({
        'layer': 'type_audio',
        'caption_format': caption_format,
        'sfx': sfx or HERO_CATALOG.get(preset, {}).get('default_sfx', 'pop'),
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
            items.append({'layer': 'depth', 'effect': 'live_framing', 't0': round(t0, 3), 't1': round(t1, 3)})
        notes.append('expanded <2 -> %d layers (min 2)' % len(items))

    return items, notes
