#!/usr/bin/env python3
"""80% Kinetic Multi-Font Subtitle Choreography for kz-kinetic-studio.

    python -X utf8 scripts/caption_words.py PROJECT_DIR --from 0.45 --to 53.50 [--y 1380] [--size 72] [--merge EDL]

Enforces all 5 Step-3 Kinetic Subtitle Laws:
  1. Locked Safe Zone (y = 1280..1520, default 1380) — never jumps to y=960 or over face/eyes.
  2. min_token_len >= 3 + Kazakh particle/auxiliary binder: short words (< 3 letters) and
     particles/auxiliaries NEVER stand alone — every caption forms natural 2–4 word phrase blocks.
  3. Inline Keyword Spotlight (1.35x scale punch + impact/editorial font contrast + underline/tilted pill + pop.wav).
  4. Zero hidden behind-head captions: keywords explode INSIDE the main kinetic subtitle lane.
  5. Zero consecutive caption_format repetition.
"""
import argparse
import json
import os
import re
import sys

MIN_TOKEN_LEN = 3

PARTICLES = {
    'ма', 'ме', 'ба', 'бе', 'па', 'пе', 'да', 'де', 'та', 'те', 'ғой', 'қой',
    'ше', 'ау', 'ақ', 'ғана', 'қана', 'мыс', 'міс', 'екен', 'еді', 'емес',
    'деп', 'үшін', 'сайын', 'гөрі', 'бойы',
}

AUXILIARIES = {
    'жатты', 'жатыр', 'қалды', 'болды', 'болады', 'болу', 'керек', 'деді',
    'дейді', 'деймін', 'сөйтем', 'сияқты', 'тұр', 'жүр', 'отыр', 'екеуі',
    'мен', 'сен', 'ол', 'ал', 'не', 'бұл', 'сол', 'оны', 'оған', 'бар', 'жоқ',
    'бір', 'екі', 'тағы', 'дағы', 'ғана', 'қана', 'дейін',
}

CONTRAST_CONJ = {'бірақ', 'алайда', 'себебі', 'өйткені', 'дегенмен', 'керісінше', 'сондықтан', 'әйтпесе'}
NUM_RE = re.compile(r'^(\d+(?:[.,]\d+)?)\s*(%|₸|\$|€|x|х|k|к|м|млн|млрд|ж)?$', re.IGNORECASE)

CAPTION_FORMATS_V2 = (
    'word_by_word_pop',
    'graffiti_underline_strike',
    'tilted_pill_badge',
    'keyword_spotlight_burst',
    'asymmetric_bento_stack',
    'split_left_right_dialogue',
    'slot_machine_counter',
    'whisper_glitch_box',
)


def clean(w):
    w = w.strip().lower()
    w = re.sub(r'[«»"“”„.,;:…()\[\]]+', '', w)
    return w.strip('-–— ')


def _is_weak_token(tok_str):
    bare = re.sub(r'[?!]', '', clean(tok_str))
    if not bare:
        return True
    if NUM_RE.match(bare):
        return False
    return len(bare) < MIN_TOKEN_LEN or bare in PARTICLES or bare in AUXILIARIES


def _group_kz_words(words, t0, t1):
    """Bind particles, <3-char words, and auxiliaries to neighbors so zero orphans ever appear."""
    raw = [dict(s=w['s'], e=w['e'], w=clean(w['w'])) for w in words if t0 - 0.02 <= w['s'] < t1 - 0.02]
    raw = [w for w in raw if w['w']]
    if not raw:
        return []

    units = []
    for w in raw:
        bare = w['w'].rstrip('?!')
        gap = (w['s'] - units[-1]['e']) if units else 0.0
        prev_words = len(units[-1]['w'].split()) if units else 0
        if units and units[-1].get('wait'):
            units[-1]['w'] += ' ' + w['w']
            units[-1]['e'] = w['e']
            units[-1]['wait'] = False
        elif units and (bare in PARTICLES or (bare in AUXILIARIES and prev_words < 2 and gap < 0.55)):
            units[-1]['w'] += ' ' + w['w']
            units[-1]['e'] = w['e']
        else:
            must_wait = bare in PARTICLES or (len(bare) < MIN_TOKEN_LEN and not NUM_RE.match(bare))
            units.append(dict(s=w['s'], e=w['e'], w=w['w'], wait=must_wait))

    # Tail sweep: if final unit is still a single short/auxiliary word, bind it backward cleanly
    if len(units) >= 2 and len(units[-1]['w'].split()) == 1 and _is_weak_token(units[-1]['w']):
        if (units[-1]['s'] - units[-2]['e']) < 0.85:
            units[-2]['w'] += ' ' + units[-1]['w']
            units[-2]['e'] = units[-1]['e']
            units.pop()
    return units


