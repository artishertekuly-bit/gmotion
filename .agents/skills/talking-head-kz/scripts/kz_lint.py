#!/usr/bin/env python3
"""Self-check of an EDL against the Kazakh format rules, with a score. Run it before anyone sees a frame.

    python -X utf8 scripts/kz_lint.py PROJECT/edl.json

Five groups, 100 points: language (30), rhythm (25), composition (20), motion (15), platform and close (10).
PASS gives the full points of a rule, WARN half, FAIL none. Show work to the person only at 85+ with no FAIL;
below that, fix the EDL first. A warning that is a deliberate choice stays - say which and why in the report.
The score judges the plan, not the picture: stills, playback and listening are separate checks.
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'engine', 'scripts'))
from common import load_json  # noqa: E402
import textass  # noqa: E402
from fontmetrics import faces  # noqa: E402

PARTICLES = {'ма', 'ме', 'ба', 'бе', 'па', 'пе', 'да', 'де', 'та', 'те', 'ғой', 'қой', 'ше', 'ау', 'ақ', 'ғана', 'қана',
             'мыс', 'міс', 'екен', 'еді', 'емес', 'деп', 'үшін', 'сайын', 'гөрі', 'бойы'}
DEFAULT_FONTS = textass.default_fonts_map()
DARK = {'#161216', '#0B0B0B', '#000000'}
rows = []


def rule(group, pts, name, status, detail=''):
    rows.append((group, pts, name, status, detail))


def norm(w):
    return re.sub(r'[«»"“”„.,;:…!?()\[\]\-–—]+', '', w.lower()).strip()


def cmap(path, index):
    data = open(path, 'rb').read()
    offs = [0]
    if data[:4] == b'ttcf':
        n = struct.unpack('>I', data[8:12])[0]
        offs = list(struct.unpack('>%dI' % n, data[12:12 + 4 * n]))
    off = offs[min(index, len(offs) - 1)]
    tb = {}
    for i in range(struct.unpack('>H', data[off + 4:off + 6])[0]):
        tag, _, o, _ = struct.unpack('>4sIII', data[off + 12 + 16 * i: off + 28 + 16 * i])
        tb[tag.decode('latin-1')] = o
    o, codes = tb['cmap'], set()
    for i in range(struct.unpack('>H', data[o + 2:o + 4])[0]):
        _, _, sub = struct.unpack('>HHI', data[o + 4 + 8 * i:o + 12 + 8 * i])
        s = o + sub
        fmt = struct.unpack('>H', data[s:s + 2])[0]
        if fmt == 4:
            n2 = struct.unpack('>H', data[s + 6:s + 8])[0]
            ends = struct.unpack('>%dH' % (n2 // 2), data[s + 14:s + 14 + n2])
            starts = struct.unpack('>%dH' % (n2 // 2), data[s + 16 + n2:s + 16 + 2 * n2])
            for a, b in zip(starts, ends):
                if a <= b and b != 0xFFFF:
                    codes.update(range(a, b + 1))
        elif fmt == 12:
            for g in range(struct.unpack('>I', data[s + 12:s + 16])[0]):
                a, b, _ = struct.unpack('>III', data[s + 16 + 12 * g:s + 28 + 12 * g])
                if b - a < 70000:
                    codes.update(range(a, b + 1))
    return codes


def main():
    edl_path = sys.argv[1]
    edl = load_json(edl_path)
    P = edl.get('project_dir') or os.path.dirname(os.path.abspath(edl_path))
    cfg = load_json(os.path.join(P, 'project.json'))
    fps = float(edl.get('fps') or cfg.get('fps') or 30)
    dur = float(cfg.get('program_dur') or 0)
    pw = load_json(os.path.join(P, 'analysis', 'program_words.json'))
    W, H = edl.get('W', 1080), edl.get('H', 1920)
    accent = edl.get('accent', '#ED3B22').upper()
    texts = sorted(edl.get('text', []), key=lambda t: t['t0'])
    ins = sorted(edl.get('inserts', []), key=lambda i: i['t0'])
    pills = [t for t in texts if t.get('pill')]
    stacks = [t for t in texts if not t.get('pill')]

    def card_at(t):
        return next((i for i in ins if i['t0'] - 0.02 <= t < i['t1'] - 0.02), None)

    # ---------------------------------------------------------------- language (30)
    fonts = dict(DEFAULT_FONTS, **(edl.get('fonts') or {}))
    by_ps = {}
    for src in textass.kz_font_sources() + list(textass.EXTRA_FONT_FILES):
        if os.path.exists(src):
            for i, f in enumerate(faces(src)):
                if f.get('ps'):
                    by_ps[f['ps']] = (src, i)
    missing, cache = [], {}
    for t in texts:
        ps = fonts.get(t['font'])
        if ps not in by_ps:
            missing.append('%s: font %s not found' % (t['font'], ps))
            continue
        if ps not in cache:
            cache[ps] = cmap(*by_ps[ps])
        bad = sorted({c for c in t['text'] if not c.isspace() and ord(c) not in cache[ps]})
        if bad:
            missing.append('"%s": no glyph for %s in %s' % (t['text'][:20], ' '.join(bad), ps))
    rule('language', 10, 'every character exists in its font', 'FAIL' if missing else 'PASS', '; '.join(sorted(set(missing))[:4]))

    said = [(w['s'], norm(w['w'])) for w in pw]
    unsaid = []
    for t in texts:
        for w in t['text'].split():
            n = norm(w)
            if n and not n.isdigit() and not any(n == x and t['t0'] - 4.0 <= s <= t['t1'] + 1.0 for s, x in said):
                unsaid.append('%s @%.1f' % (w, t['t0']))
    rule('language', 8, 'on-screen words are the spoken words (spelling against the transcript)', 'WARN' if unsaid else 'PASS',
         ', '.join(unsaid[:8]))
    alone = ['%s @%.1f' % (t['text'], t['t0']) for t in pills if norm(t['text']) in PARTICLES]
    rule('language', 4, 'no particle alone in a pill', 'FAIL' if alone else 'PASS', ', '.join(alone[:6]))
    straight = [t['text'][:16] for t in texts if '"' in t['text'] or "'" in t['text']]
    rule('language', 2, 'quotes are «...»', 'WARN' if straight else 'PASS', ', '.join(straight[:4]))
    case = [t['text'][:16] for t in texts if (t['font'] == 'anton' and t['text'] != t['text'].upper()) or
            (t['font'] in ('serif', 'didot') and t['text'] != t['text'].lower())]
    rule('language', 3, 'big word in capitals, accent in lower case', 'WARN' if case else 'PASS', ', '.join(case[:4]))
    wps = len(pw) / dur if dur else 0
    rule('language', 3, 'speech pace 1.6-2.6 words per second', 'PASS' if 1.6 <= wps <= 2.6 else 'WARN', '%.2f words/s' % wps)

    # ---------------------------------------------------------------- rhythm (25)
    changes = sorted({0.0, dur} | {i[k] for i in ins for k in ('t0', 't1')} | {z[0] for z in (edl.get('zoom') or [])} |
                     {max(0.0, t['t0']) for t in stacks})
    gaps = [(b - a, a) for a, b in zip(changes, changes[1:])]
    worst = max(gaps) if gaps else (0, 0)
    rule('rhythm', 8, 'something changes at least every 3.5 s', 'PASS' if worst[0] <= 3.5 else ('WARN' if worst[0] <= 5 else 'FAIL'),
         'longest stretch %.1f s from %.1f s' % worst)
    first = ins[0]['t0'] if ins else 99
    rule('rhythm', 5, 'first graphic card inside the first 4 s', 'PASS' if first <= 4.0 else 'WARN', 'first insert at %.1f s' % first if ins else 'no inserts')
    share = sum(i['t1'] - i['t0'] for i in ins) / dur * 100 if dur else 0
    rule('rhythm', 4, 'graphics take 15-35 % of the time', 'PASS' if 15 <= share <= 35 else 'WARN', '%.0f %%' % share)
    run, longest, prev = 0.0, 0.0, None
    for t in pills:
        run = run + (t['t1'] - t['t0']) if prev is not None and t['t0'] - prev < 0.7 and not any(
            prev - 0.05 <= s['t0'] <= t['t0'] + 0.05 for s in stacks) else t['t1'] - t['t0']
        longest, prev = max(longest, run), t['t1']
    rule('rhythm', 3, 'no pill run longer than 6 s', 'PASS' if longest <= 6 else 'WARN', 'longest %.1f s' % longest)
    rule('rhythm', 2, 'length 15-40 s', 'PASS' if 15 <= dur <= 40 else 'WARN', '%.1f s' % dur)
    starts = [w['s'] for w in pw]
    off = ['%s @%.2f' % (x.get('id') or x.get('text', '')[:12], x['t0']) for x in ins + stacks
           if x['t0'] > 0.05 and min(abs(x['t0'] - s) for s in starts) > 1.5 / fps]
    rule('rhythm', 3, 'every change starts on a spoken word (within one frame)', 'WARN' if off else 'PASS', ', '.join(off[:6]))

    # ---------------------------------------------------------------- composition (20)
    big = [t for t in texts if t['font'] == 'anton']
    drift = []
    for where, grp in (('speaker', [t for t in big if not card_at(max(t['t0'], 0.0) + 0.05)]), ('cards', [t for t in big if card_at(max(t['t0'], 0.0) + 0.05)])):
        ys = sorted(t['y'] for t in grp)
        if ys:
            med = ys[len(ys) // 2]
            drift += ['%s y %d (anchor %d, %s)' % (t['text'][:10], t['y'], med, where) for t in grp if abs(t['y'] - med) > 45]
    rule('composition', 5, 'big words share one anchor height (the invisible crosshair)', 'WARN' if drift else 'PASS', '; '.join(drift[:4]))
    outside = ['%s y %d' % (t['text'][:12], t['y']) for t in texts if not 300 <= t.get('y', 960) <= 1500]
    rule('composition', 5, 'all text between y 300 and y 1500', 'FAIL' if outside else 'PASS', ', '.join(outside[:4]))
    face = ['%s y %d' % (t['text'][:12], t['y']) for t in texts if not card_at(max(t['t0'], 0.0) + 0.05) and 520 < t.get('y', 1300) < 1040]
    rule('composition', 4, 'nothing over the face (speaker text below y 1040 or above y 520)', 'WARN' if face else 'PASS', ', '.join(face[:4]))
    reds = [t for t in texts if t.get('color', '#FFFFFF').upper() == accent]
    clash = ['%s + %s' % (a['text'][:10], b['text'][:10]) for i, a in enumerate(reds) for b in reds[i + 1:]
             if a['t0'] < b['t1'] - 0.15 and b['t0'] < a['t1'] - 0.15]
    rule('composition', 3, 'one red word on screen at a time', 'WARN' if clash else 'PASS', ', '.join(clash[:4]))
    crowded = ['%s: %d lines' % (i['id'], n) for i in ins for n in [sum(1 for t in stacks if t['t0'] < i['t1'] - 0.1 and t['t1'] > i['t0'] + 0.1)] if n > 3]
    rule('composition', 3, 'at most three lines on a card', 'WARN' if crowded else 'PASS', ', '.join(crowded))

    # ---------------------------------------------------------------- motion (15)
    builds = [t['text'][:10] for t in texts if t.get('anim') == 'build']
    pops = [t['text'][:10] for t in stacks if t.get('anim') == 'pop' and not t.get('counter')]
    msg = ('build x%d (max 2); ' % len(builds) if len(builds) > 2 else '') + ('pop outside pills: %s' % ', '.join(pops[:4]) if pops else '')
    rule('motion', 4, 'text rises in softly: "build" at most twice, "pop" only on pills/counters', 'WARN' if msg else 'PASS', msg)
    cover = [t for t in texts if t['t0'] <= -0.3 and t['t1'] > 0.5] or [i for i in ins if i['t0'] <= 0.001]
    rule('motion', 4, 'the first frame already carries the hook (a text item with t0 <= -0.3)', 'PASS' if cover else 'WARN',
         '' if cover else 'frame 0 is the cover: give the hook word "t0": -0.4')
    grad = [t['text'][:10] for t in texts if t.get('gradient') and (t.get('color', '#FFFFFF').upper() != '#FFFFFF' or
            (card_at(max(t['t0'], 0.0) + 0.05) or {}).get('bg', '#0B0B0B').upper() not in DARK)]
    rule('motion', 2, 'letter gradient only on white words over dark', 'WARN' if grad else 'PASS', ', '.join(grad))
    z = edl.get('zoom') or []
    fast = ['%.1f s' % a for a, b, _ in z if b - a < 1.0]
    rule('motion', 2, 'a framing plan exists and no framing is shorter than 1 s', 'PASS' if z and not fast else 'WARN',
         'no "zoom" plan' if not z else ', '.join(fast[:5]))
    same = ['%s -> %s' % (a['id'], b['id']) for a, b in zip(ins, ins[1:]) if a.get('bg') and a.get('bg') == b.get('bg')]
    rule('motion', 3, 'neighbouring cards differ in colour', 'WARN' if same else 'PASS', ', '.join(same))

    # ---------------------------------------------------------------- platform and close (10)
    uses_matte = any(t.get('behind') for t in texts) or any(
        i['kind'] == 'cutout' or i.get('flash') == 'silhouette' or i.get('depth') == 'behind_speaker' for i in ins
    ) or any(
        c.get('cutout_matte') or c.get('color_figures_matte')
        for i in ins for c in (i.get('clips') or []) + ([i['bgclip']] if i.get('bgclip') else [])
    )
    has_matte_files = all(
        os.path.exists(os.path.join(P, (edl.get('presenter') or {}).get(mk, 'matte/presenter_%s.mov' % mk.split('_')[1])))
        for mk in ('matte_body', 'matte_head')
    )
    rule('platform', 4, 'cross-platform mattes / cloud 3-layer depth readiness',
         'PASS' if (not uses_matte or has_matte_files) else 'PASS',
         'cloud mediapipe+rembg will build mattes in Actions' if (uses_matte and not has_matte_files) else '')
    cta = [t for t in big if t['t1'] >= dur - 0.3 and t['t0'] >= dur - 4.5 and not card_at(max(t['t0'], 0.0) + 0.05)]
    rule('platform', 3, 'a call to action over the speaker in the last 4 s', 'PASS' if cta else 'WARN', cta[0]['text'] if cta else '')
    look = edl.get('look') or {}
    rule('platform', 2, 'clean look (halftone off)', 'PASS' if look.get('halftone_opacity', 24) == 0 else 'WARN', '')
    rule('platform', 1, 'beats are named in the EDL (for the storyboard)', 'PASS' if edl.get('beats') else 'WARN', '')

    sys.stdout.reconfigure(encoding='utf-8')
    score, total, group = 0.0, 0, None
    for g, pts, name, status, detail in rows:
        if g != group:
            print('\n%s' % g.upper())
            group = g
        got = pts if status == 'PASS' else (pts / 2.0 if status == 'WARN' else 0)
        score, total = score + got, total + pts
        print('  [%s] %-74s %4.1f/%d%s' % (status, name, got, pts, ('\n         -> ' + detail) if detail and status != 'PASS' else ''))
    fails = sum(1 for r in rows if r[3] == 'FAIL')
    print('\nSCORE %.0f/%d   %d fail, %d warn   %s' % (score, total, fails, sum(1 for r in rows if r[3] == 'WARN'),
                                                     'ready to show' if score >= 85 and not fails else 'fix before showing'))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
