#!/usr/bin/env python3
"""Numbered storyboard + kz-kinetic-studio Hero Hook router (2-3 Hero Hooks, 80% Kinetic Subtitles).

    python -X utf8 scripts/storyboard.py PROJECT/kz_edl.json [--out-dir PROJECT/qa/storyboard] [--plan-only] [--enrich-edl]
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(os.path.dirname(HERE), 'engine', 'scripts')
sys.path.insert(0, ENGINE)
sys.path.insert(0, HERE)
from common import load_json  # noqa: E402
from hook_registry import (  # noqa: E402
    CAMERA_PRESETS,
    CAPTION_FORMATS,
    HERO_CATALOG,
    MAX_HERO_HOOKS,
    balance_keyframe_stack,
    build_compound_keyframes,
    extract_transcript_metaphor,
    pick_hook_preset,
)
from sfx_from_edl import events_from_edl  # noqa: E402


def route_mastery_v2(edl, words, project_dir=None, write_custom_scenes=False):
    """Apply kz-kinetic-studio laws: strictly 2-3 transparent Hero Hooks, Zero Black Screens, 2..4 Layers."""
    beats = edl.get('beats') or []
    inserts = sorted(edl.get('inserts', []), key=lambda i: i['t0'])
    if len(inserts) > MAX_HERO_HOOKS:
        # Keep top 3 spaced hooks (start, middle, climax/close)
        keep_idx = sorted({0, len(inserts) // 2, len(inserts) - 1})[:MAX_HERO_HOOKS]
        inserts = [inserts[k] for k in keep_idx]
        edl['inserts'] = inserts

    last_used = []
    for ins_idx, ins in enumerate(inserts):
        t0, t1 = float(ins['t0']), float(ins['t1'])
        said = ' '.join(w['w'].strip() for w in words if t0 - 0.15 <= w['s'] < t1 - 0.02)
        meta = extract_transcript_metaphor(said, ins.get('title', ''))
        preset = ins.get('preset')
        if preset not in HERO_CATALOG:
            preset = pick_hook_preset(said, ins.get('title', ''), last_used_styles=last_used, fallback_idx=ins_idx)
        else:
            last_used.append(preset)
        spec = HERO_CATALOG[preset]
        ins['preset'] = preset
        ins['kind'] = 'overlay'
        ins['depth'] = 'front'
        ins['layout'] = 'full'
        ins['trans'] = 'cut'
        ins.setdefault('x', spec['x'])
        ins.setdefault('y', spec['y'])
        ins.setdefault('width', spec['width'])
        ins.setdefault('height', spec['height'])
        ins.setdefault('blur_bg', spec['blur_bg'])
        ins.setdefault('overlay', {'src': f"hooks_rendered/{ins['id']}.webm"})
        ins.pop('clips', None)
        for k in ('title', 'subtitle', 'label', 'stamp', 'asset', 'from', 'to', 'suffix'):
            if k not in ins and meta.get(k) not in (None, '', []):
                ins[k] = meta[k]

    kf_out = []
    for idx, bt in enumerate(beats):
        t0, t1 = float(bt['t0']), float(bt['t1'])
        active_ins = [i for i in inserts if i['t0'] < t1 - 0.05 and i['t1'] > t0 + 0.05]
        preset = active_ins[0]['preset'] if active_ins else bt.get('preset')
        if preset not in HERO_CATALOG:
            preset = None
        cap_fmt = CAPTION_FORMATS[idx % len(CAPTION_FORMATS)]
        cam_preset = bt.get('camera_motion') or (HERO_CATALOG[preset]['camera_default'] if preset else CAMERA_PRESETS[idx % len(CAMERA_PRESETS)])
        anims = bt.get('animations')
        if not anims:
            anims = build_compound_keyframes(t0, t1, preset=preset, caption_format=cap_fmt, role_index=idx)
            for a_ in anims:
                if a_.get('layer') == 'camera':
                    a_['effect'] = cam_preset
        anims, _ = balance_keyframe_stack(anims, t0=t0, t1=t1, role_index=idx)
        if preset:
            bt['preset'] = preset
        bt['camera_motion'] = cam_preset
        bt['animations'] = anims
        kf_out.append({'beat': bt.get('n', idx + 1), 't0': t0, 't1': t1, 'preset': preset, 'camera_motion': cam_preset, 'animations': anims})
    if kf_out:
        edl['keyframes'] = kf_out
    return edl


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
    ap.add_argument('--plan-only', action='store_true', default=(os.name == 'nt'))
    ap.add_argument('--render-stills', action='store_true')
    ap.add_argument('--enrich-edl', action='store_true')
    a = ap.parse_args()
    edl = load_json(a.edl)
    P = edl.get('project_dir') or os.path.dirname(os.path.abspath(a.edl))
    cfg_path = os.path.join(P, 'project.json')
    cfg = load_json(cfg_path) if os.path.exists(cfg_path) else {}
    fps = float(edl.get('fps') or cfg.get('fps') or 30)
    dur = float(cfg.get('program_dur') or max([t['t1'] for t in edl.get('text', [])] + [i['t1'] for i in edl.get('inserts', [])] + [0]))
    pw_path = os.path.join(P, 'analysis', 'program_words.json')
    words = load_json(pw_path) if os.path.exists(pw_path) else []
    if not edl.get('beats'):
        edl['beats'] = auto_beats(edl, dur)
    route_mastery_v2(edl, words, project_dir=P, write_custom_scenes=bool(a.enrich_edl))
    if a.enrich_edl:
        with open(a.edl, 'w', encoding='utf-8') as fh:
            json.dump(edl, fh, indent=2, ensure_ascii=False)
            fh.write('\n')

    beats = edl['beats']
    out_dir = os.path.abspath(a.out_dir or os.path.join(P, 'qa', 'storyboard'))
    os.makedirs(out_dir, exist_ok=True)

    sfx = events_from_edl(edl, fps)
    zoom = edl.get('zoom') or []
    rows = []
    for bt in beats:
        said = ' '.join(w['w'].strip() for w in words if bt['t0'] - 0.02 <= w['s'] < bt['t1'] - 0.02)
        ins = [i for i in edl.get('inserts', []) if i['t0'] < bt['t1'] - 0.05 and i['t1'] > bt['t0'] + 0.05]
        enter = ', '.join(f"{i.get('preset', i['kind'])} (alpha)" for i in ins) or 'live_speaker + kinetic_subs'
        cam = bt.get('camera_motion') or '/'.join(dict.fromkeys(z for z0, z1, z in zoom if z0 < bt['t1'] - 0.05 and z1 > bt['t0'] + 0.05)) or '-'
        cues = ', '.join(dict.fromkeys(k for t, k, _ in sfx if bt['t0'] - 0.03 <= t < bt['t1'] - 0.03)) or '-'
        txt = ' / '.join(t['text'].replace('\n', ' ') for t in edl.get('text', []) if t['t0'] < bt['t1'] - 0.05 and t['t1'] > bt['t0'] + 0.05)
        rows.append(dict(n=bt.get('n'), name=bt.get('name', ''), t0=bt['t0'], t1=bt['t1'], said=said, enter=enter, cam=cam, sfx=cues,
                         text=txt[:120], preset=bt.get('preset') or 'kinetic_subs_only', layers=len(bt.get('animations') or [])))

    tw, th, pad, cap = 300, 360, 22, 220
    cols = min(a.cols, max(1, len(rows)))
    nrows = (len(rows) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * (tw + pad) + pad, nrows * (th + cap + pad) + pad), (24, 24, 26))
    d = ImageDraw.Draw(sheet)
    fb, fn, fs = font(28, True), font(20, True), font(18)
    for i, r in enumerate(rows):
        x, y = pad + (i % cols) * (tw + pad), pad + (i // cols) * (th + cap + pad)
        d.rectangle([x, y, x + tw, y + th], fill=(34, 34, 40), outline=(75, 80, 92), width=2)
        d.ellipse([x + 10, y + 10, x + 56, y + 56], fill=(224, 43, 32))
        num = str(r['n'])
        d.text((x + 33 - d.textlength(num, font=fb) / 2, y + 14), num, font=fb, fill=(255, 255, 255))
        py_box = y + 76
        for ln in wrap(d, r['enter'], fn, tw - 32)[:4]:
            d.text((x + 16, py_box), ln, font=fn, fill=(255, 214, 0))
            py_box += 28
        d.text((x + 16, y + th - 64), f"{r['cam']} [{r['layers']}L]", font=fs, fill=(0, 230, 118))
        d.text((x + 16, y + th - 36), '[PLAN-ONLY LIGHTWEIGHT]', font=fs, fill=(130, 140, 155))
        ty = y + th + 8
        d.text((x, ty), f"{r['name']}   {r['t0']:.1f}-{r['t1']:.1f}s", font=fn, fill=(255, 255, 255))
        ty += 28
        for ln in wrap(d, r['said'], fs, tw)[:4]:
            d.text((x, ty), ln, font=fs, fill=(205, 205, 210))
            ty += 24
    png = os.path.join(out_dir, 'storyboard.png')
    sheet.save(png)
    md = ['| № | бөлім | уақыт | айтылатын сөз | хук/сахна | камера | қабат | дыбыс |',
          '|---|---|---|---|---|---|---|---|']
    for r in rows:
        md.append(f"| {r['n']} | {r['name']} | {r['t0']:.2f}-{r['t1']:.2f} | {r['said']} | {r['enter']} | {r['cam']} | {r['layers']} | {r['sfx']} |")
    with open(os.path.join(out_dir, 'storyboard.md'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(md) + '\n')
    with open(os.path.join(out_dir, 'storyboard.json'), 'w', encoding='utf-8') as fh:
        json.dump(rows, fh, indent=1, ensure_ascii=False)
    sys.stdout.reconfigure(encoding='utf-8')
    print(f'storyboard: {len(rows)} beats, {len(edl.get("inserts", []))} hero hooks -> {png}')


if __name__ == '__main__':
    main()