def caption_items(words, t0, t1, y=1380, x=540, size=72, pill='#2F3E2E', color='#FFFFFF', hold=0.45):
    """Classic pill/shadow captions in locked safe zone (zero orphans)."""
    groups = _group_kz_words(words, t0, t1)
    y = max(1280, min(1520, int(round(y))))
    items = []
    for i, g in enumerate(groups):
        nxt = groups[i + 1]['s'] if i + 1 < len(groups) else None
        end = min(t1, nxt if nxt is not None and nxt - g['e'] < 0.6 else g['e'] + hold)
        it = dict(font='clean', text=g['w'], t0=round(g['s'], 3), t1=round(end, 3), x=x, y=y, size=size, color=color, anim='pop', fadeout=False)
        if pill and pill.lower() != 'none':
            it['pill'] = pill
        else:
            it['shadow'] = True
        items.append(it)
    return items


def _flatten_wt(chunk):
    wt = []
    for tok in chunk:
        subwords = tok['w'].split()
        dt = max(0.04, (tok['e'] - tok['s']) / max(len(subwords), 1))
        for si in range(len(subwords)):
            wt.append(round(tok['s'] + si * dt, 3))
    return wt


def _word_emphasis_vectors(words_list, keywords_set=None):
    """Build contrasting `word_fonts` and `word_scales` (`1.35x` on spotlight keywords) cleanly."""
    kws = keywords_set or set()
    if len(words_list) <= 1:
        w0 = words_list[0].rstrip('?!') if words_list else ''
        is_sp = w0 in kws or len(w0) >= 7
        return ([('impact' if is_sp else 'clean')] if words_list else None), ([1.35 if is_sp else 1.0] if words_list else None)
    best_idx = max(range(len(words_list)), key=lambda k: (
        200 if any(words_list[k].rstrip('?!').startswith(kw[:5]) for kw in kws if len(kw) >= 4) or words_list[k].rstrip('?!') in kws else 0,
        len(words_list[k].rstrip('?!')),
    ))
    roles, scales = [], []
    for k, w in enumerate(words_list):
        bare = w.rstrip('?!')
        is_kw = bare in kws or any(len(kw) >= 5 and bare.startswith(kw[:5]) for kw in kws)
        if k == best_idx:
            roles.append('editorial' if ('?' in w or '!' in w) else 'impact')
            scales.append(1.35 if (is_kw or len(bare) >= 7) else 1.22)
        elif is_kw:
            roles.append('impact')
            scales.append(1.25)
        elif k % 3 == 1 and len(bare) >= 5:
            roles.append('editorial')
            scales.append(1.0)
        else:
            roles.append('clean')
            scales.append(1.0)
    return roles, scales


def _pick_next_format(candidates, last_format, counts):
    pool = [c for c in candidates if c != last_format] or list(candidates)
    return min(pool, key=lambda c: (counts.get(c, 0), pool.index(c)))


