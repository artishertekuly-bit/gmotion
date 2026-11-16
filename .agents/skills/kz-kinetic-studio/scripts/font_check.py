#!/usr/bin/env python3
"""Check which font files contain every Kazakh Cyrillic letter and map Mastery V2 4-Role Font Matrix.

Usage:
    python -X utf8 scripts/font_check.py FONT [FONT ...]
    python -X utf8 scripts/font_check.py --roles [--json]
"""
import argparse
import json
import os
import struct
import sys

KZ = 'ӘәҒғҚқҢңӨөҰұҮүҺһІі'
RU = 'АаБбЯяЁёЩщЫы'

ROLE_PREFERENCES = {
    'impact': ('Unbounded-Black', 'Unbounded-ExtraBold', 'Montserrat-Black', 'Unbounded-Regular', 'SegoeUIBlack', 'NotoSans-Black', 'DejaVuSans-Bold', 'Arial-Black', 'RubikWetPaint-Regular'),
    'clean': ('Montserrat-ExtraBold', 'Montserrat-Bold', 'Inter-Bold', 'Inter-SemiBold', 'SegoeUI-Bold', 'SegoeUI-Semibold', 'NotoSans-SemiBold', 'LiberationSans-Bold', 'DejaVuSans-Bold', 'Arial-BoldMT'),
    'editorial': ('PlayfairDisplay-BlackItalic', 'PlayfairDisplay-BoldItalic', 'Cormorant-BoldItalic', 'CormorantGaramond-BoldItalic', 'TimesNewRomanPS-BoldItalicMT', 'PalatinoLinotype-BoldItalic', 'DejaVuSerif-BoldItalic', 'DejaVuSerif-Italic'),
    'tech': ('JetBrainsMono-ExtraBold', 'JetBrainsMono-Bold', 'Consolas-Bold', 'NotoSansMono-Bold', 'LiberationMono-Bold', 'DejaVuSansMono-Bold', 'CourierNewPS-BoldMT'),
}


def tables(data, off):
    num = struct.unpack('>H', data[off + 4:off + 6])[0]
    t = {}
    for i in range(num):
        tag, _, o, ln = struct.unpack('>4sIII', data[off + 12 + 16 * i: off + 28 + 16 * i])
        t[tag.decode('latin-1')] = (o, ln)
    return t


def cmap_codes(data, tb):
    o, _ = tb['cmap']
    n = struct.unpack('>H', data[o + 2:o + 4])[0]
    codes = set()
    for i in range(n):
        _, _, sub = struct.unpack('>HHI', data[o + 4 + 8 * i:o + 12 + 8 * i])
        s = o + sub
        fmt = struct.unpack('>H', data[s:s + 2])[0]
        if fmt == 4:
            segx2 = struct.unpack('>H', data[s + 6:s + 8])[0]
            seg = segx2 // 2
            ends = struct.unpack('>%dH' % seg, data[s + 14:s + 14 + segx2])
            starts = struct.unpack('>%dH' % seg, data[s + 16 + segx2:s + 16 + 2 * segx2])
            for a, b in zip(starts, ends):
                if a <= b and b != 0xFFFF:
                    codes.update(range(a, b + 1))
        elif fmt == 12:
            ng = struct.unpack('>I', data[s + 12:s + 16])[0]
            for g in range(ng):
                a, b, _ = struct.unpack('>III', data[s + 16 + 12 * g:s + 28 + 12 * g])
                if b - a < 70000:
                    codes.update(range(a, b + 1))
    return codes


def names(data, tb):
    o, _ = tb['name']
    _, count, so = struct.unpack('>HHH', data[o:o + 6])
    out = {}
    for i in range(count):
        pid, _, _, nid, ln, no = struct.unpack('>HHHHHH', data[o + 6 + 12 * i:o + 18 + 12 * i])
        raw = data[o + so + no:o + so + no + ln]
        try:
            s = raw.decode('utf-16-be') if pid in (0, 3) else raw.decode('mac_roman')
        except Exception:
            continue
        out.setdefault(nid, s)
    return out


