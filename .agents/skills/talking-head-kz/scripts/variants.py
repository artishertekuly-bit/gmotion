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
sys.path.insert(0, HERE)
from common import load_json  # noqa: E402
from hook_registry import (  # noqa: E402
    CAPTION_FORMATS,
    HOOK_CATALOG,
    HOOK_ORDER,
    build_compound_keyframes,
)


def build_auto_v2_options(edl, beat_idx=0, n_variants=4):
    """Build n genuinely different beat options across the 12 presets, 8 subtitle formats & 2-4 keyframe layers."""
    beats = edl.get('beats') or [{'n': 1, 'name': 'Хук', 't0': 0.0, 't1': min(3.5, max((t['t1'] for t in edl.get('text', [])), default=3.2))}]
    bt = beats[min(max(beat_idx, 0), len(beats) - 1)]
    w0, w1 = float(bt['t0']), float(bt['t1'])
    said_txt = ' '.join(t.get('text', '') for t in edl.get('text', []) if t['t0'] < w1 and t['t1'] > w0)[:48] or bt.get('name', 'МАҢЫЗДЫ СӘТ')
    used_presets = []
    options = {}
    zooms = ('tight', 'wide', 'tight', 'wide')
    labels = ('A', 'B', 'C', 'D', 'E')[:max(3, min(5, n_variants))]
    for idx, key in enumerate(labels):
        # Strictly pick distinct preset across every variant option
        preset = next((p for p in HOOK_ORDER if p not in used_presets), HOOK_ORDER[idx % len(HOOK_ORDER)])
        used_presets.append(preset)
        cap_fmt = CAPTION_FORMATS[(beat_idx + idx * 2) % len(CAPTION_FORMATS)]
        keyframes = build_compound_keyframes(w0, w1, preset=preset, caption_format=cap_fmt, role_index=idx)
        ins = {
            'id': f'var_{key.lower()}_{preset}',
            'kind': 'overlay',
            'preset': preset,
            't0': round(max(0.0, w0 + 0.05), 3),
            't1': round(max(w0 + 1.2, min(w1, w0 + 3.2)), 3),
            'title': said_txt[:24].upper(),
            'alpha': True,
            'depth': HOOK_CATALOG[preset]['depth'],
            'trans': 'cut',
            'overlay': {'src': f'hooks_rendered/var_{key.lower()}_{preset}.mov'},
        }
        txt = {
            'font': 'impact' if idx % 2 == 0 else 'editorial',
            'text': said_txt.upper() if idx % 2 == 0 else said_txt.lower(),
            't0': round(w0 if w0 > 0 else -0.35, 3),
            't1': round(w1, 3),
            'x': 540,
            'y': 580 if cap_fmt == 'behind_head_giant' else 1280,
            'size': 190 if cap_fmt == 'behind_head_giant' else 78,
            'behind': cap_fmt == 'behind_head_giant',
            'caption_format': cap_fmt,
            'anim': 'pop' if cap_fmt == 'tilted_pill_badge' else ('terminal' if cap_fmt == 'whisper_glitch_box' else 'rise'),
            'tilt': -4 if cap_fmt == 'tilted_pill_badge' else 0,
            'pill': '#2F3E2E' if cap_fmt == 'tilted_pill_badge' else None,
            'underline': 'yellow' if cap_fmt == 'graffiti_underline_strike' else None,
            'barcode': cap_fmt == 'whisper_glitch_box',
            'color': '#FFD600' if idx % 2 == 0 else '#FFFFFF',
        }
        options[key] = {
            'note': f'{preset} + {cap_fmt} ({len(keyframes)}L)',
            'zoom': zooms[idx % len(zooms)],
            'preset': preset,
            'animations': keyframes,
            'inserts': [ins],
            'text': [txt],
        }
    return {
        'window': [w0, w1],
        'at': [round(w0 + 0.05, 2), round((w0 + w1) / 2.0, 2), round(max(w0 + 0.2, w1 - 0.25), 2)],
        'options': options,
    }


def font(size, bold=False):
    windir = os.environ.get('WINDIR') or os.environ.get('SystemRoot') or ''
    p = os.path.join(windir, 'Fonts', 'segoeuib.ttf' if bold else 'segoeui.ttf')
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('edl')
    ap.add_argument('--options', help='Options JSON file (optional if --auto-v2 is passed)')
    ap.add_argument('--auto-v2', action='store_true', help='Auto-generate 4 diverse Mastery V2 options (12 hooks + 8 caption formats)')
    ap.add_argument('--beat', type=int, default=0, help='Beat index for --auto-v2')
    ap.add_argument('--plan-only', action='store_true', default=(os.name == 'nt'),
                    help='Build variant EDLs + blueprint PNG without invoking render_reel.py (default on Windows)')
    ap.add_argument('--render-stills', action='store_true', help='Force real render_reel.py stills')
    ap.add_argument('--out-dir')
    ap.add_argument('--workers', type=int, default=2)
    a = ap.parse_args()
    edl = load_json(a.edl)
    P = edl.get('project_dir') or os.path.dirname(os.path.abspath(a.edl))
    out_dir = os.path.abspath(a.out_dir or os.path.join(P, 'qa', 'variants'))
    os.makedirs(out_dir, exist_ok=True)
    if a.options:
        opt = load_json(a.options)
    else:
        opt = build_auto_v2_options(edl, beat_idx=a.beat)
        with open(os.path.join(out_dir, 'options_v2.json'), 'w', encoding='utf-8') as fh:
            json.dump(opt, fh, indent=1, ensure_ascii=False)
    do_render = bool(a.render_stills) or not a.plan_only
    w0, w1 = opt['window']
    at = opt['at'] if isinstance(opt['at'], list) else [opt['at']]

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
        files = []
        if do_render:
            subprocess.run([sys.executable, '-X', 'utf8', os.path.join(ENGINE, 'render_reel.py'), p, '--stills'] + ['%.3f' % t for t in at] +
                           ['--out-dir', sd, '--workers', str(a.workers)], check=True)
            files = [os.path.join(sd, f) for f in sorted(os.listdir(sd)) if f.startswith('f_') and f.endswith('.png')]
        rows.append((key, o.get('note', ''), files))

    tw, th, pad, left = 270, 480, 14, 250
    n = max([len(r[2]) for r in rows] + [len(at)])
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
        if files:
            for j, f in enumerate(files):
                sheet.paste(Image.open(f).convert('RGB').resize((tw, th), Image.LANCZOS), (left + pad + j * (tw + pad), y))
        else:
            for j, t_at in enumerate(at):
                rx = left + pad + j * (tw + pad)
                d.rectangle([rx, y, rx + tw, y + th], fill=(32, 34, 42), outline=(85, 92, 110), width=2)
                d.text((rx + 14, y + 18), f'Option {key} @ {t_at:.2f}s', font=ft, fill=(255, 214, 0))
                d.text((rx + 14, y + th - 36), '[PLAN-ONLY]', font=ft, fill=(140, 150, 165))
    png = os.path.join(out_dir, 'variants.png')
    sheet.save(png)
    sys.stdout.reconfigure(encoding='utf-8')
    print('variants: %s -> %s' % (', '.join(r[0] for r in rows), png))


if __name__ == '__main__':
    main()
