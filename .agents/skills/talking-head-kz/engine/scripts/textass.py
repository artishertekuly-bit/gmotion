"""Kinetic typography through libass (ffmpeg's `ass` filter): one subtitle event per frame per text,
with per-letter override tags. This reproduces the house animations:

  build  - letters arrive in random order, stretched tall and spread wide, outline first, then fill,
           in stepped jumps (2 frames each); the whole word drifts 106% -> 100% while on screen
  soft   - fades in from a blur with a slight grow (serif accents)
  words  - subtitles: every word appears exactly when it is spoken
  pop    - small labels: 118% -> 100% in 2 frames
  exit   - big/serif words dissolve letter by letter (fade + grow + blur); other text fades out

Text is positioned like a design tool: (x, y) is the centre of the visible ink, measured once per
text in a measurement pass, so libass's line-box centring does not shift anything.
"""
import math
import os
import random
import subprocess

import numpy as np

from fontmetrics import extract_faces, faces, libass_factor

FONT_FILES = {
    'Anton-Regular': None,                                    # bundled
    'Didot': '/System/Library/Fonts/Supplemental/Didot.ttc',
    'HelveticaNeue-Medium': '/System/Library/Fonts/HelveticaNeue.ttc',
}
EXTRA_FONT_FILES = [p for p in os.environ.get('REEL_FONT_FILES', '').split(os.pathsep) if p]   # more .ttf/.otf/.ttc
SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# KZ/Windows + Linux patch: Anton has no Cyrillic and Didot / Helvetica Neue only exist on macOS.
# These Windows + Ubuntu fonts contain every Kazakh letter (ӘәҒғҚқҢңӨөҰұҮүҺһІі), plus user's ./kzfonts/.
WIN_KZ_FONTS = ['seguibl.ttf', 'segoeuib.ttf', 'seguisb.ttf', 'segoeui.ttf', 'timesbi.ttf', 'timesbd.ttf', 'timesi.ttf',
                'palabi.ttf', 'arialbd.ttf', 'consolab.ttf', 'consola.ttf', 'courbd.ttf', 'cour.ttf']
LINUX_KZ_FONTS = [
    '/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf',
    '/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSerif-BoldItalic.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf',
    '/usr/share/fonts/truetype/noto/NotoSans-Black.ttf',
    '/usr/share/fonts/truetype/noto/NotoSans-SemiBold.ttf',
    '/usr/share/fonts/truetype/noto/NotoSansMono-Bold.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf',
]


def _scan_font_dir(root_dir):
    found = []
    if not root_dir or not os.path.isdir(root_dir):
        return found
    for dp, _, fns in sorted(os.walk(root_dir)):
        for fn in sorted(fns):
            if fn.lower().endswith(('.ttf', '.otf', '.ttc')):
                found.append(os.path.join(dp, fn))
    return found


def kz_font_sources(extra_dirs=None):
    """Every font file in ./kzfonts/, skill assets/fonts, Windows Kazakh fonts, and Linux Ubuntu/Google Kazakh fonts."""
    out = []
    # Check ./kzfonts/ from env, cwd, and skill parent workspace root
    cand_dirs = [
        os.environ.get('REEL_KZFONTS_DIR'),
        os.path.join(os.getcwd(), 'kzfonts'),
        os.path.abspath(os.path.join(SKILL, '..', '..', '..', 'kzfonts')),
        os.path.expanduser('~/.local/share/fonts'),
        '/usr/local/share/fonts',
    ]
    if extra_dirs:
        cand_dirs.extend(extra_dirs)
    seen_dirs = set()
    for d in cand_dirs:
        if d:
            ad = os.path.abspath(d)
            if ad not in seen_dirs:
                seen_dirs.add(ad)
                out.extend(_scan_font_dir(ad))
    out.extend(_scan_font_dir(os.path.join(SKILL, 'assets', 'fonts')))
    windir = os.environ.get('WINDIR') or os.environ.get('SystemRoot')
    if windir:
        out += [os.path.join(windir, 'Fonts', f) for f in WIN_KZ_FONTS]
    out.extend([p for p in LINUX_KZ_FONTS if os.path.exists(p)])
    return out


