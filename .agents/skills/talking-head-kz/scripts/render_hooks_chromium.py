#!/usr/bin/env python3
"""Cloud-first Headless Chromium 60fps renderer for 40% HTML / Three.js / Canvas / SVG hooks & B-roll.

Reads standalone HTML animations implementing deterministic `window.seek(t)` (virtual-clock pattern
from reanimate & opus-video-prompts), captures transparent RGBA or opaque frames with Playwright +
Chromium (--use-angle=swiftshader), and encodes pixel-accurate `.mov` (qtrle RGBA) for `render_reel.py`.

LOCAL LAPTOP PROTECTION:
    By default this script REFUSES to launch Chromium on local Windows laptops (<12 GB RAM) unless
    `--force-local` is passed, preventing RAM exhaustion on 8 GB HDD laptops. Run inside GitHub Actions.

Usage:
    python -X utf8 scripts/render_hooks_chromium.py PROJECT/edl.json [--fps 60] [--out-dir PROJECT/hooks_rendered]
    python -X utf8 scripts/render_hooks_chromium.py --html hook.html --dur 3.5 --out hook.mov --alpha
"""
import argparse
import ctypes
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL, 'engine', 'scripts'))
sys.path.insert(0, HERE)
from common import find_ffmpeg, load_json  # noqa: E402
from hook_registry import HOOK_CATALOG  # noqa: E402


def _to_file_url(p):
    ap = os.path.abspath(p).replace('\\', '/')
    return 'file://' + ('' if ap.startswith('/') else '/') + ap


def _skill_assets_url_map():
    """Map short asset keys -> file:// URLs across assets/3d, assets/frazix, assets/graffiti, and halftone."""
    key_map = {
        'dossier': os.path.join(SKILL, 'assets', 'frazix', 'frazix_dossier_card.png'),
        'barcode': os.path.join(SKILL, 'assets', 'frazix', 'frazix_barcode.png'),
        'dotgrid': os.path.join(SKILL, 'assets', 'frazix', 'frazix_dotgrid.png'),
        'sparkleGold': os.path.join(SKILL, 'assets', 'frazix', 'frazix_sparkle_gold.png'),
        'sparkleRed': os.path.join(SKILL, 'assets', 'frazix', 'frazix_sparkle_red.png'),
        'sparkle': os.path.join(SKILL, 'assets', 'frazix', 'frazix_sparkle_gold.png'),
        'card': os.path.join(SKILL, 'assets', '3d', 'card_3d_bakyt.png'),
        'compass': os.path.join(SKILL, 'assets', '3d', 'compass_3d_gold.png'),
        'fakt': os.path.join(SKILL, 'assets', 'graffiti', 'badge_fakt.png'),
        'erezhe': os.path.join(SKILL, 'assets', 'graffiti', 'badge_erezhe.png'),
        'torn': os.path.join(SKILL, 'assets', 'graffiti', 'torn_paper_strip.png'),
        'arrow': os.path.join(SKILL, 'assets', 'graffiti', 'arrow_red_loop.png'),
        'ovalRed': os.path.join(SKILL, 'assets', 'graffiti', 'oval_red.png'),
        'ovalCyan': os.path.join(SKILL, 'assets', 'graffiti', 'oval_cyan.png'),
        'ulYellow': os.path.join(SKILL, 'assets', 'graffiti', 'underline_yellow.png'),
        'ulRed': os.path.join(SKILL, 'assets', 'graffiti', 'underline_red.png'),
        'halftone': os.path.join(SKILL, 'engine', 'assets', 'textures', 'halftone_1080x1920.png'),
    }
    return {k: _to_file_url(v) for k, v in key_map.items() if os.path.exists(v)}