def inspect_font(path):
    results = []
    try:
        data = open(path, 'rb').read()
    except OSError as e:
        return [dict(path=path, file=os.path.basename(path), ps='?', verdict='ERROR: %s' % e, kz_ok=False)]
    offs = [0]
    if data[:4] == b'ttcf':
        n = struct.unpack('>I', data[8:12])[0]
        offs = list(struct.unpack('>%dI' % n, data[12:12 + 4 * n]))
    for off in offs:
        tb = tables(data, off)
        try:
            codes = cmap_codes(data, tb)
            nm = names(data, tb)
        except Exception as e:
            results.append(dict(path=path, file=os.path.basename(path), ps='?', verdict='PARSE ERROR %s' % e, kz_ok=False))
            continue
        miss_kz = [c for c in KZ if ord(c) not in codes]
        miss_ru = [c for c in RU if ord(c) not in codes]
        kz_ok = (not miss_kz and not miss_ru)
        verdict = 'KZ OK' if kz_ok else ('RU only, missing ' + ''.join(miss_kz) if not miss_ru else 'NO CYRILLIC')
        results.append(dict(path=path, file=os.path.basename(path), ps=nm.get(6, '?'), family=nm.get(1, '?'), kz_ok=kz_ok, verdict=verdict))
    return results


def discover_role_matrix(sources):
    kz_faces = {}
    for src in sources:
        if not src or not os.path.exists(src):
            continue
        for info in inspect_font(src):
            if info['kz_ok'] and info['ps'] != '?':
                kz_faces.setdefault(info['ps'], info)

    matrix = {}
    for role, prefs in ROLE_PREFERENCES.items():
        chosen = next((ps for ps in prefs if ps in kz_faces), None)
        if not chosen and kz_faces:
            # Fuzzy fallback match across ./kzfonts/ or system KZ OK fonts
            for ps in sorted(kz_faces):
                low = ps.lower()
                if role == 'impact' and any(k in low for k in ('black', 'heavy', 'unbounded', 'wet')):
                    chosen = ps; break
                if role == 'editorial' and 'italic' in low and any(k in low for k in ('serif', 'playfair', 'cormorant', 'times', 'palatino', 'didot')):
                    chosen = ps; break
                if role == 'tech' and any(k in low for k in ('mono', 'consolas', 'cour', 'jetbrains')):
                    chosen = ps; break
            if not chosen:
                chosen = next(iter(kz_faces))
        matrix[role] = chosen
    return matrix, kz_faces


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser()
    ap.add_argument('fonts', nargs='*')
    ap.add_argument('--roles', action='store_true', help='Scan installed + ./kzfonts fonts and print 4-role Kazakh matrix')
    ap.add_argument('--json', action='store_true', help='Output role matrix as JSON (with --roles)')
    a = ap.parse_args()

    if a.roles or not a.fonts:
        here = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, os.path.join(os.path.dirname(here), 'engine', 'scripts'))
        import textass  # noqa: E402
        matrix, kz_faces = discover_role_matrix(textass.kz_font_sources() + list(textass.EXTRA_FONT_FILES))
        if a.json:
            print(json.dumps({'roles': matrix, 'available_kz_ps': sorted(kz_faces.keys())}, indent=1, ensure_ascii=False))
        else:
            print('Mastery V2 4-Role Kazakh Font Matrix:')
            for role in ('impact', 'clean', 'editorial', 'tech'):
                ps = matrix.get(role) or 'MISSING'
                src = os.path.basename(kz_faces[ps]['path']) if ps in kz_faces else '-'
                print('  FONT_%-9s -> %-30s (%s)' % (role.upper(), ps, src))
        return

    for path in a.fonts:
        for info in inspect_font(path):
            print('%-22s ps=%-30s %s' % (info['file'], info['ps'], info['verdict']))


if __name__ == '__main__':
    main()
