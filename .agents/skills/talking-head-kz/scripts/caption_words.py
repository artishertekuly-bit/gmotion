#!/usr/bin/env python3
"""Single-word "pill" captions for a stretch of the talk (the connective speech between the big moments).

    python -X utf8 scripts/caption_words.py PROJECT_DIR --from 2.30 --to 9.00 [--y 1290] [--size 76]
                                            [--pill "#2F3E2E"] [--color "#FFFFFF"] [--merge OUT_EDL]

Reads analysis/program_words.json (program seconds) and prints one EDL text item per caption: each word alone,
lower case, on a rounded pill, replaced by the next word the moment that one is spoken.

Kazakh rules built in:
  * a postpositive particle never stands alone - it joins the word before it ("келдің бе", "жақсы ғой", "сен де"),
    or the word after it when it opens the stretch ("деп сұрайсың");
  * a word of 1-2 letters joins the word after it ("ал сен", "я бұл") unless it is one of those particles;
  * punctuation is dropped except "?" and "!"; a number keeps its digits.
Without --merge nothing is written: paste the printed items into the EDL "text" list. With --merge the items are
appended to that EDL's "text" (the file must already exist; a copy is NOT made - version the EDL yourself first).
"""
import argparse
import json
import os
import re
import sys

PARTICLES = {'ма', 'ме', 'ба', 'бе', 'па', 'пе', 'да', 'де', 'та', 'те', 'ғой', 'қой', 'ше', 'ау', 'ақ', 'ғана', 'қана',
             'мыс', 'міс', 'екен', 'еді', 'емес', 'деп', 'үшін', 'сайын', 'гөрі', 'бойы'}


def clean(w):
    w = w.strip().lower()
    w = re.sub(r'[«»"“”„.,;:…()\[\]]+', '', w)
    return w.strip('-–— ')


def caption_items(words, t0, t1, y=1290, x=540, size=76, pill='#2F3E2E', color='#FFFFFF', hold=0.45):
    """EDL text items for the words spoken in [t0, t1): one caption per word, particles and tiny words joined."""
    ws = [dict(s=w['s'], e=w['e'], w=clean(w['w'])) for w in words if t0 - 0.02 <= w['s'] < t1 - 0.02]
    ws = [w for w in ws if w['w']]
    groups = []
    for w in ws:
        bare = w['w'].rstrip('?!')
        if groups and groups[-1].get('wait'):                   # the item before is waiting for this word
            groups[-1]['w'] += ' ' + w['w']
            groups[-1]['e'] = w['e']
            groups[-1]['wait'] = False
        elif groups and bare in PARTICLES:                      # a particle joins the word before it
            groups[-1]['w'] += ' ' + w['w']
            groups[-1]['e'] = w['e']
        else:                                                   # a tiny word, or a particle that opens the stretch, waits for the next
            groups.append(dict(s=w['s'], e=w['e'], w=w['w'], wait=bare in PARTICLES or (len(bare) <= 2 and not bare.isdigit())))
    items = []
    for i, g in enumerate(groups):
        nxt = groups[i + 1]['s'] if i + 1 < len(groups) else None
        end = min(t1, nxt if nxt is not None and nxt - g['e'] < 0.6 else g['e'] + hold)
        it = dict(font='sub', text=g['w'], t0=round(g['s'], 3), t1=round(end, 3), x=x, y=y, size=size, color=color, anim='pop', fadeout=False)
        if pill and pill.lower() != 'none':
            it['pill'] = pill
        else:
            it['shadow'] = True
        items.append(it)
    return items


NUM_RE = re.compile(r'^(\d+(?:[.,]\d+)?)\s*(%|₸|\$|€|x|х|k|к|м|млн|ж)?$', re.IGNORECASE)


