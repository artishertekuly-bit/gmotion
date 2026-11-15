#!/usr/bin/env python3
"""Check the FINAL decoded MP4, not the plan: file facts, every frame-to-frame jump, the joins, the sound level.

    python -X utf8 scripts/review_render.py PROJECT/render/NAME_v1.mp4 --edl PROJECT/edl.json [--out-dir PROJECT/qa/review_v1]

What it does (the first build is a draft - run this, fix what it finds, render again):
  * file: size, frame rate, number of decoded frames against the program length, audio stream, loudness (LUFS);
  * pops: decodes every frame small and measures the change between neighbours. A spike where the EDL plans a
    change (insert in/out, flash, jump cut, framing change) is expected; a spike anywhere else is listed as UNPLANNED;
  * dead air: stretches where almost nothing moves for more than a second;
  * joins: writes joins.png - the frame before, the frame of and two frames after every insert boundary;
  * first and last frame: not black, and saved as first.png / last.png (frame 0 is the cover).
Writes review.md with honest statuses. It cannot watch motion or hear sound: those lines stay "not checked"
until a person plays the file.
"""
import argparse
import math
import os
import re
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'engine', 'scripts'))
from common import find_ffmpeg, load_json, probe  # noqa: E402

SW, SH = 54, 96


def grab(ff, path, t, w=270, h=480, fps=30.0):
    t = t - 0.5 / fps                                     # half a frame early: the seek then lands on exactly this frame
    raw = subprocess.run([ff, '-v', 'error', '-ss', '%.4f' % max(0, t), '-i', path, '-frames:v', '1', '-vf', 'scale=%d:%d' % (w, h),
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, stdin=subprocess.DEVNULL).stdout
    if len(raw) != w * h * 3:
        return Image.new('RGB', (w, h), (60, 0, 0))
    return Image.frombytes('RGB', (w, h), raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('--edl', required=True)
    ap.add_argument('--out-dir')
    a = ap.parse_args()
    ff = find_ffmpeg()
    edl = load_json(a.edl)
    P = edl.get('project_dir') or os.path.dirname(os.path.abspath(a.edl))
    cfg = load_json(os.path.join(P, 'project.json'))
    out_dir = os.path.abspath(a.out_dir or os.path.join(P, 'qa', 'review'))
    os.makedirs(out_dir, exist_ok=True)
    info = probe(a.video, ff)
    fps = info['fps'] or float(edl.get('fps') or cfg.get('fps') or 30)
    banner = subprocess.run([ff, '-hide_banner', '-i', a.video], capture_output=True, text=True, stdin=subprocess.DEVNULL).stderr
    vline = next((l for l in banner.split('\n') if 'Video:' in l), '')
    aline = next((l for l in banner.split('\n') if 'Audio:' in l), '')
    notes, bad = [], 0

    def note(ok, what, detail=''):
        nonlocal bad
        bad += 0 if ok else 1
        notes.append('| %s | %s | %s |' % ('OK' if ok else 'FIX', what, detail))

    note(info['w'] == edl.get('W', 1080) and info['h'] == edl.get('H', 1920), 'frame size', '%dx%d' % (info['w'], info['h']))
    note('h264' in vline and 'yuv420p' in vline, 'H.264, yuv420p', re.sub(r'\s+', ' ', vline.strip())[:70])
    note(abs(fps - float(edl.get('fps') or cfg.get('fps') or fps)) < 0.02, 'frame rate', '%.3g fps' % fps)

    raw = subprocess.run([ff, '-v', 'error', '-i', a.video, '-vf', 'scale=%d:%d,format=gray' % (SW, SH), '-f', 'rawvideo', '-'],
                         capture_output=True, stdin=subprocess.DEVNULL).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, SH, SW).astype(np.float32)
    n = len(fr)
    want = int(round(float(cfg.get('program_dur', info['dur'])) * fps))
    note(abs(n - want) <= 1, 'decoded frames match the program', '%d decoded, %d planned (%.2f s)' % (n, want, n / fps))
    diff = np.abs(fr[1:] - fr[:-1]).mean(axis=(1, 2))                     # diff[k] = change going INTO frame k+1
    med = float(np.median(diff))
    thr = max(6 * med, 9.0)
    spikes = [k + 1 for k in range(len(diff)) if diff[k] > thr]

    planned = {}                                                          # frame -> why a jump is expected there
    def plan(t, why, before=1, after=3):
        k = int(math.ceil(t * fps - 1e-6))
        for j in range(k - before, k + after + 1):
            planned.setdefault(j, why)
    ins = sorted(edl.get('inserts', []), key=lambda i: i['t0'])
    for I in ins:
        plan(I['t0'], 'insert %s in' % I['id'], after=14)                 # moving entries keep changing for ~0.4 s
        plan(I['t1'], 'insert %s out' % I['id'], after=16)                # the engine may hold an insert up to ~0.45 s past t1
        if I.get('flash'):
            plan(I['t0'], 'flash %s' % I['id'], after=4)
    cuts_p = os.path.join(P, 'analysis', 'cuts.json')
    if os.path.exists(cuts_p):
        for c in load_json(cuts_p)[1:]:
            plan(c['prog_t0'], 'jump cut (pause removed)')
    for z in (edl.get('zoom') or []):
        plan(z[0], 'framing change')
    for I in ins:                                                          # the punch-in before an insert and the release after it
        plan(I['t0'] - 0.18, 'punch-in before %s' % I['id'], after=6)
    unplanned = [k for k in spikes if k not in planned]
    groups = []
    for k in unplanned:
        if groups and k - groups[-1][-1] <= 2:
            groups[-1].append(k)
        else:
            groups.append([k])
    note(not groups, 'no unplanned jump between frames',
         ', '.join('%.2f s (frame %d, change %.0f)' % (g[0] / fps, g[0], diff[g[0] - 1]) for g in groups[:8]) or
         '%d jumps, all at planned changes' % len(spikes))

    still, run0, dead = diff < 0.03, None, []
    for k, s in enumerate(list(still) + [False]):
        if s and run0 is None:
            run0 = k
        elif not s and run0 is not None:
            if (k - run0) / fps > 1.0:
                dead.append('%.1f-%.1f s' % (run0 / fps, k / fps))
            run0 = None
    note(not dead, 'something is always moving (no frozen stretch over 1 s)', ', '.join(dead[:6]))
    note(fr[0].mean() > 12 and fr[-1].mean() > 12, 'first and last frame are not black', 'luma %.0f / %.0f' % (fr[0].mean(), fr[-1].mean()))

    has_audio = bool(aline)
    lufs = None
    if has_audio:
        err = subprocess.run([ff, '-hide_banner', '-nostats', '-i', a.video, '-map', '0:a', '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                             capture_output=True, text=True, stdin=subprocess.DEVNULL).stderr
        m = re.findall(r'I:\s+(-?[\d.]+) LUFS', err)
        pk = re.findall(r'Peak:\s+(-?[\d.]+) dBFS', err)
        lufs = float(m[-1]) if m else None
        note(lufs is not None and -15.5 <= lufs <= -12.5, 'loudness near -14 LUFS', '%s LUFS, true peak %s dBFS' % (lufs, pk[-1] if pk else '?'))
    else:
        note(False, 'audio stream present', 'the file is silent')

    grab(ff, a.video, 0, 540, 960, fps).save(os.path.join(out_dir, 'first.png'))
    grab(ff, a.video, (n - 1) / fps, 540, 960, fps).save(os.path.join(out_dir, 'last.png'))
    marks = [(I['t0'], '%s in' % I['id']) for I in ins] + [(I['t1'], '%s out' % I['id']) for I in ins]
    marks = sorted(marks)[:16]
    if marks:
        tw, th, pad = 216, 384, 8
        sheet = Image.new('RGB', (4 * (tw + pad) + pad, len(marks) * (th + pad) + pad), (24, 24, 26))
        for r, (t, _) in enumerate(marks):
            k = int(math.ceil(t * fps - 1e-6))
            for c, j in enumerate((k - 1, k, k + 2, k + 5)):
                sheet.paste(grab(ff, a.video, min(max(j, 0), n - 1) / fps, tw, th, fps), (pad + c * (tw + pad), pad + r * (th + pad)))
        sheet.save(os.path.join(out_dir, 'joins.png'))

    md = ['# Render review: %s' % os.path.basename(a.video), '',
          '| result | check | detail |', '|---|---|---|'] + notes + ['',
          '## What this review can and cannot say', '',
          '| status | item |', '|---|---|',
          '| measured by running | file facts, frame count, frame-to-frame jumps, loudness |',
          '| seen in frames | first.png, last.png, joins.png (rows: %s) - LOOK AT THEM before reporting |' % ', '.join(m[1] for m in marks),
          '| NOT checked: motion | nobody has played the file at speed - the person must watch it once |',
          '| NOT checked: sound | nobody has listened to the voice, the effects or the mix |', '',
          'Median frame change %.2f, jump threshold %.1f, %d jumps in total, %d unplanned.' % (med, thr, len(spikes), len(unplanned)), '']
    with open(os.path.join(out_dir, 'review.md'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(md))
    sys.stdout.reconfigure(encoding='utf-8')
    print('\n'.join(notes))
    print('\n%d item(s) to fix. Review -> %s' % (bad, os.path.join(out_dir, 'review.md')))
    print('Now look at first.png, last.png and joins.png. Motion and sound are NOT checked - say so.')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
