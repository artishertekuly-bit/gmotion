#!/usr/bin/env python3
"""Setup check for talking-head-kz on Windows (use this instead of engine/scripts/check_setup.py, which is macOS-only).

    python -X utf8 scripts/check_setup_kz.py
"""
import importlib
import os
import shutil
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL, 'engine', 'scripts'))
from common import ffmpeg_candidates, ffmpeg_has_ass  # noqa: E402
import textass  # noqa: E402
from fontmetrics import faces  # noqa: E402

KZ = 'ӘәҒғҚқҢңӨөҰұҮүҺһІі'
DEFAULT_ROLES = dict(anton='SegoeUIBlack', serif='TimesNewRomanPS-BoldItalicMT', didot='TimesNewRomanPS-ItalicMT', sub='SegoeUI-Semibold')
bad = 0


def line(state, what, fix=''):
    global bad
    print('[%s] %s' % (state, what))
    if state != 'ok  ' and fix:
        print('       -> ' + fix)
    if state == 'MISS':
        bad += 1


def cmap_codes(path, face_index=0):
    data = open(path, 'rb').read()
    offs = [0]
    if data[:4] == b'ttcf':
        n = struct.unpack('>I', data[8:12])[0]
        offs = list(struct.unpack('>%dI' % n, data[12:12 + 4 * n]))
    off = offs[min(face_index, len(offs) - 1)]
    num = struct.unpack('>H', data[off + 4:off + 6])[0]
    tb = {}
    for i in range(num):
        tag, _, o, ln = struct.unpack('>4sIII', data[off + 12 + 16 * i: off + 28 + 16 * i])
        tb[tag.decode('latin-1')] = o
    o = tb['cmap']
    codes = set()
    for i in range(struct.unpack('>H', data[o + 2:o + 4])[0]):
        _, _, sub = struct.unpack('>HHI', data[o + 4 + 8 * i:o + 12 + 8 * i])
        s = o + sub
        fmt = struct.unpack('>H', data[s:s + 2])[0]
        if fmt == 4:
            segx2 = struct.unpack('>H', data[s + 6:s + 8])[0]
            ends = struct.unpack('>%dH' % (segx2 // 2), data[s + 14:s + 14 + segx2])
            starts = struct.unpack('>%dH' % (segx2 // 2), data[s + 16 + segx2:s + 16 + 2 * segx2])
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
    sys.stdout.reconfigure(encoding='utf-8')
    print('talking-head-kz setup check\n')
    v = sys.version_info
    line('ok  ' if v >= (3, 9) else 'MISS', 'Python %d.%d (%s)' % (v.major, v.minor, sys.executable), 'use Python 3.9 or newer')
    for mod, why, need in (('numpy', 'compositing every frame', True), ('scipy', 'synthesised sound effects (sfx_from_edl.py)', False)):
        try:
            importlib.import_module(mod)
            line('ok  ', '%s (%s)' % (mod, why))
        except Exception:
            line('MISS' if need else 'warn', '%s (%s)' % (mod, why), 'pip install ' + mod)
    cands = ffmpeg_candidates()
    with_ass = [c for c in cands if ffmpeg_has_ass(c)]
    if with_ass:
        ver = subprocess.run([with_ass[0], '-version'], capture_output=True, text=True).stdout.split('\n')[0]
        line('ok  ', 'ffmpeg with libass: %s' % ver[:60])
    else:
        line('MISS', 'ffmpeg with the libass "ass" filter (all text is drawn with it)', 'winget install Gyan.FFmpeg  (the full build)')

    by_ps = {}
    for src in textass.kz_font_sources():
        if os.path.exists(src):
            for i, f in enumerate(faces(src)):
                if f.get('ps'):
                    by_ps[f['ps']] = (src, i)
    for role, ps in DEFAULT_ROLES.items():
        if ps not in by_ps:
            line('MISS', 'font for "%s": %s not found' % (role, ps), 'put a Kazakh-capable font in assets/fonts and map it with "fonts" in the EDL')
            continue
        codes = cmap_codes(*by_ps[ps])
        miss = ''.join(c for c in KZ if ord(c) not in codes)
        line('ok  ' if not miss else 'MISS', 'font for "%s": %s%s' % (role, ps, '' if not miss else ' - no glyphs for ' + miss),
             'choose another font: python -X utf8 scripts/font_check.py FILE.ttf')
    extra = [ps for ps, (src, _) in by_ps.items() if os.path.dirname(src) == os.path.join(SKILL, 'assets', 'fonts') and ps != 'Anton-Regular']
    if extra:
        print('       extra fonts in assets/fonts: ' + ', '.join(sorted(extra)))

    key = os.environ.get('ELEVENLABS_API_KEY')
    env = os.path.join(os.path.expanduser('~'), 'Motion', '.env')
    if not key and os.path.exists(env):
        key = any(l.strip().startswith('ELEVENLABS_API_KEY') for l in open(env, encoding='utf-8', errors='ignore'))
    line('ok  ' if key else 'warn', 'ElevenLabs key for Scribe transcription (value not shown)', 'add ELEVENLABS_API_KEY to Motion/.env, or write analysis/asr.json by hand')
    line('ok  ' if shutil.which('swiftc') else 'warn', 'matte tools (Apple Vision) - NOT available on Windows',
         'do not use "behind", "cutout", flash "silhouette", cutout_matte or color_figures_matte in the EDL')
    print('\n%s' % ('All required parts are in place.' if not bad else '%d required item(s) missing.' % bad))
    return 2 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
