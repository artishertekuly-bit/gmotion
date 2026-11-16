#!/usr/bin/env python3
"""Zero-Bloat Cloud Headless Chromium Renderer for 2-3 Compact Hero Hook Composites.

Pipes RGBA PNG buffers straight from Playwright into FFmpeg `image2pipe` -> lightweight
WebM (VP9 yuva420p alpha) at compact card dimensions (880x420 / 920x520, zero PNG temp dump on disk).

LOCAL LAPTOP PROTECTION:
    Refuses to run locally on <12 GB RAM Windows machines unless `--force-local` is passed.

Usage:
    python -X utf8 scripts/render_hooks_chromium.py PROJECT/kz_edl.json [--fps 30]
"""
import argparse
import ctypes
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL, 'engine', 'scripts'))
sys.path.insert(0, HERE)
from common import find_ffmpeg, load_json  # noqa: E402
from hook_registry import HERO_CATALOG  # noqa: E402


def _to_file_url(p):
    ap = os.path.abspath(p).replace('\\', '/')
    return 'file://' + ('' if ap.startswith('/') else '/') + ap


def _skill_assets_url_map():
    key_map = {
        'dossier': os.path.join(SKILL, 'assets', 'frazix', 'frazix_dossier_card.png'),
        'barcode': os.path.join(SKILL, 'assets', 'frazix', 'frazix_barcode.png'),
        'dotgrid': os.path.join(SKILL, 'assets', 'frazix', 'frazix_dotgrid.png'),
        'sparkleGold': os.path.join(SKILL, 'assets', 'frazix', 'frazix_sparkle_gold.png'),
        'sparkleRed': os.path.join(SKILL, 'assets', 'frazix', 'frazix_sparkle_red.png'),
        'card': os.path.join(SKILL, 'assets', '3d', 'card_3d_bakyt.png'),
        'compass': os.path.join(SKILL, 'assets', '3d', 'compass_3d_gold.png'),
        'fakt': os.path.join(SKILL, 'assets', 'graffiti', 'badge_fakt.png'),
        'erezhe': os.path.join(SKILL, 'assets', 'graffiti', 'badge_erezhe.png'),
        'torn': os.path.join(SKILL, 'assets', 'graffiti', 'torn_paper_strip.png'),
        'arrow': os.path.join(SKILL, 'assets', 'graffiti', 'arrow_red_loop.png'),
        'arrowDown': os.path.join(SKILL, 'assets', 'graffiti', 'arrow_yellow_down.png'),
        'ovalRed': os.path.join(SKILL, 'assets', 'graffiti', 'oval_red.png'),
        'ovalCyan': os.path.join(SKILL, 'assets', 'graffiti', 'oval_cyan.png'),
        'ulYellow': os.path.join(SKILL, 'assets', 'graffiti', 'underline_yellow.png'),
        'ulRed': os.path.join(SKILL, 'assets', 'graffiti', 'underline_red.png'),
    }
    return {k: _to_file_url(v) for k, v in key_map.items() if os.path.exists(v)}


