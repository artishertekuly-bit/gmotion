#!/usr/bin/env python3
"""Quiet synthesised sound effects (and an optional music bed) under the voice, placed from the EDL.

    python -X utf8 scripts/sfx_from_edl.py PROJECT/edl.json [--gain 0] [--music FILE --music-db -20] [--dry]

The mapping follows the sound rules of the saas-animation skill - sound means something, it is never decoration:
    insert that MOVES in (trans whip / whipL / zoom / bulge)  -> whoosh, its loudest moment in the middle of the move
    insert that cuts or morphs in (trans cut / flood)         -> soft thud / pop - never a whoosh
    insert with a "flash"                                     -> shutter click
    big word (font "anton")                                   -> pop        accent (font "serif") -> soft tick
    the first frame, when anything is on screen by 0.3 s      -> soft low hit
Pill captions get nothing. Any insert or text item may carry "sfx": false, or "sfx": "pop" | "whoosh" | "tick" |
"hit" | "thud" | "shutter" | "riser" to choose the cue.

Every cue is aligned by its PEAK to the first frame that shows the change, and no sample is repeated identically
(pitch and level vary a little). The script prints each cue's offset from its frame - more than one frame is a bug.

Writes audio/program_sfx.wav (voice + effects + music), audio/sfx_stem.wav (effects only) and
analysis/sfx_events.json. To use it set "audio": "audio/program_sfx.wav" in the EDL. Numbers do not prove it sounds
right: nobody has listened until the person does - say so.
"""
import argparse
import math
import os
import re
import subprocess
import sys

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'engine', 'scripts'))
from common import find_ffmpeg, load_json, save_json  # noqa: E402

SR = 48000
PEAK_DB = dict(whoosh=-27.0, pop=-20.0, tick=-26.0, hit=-18.0, thud=-21.0, shutter=-25.0, riser=-24.0, click=-23.0, glitch=-24.0)
MOVES = dict(whip=0.22, whipL=0.22, zoom=0.22, zoomrot=0.22, bulge=0.26)                                 # entry time of moving transitions


def find_sfx_dirs(extra_dir=None, project_dir=None):
    """Discover optional ./soundeffects/ directories (project, cwd, or workspace root)."""
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cands = [
        extra_dir,
        os.environ.get('REEL_SOUNDEFFECTS_DIR'),
        os.path.join(project_dir, 'soundeffects') if project_dir else None,
        os.path.join(os.getcwd(), 'soundeffects'),
        os.path.abspath(os.path.join(skill_dir, '..', '..', '..', 'soundeffects')),
    ]
    out, seen = [], set()
    for d in cands:
        if d:
            ad = os.path.abspath(d)
            if ad not in seen and os.path.isdir(ad):
                seen.add(ad)
                out.append(ad)
    return out


def resolve_external_sfx(kind, sfx_dirs):
    """Find a matching audio file in ./soundeffects/ by exact filename or stem match."""
    target = kind.lower()
    stem_target = os.path.splitext(target)[0]
    for d in sfx_dirs:
        for dp, _, fns in sorted(os.walk(d)):
            for fn in sorted(fns):
                low = fn.lower()
                if not low.endswith(('.wav', '.mp3', '.ogg', '.m4a', '.flac', '.aac')):
                    continue
                if low == target or os.path.splitext(low)[0] == stem_target:
                    return os.path.join(dp, fn)
    return None


def band(x, lo, hi):
    return sosfilt(butter(2, [lo / (SR / 2), min(hi, SR / 2 - 100) / (SR / 2)], 'band', output='sos'), x)


def env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(t / max(attack, 1e-4), 1) * np.exp(-t / decay)


def tone(f0, n, f1=None):
    return np.sin(2 * np.pi * np.cumsum(np.linspace(f0, f1 or f0, n)) / SR)


