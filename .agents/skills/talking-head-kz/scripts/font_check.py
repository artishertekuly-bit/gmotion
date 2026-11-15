"""Check which font files contain every Kazakh Cyrillic letter (no dependencies).
usage: python -I kzcov.py FONT [FONT ...]
"""
import struct
import sys

KZ = 'ӘәҒғҚқҢңӨөҰұҮүҺһІі'
RU = 'АаБбЯяЁёЩщЫы'


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
        pid, eid, sub = struct.unpack('>HHI', data[o + 4 + 8 * i:o + 12 + 8 * i])
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
        pid, eid, lid, nid, ln, no = struct.unpack('>HHHHHH', data[o + 6 + 12 * i:o + 18 + 12 * i])
        raw = data[o + so + no:o + so + no + ln]
        try:
            s = raw.decode('utf-16-be') if pid in (0, 3) else raw.decode('mac_roman')
        except Exception:
            continue
        out.setdefault(nid, s)
    return out


for path in sys.argv[1:]:
    try:
        data = open(path, 'rb').read()
    except OSError as e:
        print('%-22s cannot read (%s)' % (path.replace('\\', '/').split('/')[-1], e))
        continue
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
            print('%-22s parse error %s' % (path.replace('\\', '/').split('/')[-1], e))
            continue
        miss_kz = [c for c in KZ if ord(c) not in codes]
        miss_ru = [c for c in RU if ord(c) not in codes]
        verdict = 'KZ OK' if not miss_kz and not miss_ru else ('RU only, missing ' + ''.join(miss_kz) if not miss_ru else 'NO CYRILLIC')
        print('%-16s ps=%-28s %s' % (path.replace('\\', '/').split('/')[-1], nm.get(6, '?'), verdict))
