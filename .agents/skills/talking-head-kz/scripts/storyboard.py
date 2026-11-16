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
from hook_registry import (  # noqa: E402
    CAMERA_PRESETS,
    CAPTION_FORMATS,
    HOOK_CATALOG,
    balance_keyframe_stack,
    build_compound_keyframes,
    extract_transcript_metaphor,
    pick_hook_preset,
)
from sfx_from_edl import events_from_edl  # noqa: E402


def generate_custom_html_scene(project_dir, beat_idx, metaphor_info):
    """Module 4: Generate bespoke Canvas/WebGL HTML story scene matched to transcript metaphor."""
    metaphor = metaphor_info.get('metaphor', 'process_steps')
    rel_dir = os.path.join('motion_hooks')
    os.makedirs(os.path.join(project_dir, rel_dir), exist_ok=True)
    fname = f'scene_b{beat_idx + 1}_{metaphor}.html'
    rel_path = os.path.join(rel_dir, fname).replace('\\', '/')
    abs_path = os.path.join(project_dir, rel_dir, fname)

    # Interactive story-metaphor draw code tailored to exact metaphor class using window.EDL_PAYLOAD
    if metaphor == 'call_ui':
        body_js = """
  // Bespoke Phone Call / Communication Metaphor Scene
  const cardW = 620, cardH = cfg.isFull ? 760 : 540;
  const cx = cfg.W / 2, cy = cfg.cy;
  const sp = springPhys(t, 220, 18);
  const ringP = (t * 1.8) % 1;

  // Expanding sonar call rings behind phone frame
  for (let i = 0; i < 3; i++) {
    const ru = (t * 0.9 + i * 0.33) % 1;
    ctx.strokeStyle = cfg.accent2;
    ctx.globalAlpha = (1 - ru) * 0.38 * alpha;
    ctx.lineWidth = 4;
    ctx.beginPath(); ctx.arc(cx, cy, 180 + ru * 280, 0, Math.PI * 2); ctx.stroke();
  }

  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.translate(cx, cy);
  ctx.scale(0.92 + 0.08 * sp, 0.92 + 0.08 * sp);
  roundRectPath(ctx, -cardW / 2, -cardH / 2, cardW, cardH, 42);
  ctx.fillStyle = 'rgba(18, 20, 26, 0.96)';
  ctx.fill();
  ctx.strokeStyle = cfg.accent2;
  ctx.lineWidth = 4;
  ctx.stroke();

  // Pulsing call avatar + live audio waveform
  const pulse = 1 + 0.08 * Math.sin(t * 9.0);
  ctx.fillStyle = cfg.accent;
  ctx.beginPath(); ctx.arc(0, -cardH * 0.20, 62 * pulse, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#0B0B0E';
  ctx.font = '900 48px "Unbounded", sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('☎', 0, -cardH * 0.20 + 16);

  ctx.fillStyle = '#FFFFFF';
  ctx.font = '900 44px "Unbounded", "Montserrat", sans-serif';
  ctx.fillText(title.toUpperCase().slice(0, 18), 0, -10);
  if (subtitle) {
    ctx.fillStyle = 'rgba(237,230,222,0.82)';
    ctx.font = 'italic 700 30px "Playfair Display", serif';
    ctx.fillText(subtitle.slice(0, 26), 0, 46);
  }

  // Animated EQ bars representing incoming speech
  for (let b = -7; b <= 7; b++) {
    const bh = 18 + Math.abs(Math.sin(t * 7.5 + b * 0.7)) * 74 * sp;
    ctx.fillStyle = Math.abs(b) <= 2 ? cfg.accent : cfg.accent2;
    roundRectPath(ctx, b * 24 - 7, cardH * 0.24 - bh / 2, 14, bh, 7);
    ctx.fill();
  }
  ctx.restore();"""
    elif metaphor == 'currency_compare':
        body_js = """
  // Bespoke Currency / Value Comparison Bar Scene
  const cx = cfg.W / 2, cy = cfg.cy;
  const sp = springPhys(t, 220, 18);
  const grow = clamp(seg(t, 0.14, Math.min(cfg.dur - 0.4, 1.5)));
  const e = 1 - Math.pow(1 - grow, 3);
  const items = Array.isArray(cfg.items) && cfg.items.length >= 2 ? cfg.items : [cfg.left_label, cfg.right_label];
  const barW = 240, maxH = cfg.isFull ? 580 : 380;

  ctx.save();
  ctx.globalAlpha = alpha;
  if (title) {
    ctx.textAlign = 'center';
    ctx.fillStyle = '#FFFFFF';
    ctx.font = '900 46px "Unbounded", "Montserrat", sans-serif';
    ctx.fillText(title.toUpperCase().slice(0, 24), cx, cy - maxH * 0.56);
  }

  const cols = [cfg.danger, cfg.accent2];
  const ratios = [0.58, 0.96];
  const xs = [cx - 210, cx + 210];
  ratios.forEach((r, idx) => {
    const bh = maxH * r * e;
    const x = xs[idx], yBot = cy + maxH * 0.42;
    ctx.fillStyle = 'rgba(255,255,255,0.08)';
    roundRectPath(ctx, x - barW / 2, yBot - maxH, barW, maxH, 20);
    ctx.fill();
    ctx.fillStyle = cols[idx];
    roundRectPath(ctx, x - barW / 2, yBot - Math.max(16, bh), barW, Math.max(16, bh), 20);
    ctx.fill();
    const lbl = String(items[idx] || '').toUpperCase().slice(0, 12);
    if (lbl) {
      ctx.textAlign = 'center';
      ctx.fillStyle = '#FFFFFF';
      ctx.font = '900 32px "JetBrains Mono", monospace';
      ctx.fillText(lbl, x, yBot + 54);
    }
  });
  ctx.restore();"""
    else:
        body_js = """
  // Bespoke Step / Story Cards Reveal driven purely by EDL_PAYLOAD tokens
  const cx = cfg.W / 2, cy = cfg.cy;
  const rawSteps = (Array.isArray(cfg.items) && cfg.items.length) ? cfg.items : tokens.slice(0, 3);
  const n = Math.max(1, Math.min(3, rawSteps.length));
  const gap = cfg.isFull ? 165 : 132;
  const startY = cy - ((n - 1) * gap) * 0.5 + 30;

  ctx.save();
  ctx.globalAlpha = alpha;
  if (title) {
    ctx.textAlign = 'center';
    ctx.fillStyle = cfg.accent;
    ctx.font = '900 46px "Unbounded", "Montserrat", sans-serif';
    ctx.fillText(title.toUpperCase().slice(0, 24), cx, startY - 120);
  }
  for (let i = 0; i < n; i++) {
    const sp = springPhys(Math.max(0, t - i * 0.16), 220, 18);
    const y = startY + i * gap;
    ctx.save();
    ctx.translate(cx - (1 - clamp(sp, 0, 1.05)) * 120, y);
    roundRectPath(ctx, -400, -52, 800, 104, 22);
    ctx.fillStyle = i === n - 1 ? 'rgba(255,214,0,0.16)' : 'rgba(22,19,26,0.92)';
    ctx.fill();
    ctx.strokeStyle = i === n - 1 ? cfg.accent : 'rgba(255,255,255,0.22)';
    ctx.lineWidth = 3;
    ctx.stroke();

    ctx.fillStyle = cfg.accent2;
    ctx.font = '900 34px "JetBrains Mono", monospace';
    ctx.textAlign = 'left';
    ctx.fillText(`0${i + 1}`, -365, 12);

    ctx.fillStyle = '#FFFFFF';
    ctx.font = '800 34px "Montserrat", sans-serif';
    ctx.fillText(String(rawSteps[i] || '').toUpperCase().slice(0, 20), -285, 12);
    ctx.restore();
  }
  ctx.restore();"""

    html = f"""<!DOCTYPE html>
<html lang="kk">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=1080, height=1920, initial-scale=1.0" />
<title>Bespoke Scene: {metaphor}</title>
<style>html,body{{margin:0;padding:0;overflow:hidden;background:transparent;}}canvas{{display:block;}}</style>
</head>
<body>
<canvas id="stage"></canvas>
<script>
HookCore.initStage((ctx, t, imgs, cfg) => {{
  const {{ clamp, seg, springPhys, envelope, roundRectPath, drawStageBackdrop, deriveText }} = HookCore;
  const {{ alpha }} = envelope(t, cfg.dur);
  if (alpha <= 0.005) return;
  drawStageBackdrop(ctx, cfg.W, cfg.H, cfg, t);
  const {{ title, subtitle, label, tokens }} = deriveText(cfg);
{body_js}
}}, {{}});
</script>
</body>
</html>
"""
    with open(abs_path, 'w', encoding='utf-8') as fh:
        fh.write(html)
    return rel_path


