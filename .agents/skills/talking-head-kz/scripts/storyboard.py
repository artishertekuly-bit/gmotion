#!/usr/bin/env python3
"""Numbered storyboard of an EDL, made from real renderer stills - show it and get a yes before sound and the full render.

    python -X utf8 scripts/storyboard.py PROJECT/edl.json [--out-dir PROJECT/qa/storyboard_v1] [--workers 2] [--cols 4]

One card per beat: number, beat name, time range, the words spoken in it, how the beat enters (transition), the
speaker framing and the planned sound cue. The numbers let the person say "the move from 4 into 5 does not work".
Beats come from the EDL's "beats" list ([{"n": 1, "name": "Хук", "t0": 0, "t1": 2.95}, ...]); without it they are
cut at every insert boundary and every long stretch of speaker is one beat.

Writes storyboard.png and storyboard.md (the same plan as a table) into the output folder.
Stills are not playback: say which moves were only seen as single frames.
"""
import argparse
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(os.path.dirname(HERE), 'engine', 'scripts')
sys.path.insert(0, ENGINE)
sys.path.insert(0, HERE)
from common import load_json  # noqa: E402
from sfx_from_edl import events_from_edl  # noqa: E402


def font(size, bold=False):
    windir = os.environ.get('WINDIR') or os.environ.get('SystemRoot') or ''
    for n in (('segoeuib.ttf', 'arialbd.ttf') if bold else ('segoeui.ttf', 'arial.ttf')):
        p = os.path.join(windir, 'Fonts', n)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def wrap(draw, text, f, width):
    lines, cur = [], ''
    for w in text.split():
        t = (cur + ' ' + w).strip()
        if draw.textlength(t, font=f) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def auto_beats(edl, dur):
    cuts = sorted({0.0, dur} | {round(i[k], 3) for i in edl.get('inserts', []) for k in ('t0', 't1')})
    beats = []
    for a, b in zip(cuts, cuts[1:]):
        if beats and b - a < 1.0:
            beats[-1]['t1'] = b
        else:
            beats.append(dict(t0=a, t1=b, name=''))
    for n, bt in enumerate(beats):
        bt['n'] = n + 1
    return beats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('edl')
    ap.add_argument('--out-dir')
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--cols', type=int, default=4)
    ap.add_argument('--plan-only', action='store_true', default=(os.name == 'nt'),
                    help='Build storyboard.md/.json + vector blueprint PNG without running heavy render_reel stills (default on Windows)')
    ap.add_argument('--render-stills', action='store_true',
                    help='Force rendering PNG stills via render_reel.py (use in Cloud Actions or machines with >16GB RAM)')
    a = ap.parse_args()
    do_render = bool(a.render_stills) or not a.plan_only
    edl = load_json(a.edl)
    P = edl.get('project_dir') or os.path.dirname(os.path.abspath(a.edl))
    cfg_path = os.path.join(P, 'project.json')
    cfg = load_json(cfg_path) if os.path.exists(cfg_path) else {}
    fps = float(edl.get('fps') or cfg.get('fps') or 30)
    dur = float(cfg.get('program_dur') or max([t['t1'] for t in edl.get('text', [])] + [i['t1'] for i in edl.get('inserts', [])] + [0]))
    pw_path = os.path.join(P, 'analysis', 'program_words.json')
    words = load_json(pw_path) if os.path.exists(pw_path) else []
    beats = edl.get('beats') or auto_beats(edl, dur)
    out_dir = os.path.abspath(a.out_dir or os.path.join(P, 'qa', 'storyboard'))
    still_dir = os.path.join(out_dir, 'stills')
    os.makedirs(still_dir, exist_ok=True)
    for f in os.listdir(still_dir):
        if f.endswith('.png') or f == 'sheet.jpg':
            os.remove(os.path.join(still_dir, f))

    stills = [None] * len(beats)
    if do_render:
        def richness(t):
            s = 0.0
            for i in edl.get('inserts', []):
                if i['t0'] + 0.5 <= t <= i['t1'] - 0.2:
                    s += 3
            for x in edl.get('text', []):
                if x.get('pill'):
                    s += 0.5 if x['t0'] <= t < x['t1'] else 0
                elif x['t0'] + 0.45 <= t <= x['t1'] - 0.3:
                    s += 2
            return s

        times = []
        for bt in beats:
            lo, hi = bt['t0'] + 0.2, max(bt['t0'] + 0.25, bt['t1'] - 0.25)
            cands = [lo + 0.1 * j for j in range(int((hi - lo) / 0.1) + 1)]
            t = max(cands, key=lambda c: (richness(c), c))
            k = int(round(t * fps))
            while times and k <= times[-1]:
                k += 1
            times.append(k)
        cmd = [sys.executable, '-X', 'utf8', os.path.join(ENGINE, 'render_reel.py'), os.path.abspath(a.edl), '--stills'] + \
              ['%.4f' % (k / fps) for k in times] + ['--out-dir', still_dir, '--workers', str(a.workers)]
        subprocess.run(cmd, check=True)
        stills = sorted(f for f in os.listdir(still_dir) if f.startswith('f_') and f.endswith('.png'))
        if len(stills) != len(beats):
            sys.exit('ERROR: %d stills for %d beats' % (len(stills), len(beats)))

    sfx = events_from_edl(edl, fps)
    zoom = edl.get('zoom') or []
    rows = []
    for bt, st in zip(beats, stills):
        said = ' '.join(w['w'].strip() for w in words if bt['t0'] - 0.02 <= w['s'] < bt['t1'] - 0.02)
        ins = [i for i in edl.get('inserts', []) if i['t0'] < bt['t1'] - 0.05 and i['t1'] > bt['t0'] + 0.05]
        enter = ', '.join('%s:%s' % (i['kind'], i.get('trans', 'whip')) for i in ins) or 'спикер'
        cam = '/'.join(dict.fromkeys(z for z0, z1, z in zoom if z0 < bt['t1'] - 0.05 and z1 > bt['t0'] + 0.05)) or '-'
        cues = ', '.join(dict.fromkeys(k for t, k, _ in sfx if bt['t0'] - 0.03 <= t < bt['t1'] - 0.03)) or '-'
        txt = ' / '.join(t['text'].replace('\n', ' ') for t in edl.get('text', [])
                         if not t.get('pill') and t['t0'] < bt['t1'] - 0.05 and t['t1'] > bt['t0'] + 0.05)
        pills = sum(1 for t in edl.get('text', []) if t.get('pill') and bt['t0'] - 0.02 <= t['t0'] < bt['t1'] - 0.02)
        rows.append(dict(n=bt.get('n'), name=bt.get('name', ''), t0=bt['t0'], t1=bt['t1'], said=said, enter=enter, cam=cam, sfx=cues,
                         text=txt, pills=pills, still=st))

    tw, th, pad, cap = 300, 533, 22, 214
    cols = min(a.cols, len(rows))
    nrows = (len(rows) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * (tw + pad) + pad, nrows * (th + cap + pad) + pad), (24, 24, 26))
    d = ImageDraw.Draw(sheet)
    fb, fn, fs = font(30, True), font(21, True), font(19)
    for i, r in enumerate(rows):
        x, y = pad + (i % cols) * (tw + pad), pad + (i // cols) * (th + cap + pad)
        if r['still']:
            sheet.paste(Image.open(os.path.join(still_dir, r['still'])).convert('RGB').resize((tw, th), Image.LANCZOS), (x, y))
        else:
            d.rectangle([x, y, x + tw, y + th], fill=(34, 34, 40), outline=(75, 80, 92), width=2)
            bt_txt = r['text'] or r['enter'] or 'Talking Head'
            py_box = y + 90
            for ln in wrap(d, bt_txt, fn, tw - 32)[:6]:
                d.text((x + 16, py_box), ln, font=fn, fill=(255, 214, 0))
                py_box += 30
            d.text((x + 16, y + th - 40), '[PLAN-ONLY LIGHTWEIGHT MODE]', font=fs, fill=(130, 140, 155))
        d.ellipse([x + 10, y + 10, x + 62, y + 62], fill=(224, 43, 32))
        num = str(r['n'])
        d.text((x + 36 - d.textlength(num, font=fb) / 2, y + 15), num, font=fb, fill=(255, 255, 255))
        ty = y + th + 8
        d.text((x, ty), ('%s   %.1f–%.1f с' % (r['name'], r['t0'], r['t1'])).strip(), font=fn, fill=(255, 255, 255))
        ty += 30
        for ln in wrap(d, r['said'], fs, tw)[:4]:
            d.text((x, ty), ln, font=fs, fill=(205, 205, 210))
            ty += 24
        ty = y + th + 8 + 30 + 4 * 24 + 4
        for label, val in (('кіру', r['enter']), ('камера', r['cam']), ('дыбыс', r['sfx'])):
            d.text((x, ty), '%s: %s' % (label, val), font=fs, fill=(140, 150, 165))
            ty += 24
    png = os.path.join(out_dir, 'storyboard.png')
    sheet.save(png)

    md = ['| № | бөлім | уақыт | айтылатын сөз | экрандағы мәтін | капсула | кіру | камера | дыбыс |', '|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        md.append('| %s | %s | %.2f–%.2f | %s | %s | %d | %s | %s | %s |' % (r['n'], r['name'], r['t0'], r['t1'], r['said'], r['text'] or '-',
                                                                         r['pills'], r['enter'], r['cam'], r['sfx']))
    with open(os.path.join(out_dir, 'storyboard.md'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(md) + '\n')
    with open(os.path.join(out_dir, 'storyboard.json'), 'w', encoding='utf-8') as fh:
        json.dump(rows, fh, indent=1, ensure_ascii=False)
    sys.stdout.reconfigure(encoding='utf-8')
    print('storyboard: %d beats -> %s' % (len(rows), png))
    print('show it, then STOP until the person approves (notes are not approval)')


if __name__ == '__main__':
    main()