_FONT_PREFS = {
    'impact': ('Unbounded-Black', 'Unbounded-ExtraBold', 'Montserrat-Black', 'Unbounded-Regular', 'SegoeUIBlack', 'NotoSans-Black', 'RubikWetPaint-Regular', 'DejaVuSans-Bold'),
    'clean': ('Montserrat-ExtraBold', 'Montserrat-Bold', 'Inter-Bold', 'Inter-SemiBold', 'Montserrat-Regular', 'Inter-Regular', 'SegoeUI-Bold', 'SegoeUI-Semibold', 'NotoSans-SemiBold', 'LiberationSans-Bold', 'DejaVuSans-Bold'),
    'editorial': ('PlayfairDisplay-BlackItalic', 'PlayfairDisplay-BoldItalic', 'Cormorant-BoldItalic', 'PlayfairDisplay-Italic', 'Cormorant-Italic', 'CormorantGaramond-BoldItalic', 'TimesNewRomanPS-BoldItalicMT', 'PalatinoLinotype-BoldItalic', 'DejaVuSerif-BoldItalic', 'DejaVuSerif-Italic'),
    'tech': ('JetBrainsMono-ExtraBold', 'JetBrainsMono-Bold', 'JetBrainsMono-Regular', 'Consolas-Bold', 'NotoSansMono-Bold', 'LiberationMono-Bold', 'DejaVuSansMono-Bold'),
}


def default_fonts_map():
    """Platform-safe Mastery V2 4-role font matrix (impact, clean, editorial, tech + legacy aliases)."""
    avail = set()
    for src in kz_font_sources():
        if src and os.path.exists(src):
            try:
                # Filter out fonts missing Kazakh letters when possible
                raw = open(src, 'rb').read()
                for f in faces(src):
                    if f.get('ps'):
                        avail.add(f['ps'])
            except Exception:
                pass
    role_picked = {}
    for role, prefs in _FONT_PREFS.items():
        role_picked[role] = next((ps for ps in prefs if ps in avail), None)
    if not any(role_picked.values()):
        if os.name == 'nt':
            role_picked = dict(impact='SegoeUIBlack', clean='SegoeUI-Semibold', editorial='TimesNewRomanPS-BoldItalicMT', tech='Consolas-Bold')
        elif os.path.exists('/System/Library/Fonts/Supplemental/Didot.ttc'):
            role_picked = dict(impact='Anton-Regular', clean='HelveticaNeue-Medium', editorial='Didot-Italic', tech='Menlo-Bold')
        else:
            role_picked = dict(impact='DejaVuSans-Bold', clean='DejaVuSans-Bold', editorial='DejaVuSerif-BoldItalic', tech='DejaVuSansMono-Bold')
    else:
        fallbacks = (
            dict(impact='SegoeUIBlack', clean='SegoeUI-Semibold', editorial='TimesNewRomanPS-BoldItalicMT', tech='Consolas-Bold')
            if os.name == 'nt' else
            dict(impact='DejaVuSans-Bold', clean='DejaVuSans-Bold', editorial='DejaVuSerif-BoldItalic', tech='DejaVuSansMono-Bold')
        )
        for r, fb in fallbacks.items():
            if not role_picked[r]:
                role_picked[r] = fb

    return dict(
        impact=role_picked['impact'],
        clean=role_picked['clean'],
        editorial=role_picked['editorial'],
        tech=role_picked['tech'],
        anton=role_picked['impact'],
        sub=role_picked['clean'],
        serif=role_picked['editorial'],
        didot=role_picked['editorial'],
        mono=role_picked['tech'],
    )


def fonts_dir(cache):
    """A folder with one .ttf per face (bundled fonts, the Windows Kazakh set, the macOS Didot / Helvetica Neue), as libass needs them."""
    d = os.path.join(cache, 'fonts')
    os.makedirs(d, exist_ok=True)
    sources = kz_font_sources() + [FONT_FILES['Didot'], FONT_FILES['HelveticaNeue-Medium']]
    for src in sources + list(EXTRA_FONT_FILES):
        if src and os.path.exists(src):
            extract_faces(src, d)
    return d


FACE_INFO = {}        # PostScript name -> family / weight / italic (filled by font_factors)


def font_factors(fdir):
    """libass size factor per PostScript name; also records how to select each face in libass."""
    out = {}
    for fn in sorted(os.listdir(fdir)):
        if not fn.lower().endswith(('.ttf', '.otf', '.ttc')):
            continue
        for f in faces(os.path.join(fdir, fn)):
            if f.get('ps'):
                out[f['ps']] = libass_factor(f)
                FACE_INFO[f['ps']] = dict(family=f['family'] or f['ps'], weight=f['weight'], italic=f['italic'])
    return out


def font_tags(ps):
    """libass does not find faces of a family by PostScript name: select family (style) + exact weight (tag)."""
    info = FACE_INFO.get(ps)
    if not info:
        return ''
    return '\\b%d\\i%d' % (info['weight'], 1 if info['italic'] else 0)


def hexcol(h):
    return h[5:7] + h[3:5] + h[1:3]           # #RRGGBB -> BBGGRR for ASS