def route_mastery_v2(edl, words, project_dir=None, write_custom_scenes=False):
    """Apply Autonomous Expertise: Layout Quota, Metaphor Extraction, Anti-Repeat & 2..4 Layers."""
    beats = edl.get('beats') or []
    last_used = []
    kf_out = []
    ins_by_time = sorted(edl.get('inserts', []), key=lambda i: i['t0'])
    n_beats = max(len(beats), 1)
    # Deterministic quota sequence: ensure >=2 split and >=2 full while capping behind_speaker <= 1 beat (<=15%)
    quota_ring = ['full', 'split', 'full', 'split', 'cards', 'split', 'behind_speaker']

    for idx, bt in enumerate(beats):
        t0, t1 = float(bt['t0']), float(bt['t1'])
        said = ' '.join(w['w'].strip() for w in words if t0 - 0.02 <= w['s'] < t1 - 0.02)
        meta = extract_transcript_metaphor(said, bt.get('name', ''))
        active_ins = [i for i in ins_by_time if i['t0'] < t1 - 0.05 and i['t1'] > t0 + 0.05]

        preset = None
        for i in active_ins:
            p = i.get('preset')
            if p in HOOK_CATALOG and (not last_used or p != last_used[-1]):
                preset = p
                break
        if not preset:
            preset = pick_hook_preset(said, bt.get('name', ''), last_used_styles=last_used, fallback_idx=idx)
        else:
            last_used.append(preset)

        target_mode = quota_ring[idx % len(quota_ring)]
        for i in active_ins:
            if not i.get('preset') and not i.get('html_hook') and not i.get('custom_html_scene'):
                if target_mode == 'behind_speaker' and idx / n_beats <= 0.15:
                    i['kind'] = 'overlay'
                    i['depth'] = 'behind_speaker'
                    i['preset'] = 'halftone_cutout_backsplash'
                else:
                    i['preset'] = preset
                    if target_mode == 'split':
                        i['kind'] = 'full'
                        i['layout'] = 'split'
                    elif target_mode == 'full':
                        i['kind'] = 'full'
                        i['layout'] = 'full'
            # Inject spoken semantic payload fields if missing (Zero-Placeholder Law)
            for k in ('title', 'subtitle', 'label', 'from', 'to', 'suffix', 'kpis', 'items', 'left_label', 'right_label'):
                if k not in i and meta.get(k) not in (None, '', []):
                    i[k] = meta[k]
            if write_custom_scenes and project_dir and i.get('kind') in ('full',) and not i.get('html_hook') and not i.get('custom_html_scene'):
                if meta['metaphor'] in ('call_ui', 'currency_compare', 'process_steps'):
                    i['custom_html_scene'] = generate_custom_html_scene(project_dir, idx, meta)

        cap_fmt = CAPTION_FORMATS[idx % len(CAPTION_FORMATS)]
        cam_preset = bt.get('camera_motion') or CAMERA_PRESETS[idx % len(CAMERA_PRESETS)]
        anims = bt.get('animations')
        if not anims:
            anims = build_compound_keyframes(t0, t1, preset=preset, caption_format=cap_fmt, role_index=idx)
            for a_ in anims:
                if a_.get('layer') == 'camera':
                    a_['effect'] = cam_preset
        anims, _ = balance_keyframe_stack(anims, t0=t0, t1=t1, role_index=idx)
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
    ap.add_argument('--plan-only', action='store_true', default=(os.name == 'nt'),
                    help='Build storyboard.md/.json + vector blueprint PNG without running heavy render_reel stills (default on Windows)')
    ap.add_argument('--render-stills', action='store_true',
                    help='Force rendering PNG stills via render_reel.py (use in Cloud Actions or machines with >16GB RAM)')
    ap.add_argument('--enrich-edl', action='store_true',
                    help='Route 12-hook presets (anti-repeat) + 2..4 Compound Keyframes into the EDL JSON in place')
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
    if not edl.get('beats'):
        edl['beats'] = auto_beats(edl, dur)
    route_mastery_v2(edl, words, project_dir=P, write_custom_scenes=bool(a.enrich_edl))
    if a.enrich_edl:
        with open(a.edl, 'w', encoding='utf-8') as fh:
            json.dump(edl, fh, indent=2, ensure_ascii=False)
            fh.write('\n')
    beats = edl['beats']
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
        preset = bt.get('preset', '-')
        nlayers = len(bt.get('animations') or [])
        rows.append(dict(n=bt.get('n'), name=bt.get('name', ''), t0=bt['t0'], t1=bt['t1'], said=said, enter=enter, cam=cam, sfx=cues,
                         text=txt, pills=pills, preset=preset, layers=nlayers, still=st))

    tw, th, pad, cap = 300, 533, 22, 236
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
            d.text((x + 16, y + th - 68), '%s [%dL]' % (r['preset'][:22], r['layers']), font=fs, fill=(0, 230, 118))
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
        for label, val in (('кіру', r['enter']), ('пресет', '%s (%dL)' % (r['preset'][:18], r['layers'])), ('камера', r['cam']), ('дыбыс', r['sfx'])):
            d.text((x, ty), '%s: %s' % (label, val), font=fs, fill=(140, 150, 165))
            ty += 22
    png = os.path.join(out_dir, 'storyboard.png')
    sheet.save(png)

    md = ['| № | бөлім | уақыт | айтылатын сөз | экрандағы мәтін | капсула | пресет | қабат | кіру | камера | дыбыс |',
          '|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        md.append('| %s | %s | %.2f–%.2f | %s | %s | %d | %s | %d | %s | %s | %s |' % (
            r['n'], r['name'], r['t0'], r['t1'], r['said'], r['text'] or '-',
            r['pills'], r['preset'], r['layers'], r['enter'], r['cam'], r['sfx']))
    with open(os.path.join(out_dir, 'storyboard.md'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(md) + '\n')
    with open(os.path.join(out_dir, 'storyboard.json'), 'w', encoding='utf-8') as fh:
        json.dump(rows, fh, indent=1, ensure_ascii=False)
    sys.stdout.reconfigure(encoding='utf-8')
    print('storyboard: %d beats -> %s' % (len(rows), png))


if __name__ == '__main__':
    main()
