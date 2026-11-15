#!/usr/bin/env python3
"""Side-by-side "Кейін / Дейін" (after / before) or "A vs B" packaging of a finished reel - the wrapper that got the
reference account its reach (the same edit: 2 K views alone, 61 K and 120 K as a comparison).

    python -X utf8 scripts/compare_pack.py --main AFTER.mp4 --other BEFORE.mp4 --out PACK.mp4
           [--label-main "Кейін"] [--label-other "Дейін"] [--brand "@name"] [--bg "#7A0C10"] [--swap]

--main is the bigger card (its sound is used); --other the smaller one. Both should have the same length and cuts:
for a before/after, render the same EDL once more with empty "inserts" and "text" as the "before".
--swap puts the big card on the right (default: left). Output: 1080x1920 H.264, length of --main.
"""
import argparse
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'engine', 'scripts'))
from common import find_ffmpeg, probe  # noqa: E402

W, H = 1080, 1920


def font(size, names=('seguibl.ttf', 'segoeuib.ttf', 'arialbd.ttf')):
    windir = os.environ.get('WINDIR') or os.environ.get('SystemRoot') or ''
    for n in names:
        p = os.path.join(windir, 'Fonts', n)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def mask(w, h, r, path):
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
    m.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--main', required=True)
    ap.add_argument('--other', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--label-main', default='Кейін')
    ap.add_argument('--label-other', default='Дейін')
    ap.add_argument('--brand', default='')
    ap.add_argument('--bg', default='#7A0C10')
    ap.add_argument('--swap', action='store_true')
    a = ap.parse_args()
    ff = find_ffmpeg()
    dur = probe(a.main, ff)['dur']
    tmp = tempfile.mkdtemp(prefix='pack_')
    mw, mh, ow, oh, r = 520, 924, 410, 729, 34                  # both cards 9:16
    mx, ox = (60, 1080 - 60 - ow) if not a.swap else (1080 - 60 - mw, 60)
    my = 420
    oy = my + (mh - oh) // 2 + 40

    top, bottom = hexrgb(a.bg), tuple(int(c * 0.28) for c in hexrgb(a.bg))
    bg = Image.new('RGB', (W, H))
    d = ImageDraw.Draw(bg)
    for y in range(H):
        k = (y / H) ** 1.3
        d.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3)))
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))                # soft shadows under the cards
    sd = ImageDraw.Draw(sh)
    for x, y, w, h in ((mx, my, mw, mh), (ox, oy, ow, oh)):
        sd.rounded_rectangle([x - 4, y + 14, x + w + 4, y + h + 26], radius=r + 6, fill=(0, 0, 0, 150))
    bg = Image.alpha_composite(bg.convert('RGBA'), sh.filter(ImageFilter.GaussianBlur(22)))
    d = ImageDraw.Draw(bg)
    for txt, x, y, w, size in ((a.label_main, mx, my, mw, 60), (a.label_other, ox, oy, ow, 50)):
        f = font(size)
        tw = d.textlength(txt, font=f)
        d.text((x + (w - tw) / 2, y - size - 34), txt, font=f, fill=(255, 255, 255, 255))
    if a.brand:
        f = font(46, ('segoeuib.ttf', 'arialbd.ttf'))
        d.text(((W - d.textlength(a.brand, font=f)) / 2, 1690), a.brand, font=f, fill=(255, 255, 255, 235))
    bgp = os.path.join(tmp, 'bg.png')
    bg.convert('RGB').save(bgp)
    m1, m2 = os.path.join(tmp, 'm1.png'), os.path.join(tmp, 'm2.png')
    mask(mw, mh, r, m1)
    mask(ow, oh, r - 6, m2)

    fc = ('[1:v]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,format=rgba[a];[3:v]format=gray[ma];[a][ma]alphamerge[a2];'
          '[2:v]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,format=rgba[b];[4:v]format=gray[mb];[b][mb]alphamerge[b2];'
          '[0:v][b2]overlay=%d:%d[t];[t][a2]overlay=%d:%d,format=yuv420p[v]') % (mw, mh, mw, mh, ow, oh, ow, oh, ox, oy, mx, my)
    cmd = [ff, '-v', 'error', '-y', '-loop', '1', '-i', bgp, '-i', a.main, '-i', a.other, '-loop', '1', '-i', m1, '-loop', '1', '-i', m2,
           '-filter_complex', fc, '-map', '[v]', '-map', '1:a?', '-t', '%.3f' % dur, '-r', '30', '-c:v', 'libx264', '-preset', 'medium',
           '-crf', '16', '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', os.path.abspath(a.out)]
    subprocess.run(cmd, check=True, stdin=subprocess.DEVNULL)
    info = probe(a.out, ff)
    print('pack -> %s  %dx%d  %.2f s  audio %s' % (os.path.abspath(a.out), info['w'], info['h'], info['dur'], 'yes' if info['audio'] else 'NO'))


if __name__ == '__main__':
    main()