def a8(opacity):
    return '%02X' % int(round(255 * (1 - max(0.0, min(1.0, opacity)))))


def bez(u, i_out, i_in):
    """Keyframe-style temporal ease (speed 0, influence i_out / i_in in 0..1) as a progress curve."""
    if u <= 0:
        return 0.0
    if u >= 1:
        return 1.0
    x1, x2 = i_out, 1 - i_in
    s = u
    for _ in range(12):
        x = 3 * (1 - s) ** 2 * s * x1 + 3 * (1 - s) * s * s * x2 + s ** 3
        dx = 3 * (1 - s) ** 2 * x1 + 6 * (1 - s) * s * (x2 - x1) + 3 * s * s * (1 - x2)
        if abs(dx) < 1e-6:
            break
        s = min(1.0, max(0.0, s - (x - u) / dx))
    return 3 * (1 - s) * s * s + s ** 3


def ramp(t, t0, t1, v0, v1, ease=None):
    if t <= t0:
        return v0
    if t >= t1:
        return v1
    u = (t - t0) / (t1 - t0)
    if ease:
        u = bez(u, ease, ease)
    return v0 + (v1 - v0) * u


def spring_step(tau, k=260.0, z=0.58):
    """Analytic damped spring response (0 -> 1 with gentle overshoot, from lemo-opuscar / reanimate)."""
    if tau <= 0:
        return 0.0
    w = math.sqrt(k)
    if z < 1.0:
        wd = w * math.sqrt(1.0 - z * z)
        return 1.0 - math.exp(-z * w * tau) * (math.cos(wd * tau) + (z * w / wd) * math.sin(wd * tau))
    return 1.0 - math.exp(-w * tau) * (1.0 + w * tau)


def expand_counters(texts, fps):
    """Expand `counter` text items into per-frame numeric roll-ups (reanimate_counter & slot_machine_counter)."""
    expanded = []
    for T in texts:
        cnt = T.get('counter')
        if not cnt:
            expanded.append(T)
            continue
        if len(cnt) == 5:
            a0, a1, v0, v1, suf = cnt
        elif len(cnt) == 3:
            v0, v1, suf = cnt
            a0, a1 = T['t0'], min(T['t0'] + 0.48, T['t1'])
        else:
            expanded.append(T)
            continue
        is_slot = bool(T.get('slot') or T.get('anim') == 'slot')
        f_start = int(T['t0'] * fps)
        f_end = int(math.ceil(T['t1'] * fps))
        for k in range(f_start, f_end):
            tt = k / fps
            u = max(0.0, min(1.0, (tt - a0) / max(a1 - a0, 1e-4)))
            eased = 1.0 - (1.0 - u) ** 3
            val = v0 + (v1 - v0) * eased
            if isinstance(v1, float) and not float(v1).is_integer():
                txt_val = '%.1f%s' % (val, suf)
            else:
                txt_val = '%d%s' % (round(val), suf)
            U = dict(T, text=txt_val, t0=tt, t1=tt + 1.0 / fps)
            U['anim'] = 'pop' if tt < T['t0'] + 0.08 else 'none'
            if is_slot and u < 0.98:
                U['_slot_dy'] = ((k % 3) - 1) * 18.0 * (1.0 - u)
            U['fadeout'] = False
            U.pop('counter', None)
            expanded.append(U)
    return expanded


def _default_word_font_pairs(chars, spans, base):
    """Module 5 default: automatically pair Impact/Clean/Editorial inside multi-word frames."""
    if base in ('mono', 'tech') or len(spans) < 2:
        return None
    lens = [len(idx) for idx in spans]
    best = max(range(len(spans)), key=lambda k: lens[k])
    pairs = []
    for wi, ln in enumerate(lens):
        if wi == best:
            pairs.append('editorial' if base in ('clean', 'sub', 'anton', 'impact') else 'impact')
        elif ln >= 6 and wi % 2 == 1:
            pairs.append('impact')
        else:
            pairs.append('clean')
    return pairs


def _char_font_roles(T):
    """Return a list of font role keys parallel to characters in T['text'], supporting per-word font mixing."""
    chars = list(T['text'].replace('\r\n', '\n').replace('\r', '\n'))
    wf = T.get('word_fonts')
    base = T['font']
    roles = [base] * len(chars)
    # Collect word character spans
    spans, cur = [], []
    for i, ch in enumerate(chars):
        if ch.isspace():
            if cur:
                spans.append(cur); cur = []
        else:
            cur.append(i)
    if cur:
        spans.append(cur)
    if not wf and not T.get('single_font'):
        wf = _default_word_font_pairs(chars, spans, base)
    if not wf:
        return roles
    for wi, idx in enumerate(spans):
        r = base
        if isinstance(wf, list) and wi < len(wf) and wf[wi]:
            r = wf[wi]
        elif isinstance(wf, dict):
            w_str = ''.join(chars[i] for i in idx).lower()
            r = wf.get(str(wi)) or wf.get(wi) or wf.get(w_str) or base
        for i in idx:
            roles[i] = r
    return roles