def caption_items_60_40(
    words,
    t0,
    t1,
    y=1380,
    x=540,
    size=70,
    pill='#2F3E2E',
    color='#FFFFFF',
    highlight_colors=('#FFD600', '#00E676'),
    hold=0.42,
    keywords=None,
    stack_windows=None,
):
    """80% Kinetic Subtitle Choreography in Locked Safe Zone (y=1280..1520, zero orphans, 1.35x inline keywords)."""
    groups = _group_kz_words(words, t0, t1)
    if not groups:
        return []
    safe_y = max(1290, min(1500, int(round(y))))
    kw_set = {clean(k) for k in (keywords or []) if clean(k)}
    stacks = stack_windows or []
    items = []
    i = 0
    chunk_idx = 0
    last_fmt = None
    fmt_counts = {f: 0 for f in CAPTION_FORMATS_V2}

    def nxt_start(idx, default_end):
        ns = groups[idx]['s'] if idx < len(groups) else None
        if ns is not None and ns - groups[idx - 1]['e'] < 0.65:
            return min(t1, ns)
        return min(t1, default_end)

    def _matches_kw(tok_txt):
        for w_ in tok_txt.rstrip('?!').split():
            if w_ in kw_set or w_ in CONTRAST_CONJ or any(len(k) >= 5 and w_.startswith(k[:5]) for k in kw_set):
                return True
        return False

    while i < len(groups):
        g = groups[i]
        bare = g['w'].rstrip('?!')
        gap_before = (g['s'] - groups[i - 1]['e']) if i > 0 else 0.0
        in_stack = any(a - 0.05 <= g['s'] < b - 0.05 for a, b in stacks)

        # 1) Slot counter when numeric token appears
        m = NUM_RE.match(bare)
        if m and last_fmt != 'slot_machine_counter':
            raw_num = m.group(1).replace(',', '.')
            val = float(raw_num) if '.' in raw_num else int(raw_num)
            suf = m.group(2) or ''
            end = nxt_start(i + 1, g['e'] + hold + 0.22)
            anim_end = round(min(end - 0.04, g['s'] + 0.42), 3)
            fmt = 'slot_machine_counter'
            items.append(dict(
                font='tech',
                caption_format=fmt,
                text='%s%s' % (m.group(1), suf),
                t0=round(g['s'], 3),
                t1=round(end, 3),
                x=x,
                y=safe_y,
                size=round(size * 1.35),
                color=highlight_colors[0],
                anim='slot',
                counter=[round(g['s'], 3), max(round(g['s'] + 0.1, 3), anim_end), 0, val, suf],
                glow=True,
                shadow=True,
                fadeout=False,
            ))
            last_fmt = fmt; fmt_counts[fmt] += 1; i += 1; chunk_idx += 1
            continue

        # 2) Asymmetric 3-line kinetic stack (clamped inside locked safe zone 1280..1520)
        if in_stack and i + 2 < len(groups) and last_fmt != 'asymmetric_bento_stack':
            tri = groups[i:i + 3]
            end = nxt_start(i + 3, tri[-1]['e'] + hold)
            fmt = 'asymmetric_bento_stack'
            xs = [round(x - 95), round(x + 35), round(x - 55)]
            ys = [max(1285, safe_y - 84), safe_y, min(1515, safe_y + 78)]
            szs = [round(size * 1.18), round(size * 0.98), round(size * 0.86)]
            fonts_seq = ['impact', 'clean', 'editorial']
            cols = [highlight_colors[0], color, '#EDE6DE']
            for row, tok in enumerate(tri):
                items.append(dict(
                    font=fonts_seq[row],
                    caption_format=fmt,
                    text=tok['w'].upper() if row == 0 else tok['w'],
                    t0=round(tok['s'], 3),
                    t1=round(end, 3),
                    x=xs[row],
                    y=ys[row],
                    size=szs[row],
                    color=cols[row],
                    anim='rise',
                    glow=(row == 0),
                    shadow=True,
                    fadeout=False,
                ))
            last_fmt = fmt; fmt_counts[fmt] += 1; i += 3; chunk_idx += 1
            continue

        # 3) Word-by-word glitch box after vocal pauses (2–3 word phrase, zero orphan)
        if gap_before >= 0.45 and i + 1 < len(groups) and last_fmt != 'whisper_glitch_box':
            take_g = 3 if (i + 2 < len(groups) and (groups[i + 2]['s'] - groups[i + 1]['e']) < 0.45 and len(groups[i]['w']) + len(groups[i + 1]['w']) <= 14) else 2
            span = groups[i:i + take_g]
            end = nxt_start(i + take_g, span[-1]['e'] + hold + 0.15)
            fmt = 'whisper_glitch_box'
            txt_s = ' '.join(tok['w'] for tok in span)
            wf, ws = _word_emphasis_vectors(txt_s.split(), kw_set)
            items.append(dict(
                font='tech',
                word_fonts=wf,
                word_scales=ws,
                caption_format=fmt,
                text=txt_s,
                t0=round(span[0]['s'], 3),
                t1=round(end, 3),
                x=x,
                y=safe_y,
                size=round(size * 0.80),
                color='#EDE6DE',
                highlight_color=highlight_colors[0],
                anim='glitch',
                pill='#14161D',
                pill_radius=0.22,
                pill_opacity=0.88,
                sfx='pop',
                fadeout=False,
            ))
            last_fmt = fmt; fmt_counts[fmt] += 1; i += take_g; chunk_idx += 1
            continue

        # Build natural 2–4 word phrase block around current position
        chunk = [groups[i]]
        max_take = 3
        while len(chunk) < max_take and (i + len(chunk)) < len(groups):
            nxt = groups[i + len(chunk)]
            if nxt['s'] - chunk[-1]['e'] >= 0.50:
                break
            cur_len = sum(len(c['w']) + 1 for c in chunk)
            nxt_len = len(nxt['w'])
            # Allow pushing up to 4 words if an orphan auxiliary trails cleanly
            if cur_len + nxt_len <= 24 or _is_weak_token(nxt['w']):
                chunk.append(nxt)
            else:
                break
            if NUM_RE.match(nxt['w'].rstrip('?!')) and len(chunk) >= 2:
                chunk.pop()
                break

        # If next token outside chunk would be orphaned as a single short/auxiliary word, pull it in!
        nxt_idx = i + len(chunk)
        if nxt_idx < len(groups):
            rem = len(groups) - nxt_idx
            nxt_w = groups[nxt_idx]['w']
            if rem == 1 and _is_weak_token(nxt_w) and (groups[nxt_idx]['s'] - chunk[-1]['e']) < 0.70:
                chunk.append(groups[nxt_idx])
                nxt_idx += 1

        end = nxt_start(nxt_idx, chunk[-1]['e'] + hold)
        txt_joined = ' '.join(tok['w'] for tok in chunk)
        split_ws = txt_joined.split()
        has_kw = any(_matches_kw(tok['w']) for tok in chunk) or any(('?' in tok['w'] or '!' in tok['w']) for tok in chunk)
        wf, ws = _word_emphasis_vectors(split_ws, kw_set)

        if has_kw:
            fmt = _pick_next_format(['keyword_spotlight_burst', 'tilted_pill_badge', 'graffiti_underline_strike'], last_fmt, fmt_counts)
            if fmt == 'tilted_pill_badge':
                items.append(dict(
                    font='impact',
                    word_fonts=wf,
                    word_scales=ws,
                    caption_format=fmt,
                    text=txt_joined,
                    t0=round(chunk[0]['s'], 3),
                    t1=round(end, 3),
                    x=x,
                    y=safe_y,
                    size=round(size * 0.94),
                    color='#FFFFFF',
                    pill=pill if (pill and pill.lower() != 'none') else '#2F3E2E',
                    tilt=-3.2 if chunk_idx % 2 == 0 else 3.0,
                    anim='pop',
                    sfx='pop',
                    fadeout=False,
                ))
            elif fmt == 'graffiti_underline_strike':
                items.append(dict(
                    font='clean',
                    word_fonts=wf,
                    word_scales=ws,
                    caption_format=fmt,
                    text=txt_joined,
                    t0=round(chunk[0]['s'], 3),
                    t1=round(end, 3),
                    x=x,
                    y=safe_y,
                    size=size,
                    color=color,
                    highlight_color=highlight_colors[chunk_idx % len(highlight_colors)],
                    wt=_flatten_wt(chunk),
                    underline='yellow' if chunk_idx % 2 == 0 else 'red',
                    anim='word_pop',
                    shadow=True,
                    sfx='pop',
                    fadeout=False,
                ))
            else:  # keyword_spotlight_burst: inline 1.35x keyword pop + underline
                items.append(dict(
                    font='clean',
                    word_fonts=wf,
                    word_scales=[round(s * 1.04, 2) if s > 1.1 else s for s in ws],
                    caption_format='keyword_spotlight_burst',
                    text=txt_joined,
                    t0=round(chunk[0]['s'], 3),
                    t1=round(end, 3),
                    x=x,
                    y=safe_y,
                    size=round(size * 1.02),
                    color=color,
                    highlight_color=highlight_colors[0],
                    wt=_flatten_wt(chunk),
                    underline='yellow',
                    anim='word_pop',
                    glow=True,
                    glow_color='#FFD600',
                    shadow=True,
                    sfx='pop',
                    fadeout=False,
                ))
        elif len(chunk) == 2 and fmt_counts['split_left_right_dialogue'] * 4 <= chunk_idx and chunk_idx % 5 == 3 and last_fmt != 'split_left_right_dialogue':
            a, b = chunk[0], chunk[1]
            fmt = 'split_left_right_dialogue'
            items.append(dict(
                font='clean',
                caption_format=fmt,
                text=a['w'],
                t0=round(a['s'], 3),
                t1=round(end, 3),
                x=round(x - 135),
                y=max(1285, safe_y - 38),
                size=round(size * 0.90),
                color='#EDE6DE',
                anim='pop',
                shadow=True,
                fadeout=False,
            ))
            items.append(dict(
                font='impact',
                caption_format=fmt,
                text=b['w'].upper(),
                t0=round(b['s'], 3),
                t1=round(end, 3),
                x=round(x + 135),
                y=min(1515, safe_y + 42),
                size=round(size * 1.08),
                color=highlight_colors[chunk_idx % len(highlight_colors)],
                anim='pop',
                glow=True,
                shadow=True,
                fadeout=False,
            ))
        else:
            conn_pool = ['word_by_word_pop', 'graffiti_underline_strike', 'tilted_pill_badge']
            fmt = _pick_next_format(conn_pool, last_fmt, fmt_counts)
            if fmt == 'tilted_pill_badge':
                items.append(dict(
                    font='clean',
                    word_fonts=wf,
                    caption_format=fmt,
                    text=txt_joined,
                    t0=round(chunk[0]['s'], 3),
                    t1=round(end, 3),
                    x=x,
                    y=safe_y,
                    size=round(size * 0.90),
                    color='#FFFFFF',
                    pill=pill if (pill and pill.lower() != 'none') else '#2F3E2E',
                    tilt=-3.0 if chunk_idx % 2 == 0 else 3.0,
                    anim='pop',
                    sfx='pop',
                    fadeout=False,
                ))
            elif fmt == 'graffiti_underline_strike':
                items.append(dict(
                    font='clean',
                    word_fonts=wf,
                    caption_format=fmt,
                    text=txt_joined,
                    t0=round(chunk[0]['s'], 3),
                    t1=round(end, 3),
                    x=x,
                    y=safe_y,
                    size=size,
                    color=color,
                    highlight_color=highlight_colors[chunk_idx % len(highlight_colors)],
                    wt=_flatten_wt(chunk),
                    underline='yellow' if chunk_idx % 2 == 0 else 'red',
                    anim='word_pop',
                    shadow=True,
                    fadeout=False,
                ))
            else:
                fmt = 'word_by_word_pop'
                items.append(dict(
                    font='clean',
                    word_fonts=wf,
                    caption_format=fmt,
                    text=txt_joined,
                    t0=round(chunk[0]['s'], 3),
                    t1=round(end, 3),
                    x=x,
                    y=safe_y,
                    size=size,
                    color=color,
                    highlight_color=highlight_colors[chunk_idx % len(highlight_colors)],
                    wt=_flatten_wt(chunk),
                    anim='word_pop',
                    glow=(chunk_idx % 3 == 0),
                    glow_color=highlight_colors[chunk_idx % len(highlight_colors)],
                    shadow=True,
                    fadeout=False,
                ))

        last_fmt = fmt
        fmt_counts[fmt] += 1
        i = nxt_idx
        chunk_idx += 1

    return items


