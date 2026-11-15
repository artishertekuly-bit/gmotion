#!/usr/bin/env python3
"""Try 3-5 genuinely different treatments of one beat and put them side by side, before committing to one.

    python -X utf8 scripts/variants.py PROJECT/edl.json --options OPTIONS.json [--out-dir PROJECT/qa/variants_hook] [--workers 2]

OPTIONS.json:
    {"window": [0.0, 2.95],            the beat: every text item and insert that overlaps it is replaced
     "at": [0.0, 1.4, 2.6],            the moments to render for every option (program seconds)
     "options": {
        "A": {"note": "баған, мойын астында", "text": [...], "inserts": [...], "zoom": "tight"},
        "B": {"note": "алдымен карточка", "text": [...], "inserts": [...]},
        "C": {...}}}

"text" and "inserts" are ordinary EDL items; "zoom" (optional) forces the speaker framing inside the window.
An option differs by action, layout or transition - another colour or font alone is not a new option.
Writes one EDL per option (edl_A.json, ...) and variants.png: one row per option, one frame per moment.
Pick the strongest for the whole reel, copy its items into the working EDL, and say in one line why.
"""
import argparse
import copy
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(os.path.dirname(HERE), 'engine', 'scripts')
sys.path.insert(0, ENGINE)
from common import load_json  # noqa: E402


def font(size, bold=False):
    windir = os.environ.get('WINDIR') or os.environ.get('SystemRoot') or ''
    p = os.path.join(windir, 'Fonts', 'segoeuib.ttf' if bold else 'segoeui.ttf')
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('edl')
    ap.add_argument('--options', required=True)
    ap.add_argument('--out-dir')
    ap.add_argument('--workers', type=int, default=2)
    a = ap.parse_args()
    edl = load_json(a.edl)
    opt = load_json(a.options)
    P = edl.get('project_dir') or os.path.dirname(os.path.abspath(a.edl))
    w0, w1 = opt['window']
    at = opt['at'] if isinstance(opt['at'], list) else [opt['at']]
    out_dir = os.path.abspath(a.out_dir or os.path.join(P, 'qa', 'variants'))
    os.makedirs(out_dir, exist_ok=True)

    def outside(item):
        return not (item['t0'] < w1 - 0.01 and item['t1'] > w0 + 0.01)

    rows = []
    for key, o in opt['options'].items():
        e = copy.deepcopy(edl)
        e['project_dir'] = P
        e['text'] = [t for t in e.get('text', []) if outside(t)] + o.get('text', [])
        e['inserts'] = [i for i in e.get('inserts', []) if outside(i)] + o.get('inserts', [])
        if o.get('zoom'):
            z = [list(x) for x in (e.get('zoom') or []) if not (x[0] < w1 and x[1] > w0)]
            e['zoom'] = sorted(z + [[w0, w1, o['zoom']]])
        p = os.path.join(out_dir, 'edl_%s.json' % key)
        with open(p, 'w', encoding='utf-8') as fh:
            json.dump(e, fh, indent=1, ensure_ascii=False)
        sd = os.path.join(out_dir, key)
        os.makedirs(sd, exist_ok=True)
        for f in os.listdir(sd):
            if f.endswith('.png') or f == 'sheet.jpg':
                os.remove(os.path.join(sd, f))
        subprocess.run([sys.executable, '-X', 'utf8', os.path.join(ENGINE, 'render_reel.py'), p, '--stills'] + ['%.3f' % t for t in at] +
                       ['--out-dir', sd, '--workers', str(a.workers)], check=True)
        rows.append((key, o.get('note', ''), [os.path.join(sd, f) for f in sorted(os.listdir(sd)) if f.startswith('f_') and f.endswith('.png')]))

    tw, th, pad, left = 270, 480, 14, 250
    n = max(len(r[2]) for r in rows)
    sheet = Image.new('RGB', (left + n * (tw + pad) + pad, len(rows) * (th + pad) + pad + 40), (24, 24, 26))
    d = ImageDraw.Draw(sheet)
    fb, fs, ft = font(96, True), font(22), font(20)
    for j, t in enumerate(at):
        d.text((left + pad + j * (tw + pad), 8), '%.2f с' % t, font=ft, fill=(140, 150, 165))
    for i, (key, note, files) in enumerate(rows):
        y = 40 + pad + i * (th + pad)
        d.text((28, y + 10), key, font=fb, fill=(224, 43, 32))
        ty, cur = y + 140, ''
        for w in note.split():
            if d.textlength((cur + ' ' + w).strip(), font=fs) > left - 44 and cur:
                d.text((28, ty), cur, font=fs, fill=(215, 215, 220))
                ty, cur = ty + 28, w
            else:
                cur = (cur + ' ' + w).strip()
        d.text((28, ty), cur, font=fs, fill=(215, 215, 220))
        for j, f in enumerate(files):
            sheet.paste(Image.open(f).convert('RGB').resize((tw, th), Image.LANCZOS), (left + pad + j * (tw + pad), y))
    png = os.path.join(out_dir, 'variants.png')
    sheet.save(png)
    sys.stdout.reconfigure(encoding='utf-8')
    print('variants: %s -> %s' % (', '.join(r[0] for r in rows), png))


if __name__ == '__main__':
    main()