def esc(ch):
    return {'{': '\\{', '}': '\\}', '\\': '\\\\'}.get(ch, ch)


def text_lines(text):
    """Split on newlines: list of (first char index, line text)."""
    out, i = [], 0
    for ln in text.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        out.append((i, ln))
        i += len(ln) + 1
    return out


def tracking_px(T):
    """Letter spacing in design pixels: 'tracking' is in 1/1000 em like design tools (Anton/Impact default -10)."""
    return T.get('tracking', -10 if T['font'] in ('anton', 'impact') else 0) / 1000.0 * T['size']


def leading_px(T):
    return T.get('leading', 1.2 * T['size'])


def ass_time(t):
    cs = int(math.floor(t * 100 + 1e-6))
    return '%d:%02d:%02d.%02d' % (cs // 360000, (cs // 6000) % 60, (cs // 100) % 60, cs % 100)


class TextAnim:
    """Evaluates one text item frame by frame. Times are in the time base of the canvas it lives on."""

    def __init__(self, T, fps, uid):
        self.T, self.fps = T, fps
        self.t0, self.t1 = T['t0'], T['t1']
        self.chars = list(T['text'].replace('\r\n', '\n').replace('\r', '\n'))
        self.ns = [i for i, c in enumerate(self.chars) if not c.isspace()]
        n = len(self.ns)
        rnd = random.Random(1000 + uid)
        self.pos_build = self._perm(rnd, n)
        self.pos_outline = self._perm(random.Random(7000 + uid), n)
        self.pos_exit = self._perm(random.Random(3000 + uid), n)
        nch = n
        self.steps = 3 if nch <= 3 else (4 if nch <= 6 else 5)
        self.stepT = 2.0 / fps
        self.ed = min(0.3, (self.t1 - self.t0) * 0.3)
        self.has_exit = T.get('fadeout', True) is not False and self.ed > 0.06
        words, cur = [], []
        for i, c in enumerate(self.chars):
            if c.isspace():
                if cur:
                    words.append(cur)
                    cur = []
            else:
                cur.append(i)
        if cur:
            words.append(cur)
        self.words = words

    @staticmethod
    def _perm(rnd, n):
        order = list(range(n))
        rnd.shuffle(order)
        pos = [0] * n
        for p, i in enumerate(order):
            pos[i] = p
        return pos

    def stepped(self, t, delay_steps):
        """Hold-keyed selector start (0..1) for the build / outline animators."""
        k = math.floor((t - self.t0) / self.stepT + 1e-6) - delay_steps
        return max(0.0, min(1.0, k / float(self.steps)))

    def state(self, t):
        """Per-layer and per-character parameters at time t (None = not visible)."""
        T, a = self.T, self.T['anim']
        if t < self.t0 - 1e-6 or t >= self.t1 - 1e-6:
            return None
        lay = dict(scale=100.0, opacity=1.0, blur=0.0, dy=0.0)
        n = len(self.ns)
        ch = [dict(op=1.0, fill=1.0, sx=100.0, sy=100.0, sp=0.0, bord=0.0, blur=0.0) for _ in self.chars]
        if a == 'build':
            lay['scale'] = ramp(t, self.t0, self.t1, 106, 100)
            s1 = self.stepped(t, 0)
            s2 = self.stepped(t, 2)
            sw = max(2, round(T['size'] / 60.0))
            for j, i in enumerate(self.ns):
                a1 = max(0.0, min(1.0, (self.pos_build[j] + 1) - n * s1))
                a2 = max(0.0, min(1.0, (self.pos_outline[j] + 1) - n * s2))
                c = ch[i]
                c['op'] *= 1 - a1
                c['sx'] = 100 + (60 - 100) * a1
                c['sy'] = 100 + (300 - 100) * a1
                c['sp'] = 0.18 * a1 * T['size']
                c['fill'] = 1 - a2
                c['bord'] = sw * a2
        elif a == 'words':
            lay['scale'] = ramp(t, self.t0, self.t0 + 0.12, 108, 100, 0.75)
            wt = T.get('wt') or []
            for w, idx in enumerate(self.words):
                vis = (w < len(wt) and t >= wt[w] - 1e-6) or w >= len(wt)
                if not vis:
                    for i in idx:
                        ch[i]['op'] = 0.0
        elif a == 'word_pop':
            # 60% High-Edit hero style: 2-3 word chunk, active word lights up (#FFD600 / #00E676) + 125% spring overshoot
            wt = T.get('wt') or []
            hl = T.get('highlight_color', '#FFD600')
            peak_add = float(T.get('pop_scale', 125.0)) - 100.0
            nw = max(len(self.words), 1)
            dur = max(self.t1 - self.t0, 0.08)
            for w, idx in enumerate(self.words):
                ws = wt[w] if w < len(wt) else (self.t0 + w * dur / nw)
                we = wt[w + 1] if (w + 1) < len(wt) else self.t1
                if t < ws - 1e-6:
                    for i in idx:
                        ch[i]['op'] = 0.25 if T.get('preview_upcoming') else 0.0
                else:
                    tau = t - ws
                    sp = spring_step(tau, k=320.0, z=0.52)
                    pop_s = 100.0 + peak_add * (1.0 - min(sp, 1.12)) if tau < 0.18 else 100.0
                    active = (ws - 1e-6 <= t < we - 1e-6) or (w == nw - 1 and t >= ws - 1e-6)
                    for i in idx:
                        ch[i]['sx'] = pop_s
                        ch[i]['sy'] = pop_s
                        if active:
                            ch[i]['col'] = hl
        elif a in ('terminal', 'glitch'):
            # whisper_terminal / whisper_glitch_box: monospace typewriter + glitch flicker reveal
            type_dur = min(T.get('type_dur', 0.65), max((self.t1 - self.t0) * 0.7, 0.08))
            prog = max(0.0, min(1.0, (t - self.t0) / type_dur))
            vis_n = max(1, int(round(prog * max(n, 1))))
            hl = T.get('highlight_color', '#00E676')
            if a == 'glitch':
                step_f = int(round((t - self.t0) * self.fps))
                if step_f < 4 and step_f % 2 == 1:
                    lay['opacity'] *= 0.72
            for j, i in enumerate(self.ns):
                if j >= vis_n:
                    ch[i]['op'] = 0.0
                elif j == vis_n - 1 and prog < 0.99:
                    ch[i]['col'] = hl
                    ch[i]['bord'] = 1.5
        elif a in ('pop', 'slot'):
            lay['scale'] = ramp(t, self.t0, self.t0 + 0.08, 118, 100)
            if '_slot_dy' in T:
                lay['dy'] += float(T['_slot_dy'])
        elif a == 'soft':
            lay['opacity'] *= ramp(t, self.t0, self.t0 + 0.2, 0, 1)
            lay['blur'] = ramp(t, self.t0, self.t0 + 0.26, 30, 0)
            lay['scale'] = ramp(t, self.t0, self.t0 + 0.3, 94, 100, 0.8)
        elif a == 'none':
            if '_slot_dy' in T:
                lay['dy'] += float(T['_slot_dy'])
        elif a == 'rise':
            # KZ patch (saas-animation text rule): word by word, blurred -> sharp with a small rise, ~0.075 s stagger,
            # fast first then slow for longer, no pops or bounces; a slow push keeps the line alive while it holds.
            d, st = T.get('rise_d', 0.28), T.get('rise_stagger', 0.075)
            wt = T.get('wt') or []
            lay['scale'] = ramp(t, self.t0, self.t1, 100, 100 + T.get('drift', 3))
            first = 1.0
            for w, idx in enumerate(self.words):
                tw = wt[w] if w < len(wt) else self.t0 + w * st
                u = max(0.0, min(1.0, (t - tw) / d))
                e = 1 - (1 - u) ** 3
                if w == 0:
                    first = e
                for i in idx:
                    ch[i]['op'] = e
                    ch[i]['blur'] = 26 * (1 - e)
            lay['dy'] = T.get('rise_px', 0.16 * float(T['size'])) * (1 - first)
        if self.has_exit:
            if a == 'rise':                             # leaves the same way: up, soft, together
                x = ramp(t, self.t1 - min(self.ed, 0.2), self.t1, 0, 1) ** 2
                lay['opacity'] *= 1 - x
                lay['blur'] += 22 * x
                lay['dy'] -= 0.08 * float(T['size']) * x
            elif T['font'] not in ('sub', 'clean'):     # display fonts dissolve letter by letter
                e = ramp(t, self.t1 - self.ed, self.t1 - 0.02, 0, 1, 0.55)
                for j, i in enumerate(self.ns):
                    a3 = max(0.0, min(1.0, n * e - self.pos_exit[j]))
                    c = ch[i]
                    c['op'] *= 1 - a3
                    c['sx'] *= 1 + 0.16 * a3
                    c['sy'] *= 1 + 0.16 * a3
                    c['blur'] = 16 * a3
            else:
                lay['opacity'] *= ramp(t, self.t1 - 0.16, self.t1, 1, 0, 0.5)
        if T.get('opacity_keys'):                       # optional explicit fades
            for (ta, va), (tb, vb) in zip(T['opacity_keys'], T['opacity_keys'][1:]):
                if ta <= t < tb:
                    lay['opacity'] *= ramp(t, ta, tb, va, vb) / 100.0
        return lay, ch


def _font_switch_tag(role, fonts, factors, base_size):
    ps = fonts.get(role)
    if not ps or ps not in factors:
        return ''
    fam = FACE_INFO.get(ps, {}).get('family', ps)
    return '\\fn%s%s\\fs%.2f' % (fam, font_tags(ps), base_size * factors[ps])


def event_text(T, lay, ch, factor, offset, colour, opacity_mul=1.0, blur_add=0.0, border_colour=None, glow=False, extra=''):
    """Event bodies (one per non-empty line). Lines are stacked with design-tool leading around (x, y)."""
    sc = lay['scale'] / 100.0
    fs = T['size'] * factor
    trk = tracking_px(T)
    lines = text_lines(''.join(T['_chars']))
    offs = T.get('_offsets') or [offset] * len(lines)
    lead = leading_px(T)
    croles = T.get('_croles')
    fonts_map = T.get('_fonts_map')
    factors_map = T.get('_factors_map')
    tilt = float(T.get('tilt') or 0.0)
    out = []
    for k, (i0, ln) in enumerate(lines):
        if not ln.strip():
            continue
        off = offs[k] if k < len(offs) and offs[k] is not None else offset
        x = T['x'] - off[0] * sc
        y = T['y'] + (k - (len(lines) - 1) / 2.0) * lead * sc - off[1] * sc + lay.get('dy', 0.0)
        rot_tag = ('\\org(%.1f,%.1f)\\frz%.2f' % (T['x'], T['y'] + lay.get('dy', 0.0), tilt)) if abs(tilt) > 0.05 else ''
        parts = ['{\\an5\\pos(%.1f,%.1f)%s%s\\fs%.2f\\1c&H%s&\\3c&H%s&\\shad0\\bord0%s}' % (
            x, y, rot_tag, T.get('_ftags', ''), fs, hexcol(colour), hexcol(border_colour or colour), extra)]
        prev_role = T['font']
        for j, char in enumerate(ln):
            c = ch[i0 + j]
            op = c['op'] * lay['opacity'] * opacity_mul
            fill_op = op * (c['fill'] if not glow else max(c['fill'], 0.0))
            bl = c['blur'] * 0.5 + lay['blur'] * 0.5 + blur_add
            col_tag = ('\\1c&H%s&' % hexcol(c['col'])) if c.get('col') and not glow else ''
            ft_tag = ''
            if croles and fonts_map and factors_map and (i0 + j) < len(croles):
                r_now = croles[i0 + j]
                if r_now != prev_role and not char.isspace():
                    ft_tag = _font_switch_tag(r_now, fonts_map, factors_map, T['size'])
                    prev_role = r_now
            parts.append('{%s\\1a&H%s&\\3a&H%s&%s\\fscx%.1f\\fscy%.1f\\fsp%.2f\\bord%.2f\\blur%.2f}%s' % (
                ft_tag, a8(fill_op), a8(op), col_tag, c['sx'] * sc, c['sy'] * sc, (c['sp'] + trk) * sc, c['bord'] * sc, bl, esc(char)))
        out.append(''.join(parts))
    return out


def pill_event(T, lay, ink):
    """KZ patch: a rounded pill behind a ONE-LINE caption (supports tilt degrees via ASS \\frz)."""
    sc = lay['scale']
    s = float(T['size'])
    w = ink[0] + 2 * T.get('pill_pad', 0.42) * s
    h = T.get('pill_h', 1.42) * s
    r = min(h / 2.0, w / 2.0, T.get('pill_radius', 0.5) * h)
    k = r * 0.5523
    path = ('m %.1f 0 l %.1f 0 b %.1f 0 %.1f %.1f %.1f %.1f l %.1f %.1f b %.1f %.1f %.1f %.1f %.1f %.1f '
            'l %.1f %.1f b %.1f %.1f 0 %.1f 0 %.1f l 0 %.1f b 0 %.1f %.1f 0 %.1f 0') % (
        r, w - r, w - r + k, w, r - k, w, r, w, h - r, w, h - r + k, w - r + k, h, w - r, h,
        r, h, r - k, h, h - r + k, h - r, r, r - k, r - k, r)
    py = T['y'] + lay.get('dy', 0.0)
    tilt = float(T.get('tilt') or 0.0)
    rot_tag = ('\\org(%.1f,%.1f)\\frz%.2f' % (T['x'], py, tilt)) if abs(tilt) > 0.05 else ''
    return '{\\an5\\pos(%.1f,%.1f)%s\\fscx%.1f\\fscy%.1f\\1c&H%s&\\1a&H%s&\\bord0\\shad0\\blur0.8\\p1}%s{\\p0}' % (
        T['x'], py, rot_tag, sc, sc, hexcol(T['pill']), a8(lay['opacity'] * T.get('pill_opacity', 0.92)), path)


def gradient_events(T, lay, ch, factor, offset, bands=8):
    """KZ patch (saas-animation text polish): solid in the top half of the letters, shading to a cool grey at the foot.

    libass has no gradient fill, so the lower half is covered by clipped, slightly darker copies of the line.
    Text item fields: "gradient": true or "#RRGGBB" (the foot colour, default #8E96A3), "gradient_amount" (0.8).
    One-line text only; use it for light big words over dark footage, never on a colour card (it vanishes there)."""
    sc = lay['scale'] / 100.0
    w, h = T['_ink'][0] * sc, T['_ink'][1] * sc
    top = T['y'] + lay.get('dy', 0.0) - h / 2.0
    foot = T['gradient'] if isinstance(T['gradient'], str) else '#8E96A3'
    amount = T.get('gradient_amount', 0.8)
    c0 = [int(T['color'][i:i + 2], 16) for i in (1, 3, 5)]
    c1 = [int(foot[i:i + 2], 16) for i in (1, 3, 5)]
    out = []
    for k in range(bands):
        f = (k + 1) / float(bands) * amount
        col = '#%02X%02X%02X' % tuple(int(round(c0[i] + (c1[i] - c0[i]) * f)) for i in range(3))
        y0 = top + h * (0.5 + 0.5 * k / bands)
        y1 = top + h * (0.5 + 0.5 * (k + 1) / bands) + (1 if k < bands - 1 else h)
        clip = '\\clip(%d,%d,%d,%d)' % (T['x'] - w / 2 - 80, y0, T['x'] + w / 2 + 80, y1)
        out += event_text(T, lay, ch, factor, offset, col, extra=clip)
    return out


def header(W, H, fonts):
    styles = []
    for key, ps in fonts.items():
        ps = FACE_INFO.get(ps, {}).get('family', ps)
        styles.append('Style: %s,%s,60,&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1' % (key, ps))
    return ('[Script Info]\nScriptType: v4.00+\nPlayResX: %d\nPlayResY: %d\nWrapStyle: 2\nScaledBorderAndShadow: yes\nYCbCr Matrix: None\n\n'
            '[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, '
            'StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n%s\n\n'
            '[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n') % (W, H, '\n'.join(styles))


def write_ass(path, texts, W, H, fps, fonts, factors, t_from, t_to, glow_soft=11.0, shadow_soft=5.0):
    """Per-frame events for every text visible in [t_from, t_to)."""
    lines = [header(W, H, fonts)]
    f0, f1 = int(math.floor(t_from * fps + 1e-6)), int(math.ceil(t_to * fps - 1e-6))
    for uid, T in enumerate(texts):
        anim = T.get('_anim') or TextAnim(T, fps, T.get('_uid', uid))
        T['_anim'] = anim
        T['_chars'] = anim.chars
        fac = factors[fonts[T['font']]]
        T['_ftags'] = font_tags(fonts[T['font']])
        T['_croles'] = _char_font_roles(T)
        T['_fonts_map'] = fonts
        T['_factors_map'] = factors
        off = T.get('_offset', (0.0, 0.0))
        a = max(f0, int(math.floor(T['t0'] * fps + 1e-6)))
        b = min(f1, int(math.ceil(T['t1'] * fps - 1e-6)))
        for k in range(a, b):
            t = k / fps
            st = anim.state(t)
            if not st:
                continue
            lay, ch = st
            # event times are local to the chunk (frame f0 = 0); render_stream always starts at 0
            ts, te = ass_time((k - f0) / fps), ass_time((k - f0 + 1) / fps)
            evs = []
            if T.get('pill') and T.get('_ink'):
                evs.append((0, pill_event(T, lay, T['_ink'])))
            if T.get('glow'):
                evs += [(0, b) for b in event_text(T, lay, ch, fac, off, T.get('glow_color', T['color']), 0.75, glow_soft, glow=True)]
            if T.get('shadow'):
                evs += [(0, b) for b in event_text(T, lay, ch, fac, off, '#000000', 0.45, shadow_soft, '#000000')]
            evs += [(1, b) for b in event_text(T, lay, ch, fac, off, T['color'])]
            if T.get('gradient') and T.get('_ink') and '\n' not in T['text']:
                evs += [(2, b) for b in gradient_events(T, lay, ch, fac, off)]
            for layer, body in evs:
                lines.append('Dialogue: %d,%s,%s,%s,,0,0,0,,%s\n' % (layer, ts, te, T['font'], body))
    with open(path, 'w', encoding='utf-8') as fh:
        fh.writelines(lines)


def render_stream(ffmpeg, ass_path, fdir, W, H, fps, t_from, n_frames):
    """Start an ffmpeg process that emits n_frames RGBA frames (W x H) of a subtitle canvas.

    write_ass() stores event times relative to its t_from, so the stream always starts at 0
    (t_from is kept for the call signature only; offsetting PTS does not reach the ass filter)."""
    src = 'color=c=black@0.0:s=%dx%d:r=%s:d=%.5f,format=rgba' % (W, H, fps, (n_frames + 1) / fps)
    esc_ass = ass_path.replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")
    esc_fd = fdir.replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")
    return subprocess.Popen([ffmpeg, '-v', 'error', '-f', 'lavfi', '-i', src, '-vf', "ass='%s':fontsdir='%s':alpha=1" % (esc_ass, esc_fd),
                             '-frames:v', str(n_frames), '-f', 'rawvideo', '-pix_fmt', 'rgba', '-'], stdout=subprocess.PIPE, stdin=subprocess.DEVNULL)


def measure(ffmpeg, texts, fonts, factors, fdir, workdir, fps, tag='front'):
    """Ink-centre offset of every line of every text relative to its \\pos (static, final state, 100%)."""
    if not texts:
        return
    Wm, Hm = 3000, 1400
    lines = [header(Wm, Hm, fonts)]
    jobs = []                                    # (text, line index) per rendered frame
    for T in texts:
        fs = T['size'] * factors[fonts[T['font']]]
        trk = tracking_px(T)
        croles = _char_font_roles(T) if T.get('word_fonts') else None
        for li, (i0, ln) in enumerate(text_lines(T['text'])):
            if not ln.strip():
                continue
            k = len(jobs)
            jobs.append((T, li))
            if croles:
                prev_r = T['font']
                chunks = []
                for j, ch_ in enumerate(ln):
                    r_now = croles[i0 + j] if (i0 + j) < len(croles) else T['font']
                    if r_now != prev_r and not ch_.isspace():
                        sw = _font_switch_tag(r_now, fonts, factors, T['size'])
                        if sw:
                            chunks.append('{%s}' % sw)
                        prev_r = r_now
                    chunks.append(esc(ch_))
                body_str = ''.join(chunks)
            else:
                body_str = ''.join(esc(c) for c in ln)
            lines.append('Dialogue: 1,%s,%s,%s,,0,0,0,,{\\an5\\pos(%d,%d)%s\\fs%.2f\\fsp%.2f\\bord0\\shad0}%s\n' % (
                ass_time(k / fps), ass_time((k + 1) / fps), T['font'], Wm // 2, Hm // 2, font_tags(fonts[T['font']]), fs, trk,
                body_str))
    p = os.path.join(workdir, 'measure_%s.ass' % tag)
    with open(p, 'w', encoding='utf-8') as fh:
        fh.writelines(lines)
    for T in texts:
        T['_offsets'] = [None] * len(text_lines(T['text']))
        T.pop('_inkw', None)
        T.pop('_ink', None)
    proc = render_stream(ffmpeg, p, fdir, Wm, Hm, fps, 0.0, len(jobs))
    for T, li in jobs:
        buf = proc.stdout.read(Wm * Hm * 4)
        a = np.frombuffer(buf, np.uint8).reshape(Hm, Wm, 4)[:, :, 3]
        ys = np.nonzero(a.max(axis=1) > 96)[0]
        xs = np.nonzero(a.max(axis=0) > 96)[0]
        if len(ys) and len(xs):
            T['_offsets'][li] = ((xs[0] + xs[-1]) / 2.0 - Wm / 2, (ys[0] + ys[-1]) / 2.0 - Hm / 2)
            T['_inkw'] = max(T.get('_inkw', 0), int(xs[-1] - xs[0] + 1))
            if '_ink' not in T:
                T['_ink'] = (int(xs[-1] - xs[0] + 1), int(ys[-1] - ys[0] + 1))
        else:
            T['_offsets'][li] = (0.0, 0.0)
    proc.wait()
    for T in texts:
        first = [o for o in T['_offsets'] if o is not None]
        T['_offset'] = first[0] if first else (0.0, 0.0)
