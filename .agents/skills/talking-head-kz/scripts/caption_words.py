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
    """Generate High-Edit 60/40 dynamic subtitles rotating cleanly across the 5 mastery styles:
    1) word_pop (~30%): 2-3 spoken words with active spring pop + #FFD600/#00E676 highlight
    2) rossark_pill (~10%): key term UI pill + sfx='pop' cue for ./soundeffects/pop.wav
    3) kinetic_stack (~10%): 3-line stacked Anton display typography for hooks/emphasis
    4) reanimate_counter (~5%): animated 0->N numeric counter when figures/years/% appear
    5) whisper_terminal (~5%): monospace typewriter reveal after pauses/intrigue beats
    """
    groups = _group_kz_words(words, t0, t1)
    if not groups:
        return []
    kw_set = {clean(k) for k in (keywords or []) if clean(k)}
    stacks = stack_windows or []
    items = []
    i = 0
    chunk_idx = 0
    while i < len(groups):
        g = groups[i]
        bare = g['w'].rstrip('?!')
        gap_before = (g['s'] - groups[i - 1]['e']) if i > 0 else 0.0

        # 3) kinetic_stack during explicit stack/hook windows
        in_stack = any(a - 0.05 <= g['s'] < b - 0.05 for a, b in stacks)
        if in_stack and i + 2 < len(groups):
            tri = groups[i:i + 3]
            end = min(t1, (groups[i + 3]['s'] if i + 3 < len(groups) else tri[-1]['e'] + hold))
            ys = [round(y - 96), round(y), round(y + 96)]
            szs = [round(size * 0.95), round(size * 1.28), round(size * 0.95)]
            cols = [color, highlight_colors[0], color]
            for row, tok in enumerate(tri):
                items.append(dict(
                    font='anton',
                    text=tok['w'].upper(),
                    t0=round(tok['s'], 3),
                    t1=round(end, 3),
                    x=x,
                    y=ys[row],
                    size=szs[row],
                    color=cols[row],
                    anim='rise',
                    glow=(row == 1),
                    fadeout=True,
                ))
            i += 3
            chunk_idx += 1
            continue

        # 4) reanimate_counter when numbers/percentages/years/currencies appear
        m = NUM_RE.match(bare)
        if m:
            raw_num = m.group(1).replace(',', '.')
            val = float(raw_num) if '.' in raw_num else int(raw_num)
            suf = m.group(2) or ''
            nxt_s = groups[i + 1]['s'] if i + 1 < len(groups) else None
            end = min(t1, nxt_s if nxt_s is not None and nxt_s - g['e'] < 0.6 else g['e'] + hold + 0.25)
            anim_end = round(min(end - 0.04, g['s'] + 0.42), 3)
            items.append(dict(
                font='anton',
                text='%s%s' % (m.group(1), suf),
                t0=round(g['s'], 3),
                t1=round(end, 3),
                x=x,
                y=round(y - 12),
                size=round(size * 1.35),
                color=highlight_colors[1],
                anim='pop',
                counter=[round(g['s'], 3), max(round(g['s'] + 0.1, 3), anim_end), 0, val, suf],
                glow=True,
                fadeout=False,
            ))
            i += 1
            chunk_idx += 1
            continue

        # 5) whisper_terminal after a dramatic pause or aside
        if gap_before >= 0.48 and i + 1 < len(groups):
            span = groups[i:i + 2]
            nxt_s = groups[i + 2]['s'] if i + 2 < len(groups) else None
            end = min(t1, nxt_s if nxt_s is not None and nxt_s - span[-1]['e'] < 0.6 else span[-1]['e'] + hold + 0.15)
            items.append(dict(
                font='mono',
                text=' '.join(tok['w'] for tok in span),
                t0=round(span[0]['s'], 3),
                t1=round(end, 3),
                x=x,
                y=y,
                size=round(size * 0.78),
                color='#EDE6DE',
                highlight_color=highlight_colors[1],
                anim='terminal',
                pill='#0B0B0B',
                pill_radius=0.18,
                pill_opacity=0.90,
                fadeout=False,
            ))
            i += 2
            chunk_idx += 1
            continue

        # 2) rossark_pill for key nouns / emphasized beats (~20% of subtitle phrases => ~10% screen share)
        bare_tokens = bare.split()
        is_key = any(tok in kw_set for tok in bare_tokens) or (len(bare) >= 7 and chunk_idx % 5 == 2)
        if is_key:
            nxt_s = groups[i + 1]['s'] if i + 1 < len(groups) else None
            end = min(t1, nxt_s if nxt_s is not None and nxt_s - g['e'] < 0.55 else g['e'] + hold)
            items.append(dict(
                font='sub',
                text=g['w'],
                t0=round(g['s'], 3),
                t1=round(end, 3),
                x=x,
                y=y,
                size=size,
                color=color,
                pill=pill if (pill and pill.lower() != 'none') else '#2F3E2E',
                anim='pop',
                sfx='pop',
                fadeout=False,
            ))
            i += 1
            chunk_idx += 1
            continue

        # 1) word_pop default (2-3 spoken words, active word pops + lights up #FFD600 or #00E676)
        take = 3 if (i + 2 < len(groups) and len(groups[i]['w']) + len(groups[i + 1]['w']) <= 12) else 2
        chunk = groups[i:min(i + take, len(groups))]
        # Stop before any number, keyword, pause-terminal beat, or kinetic_stack window so they keep their own style
        for k in range(1, len(chunk)):
            bk = chunk[k]['w'].rstrip('?!')
            gap_k = chunk[k]['s'] - chunk[k - 1]['e']
            in_stack_k = any(a - 0.05 <= chunk[k]['s'] < b - 0.05 for a, b in stacks)
            is_kw_k = any(tok in kw_set for tok in bk.split())
            if NUM_RE.match(bk) or is_kw_k or gap_k >= 0.48 or in_stack_k:
                chunk = chunk[:k]
                break
        nxt_idx = i + len(chunk)
        nxt_s = groups[nxt_idx]['s'] if nxt_idx < len(groups) else None
        end = min(t1, nxt_s if nxt_s is not None and nxt_s - chunk[-1]['e'] < 0.5 else chunk[-1]['e'] + hold)
        # Flatten timing per whitespace-split word so wt aligns 1:1 with TextAnim.words
        wt = []
        for tok in chunk:
            subwords = tok['w'].split()
            dt = max(0.04, (tok['e'] - tok['s']) / max(len(subwords), 1))
            for si in range(len(subwords)):
                wt.append(round(tok['s'] + si * dt, 3))
        items.append(dict(
            font='sub',
            text=' '.join(tok['w'] for tok in chunk),
            t0=round(chunk[0]['s'], 3),
            t1=round(end, 3),
            x=x,
            y=y,
            size=size,
            color=color,
            highlight_color=highlight_colors[chunk_idx % len(highlight_colors)],
            wt=wt,
            anim='word_pop',
            shadow=True,
            fadeout=False,
        ))
        i += len(chunk)
        chunk_idx += 1

    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('--from', dest='t0', type=float, required=True)
    ap.add_argument('--to', dest='t1', type=float, required=True)
    ap.add_argument('--mode', choices=('60-40', 'classic'), default='60-40', help='60-40 rotates all 5 dynamic subtitle styles')
    ap.add_argument('--y', type=float, default=1290)
    ap.add_argument('--x', type=float, default=540)
    ap.add_argument('--size', type=int, default=76)
    ap.add_argument('--pill', default='#2F3E2E', help='pill colour; "none" for plain captions with a soft shadow')
    ap.add_argument('--color', default='#FFFFFF')
    ap.add_argument('--hold', type=float, default=0.45, help='how long the last word of a run stays after it ends (s)')
    ap.add_argument('--keywords', nargs='*', help='optional key Kazakh words to force rossark_pill + pop SFX')
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
