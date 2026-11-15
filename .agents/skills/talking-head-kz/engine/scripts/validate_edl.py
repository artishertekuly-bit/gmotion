#!/usr/bin/env python3
"""Check an EDL against the schema and the house style before rendering.

    python3 scripts/validate_edl.py PROJECT_DIR/edl.json

Errors stop the render (broken structure, missing files, overlapping inserts). Warnings point at
style-rule breaks that the user usually catches in review: text too wide, two lines at the bottom,
a big word placed in the subtitle zone, long stretches without an insert, a fourth font, off-palette
colours. Fix them or consciously accept them.
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(_HERE)), 'scripts')
sys.path.insert(0, _HERE)
if os.path.isdir(_SKILL_SCRIPTS):
    sys.path.insert(0, _SKILL_SCRIPTS)
from common import load_json  # noqa: E402
try:
    from hook_registry import HOOK_CATALOG, balance_keyframe_stack  # noqa: E402
except Exception:
    HOOK_CATALOG = {}
    def balance_keyframe_stack(animations, t0=0.0, t1=2.0, role_index=0):  # noqa: E306
        return list(animations or [])[:4], []

KINDS = {'full': ['clips'], 'frame': ['clips', 'rect'], 'band': ['clips'], 'vsplit': ['clips', 'tsplit'], 'logo_flash': ['slots'],
         'cards': ['cards'], 'bar': [], 'converge': ['logos'], 'number': [], 'solid': [], 'cutout': ['bgclip'], 'pframe': [],
         'overlay': []}
TRANS = {'whip', 'whipL', 'zoom', 'zoomrot', 'bulge', 'cut', 'panels', 'flood'}     # KZ patch: flood
FONTS = {'anton', 'serif', 'didot', 'sub', 'mono', 'impact', 'clean', 'editorial', 'tech'}
ANIMS = {'build', 'words', 'word_pop', 'pop', 'soft', 'rise', 'terminal', 'counter', 'slot', 'glitch', 'none'}
CHAR_W = {
    'anton': 0.41, 'impact': 0.44,
    'serif': 0.47, 'didot': 0.45, 'editorial': 0.46,
    'sub': 0.44, 'clean': 0.44,
    'mono': 0.48, 'tech': 0.48,
}
CAPS_W = 1.25


def main():
    path = sys.argv[1]
    edl = load_json(path)
    P = edl.get('project_dir') or os.path.dirname(os.path.abspath(path))
    W, H = edl.get('W', 1080), edl.get('H', 1920)
    accent = edl.get('accent', '#ED3B22').upper()
    palette = {accent, '#FFFFFF', '#EDE6DE', '#FFD600', '#00E676', '#161216', '#0B0B0B', '#000000'}
    err, warn = [], []
    cuts_p = os.path.join(P, (edl.get('presenter') or {}).get('cuts', 'analysis/cuts.json'))
    dur = None
    if os.path.exists(cuts_p):
        cuts = load_json(cuts_p)
        dur = sum(c['src_t1'] - c['src_t0'] for c in cuts)
    else:
        err.append('cut list not found: ' + cuts_p)

    def exists(rel):
        return os.path.exists(rel if os.path.isabs(rel) else os.path.join(P, rel))

    ins = sorted(edl.get('inserts', []), key=lambda i: i['t0'])
    ids = set()
    for k, I in enumerate(ins):
        tag = 'insert %s' % I.get('id')
        if I.get('id') in ids:
            err.append(tag + ': duplicate id')
        ids.add(I.get('id'))
        if I.get('kind') not in KINDS:
            err.append(tag + ': unknown kind %s' % I.get('kind'))
            continue
        for req in KINDS[I['kind']]:
            if not I.get(req):
                err.append(tag + ': needs "%s"' % req)
        if I['t1'] <= I['t0']:
            err.append(tag + ': t1 must be after t0')
        if I['t1'] - I['t0'] < 0.6:
            warn.append(tag + ': only %.2f s - inserts under ~0.6 s read as a glitch' % (I['t1'] - I['t0']))
        if dur and I['t1'] > dur + 0.02:
            err.append(tag + ': ends after the program (%.2f s)' % dur)
        if k and I['t0'] < ins[k - 1]['t1'] - 0.02:
            err.append(tag + ': overlaps %s' % ins[k - 1]['id'])
        if I.get('layout', 'full') not in ('full', 'split'):
            err.append(tag + ': layout must be full or split')
        if I.get('trans', 'whip') not in TRANS:
            err.append(tag + ': unknown transition %s' % I.get('trans'))
        if I['kind'] == 'vsplit' and len(I.get('clips') or []) < 2:
            err.append(tag + ': vsplit needs two clips')
        for c in (I.get('clips') or []) + ([I['bgclip']] if I.get('bgclip') else []) + ([I['overlay']] if isinstance(I.get('overlay'), dict) else []):
            if not c.get('src'):
                continue
            if not exists(c['src']):
                if I.get('html_hook') or I.get('preset'):
                    warn.append(tag + ': cloud overlay %s pending Chromium render of %s' % (c['src'], I.get('preset') or I.get('html_hook')))
                else:
                    err.append(tag + ': clip missing %s' % c.get('src'))
            for mk in ('cutout_matte', 'color_figures_matte'):
                if c.get(mk) and not exists(c[mk]):
                    err.append(tag + ': %s missing %s' % (mk, c[mk]))
            if c.get('src', '').lower().endswith(('.jpg', '.jpeg', '.png')):
                warn.append(tag + ': still image %s - prefer moving footage (a photo needs a push or parallax at least)' % c['src'])
        if I.get('preset') and HOOK_CATALOG and I['preset'] not in HOOK_CATALOG:
            err.append(tag + ': unknown preset %s' % I['preset'])
        if k and I.get('preset') and ins[k - 1].get('preset') == I.get('preset'):
            warn.append(tag + ': anti-repeat violation — same preset "%s" twice in a row' % I['preset'])
        if I['kind'] == 'overlay' and not (I.get('clips') or I.get('overlay') or I.get('html_hook') or I.get('preset')):
            err.append(tag + ': overlay needs "overlay", "clips", "html_hook", or "preset"')
        for key in [s[0] for s in I.get('slots', [])] + list(I.get('logos', []) if I['kind'] == 'converge' else []) + \
                [c.get('logo') for c in I.get('cards', []) if c.get('logo')]:
            if key not in (edl.get('logos') or {}):
                err.append(tag + ': logo key "%s" not in "logos"' % key)
    prev = 0.0
    for I in ins:
        if I['t0'] - prev > 6.0:
            warn.append('presenter alone %.1f-%.1f s (%.1f s) - the style wants a visual change every ~2-4 s' % (prev, I['t0'], I['t0'] - prev))
        prev = I['t1']
    if dur and dur - prev > 6.0:
        warn.append('presenter alone at the end %.1f-%.1f s' % (prev, dur))

    texts = edl.get('text', [])
    for T in texts:
        tag = 'text "%s" @%.2f' % (T.get('text', '')[:24], T.get('t0', -1))
        if T.get('font') not in FONTS:
            err.append(tag + ': font must be one of %s' % sorted(FONTS))
            continue
        wf = T.get('word_fonts')
        if isinstance(wf, list):
            for r in wf:
                if r and r not in FONTS:
                    err.append(tag + ': word_fonts entry "%s" unknown' % r)
        elif isinstance(wf, dict):
            for r in wf.values():
                if r and r not in FONTS:
                    err.append(tag + ': word_fonts entry "%s" unknown' % r)
        if T.get('anim', 'pop') not in ANIMS:
            err.append(tag + ': unknown anim %s' % T.get('anim'))
        for req in ('text', 't0', 't1', 'size'):
            if req not in T:
                err.append(tag + ': needs %s' % req)
        if 'y' not in T and not T.get('behind'):
            err.append(tag + ': needs y')
        if T.get('t1', 0) <= T.get('t0', 0):
            err.append(tag + ': t1 must be after t0')
        lines = T.get('text', '').split('\n')
        if len([ln for ln in lines if ln.strip()]) > 3:
            warn.append(tag + ': more than three lines - split it into separate text items')
        longest = max(lines, key=len)
        caps = T['font'] not in ('anton', 'impact') and longest.isupper()
        est = CHAR_W[T['font']] * (CAPS_W if caps else 1) * T.get('size', 0) * len(longest)
        if not T.get('behind') and est > 0.89 * W:
            warn.append(tag + ': ~%d px wide (> %d) - %s' % (est, 0.89 * W, 'the renderer will shrink it to fit' if T.get('fit', True) else
                                                             '"fit": false keeps it - check it is inside the frame'))
        if not T.get('behind') and T.get('y', 0) >= 0.78 * H:
            warn.append(tag + ': text in the bottom fifth - the house style keeps all text between y 700 and 1350')
        col = T.get('color', '#FFFFFF').upper()
        if col not in palette:
            warn.append(tag + ': colour %s is off-palette (accent, white)' % col)
        if T['font'] == 'anton' and T.get('text', '') != T.get('text', '').upper():
            warn.append(tag + ': big Anton words are set in capitals')
    subs = sorted([T for T in texts if T.get('anim') == 'words'], key=lambda T: T['t0'])
    for a, b in zip(subs, subs[1:]):
        if a['t1'] > b['t0'] + 0.01 and abs(a.get('y', 0) - b.get('y', 0)) < 120:
            warn.append('subtitles overlap: "%s" and "%s" (only one line at a time)' % (a['text'][:20], b['text'][:20]))

    # Compound Keyframe Density Law [2..4] validation + auto-balance
    balanced_any = False
    for list_key in ('beats', 'keyframes'):
        for idx, item in enumerate(edl.get(list_key) or []):
            anim_stack = item.get('animations')
            if anim_stack is None:
                continue
            n_layers = len(anim_stack) if isinstance(anim_stack, list) else 0
            if n_layers < 2 or n_layers > 4:
                bid = item.get('id', idx)
                balanced, _ = balance_keyframe_stack(anim_stack, t0=item.get('t0', 0.0), t1=item.get('t1', 2.0), role_index=idx)
                warn.append('%s %s has %d animation layer(s) (must be 2..4) -> auto-balanced to %d' % (
                    list_key[:-1], bid, n_layers, len(balanced)))
                item['animations'] = balanced
                balanced_any = True

    if balanced_any and '--no-fix' not in sys.argv:
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(edl, fh, indent=2, ensure_ascii=False)
            fh.write('\n')

    for e in err:
        print('ERROR  ' + e)
    for w in warn:
        print('warn   ' + w)
    print('\n%d inserts, %d text items, program %.2f s: %d error(s), %d warning(s)'
          % (len(ins), len(texts), dur or 0, len(err), len(warn)))
    sys.exit(1 if err else 0)


if __name__ == '__main__':
    main()
