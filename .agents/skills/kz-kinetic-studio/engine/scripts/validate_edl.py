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
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL_ROOT = os.path.dirname(os.path.dirname(_HERE))
_SKILL_SCRIPTS = os.path.join(_SKILL_ROOT, 'scripts')
sys.path.insert(0, _HERE)
if os.path.isdir(_SKILL_SCRIPTS):
    sys.path.insert(0, _SKILL_SCRIPTS)
from common import load_json  # noqa: E402
try:
    from hook_registry import (  # noqa: E402
        BANNED_DARK_BGS,
        BANNED_PLACEHOLDERS,
        COMMON_KZ_TYPOS,
        HERO_CATALOG,
        HOOK_CATALOG,
        MAX_HERO_HOOKS,
        MIN_HERO_HOOKS,
        VALID_CAMERA_EFFECTS,
        balance_keyframe_stack,
    )
except Exception:
    HERO_CATALOG = HOOK_CATALOG = {}
    MIN_HERO_HOOKS, MAX_HERO_HOOKS = 2, 3
    BANNED_DARK_BGS = {'#000000', '#05070A', '#0B0B0E', '#080A0E', '#0D0D12'}
    BANNED_PLACEHOLDERS = ('88%', 'негізгі көрсеткіш', 'todo', 'placeholder', 'lorem ipsum')
    COMMON_KZ_TYPOS = {'көремен': 'көрермен'}
    VALID_CAMERA_EFFECTS = {
        'punch_in', 'slow_push_in', 'dramatic_pull_out', 'speaker_whip_pan',
        'handheld_breathing', 'zoom_push', 'smooth_pan', 'micro_shake', 'snap_punch',
    }
    def balance_keyframe_stack(animations, t0=0.0, t1=2.0, role_index=0):  # noqa: E306
        return list(animations or [])[:4], []