def _group_kz_words(words, t0, t1):
    """Normalize and attach Kazakh postpositions/particles to their preceding word."""
    ws = [dict(s=w['s'], e=w['e'], w=clean(w['w'])) for w in words if t0 - 0.02 <= w['s'] < t1 - 0.02]
    ws = [w for w in ws if w['w']]
    groups = []
    for w in ws:
        bare = w['w'].rstrip('?!')
        if groups and groups[-1].get('wait'):
            groups[-1]['w'] += ' ' + w['w']
            groups[-1]['e'] = w['e']
            groups[-1]['wait'] = False
        elif groups and bare in PARTICLES:
            groups[-1]['w'] += ' ' + w['w']
            groups[-1]['e'] = w['e']
        else:
            groups.append(dict(
                s=w['s'],
                e=w['e'],
                w=w['w'],
                wait=bare in PARTICLES or (len(bare) <= 2 and not bare.isdigit()),
            ))
    return groups


CAPTION_FORMATS_V2 = (
    'word_by_word_pop',
    'graffiti_underline_strike',
    'tilted_pill_badge',
    'asymmetric_bento_stack',
    'split_left_right_dialogue',
    'behind_head_giant',
    'slot_machine_counter',
    'whisper_glitch_box',
)


def _flatten_wt(chunk):
    wt = []
    for tok in chunk:
        subwords = tok['w'].split()
        dt = max(0.04, (tok['e'] - tok['s']) / max(len(subwords), 1))
        for si in range(len(subwords)):
            wt.append(round(tok['s'] + si * dt, 3))
    return wt


def _mixed_word_fonts(words_list, base_role='clean', accent_role='editorial', keywords_set=None):
    """Build per-word font role list so one sentence blends contrasting font roles naturally."""
    kws = keywords_set or set()
    if len(words_list) <= 1:
        return [accent_role if (words_list and words_list[0].rstrip('?!') in kws) else base_role] * len(words_list)
    roles = []
    best_idx = max(range(len(words_list)), key=lambda k: (100 if words_list[k].rstrip('?!') in kws else len(words_list[k])))
    for k, w in enumerate(words_list):
        bare = w.rstrip('?!')
        if k == best_idx or bare in kws:
            roles.append(accent_role)
        elif k % 3 == 1 and len(bare) >= 5:
            roles.append('impact')
        else:
            roles.append(base_role)
    return roles


def _pick_next_format(candidates, last_format, counts):
    pool = [c for c in candidates if c != last_format] or list(candidates)
    return min(pool, key=lambda c: (counts.get(c, 0), pool.index(c)))