def caption_items_v2(*args, **kwargs):
    """Alias for kz-kinetic-studio 8-format caption generator."""
    return caption_items_60_40(*args, **kwargs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('--from', dest='t0', type=float, required=True)
    ap.add_argument('--to', dest='t1', type=float, required=True)
    ap.add_argument('--mode', choices=('60-40', 'v2', 'classic'), default='60-40', help='80% kinetic subtitle choreography')
    ap.add_argument('--y', type=float, default=1380, help='Locked safe zone default y=1380 (1280..1520)')
    ap.add_argument('--x', type=float, default=540)
    ap.add_argument('--size', type=int, default=70)
    ap.add_argument('--pill', default='#2F3E2E', help='pill colour; "none" for plain captions with a soft shadow')
    ap.add_argument('--color', default='#FFFFFF')
    ap.add_argument('--hold', type=float, default=0.45, help='how long the last word of a run stays after it ends (s)')
    ap.add_argument('--keywords', nargs='*', help='optional key Kazakh words to force 1.35x burst + SFX')
    ap.add_argument('--merge', help='append the items to the "text" list of this edl.json')
    a = ap.parse_args()
    words = json.load(open(os.path.join(a.project, 'analysis', 'program_words.json'), encoding='utf-8'))
    if a.mode == 'classic':
        items = caption_items(words, a.t0, a.t1, a.y, a.x, a.size, a.pill, a.color, a.hold)
    else:
        items = caption_items_60_40(words, a.t0, a.t1, a.y, a.x, a.size, a.pill, a.color, hold=a.hold, keywords=a.keywords)
    if a.merge:
        edl = json.load(open(a.merge, encoding='utf-8'))
        edl.setdefault('text', []).extend(items)
        with open(a.merge, 'w', encoding='utf-8') as fh:
            json.dump(edl, fh, indent=1, ensure_ascii=False)
        sys.stderr.write('%d caption items (%s) appended to %s\n' % (len(items), a.mode, a.merge))
    else:
        sys.stdout.reconfigure(encoding='utf-8')
        print(json.dumps(items, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