KINDS = {'full': [], 'split': [], 'frame': ['clips', 'rect'], 'band': ['clips'], 'vsplit': ['clips', 'tsplit'], 'logo_flash': ['slots'],
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
                if I.get('html_hook') or I.get('custom_html_scene') or I.get('preset'):
                    warn.append(tag + ': cloud scene %s pending Chromium render of %s' % (c['src'], I.get('preset') or I.get('custom_html_scene') or I.get('html_hook')))
                else:
                    err.append(tag + ': clip missing %s' % c.get('src'))
            for mk in ('cutout_matte', 'color_figures_matte'):
                if c.get(mk) and not exists(c[mk]):
                    err.append(tag + ': %s missing %s' % (mk, c[mk]))
            if c.get('src', '').lower().endswith(('.jpg', '.jpeg', '.png')):
                warn.append(tag + ': still image %s - prefer moving footage (a photo needs a push or parallax at least)' % c['src'])
        if I.get('preset') and HOOK_CATALOG and I['preset'] not in HOOK_CATALOG:
            err.append(tag + ': unknown preset %s' % I['preset'])
        if I['kind'] in ('full', 'split') and not (I.get('clips') or I.get('html_hook') or I.get('custom_html_scene') or I.get('preset')):
            err.append(tag + ': %s needs "clips", "preset", "html_hook", or "custom_html_scene"' % I['kind'])
        if I['kind'] == 'overlay' and not (I.get('clips') or I.get('overlay') or I.get('html_hook') or I.get('custom_html_scene') or I.get('preset')):
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

    # =========================================================================
    # KZ-KINETIC-STUDIO STRICT COMPILER GATE (6 Unbreakable Studio Rules)
    # =========================================================================
    beats = edl.get('beats') or []
    prog_dur = dur or max([t.get('t1', 0) for t in texts] + [i.get('t1', 0) for i in ins] + [1.0])

    # Rule 1: Strictly 2..3 High-Craft Hero Hooks (no 7-card bloat)
    if len(ins) < MIN_HERO_HOOKS or len(ins) > MAX_HERO_HOOKS:
        err.append(
            'ValidationError [Rule 1]: reel must have strictly %d..%d Hero Hooks, found %d' % (
                MIN_HERO_HOOKS, MAX_HERO_HOOKS, len(ins)
            )
        )

    # Rule 2: Zero Black Screen Law (speaker stays live 100%; no dark split/full black backgrounds)
    for i in ins:
        bg = str(i.get('bg', '')).upper()
        if bg in BANNED_DARK_BGS:
            err.append('ValidationError [Rule 2]: insert "%s" uses banned black backdrop %s' % (i.get('id'), bg))
        if i.get('layout') == 'split':
            err.append('ValidationError [Rule 2]: insert "%s" uses banned black split mode (use transparent overlay Hero composite over live speaker)' % i.get('id'))
        if i.get('kind') in ('full', 'solid') and not i.get('clips'):
            err.append('ValidationError [Rule 2]: insert "%s" uses black/solid full cutaway instead of transparent overlay Hero Hook' % i.get('id'))

    # Rule 3: Locked Safe Zone (y=1280..1520) + No behind_hair subtitles + No orphan short tokens + Zero repeats
    for t in texts:
        if t.get('behind'):
            err.append('ValidationError [Rule 3]: caption "%s" uses behind=True (keywords must explode inline in subtitle lane)' % t.get('text', '')[:20])
        if t.get('caption_format'):
            yt = float(t.get('y', 1380))
            if yt < 1260 or yt > 1540:
                err.append('ValidationError [Rule 3]: subtitle "%s" @%.2fs outside locked safe zone y=1280..1520 (y=%g)' % (
                    t.get('text', '')[:20], t.get('t0', 0), yt
                ))
            raw_tok = re.sub(r'[?!.,:;«»"\s]+', '', t.get('text', '').lower())
            if raw_tok and not raw_tok.isdigit() and len(raw_tok) < 3:
                err.append('ValidationError [Rule 3]: subtitle "%s" @%.2fs is an orphan <3-char syllable/particle' % (
                    t.get('text', ''), t.get('t0', 0)
                ))

    for k in range(1, len(ins)):
        p_prev = ins[k - 1].get('preset') or ins[k - 1].get('custom_html_scene') or ins[k - 1].get('kind')
        p_cur = ins[k].get('preset') or ins[k].get('custom_html_scene') or ins[k].get('kind')
        if p_prev and p_cur and p_prev == p_cur:
            err.append('ValidationError [Rule 3]: adjacent Hero Hooks "%s" and "%s" repeat preset "%s"' % (
                ins[k - 1].get('id'), ins[k].get('id'), p_cur
            ))
    sorted_caps = sorted([t for t in texts if t.get('caption_format') and not t.get('behind')], key=lambda t: t['t0'])
    prev_cap = None
    for t in sorted_caps:
        if prev_cap and t['t0'] >= prev_cap['t1'] - 0.08:
            if t['caption_format'] == prev_cap['caption_format']:
                err.append('ValidationError [Rule 3]: adjacent captions @%.2fs and @%.2fs repeat format "%s"' % (
                    prev_cap['t0'], t['t0'], t['caption_format']
                ))
        if not prev_cap or t['t0'] >= prev_cap['t1'] - 0.08:
            prev_cap = t

    # Rule 4: Camera motion required on every beat + dynamic zoom variation across reel
    has_dynamic_zoom = len(edl.get('zoom') or []) >= 2
    for idx, b in enumerate(beats):
        cam = b.get('camera_motion')
        if not cam:
            for a_ in (b.get('animations') or []):
                if a_.get('layer') == 'camera':
                    cam = a_.get('effect')
                    break
        if not cam or cam not in VALID_CAMERA_EFFECTS:
            err.append('ValidationError [Rule 4]: beat %s missing valid camera_motion (%s)' % (b.get('n', idx + 1), cam))
        elif cam in ('punch_in', 'slow_push_in', 'dramatic_pull_out', 'speaker_whip_pan', 'zoom_push'):
            has_dynamic_zoom = True
    if not has_dynamic_zoom:
        err.append('ValidationError [Rule 4]: entire reel has static zoom — add dynamic zoom/camera presets')

    # Rule 5: 2 <= animations <= 4 on every beat/keyframe (auto-fix ONLY when --fix passed)
    balanced_any = False
    for list_key in ('beats', 'keyframes'):
        for idx, item in enumerate(edl.get(list_key) or []):
            anim_stack = item.get('animations')
            n_layers = len(anim_stack) if isinstance(anim_stack, list) else 0
            if n_layers < 2 or n_layers > 4:
                bid = item.get('n', item.get('beat', item.get('id', idx + 1)))
                if '--fix' in sys.argv:
                    balanced, _ = balance_keyframe_stack(anim_stack, t0=item.get('t0', 0.0), t1=item.get('t1', 2.0), role_index=idx)
                    item['animations'] = balanced
                    balanced_any = True
                    warn.append('%s %s auto-balanced to %d layers' % (list_key[:-1], bid, len(balanced)))
                else:
                    err.append('ValidationError [Rule 5]: %s %s has %d animation layer(s) (must be 2 <= animations <= 4)' % (
                        list_key[:-1], bid, n_layers
                    ))

    if balanced_any:
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(edl, fh, indent=2, ensure_ascii=False)
            fh.write('\n')

    # Rule 6: Zero-Placeholder + Kazakh Typo Scanner across EDL text/inserts + referenced HTML files
    for idx_i, i in enumerate(ins):
        fields_txt = ' '.join(str(i.get(k, '')) for k in ('title', 'subtitle', 'label', 'stamp', 'left_label', 'right_label', 'kpis', 'items')).lower()
        for ph in BANNED_PLACEHOLDERS:
            if ph in fields_txt:
                err.append('ValidationError [Rule 6]: insert "%s" contains banned placeholder "%s"' % (i.get('id', idx_i), ph))
        for bad_w, good_w in COMMON_KZ_TYPOS.items():
            if re.search(r'\b' + re.escape(bad_w) + r'\b', fields_txt):
                err.append('ValidationError [Rule 6]: insert "%s" has Kazakh typo "%s" -> use "%s"' % (i.get('id', idx_i), bad_w, good_w))
        if re.search(r'\bexample\b', fields_txt):
            err.append('ValidationError [Rule 6]: insert "%s" contains banned word "example"' % i.get('id', idx_i))
        hk = i.get('custom_html_scene') or i.get('html_hook') or (HOOK_CATALOG[i['preset']]['html'] if i.get('preset') in HOOK_CATALOG else None)
        if hk:
            cand_html = next((c for c in (hk if os.path.isabs(hk) else os.path.join(P, hk), os.path.join(_SKILL_ROOT, hk)) if os.path.exists(c)), None)
            if cand_html:
                with open(cand_html, encoding='utf-8', errors='ignore') as _hf:
                    raw_html = _hf.read().lower()
                for ph in BANNED_PLACEHOLDERS:
                    if ph in raw_html:
                        err.append('ValidationError [Rule 6]: HTML "%s" (insert %s) contains banned placeholder "%s"' % (os.path.basename(cand_html), i.get('id'), ph))
                if re.search(r'\bexample\b', raw_html):
                    err.append('ValidationError [Rule 6]: HTML "%s" contains banned word "example"' % os.path.basename(cand_html))
    for t in texts:
        tlow = str(t.get('text', '')).lower()
        for ph in BANNED_PLACEHOLDERS:
            if ph in tlow:
                err.append('ValidationError [Rule 6]: caption "%s" contains banned placeholder "%s"' % (t.get('text', '')[:24], ph))
        for bad_w, good_w in COMMON_KZ_TYPOS.items():
            if re.search(r'\b' + re.escape(bad_w) + r'\b', tlow):
                err.append('ValidationError [Rule 6]: caption "%s" has Kazakh typo "%s" -> use "%s"' % (t.get('text', '')[:24], bad_w, good_w))

    for e in err:
        print('ERROR  ' + e)
    for w in warn:
        print('warn   ' + w)
    print('\n%d inserts, %d text items, program %.2f s: %d error(s), %d warning(s)'
          % (len(ins), len(texts), dur or 0, len(err), len(warn)))
    sys.exit(1 if err else 0)


if __name__ == '__main__':
    main()