def system_ram_gb():
    if os.name == 'nt':
        class MEM(ctypes.Structure):
            _fields_ = [
                ('dwLength', ctypes.c_ulong),
                ('dwMemoryLoad', ctypes.c_ulong),
                ('ullTotalPhys', ctypes.c_ulonglong),
                ('ullAvailPhys', ctypes.c_ulonglong),
                ('ullTotalPageFile', ctypes.c_ulonglong),
                ('ullAvailPageFile', ctypes.c_ulonglong),
                ('ullTotalVirtual', ctypes.c_ulonglong),
                ('ullAvailVirtual', ctypes.c_ulonglong),
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


def render_html_to_video(html_path, out_path, dur, fps=60, width=1080, height=1920, alpha=True, params=None):
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
    hook_params['assets'] = dict(_skill_assets_url_map(), **(hook_params.get('assets') or {}))

    with tempfile.TemporaryDirectory(prefix='hk_') as tmp:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    '--use-gl=angle',
                    '--use-angle=swiftshader',
                    '--enable-webgl',
                    '--ignore-gpu-blocklist',
                    '--disable-dev-shm-usage',
                ],
            )
            page = browser.new_page(viewport={'width': width, 'height': height}, device_scale_factor=1)
            page.add_init_script(f'window.__HOOK_PARAMS__ = {json.dumps(hook_params, ensure_ascii=False)};')
            page.goto(url, wait_until='networkidle')
            page.evaluate('() => Promise.all([document.fonts.ready, window.__HOOK_ASSETS_READY__ || Promise.resolve()])')

            for k in range(n_frames):
                t = k / float(fps)
                page.evaluate(
                    '''(t) => {
                        if (typeof window.seek === 'function') window.seek(t);
                        window.__t = t;
                    }''',
                    t,
                )
                page.screenshot(
                    path=os.path.join(tmp, f'f_{k:05d}.png'),
                    omit_background=bool(alpha),
                    animations='allow',
                )
            browser.close()

        pattern = os.path.join(tmp, 'f_%05d.png')
        if out_path.lower().endswith('.mov'):
            codec = ['-c:v', 'qtrle', '-pix_fmt', 'argb'] if alpha else ['-c:v', 'libx264', '-crf', '14', '-pix_fmt', 'yuv420p']
        else:
            codec = ['-c:v', 'libx264', '-preset', 'medium', '-crf', '14', '-pix_fmt', 'yuv420p']
        subprocess.run(
            [ff, '-v', 'error', '-y', '-framerate', str(fps), '-i', pattern] + codec + [out_path],
            check=True,
            stdin=subprocess.DEVNULL,
        )
    print(f'rendered HTML hook ({fps} fps, {n_frames} frames, alpha={alpha}): {out_path}')


def main():
    ap = argparse.ArgumentParser(description='Render HTML/Three.js motion hooks in Headless Chromium (Cloud CI).')
    ap.add_argument('edl', nargs='?', help='Path to EDL JSON containing inserts with "html_hook"')
    ap.add_argument('--html', help='Single HTML file to render instead of scanning an EDL')
    ap.add_argument('--dur', type=float, default=3.0, help='Duration for --html mode')
    ap.add_argument('--out', help='Output video path for --html mode')
    ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--width', type=int, default=1080)
    ap.add_argument('--height', type=int, default=1920)
    ap.add_argument('--alpha', action='store_true', default=True)
    ap.add_argument('--no-alpha', dest='alpha', action='store_false')
    ap.add_argument('--force-local', action='store_true', help='Override low-RAM Windows protection')
    a = ap.parse_args()

    ram = system_ram_gb()
    if os.name == 'nt' and ram < 12.0 and not a.force_local:
        sys.exit(
            f'BLOCKED (Local PC Protection): detected Windows with {ram:.1f} GB RAM. '
            'Headless Chromium 60fps rendering must run in GitHub Actions (.github/workflows/render-master-reel.yml). '
            'Pass --force-local only if you intentionally want to override this safeguard.'
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
    W = int(edl.get('W', a.width))
    H = int(edl.get('H', a.height))
    accent_default = edl.get('accent', '#FFD600')
    rendered = 0
    for ins in edl.get('inserts', []):
        preset = ins.get('preset')
        hk = ins.get('html_hook') or (HOOK_CATALOG[preset]['html'] if preset in HOOK_CATALOG else None)
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
        target_rel = (ins.get('overlay') or {}).get('src') or (ins.get('clips') or [{}])[0].get('src')
        if not target_rel:
            target_rel = os.path.join('hooks_rendered', f"{ins.get('id', 'hook')}.mov")
            ins['overlay'] = {'src': target_rel}
        target_abs = target_rel if os.path.isabs(target_rel) else os.path.join(P, target_rel)
        alpha = bool(ins.get('alpha', ins.get('kind') == 'overlay'))
        params = dict(ins.get('params') or {})
        for k in ('title', 'subtitle', 'label', 'from', 'to', 'suffix', 'accent'):
            if k in ins and k not in params:
                params[k] = ins[k]
        params.setdefault('accent', accent_default)
        params.setdefault('dur', dur)
        render_html_to_video(html_abs, target_abs, dur, fps=a.fps, width=W, height=H, alpha=alpha, params=params)
        rendered += 1

    if rendered:
        with open(a.edl, 'w', encoding='utf-8') as fh:
            json.dump(edl, fh, indent=1, ensure_ascii=False)
    print(f'chromium hooks complete: {rendered} overlay(s) rendered.')


if __name__ == '__main__':
    main()