def system_ram_gb():
    if os.name == 'nt':
        class MEM(ctypes.Structure):
            _fields_ = [
                ('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong),
                ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                ('sullAvailExtendedVirtual', ctypes.c_ulonglong),
            ]
        m = MEM()
        m.dwLength = ctypes.sizeof(MEM)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return m.ullTotalPhys / (1024 ** 3)
    try:
        with open('/proc/meminfo') as fh:
            for ln in fh:
                if ln.startswith('MemTotal:'):
                    return int(ln.split()[1]) / (1024 ** 2)
    except Exception:
        pass
    return 16.0


def render_html_to_video(html_path, out_path, dur, fps=30, width=880, height=420, alpha=True, params=None):
    """Stream deterministic Chromium frames straight via image2pipe into compact VP9 alpha WebM."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit('ERROR: playwright is required in cloud CI (`pip install playwright && playwright install chromium`).')

    ff = find_ffmpeg()
    n_frames = max(1, int(round(dur * fps)))
    url = _to_file_url(html_path)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    hook_params = dict(params or {})
    hook_params.setdefault('dur', float(dur))
    hook_params.setdefault('W', int(width))
    hook_params.setdefault('H', int(height))
    hook_params['assets'] = dict(_skill_assets_url_map(), **(hook_params.get('assets') or {}))
    core_js = os.path.join(SKILL, 'assets', 'hooks', '_hook_core.js')

    if out_path.lower().endswith('.webm'):
        codec = ['-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p' if alpha else 'yuv420p',
                 '-crf', '24', '-b:v', '0', '-auto-alt-ref', '0', '-deadline', 'good', '-cpu-used', '4']
    elif out_path.lower().endswith('.mov'):
        codec = ['-c:v', 'qtrle', '-pix_fmt', 'argb'] if alpha else ['-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p']
    else:
        codec = ['-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p']

    ff_cmd = [
        ff, '-v', 'error', '-y',
        '-f', 'image2pipe', '-vcodec', 'png', '-r', str(fps), '-i', '-',
    ] + codec + [out_path]
    enc = subprocess.Popen(ff_cmd, stdin=subprocess.PIPE)

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    '--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl',
                    '--ignore-gpu-blocklist', '--disable-dev-shm-usage',
                ],
            )
            page = browser.new_page(viewport={'width': int(width), 'height': int(height)}, device_scale_factor=1)
            payload_json = json.dumps(hook_params, ensure_ascii=False)
            page.add_init_script(f'window.EDL_PAYLOAD = {payload_json}; window.__HOOK_PARAMS__ = window.EDL_PAYLOAD;')
            if os.path.exists(core_js):
                page.add_init_script(path=core_js)
            page.goto(url, wait_until='networkidle')
            page.evaluate('() => Promise.all([document.fonts.ready, window.__HOOK_ASSETS_READY__ || Promise.resolve()])')

            for k in range(n_frames):
                t = k / float(fps)
                page.evaluate('(t) => { if (typeof window.seek === "function") window.seek(t); }', t)
                png_bytes = page.screenshot(type='png', omit_background=bool(alpha), animations='allow')
                enc.stdin.write(png_bytes)
            browser.close()
    finally:
        if enc.stdin:
            enc.stdin.close()
        rc = enc.wait()
        if rc != 0:
            sys.exit(f'ERROR: ffmpeg image2pipe failed ({rc}) for {out_path}')

    kb = os.path.getsize(out_path) / 1024.0 if os.path.exists(out_path) else 0.0
    print(f'rendered Hero WebM ({width}x{height}@{fps}fps, {n_frames}f, {kb:.0f} KB): {out_path}')


def main():
    ap = argparse.ArgumentParser(description='Render 2-3 Hero Hooks into compact WebM VP9 alpha (zero disk bloat).')
    ap.add_argument('edl', nargs='?', help='Path to EDL JSON')
    ap.add_argument('--html', help='Single HTML file mode')
    ap.add_argument('--dur', type=float, default=3.5)
    ap.add_argument('--out')
    ap.add_argument('--fps', type=int, default=30)
    ap.add_argument('--width', type=int, default=880)
    ap.add_argument('--height', type=int, default=420)
    ap.add_argument('--alpha', action='store_true', default=True)
    ap.add_argument('--no-alpha', dest='alpha', action='store_false')
    ap.add_argument('--force-local', action='store_true', help='Override low-RAM Windows protection')
    a = ap.parse_args()

    ram = system_ram_gb()
    if os.name == 'nt' and ram < 12.0 and not a.force_local:
        sys.exit(
            f'BLOCKED (Local PC Protection): detected Windows with {ram:.1f} GB RAM. '
            'Run Hero Hook rendering in GitHub Actions (.github/workflows/render-master-reel.yml).'
        )

    if a.html:
        if not a.out:
            ap.error('--out is required with --html')
        render_html_to_video(a.html, a.out, a.dur, fps=a.fps, width=a.width, height=a.height, alpha=a.alpha)
        return

    if not a.edl:
        ap.error('Provide an EDL path or --html')

    edl = load_json(a.edl)
    P = edl.get('project_dir') or os.path.dirname(os.path.abspath(a.edl))
    accent_default = edl.get('accent', '#FFD600')
    pw_path = os.path.join(P, 'analysis', 'program_words.json')
    pwords = load_json(pw_path) if os.path.exists(pw_path) else []

    rendered = 0
    for ins in edl.get('inserts', []):
        preset = ins.get('preset')
        meta = HERO_CATALOG.get(preset, {})
        hk = ins.get('html_hook') or ins.get('custom_html_scene') or meta.get('html')
        if not hk:
            continue
        html_abs = hk if os.path.isabs(hk) else os.path.join(P, hk)
        if not os.path.exists(html_abs):
            skill_rel = os.path.join(SKILL, hk)
            if os.path.exists(skill_rel):
                html_abs = skill_rel
        if not os.path.exists(html_abs):
            sys.exit(f"ERROR: insert {ins.get('id')} missing html_hook: {hk}")

        dur = float(ins['t1'] - ins['t0'])
        cw = int(ins.get('width') or meta.get('width') or a.width)
        ch = int(ins.get('height') or meta.get('height') or a.height)
        target_rel = os.path.join('hooks_rendered', f"{ins.get('id', 'hero')}.webm").replace('\\', '/')
        if isinstance(ins.get('overlay'), dict) and ins['overlay'].get('src'):
            target_rel = ins['overlay']['src']
        ins['kind'] = 'overlay'
        ins['depth'] = 'front'
        ins['overlay'] = {'src': target_rel}
        ins.setdefault('x', meta.get('x', 540))
        ins.setdefault('y', meta.get('y', 380))
        ins.setdefault('blur_bg', bool(meta.get('blur_bg', False)))
        target_abs = target_rel if os.path.isabs(target_rel) else os.path.join(P, target_rel)

        spoken = ' '.join(w['w'].strip() for w in pwords if ins['t0'] - 0.15 <= w['s'] < ins['t1'] - 0.02)
        params = dict(ins.get('params') or {})
        for k in ('title', 'subtitle', 'label', 'stamp', 'badge', 'asset', 'from', 'to', 'suffix', 'accent', 'accent2', 'kpis', 'items'):
            if k in ins and k not in params:
                params[k] = ins[k]
        params.setdefault('accent', accent_default)
        params.setdefault('spoken_words', spoken)
        params.update({'dur': dur, 'W': cw, 'H': ch})

        render_html_to_video(html_abs, target_abs, dur, fps=a.fps, width=cw, height=ch, alpha=True, params=params)
        rendered += 1

    with open(a.edl, 'w', encoding='utf-8') as fh:
        json.dump(edl, fh, indent=2, ensure_ascii=False)
        fh.write('\n')
    print(f'Rendered {rendered} compact WebM VP9-alpha Hero Hook(s) for {a.edl}')


if __name__ == '__main__':
    main()