def make(kind, seed=0):
    rng = np.random.default_rng(seed)
    if kind == 'whoosh':                                   # airy band-passed noise, swept up and back
        n = int(0.42 * SR)
        x, out, seg = rng.standard_normal(n), np.zeros(n), 256
        for i in range(0, n - 2 * seg, seg):
            f = 500 + 4200 * np.sin(np.pi * i / n)
            out[i:i + 2 * seg] += band(x[i:i + 2 * seg], f * 0.6, f * 1.4) * np.hanning(2 * seg)
        return out * np.sin(np.pi * np.arange(n) / n) ** 2
    if kind == 'pop':
        n = int(0.16 * SR)
        return tone(640, n, 190) * env(n, 0.002, 0.032)
    if kind == 'tick':
        n = int(0.05 * SR)
        return band(rng.standard_normal(n), 2500, 9000) * env(n, 0.001, 0.008)
    if kind == 'hit':
        n = int(0.8 * SR)
        return tone(118, n, 44) * env(n, 0.002, 0.19)
    if kind == 'thud':
        n = int(0.4 * SR)
        return (tone(150, n, 60) + 0.25 * band(rng.standard_normal(n), 300, 1500)) * env(n, 0.002, 0.07)
    if kind == 'shutter':
        n = int(0.07 * SR)
        return band(rng.standard_normal(n), 1500, 7000) * env(n, 0.001, 0.012)
    if kind == 'riser':                                     # ends on its mark
        n = int(1.2 * SR)
        u = np.arange(n) / n
        return (band(rng.standard_normal(n), 800, 7000) * 0.5 + tone(110, n, 440) * 0.5) * u ** 2.5
    if kind in ('glitch', 'click'):
        n = int(0.09 * SR)
        burst = band(rng.standard_normal(n), 1800, 6800)
        gate = ((np.arange(n) // int(0.015 * SR)) % 2 == 0).astype(np.float32)
        return burst * gate * env(n, 0.001, 0.022)
    raise ValueError(kind)


def repitch(x, ratio):
    idx = np.arange(0, len(x) - 1, ratio)
    return np.interp(idx, np.arange(len(x)), x)


def events_from_edl(edl, fps):
    def on_frame(t):                                       # the first frame that shows a change made at time t
        return max(0.0, math.ceil(t * fps - 1e-6) / fps)

    ev = []
    inserts = sorted(edl.get('inserts', []), key=lambda i: i['t0'])
    texts = sorted(edl.get('text', []), key=lambda t: t['t0'])
    starts = [i['t0'] for i in inserts] + [t['t0'] for t in texts]
    if starts and min(starts) < 0.3:
        ev.append((0.0, 'hit', 'first frame'))
    for I in inserts:
        s = I.get('sfx')
        if s is False:
            continue
        tr = I.get('trans', 'whip')
        if isinstance(s, str):
            ev.append((on_frame(I['t0']), s, 'insert %s' % I.get('id')))
            continue
        if tr in MOVES:
            ev.append((on_frame(I['t0']) + MOVES[tr] / 2, 'whoosh', 'insert %s moves in (%s)' % (I.get('id'), tr)))
        else:
            ev.append((on_frame(I['t0']), 'pop' if tr == 'flood' else 'thud', 'insert %s (%s)' % (I.get('id'), tr)))
        if I.get('flash'):
            ev.append((on_frame(I['t0']), 'shutter', 'flash %s' % I.get('id')))
    for T in texts:
        s = T.get('sfx')
        if s is False or T['t0'] < 0.02:
            continue
        if T.get('pill') and not isinstance(s, str):
            continue
        kind = s if isinstance(s, str) else {'anton': 'pop', 'impact': 'pop', 'serif': 'tick', 'editorial': 'tick', 'mono': 'tick', 'tech': 'tick'}.get(T.get('font'))
        if kind:
            ev.append((on_frame(T['t0']), kind, T['text'].replace('\n', ' ')[:24]))
    ev.sort()
    out = []
    for t, kind, why in ev:                                # no two cues of one kind closer than 0.18 s; a pop never doubles a thud
        if any((k == kind or {k, kind} == {'pop', 'thud'}) and abs(t - u) < 0.18 for u, k, _ in out):
            continue
        out.append((round(t, 4), kind, why))
    return out


def lufs(ff, path):
    err = subprocess.run([ff, '-hide_banner', '-nostats', '-i', path, '-af', 'ebur128', '-f', 'null', '-'],
                         capture_output=True, text=True, stdin=subprocess.DEVNULL).stderr
    m = re.findall(r'I:\s+(-?[\d.]+) LUFS', err)
    return float(m[-1]) if m else None


def read_audio(ff, path):
    raw = subprocess.run([ff, '-v', 'error', '-i', path, '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True, stdin=subprocess.DEVNULL).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64).copy()


def write_audio(ff, x, path):
    subprocess.run([ff, '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', '-c:a', 'pcm_s24le', path],
                   input=x.astype(np.float32).tobytes(), check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('edl')
    ap.add_argument('--gain', type=float, default=0.0, help='dB added to every cue (negative = quieter)')
    ap.add_argument('--sfx-dir', help='folder with custom audio SFX files (auto-checks ./soundeffects/)')
    ap.add_argument('--voice', help='voice file (default: audio/program_master.wav in the project)')
    ap.add_argument('--music', help='a music file the person supplied; trimmed or looped to the reel, faded in and out')
    ap.add_argument('--music-db', type=float, default=-20.0, help='music level relative to the voice (RMS), dB')
    ap.add_argument('--out', default='audio/program_sfx.wav')
    ap.add_argument('--dry', action='store_true', help='only list the cues')
    a = ap.parse_args()
    edl = load_json(a.edl)
    P = edl.get('project_dir') or os.path.dirname(os.path.abspath(a.edl))
    cfgp = os.path.join(P, 'project.json')
    fps = float(edl.get('fps') or (load_json(cfgp).get('fps') if os.path.exists(cfgp) else 0) or 30)
    ev = events_from_edl(edl, fps)
    sys.stdout.reconfigure(encoding='utf-8')
    sfx_dirs = find_sfx_dirs(a.sfx_dir, P)
    if a.dry:
        for t, kind, why in ev:
            ext = resolve_external_sfx(kind, sfx_dirs) if sfx_dirs else None
            src_tag = os.path.basename(ext) if ext else 'synth'
            print('%7.2f  %-10s [%-12s] %s' % (t, kind, src_tag, why))
        print('%d cues (sfx_dirs: %s)' % (len(ev), ', '.join(sfx_dirs) or 'none'))
        return
    ff = find_ffmpeg()
    voice_path = a.voice or os.path.join(P, 'audio', 'program_master.wav')
    out = os.path.join(P, a.out)
    if os.path.abspath(voice_path) == os.path.abspath(out):
        sys.exit('ERROR: --voice and --out are the same file')
    voice = read_audio(ff, voice_path)
    stem = np.zeros_like(voice)
    kit, rows, worst = {}, [], 0.0
    for n, (t, kind, why) in enumerate(ev):
        if kind not in kit:
            ext = resolve_external_sfx(kind, sfx_dirs) if sfx_dirs else None
            if ext:
                x = read_audio(ff, ext).mean(axis=1)
            else:
                base_kind = kind if kind in ('whoosh', 'pop', 'tick', 'hit', 'thud', 'shutter', 'riser') else 'pop'
                x = make(base_kind, seed=len(kit))
            kit[kind] = x / (np.abs(x).max() + 1e-9)
        x = repitch(kit[kind], 1 + 0.06 * math.sin(1.7 * n + 0.4))                      # never the same sample twice
        peak_db = PEAK_DB.get(kind, PEAK_DB.get(os.path.splitext(kind)[0].lower(), -22.0))
        x = x * 10 ** ((peak_db + a.gain + 1.5 * math.cos(2.3 * n)) / 20.0)
        pk = len(x) - 1 if kind == 'riser' else int(np.abs(x).argmax())                 # the peak (a riser: its end) lands on the mark
        i0 = int(round(t * SR)) - pk
        if i0 < 0:
            x, pk, i0 = x[-i0:], pk + i0, 0
        x = x[:max(0, len(stem) - i0)]
        pan = 0.5 + 0.12 * (1 if n % 2 else -1)
        stem[i0:i0 + len(x), 0] += x * (1 - pan) * 2
        stem[i0:i0 + len(x), 1] += x * pan * 2
        off_ms = ((i0 + max(pk, 0)) / SR - t) * 1000.0
        worst = max(worst, abs(off_ms))
        rows.append(dict(t=t, frame=int(round(t * fps)), kind=kind, why=why, peak_offset_ms=round(off_ms, 2)))
        print('%7.2f s  frame %4d  %-8s %+6.2f ms  %s' % (t, round(t * fps), kind, off_ms, why))
    print('%d cues; worst offset %.2f ms (one frame = %.1f ms)%s' % (len(ev), worst, 1000.0 / fps, '' if worst < 1000.0 / fps else '  <-- BUG'))
    mix = voice + stem
    if a.music:
        mus = read_audio(ff, a.music)
        if len(mus) < len(voice):
            mus = np.tile(mus, (int(math.ceil(len(voice) / float(len(mus)))), 1))
        mus = mus[:len(voice)]
        fi, fo = int(0.4 * SR), int(1.5 * SR)
        mus[:fi] *= np.linspace(0, 1, fi)[:, None]
        mus[-fo:] *= np.linspace(1, 0, fo)[:, None]
        rms = lambda z: float(np.sqrt(np.mean(z ** 2)) + 1e-9)                          # noqa: E731
        mus *= rms(voice) / rms(mus) * 10 ** (a.music_db / 20.0)
        mix += mus
        print('music: %s at %.0f dB under the voice' % (os.path.basename(a.music), -a.music_db))
    peak = float(np.abs(mix).max())
    if peak > 0.97:
        mix *= 0.97 / peak
    write_audio(ff, mix, out)
    write_audio(ff, stem, os.path.join(P, 'audio', 'sfx_stem.wav'))
    save_json(rows, os.path.join(P, 'analysis', 'sfx_events.json'))
    lv, lm = lufs(ff, voice_path), lufs(ff, out)
    print('voice %s LUFS -> mix %s LUFS, peak %.1f dBFS%s' % (lv, lm, 20 * math.log10(min(peak, 0.97) + 1e-9),
                                                             ' (scaled down to avoid clipping)' if peak > 0.97 else ''))
    print('written: %s and audio/sfx_stem.wav' % a.out.replace('\\', '/'))
    print('next: set "audio": "%s" in the EDL and render. NOT LISTENED TO - ask the person to listen.' % a.out.replace('\\', '/'))


if __name__ == '__main__':
    main()