def caption_items_60_40(
    words,
    t0,
    t1,
    y=1290,
    x=540,
    size=72,
    pill='#2F3E2E',
    color='#FFFFFF',
    highlight_colors=('#FFD600', '#00E676'),
    hold=0.42,
    keywords=None,
    stack_windows=None,
):
    """Mastery V2: Rotate all 8 Geometric Subtitle Formats + Mixed-Font Sentences across [t0, t1)."""
    groups = _group_kz_words(words, t0, t1)
    if not groups:
        return []
    kw_set = {clean(k) for k in (keywords or []) if clean(k)}
    stacks = stack_windows or []
    items = []
    i = 0
    chunk_idx = 0
    last_fmt = None
    fmt_counts = {f: 0 for f in CAPTION_FORMATS_V2}

    def nxt_start(idx, default_end):
        ns = groups[idx]['s'] if idx < len(groups) else None
        if ns is not None and ns - groups[idx - 1]['e'] < 0.6:
            return min(t1, ns)
        return min(t1, default_end)

    while i < len(groups):
        g = groups[i]
        bare = g['w'].rstrip('?!')
        gap_before = (g['s'] - groups[i - 1]['e']) if i > 0 else 0.0
        in_stack = any(a - 0.05 <= g['s'] < b - 0.05 for a, b in stacks)

        # 7) slot_machine_counter on numeric tokens
        m = NUM_RE.match(bare)
        if m:
            raw_num = m.group(1).replace(',', '.')
            val = float(raw_num) if '.' in raw_num else int(raw_num)
            suf = m.group(2) or ''
            end = nxt_start(i + 1, g['e'] + hold + 0.25)
            anim_end = round(min(end - 0.04, g['s'] + 0.44), 3)
            fmt = 'slot_machine_counter'
            items.append(dict(
                font='tech',
                caption_format=fmt,
                text='%s%s' % (m.group(1), suf),
                t0=round(g['s'], 3),
                t1=round(end, 3),
                x=x,
                y=round(y - 14),
                size=round(size * 1.38),
                color=highlight_colors[1],
                anim='slot',
                counter=[round(g['s'], 3), max(round(g['s'] + 0.1, 3), anim_end), 0, val, suf],
                glow=True,
                fadeout=False,
            ))
            last_fmt = fmt; fmt_counts[fmt] += 1; i += 1; chunk_idx += 1
            continue

        # 1) asymmetric_bento_stack in stack/emphasis windows
        if in_stack and i + 2 < len(groups):
            tri = groups[i:i + 3]
            end = nxt_start(i + 3, tri[-1]['e'] + hold)
            fmt = 'asymmetric_bento_stack'
            xs = [round(x - 110), round(x + 40), round(x - 70)]
            ys = [round(y - 108), round(y), round(y + 92)]
            szs = [round(size * 1.32), round(size * 1.05), round(size * 0.88)]
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
                    fadeout=True,
                ))
            last_fmt = fmt; fmt_counts[fmt] += 1; i += 3; chunk_idx += 1
            continue

        # 8) whisper_glitch_box after pauses / intrigue beats
        if gap_before >= 0.45 and i + 1 < len(groups):
            span = groups[i:i + 2]
            end = nxt_start(i + 2, span[-1]['e'] + hold + 0.15)
            fmt = 'whisper_glitch_box'
            txt_s = ' '.join(tok['w'] for tok in span)
            items.append(dict(
                font='tech',
                caption_format=fmt,
                text=txt_s,
                t0=round(span[0]['s'], 3),
                t1=round(end, 3),
                x=x,
                y=y,
                size=round(size * 0.78),
                color='#EDE6DE',
                highlight_color=highlight_colors[1],
                anim='glitch',
                pill='#0B0B0B',
                pill_radius=0.18,
                pill_opacity=0.92,
                barcode=True,
                sfx='glitch',
                fadeout=False,
            ))
            last_fmt = fmt; fmt_counts[fmt] += 1; i += 2; chunk_idx += 1
            continue

        # Keyword / strong noun beats rotate among graffiti_underline_strike, tilted_pill_badge, behind_head_giant
        bare_tokens = bare.split()
        is_key = any(tok in kw_set for tok in bare_tokens) or (len(bare) >= 7 and chunk_idx % 4 == 2)
        if is_key:
            key_pool = ['tilted_pill_badge', 'graffiti_underline_strike']
            if fmt_counts['behind_head_giant'] * 3 <= chunk_idx + 1 and len(bare) <= 13:
                key_pool.append('behind_head_giant')
            fmt = _pick_next_format(key_pool, last_fmt, fmt_counts)
            end = nxt_start(i + 1, g['e'] + hold)
            if fmt == 'behind_head_giant':
                items.append(dict(
                    font='impact',
                    caption_format=fmt,
                    text=g['w'].upper(),
                    t0=round(g['s'], 3),
                    t1=round(end + 0.25, 3),
                    x=540,
                    y=560,
                    size=235,
                    color='#EDE6DE',
                    behind=True,
                    anim='rise',
                    glow=False,
                    fadeout=True,
                ))
            elif fmt == 'graffiti_underline_strike':
                txt_u = g['w']
                u_words = txt_u.split()
                items.append(dict(
                    font='clean',
                    word_fonts=_mixed_word_fonts(u_words, 'clean', 'editorial', kw_set) if len(u_words) > 1 else None,
                    caption_format=fmt,
                    text=txt_u,
                    t0=round(g['s'], 3),
                    t1=round(end, 3),
                    x=x,
                    y=y,
                    size=round(size * 1.06),
                    color=color,
                    underline='yellow' if chunk_idx % 2 == 0 else 'red',
                    anim='pop',
                    shadow=True,
                    fadeout=False,
                ))
            else:  # tilted_pill_badge
                items.append(dict(
                    font='impact',
                    caption_format=fmt,
                    text=g['w'],
                    t0=round(g['s'], 3),
                    t1=round(end, 3),
                    x=x,
                    y=y,
                    size=round(size * 0.96),
                    color='#FFFFFF',
                    pill=pill if (pill and pill.lower() != 'none') else '#2F3E2E',
                    tilt=-4.0 if chunk_idx % 2 == 0 else 3.5,
                    anim='pop',
                    sfx='pop',
                    fadeout=False,
                ))
            last_fmt = fmt; fmt_counts[fmt] += 1; i += 1; chunk_idx += 1
            continue

        # Multi-word connective stretch rotates: word_by_word_pop, split_left_right_dialogue, graffiti_underline_strike, asymmetric_bento_stack
        if i + 1 < len(groups) and fmt_counts['split_left_right_dialogue'] * 4 <= chunk_idx and chunk_idx % 5 == 3:
            a, b = groups[i], groups[i + 1]
            end = nxt_start(i + 2, b['e'] + hold)
            fmt = 'split_left_right_dialogue'
            items.append(dict(
                font='clean',
                caption_format=fmt,
                text=a['w'],
                t0=round(a['s'], 3),
                t1=round(end, 3),
                x=round(x - 150),
                y=round(y - 46),
                size=round(size * 0.92),
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
                x=round(x + 150),
                y=round(y + 46),
                size=round(size * 1.10),
                color=highlight_colors[chunk_idx % len(highlight_colors)],
                anim='pop',
                glow=True,
                fadeout=False,
            ))
            last_fmt = fmt; fmt_counts[fmt] += 1; i += 2; chunk_idx += 1
            continue

        take = 3 if (i + 2 < len(groups) and len(groups[i]['w']) + len(groups[i + 1]['w']) <= 13) else 2
        chunk = groups[i:min(i + take, len(groups))]
        for k in range(1, len(chunk)):
            bk = chunk[k]['w'].rstrip('?!')
            gap_k = chunk[k]['s'] - chunk[k - 1]['e']
            in_stack_k = any(a - 0.05 <= chunk[k]['s'] < b - 0.05 for a, b in stacks)
            is_kw_k = any(tok in kw_set for tok in bk.split())
            if NUM_RE.match(bk) or is_kw_k or gap_k >= 0.45 or in_stack_k:
                chunk = chunk[:k]
                break
        nxt_idx = i + len(chunk)
        end = nxt_start(nxt_idx, chunk[-1]['e'] + hold)
        txt_joined = ' '.join(tok['w'] for tok in chunk)
        split_ws = txt_joined.split()
        wf = _mixed_word_fonts(split_ws, 'clean', 'editorial', kw_set) if len(split_ws) >= 2 else None

        if len(chunk) >= 2 and chunk_idx % 4 == 1 and last_fmt != 'graffiti_underline_strike':
            fmt = 'graffiti_underline_strike'
            items.append(dict(
                font='clean',
                word_fonts=wf,
                caption_format=fmt,
                text=txt_joined,
                t0=round(chunk[0]['s'], 3),
                t1=round(end, 3),
                x=x,
                y=y,
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
                y=y,
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
        last_fmt = fmt; fmt_counts[fmt] += 1; i += len(chunk); chunk_idx += 1

    return items


def caption_items_v2(*args, **kwargs):
    """Alias for Mastery V2 8-format caption generator."""
    return caption_items_60_40(*args, **kwargs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('--from', dest='t0', type=float, required=True)
    ap.add_argument('--to', dest='t1', type=float, required=True)
    ap.add_argument('--mode', choices=('60-40', 'v2', 'classic'), default='60-40', help='60-40 / v2 rotates all 8 geometric subtitle formats + mixed fonts')
    ap.add_argument('--y', type=float, default=1290)
    ap.add_argument('--x', type=float, default=540)
    ap.add_argument('--size', type=int, default=76)
    ap.add_argument('--pill', default='#2F3E2E', help='pill colour; "none" for plain captions with a soft shadow')
    ap.add_argument('--color', default='#FFFFFF')
    ap.add_argument('--hold', type=float, default=0.45, help='how long the last word of a run stays after it ends (s)')
    ap.add_argument('--keywords', nargs='*', help='optional key Kazakh words to force accent formats + SFX')
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
