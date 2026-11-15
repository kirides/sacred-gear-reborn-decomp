# Per-id edit table of the ability tables (T1: ids from 1000, 0x78-byte records; T2: ids from 1, 0x94-byte records):
# every field ReBorn changes, vanilla -> ReBorn, by field name (proven by a consumer) or unk_<offset> (not decoded yet).
#
#   python tools/abilities.py --reborn <SacredReborn.exe> --base <German sacred.exe> --out out/abilities_edits.json
import argparse, json, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
from exeimg import Image

# German addresses of the first record and the end of each table
TABLES = {
    'T1': dict(start=0x94DE28, end=0x950A38, stride=0x78),
    'T2': dict(start=0x950ACC, end=0x953344, stride=0x94),
}
# field: (offset, format). Names are proven by a consumer (see behaviours.md); everything else is unk_<offset>.
FIELDS = {
    'T1': {
        'id': (0x00, '<h'), 'name_text': (0x04, '<I'), 'description_text': (0x08, '<I'), 'target_mode': (0x4C, '<I'),
        'effect_base': (0x50, '<f'), 'effect_per_level': (0x54, '<f'),
        'effect2_base': (0x58, '<f'), 'effect2_per_level': (0x5C, '<f'),
    },
    'T2': {
        'id': (0x00, '<h'), 'name_text': (0x04, '<I'), 'description_text': (0x08, '<I'), 'target_mode': (0x3C, '<B'),
        'value0_base': (0x42, '<h'), 'value0_per_level': (0x44, '<h'),
        'value1_base': (0x46, '<h'), 'value1_per_level': (0x48, '<h'),
        'value2_base': (0x4A, '<h'), 'value2_per_level': (0x4C, '<h'),
        'value3_base': (0x4E, '<h'), 'value3_per_level': (0x50, '<h'),
    },
}
# how the not yet named bytes are compared: dword slots in T1 (floats and ints mixed), word slots in T2
UNK = {'T1': ('<I', 4), 'T2': ('<H', 2)}


def layout(table):
    named = FIELDS[table]
    covered = set()
    for name, (off, fmt) in named.items():
        covered.update(range(off, off + struct.calcsize(fmt)))
    fmt, size = UNK[table]
    out = list(named.items())
    for off in range(size, TABLES[table]['stride'] - size + 1, size):
        if not covered & set(range(off, off + size)):
            out.append((f'unk_{off:02x}', (off, fmt)))
    return out


def records(img, t):
    return [(t['start'] + i * t['stride'], img.rd(t['start'] + i * t['stride'], t['stride']))
            for i in range((t['end'] - t['start']) // t['stride'])]


def edits(de, rb):
    out, stats = {}, {}
    for table, t in TABLES.items():
        fields = layout(table)
        tab = {}
        for (a, x), (_, y) in zip(records(de, t), records(rb, t)):
            rid = struct.unpack_from('<h', x, 0)[0]
            changed = {}
            for name, (off, fmt) in fields:
                size = struct.calcsize(fmt)
                if x[off:off + size] != y[off:off + size]:
                    v = struct.unpack_from(fmt, x, off)[0]
                    w = struct.unpack_from(fmt, y, off)[0]
                    if isinstance(v, float):
                        v, w = round(v, 6), round(w, 6)
                    changed[name] = [v, w]
            if changed:
                tab[str(rid)] = changed
            if struct.unpack_from('<h', y, 0)[0] != rid:
                tab.setdefault('_warning', []).append(f'record at {a:08X}: id changed')
        out[table] = tab
        by_field = {}
        for rid, c in tab.items():
            if rid == '_warning':
                continue
            for name in c:
                by_field[name] = by_field.get(name, 0) + 1
        stats[table] = {'records': (t['end'] - t['start']) // t['stride'],
                        'records_edited': len([k for k in tab if k != '_warning']),
                        'edits': sum(by_field.values()), 'by_field': dict(sorted(by_field.items(), key=lambda kv: -kv[1]))}
    return out, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reborn', required=True)
    ap.add_argument('--base', required=True)
    ap.add_argument('--out', default='out/abilities_edits.json')
    args = ap.parse_args()
    de, rb = Image(args.base), Image(args.reborn)
    out, stats = edits(de, rb)
    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    with open(args.out, 'w', newline='\n') as f:
        json.dump({'tables': out, 'stats': stats}, f, indent=1)
    print(json.dumps(stats))


if __name__ == '__main__':
    main()
