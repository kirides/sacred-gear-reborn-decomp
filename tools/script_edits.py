#!/usr/bin/env python3
"""ReBorn's changes to the compiled scripts (FunkCode.bin, StartCode.bin) as readable, named edits instead of byte-run patches.

The files are streams of instructions (see script_vm.py and docs/file-formats.md). ReBorn changes about twenty instructions per file, nearly all of
them `FillSector` in the functions `Sector<N>Enter`: the spawn table of a sector, a list of `{creature, weight, group}`. The edits are written with
the names of mods/reborn/constants (CREATURE.WOLF, OPCODE.FILL_SECTOR) and find their instruction themselves:

  * FunkCode.bin, FillSector:  {fn = 'Sector88067Enter', op = OPCODE.FILL_SECTOR, sector = {88, 67}, [set_sector = {x, y},]
                                spawn = {old = {{creature = CREATURE.X, weight = 10, group = 1}, ...}, new = {...}}}
  * StartCode.bin, SetVar:      {op = OPCODE.SET_VAR, var = 'SoldatCnt', old = 0x8A2B7, new = 0x87906}
  * anything else:              {fn, op, ins = n, at = byte, old = 'hex', new = 'hex'}   (a byte range inside the n-th instruction; a comment says what it is)

Gear checks the opcode and `old` before it writes `new`; a file that is not the expected one is left alone.

  python tools/script_edits.py --reborn "<ReBorn SRB folder>" --gog "<game folder>/bin" --constants mods/reborn/constants --out <dir> --check
"""
import argparse
import bisect
import collections
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import script_vm as V

OP_CREATE_OBJ = 8
OP_FILLSECTOR = 51
OP_SET_VAR = 67
OPCODES = {OP_CREATE_OBJ: 'CREATE_OBJ', OP_FILLSECTOR: 'FILL_SECTOR', OP_SET_VAR: 'SET_VAR'}
FILLSECTOR_HEADER = 40      # bytes before the spawn table in a FillSector instruction (checked against every file)
TAG_SPAWN = 0x19
TRIPLE = 13
# FillSector header: 4 byte instruction header, then tagged operands (offsets in the instruction): 0x36 creature value, 0x34 sector X Y,
# 0x35 min count / max count / area divisor, 0x33 min level / max level
SECTOR_AT = 10


def load_constants(folder):
    """{'CREATURE': {name: id}, ...} from the constants/*.lua files."""
    out = {}
    if folder and os.path.isdir(folder):
        for f in os.listdir(folder):
            if f.endswith('.lua'):
                out[f[:-4].upper()] = {m.group(1): int(m.group(2)) for m in re.finditer(r'^\s*([A-Z0-9_]+)\s*=\s*(-?\d+)', open(os.path.join(folder, f), encoding='utf8').read(), re.M)}
    return out


def spawn_entries(raw):
    return [{'creature': struct.unpack_from('<i', raw, k + 1)[0], 'weight': struct.unpack_from('<i', raw, k + 5)[0],
             'group': struct.unpack_from('<i', raw, k + 9)[0]} for k in range(0, len(raw), TRIPLE)]


def spawn_bytes(entries):
    return b''.join(bytes([TAG_SPAWN]) + struct.pack('<3i', e['creature'], e['weight'], e['group']) for e in entries)


def fill_sector_header(a, off, length):
    """(x, y, description) of a FillSector instruction with a spawn table, else None."""
    if length <= FILLSECTOR_HEADER or (length - FILLSECTOR_HEADER) % TRIPLE or a[off + 9] != 0x34 or a[off + 18] != 0x35:
        return None
    x, y = struct.unpack_from('<2i', a, off + SECTOR_AT)
    lo, hi, div = struct.unpack_from('<3i', a, off + 19)
    lv_lo, lv_hi = struct.unpack_from('<2i', a, off + 32)
    desc = 'sector (%d, %d): %s per %d' % (x, y, ('%d creatures' % lo) if lo == hi else ('%d to %d creatures' % (lo, hi)), div)
    if lv_lo or lv_hi:
        desc += ', levels %d to %d' % (lv_lo, lv_hi)
    return x, y, desc


def is_spawn_tail(a, b, off, length):
    body = length - FILLSECTOR_HEADER
    return body > 0 and body % TRIPLE == 0 and all(a[off + FILLSECTOR_HEADER + k] == TAG_SPAWN and b[off + FILLSECTOR_HEADER + k] == TAG_SPAWN
                                                    for k in range(0, body, TRIPLE))


def describe(data, off, length):
    """The operands of a CreateObj-like instruction as text, as far as the tags are known; '' if one is not."""
    p, end, parts = off + 4, off + length, []
    try:
        while p < end:
            tag = data[p]
            if tag == 0x01:
                z = data.index(0, p + 1)
                parts.append('name "%s"' % data[p + 1:z].decode('latin1'))
                p = z + 1
            elif tag == 0x02:
                parts.append('type 0x%X' % struct.unpack_from('<i', data, p + 1)[0])
                p += 5
            elif tag == 0x20:
                parts.append('world position %s' % (struct.unpack_from('<3i', data, p + 1),))
                p += 13
            elif tag == 0x3C and struct.unpack_from('<i', data, p + 1)[0] == -2:
                z = data.index(0, p + 5)
                parts.append('symbolic position "%s"' % data[p + 5:z].decode('latin1'))
                p = z + 1
            elif tag in (0x00, 0x61):
                parts.append('tag 0x%02X' % tag)
                p += 1
            else:
                parts.append('tag 0x%02X ...' % tag)
                break
    except (ValueError, struct.error):
        return ''
    return '; '.join(parts)


def edits_funk(a, b, vectoren):
    fns = V.functions(vectoren)
    starts = [f[1] for f in fns]
    names = collections.Counter(f[0] for f in fns)
    per, cache = collections.OrderedDict(), {}
    for p in (i for i in range(len(a)) if a[i] != b[i]):
        k = bisect.bisect_right(starts, p) - 1
        if k not in cache:
            cache[k] = V.instructions(a, fns[k][1], fns[k][1] + fns[k][2])
        il = cache[k]
        j = bisect.bisect_right([x[0] for x in il], p) - 1
        off, op, length = il[j]
        per.setdefault((k, j), [off, op, length, []])[3].append(p - off)
    out = []
    for (k, j), (off, op, length, rel) in per.items():
        name = fns[k][0]
        if names[name] != 1:
            raise SystemExit('function name %s is not unique' % name)
        il = cache[k]
        head = fill_sector_header(a, off, length) if op == OP_FILLSECTOR and is_spawn_tail(a, b, off, length) else None
        if head:
            x, y, desc = head
            sector_bytes = set(range(SECTOR_AT, SECTOR_AT + 8))
            changed_head = [r for r in rel if r < FILLSECTOR_HEADER]
            if all(r in sector_bytes for r in changed_head):
                e = {'fn': name, 'op': op, 'sector': [x, y], 'desc': desc}
                if changed_head:
                    e['set_sector'] = list(struct.unpack_from('<2i', b, off + SECTOR_AT))
                if any(r >= FILLSECTOR_HEADER for r in rel):
                    e['spawn'] = {'old': spawn_entries(a[off + FILLSECTOR_HEADER:off + length]),
                                  'new': spawn_entries(b[off + FILLSECTOR_HEADER:off + length])}
                same = [i for i, (o2, op2, l2) in enumerate(il) if op2 == OP_FILLSECTOR and fill_sector_header(a, o2, l2)
                        and fill_sector_header(a, o2, l2)[:2] == (x, y)]
                if len(same) != 1:
                    e['ins'] = j + 1            # the sector alone does not find the instruction
                out.append(e)
                continue
        lo, hi = min(rel), max(rel) + 1
        e = {'fn': name, 'op': op, 'ins': j + 1, 'at': lo, 'old': a[off + lo:off + hi].hex(), 'new': b[off + lo:off + hi].hex()}
        before, after = describe(a, off, length), describe(b, off, length)
        e['note'] = 'was: %s' % before + ('; now: %s' % after if after != before else '') if before else ''
        out.append(e)
    return out


def set_var(a, off, length):
    """(name, offset of the int, value) of a SetVar instruction `01 name\\0 0B int32`, else None."""
    if a[off + 4] != 0x01:
        return None
    try:
        z = a.index(0, off + 5)
    except ValueError:
        return None
    if z + 6 != off + length or a[z + 1] != 0x0B:
        return None
    return a[off + 5:z].decode('latin1'), z + 2, struct.unpack_from('<i', a, z + 2)[0]


def edits_start(a, b):
    il = V.instructions(a)
    offs = [x[0] for x in il]
    per = collections.OrderedDict()
    for p in (i for i in range(len(a)) if a[i] != b[i]):
        j = bisect.bisect_right(offs, p) - 1
        per.setdefault(j, []).append(p - il[j][0])
    out = []
    for j, rel in per.items():
        off, op, length = il[j]
        sv = set_var(a, off, length) if op == OP_SET_VAR else None
        if sv and all(off + r >= sv[1] for r in rel):
            matches = [1 for o2, op2, l2 in il if op2 == OP_SET_VAR and (set_var(a, o2, l2) or ('',))[0] == sv[0]]
            if len(matches) == 1:
                out.append({'op': op, 'var': sv[0], 'old': sv[2], 'new': struct.unpack_from('<i', b, sv[1])[0]})
                continue
        lo, hi = min(rel), max(rel) + 1
        out.append({'op': op, 'ins': j + 1, 'at': lo, 'old': a[off + lo:off + hi].hex(), 'new': b[off + lo:off + hi].hex(), 'note': ''})
    return out


def check_range(a, out, off, length, lo, old, new, what):
    if len(old) != len(new) or lo + len(old) > length:
        raise ValueError('%s does not fit in the instruction' % what)
    if a[off + lo:off + lo + len(old)] != old:
        raise ValueError('the file has other bytes than %s expects' % what)
    out[off + lo:off + lo + len(new)] = new


def apply_edit(a, out, il, e, funk_label):
    """Applies one edit given the instruction list `il` it is looked up in; the reference of Gear's `script` patch kind."""
    if 'sector' in e:
        want = tuple(e['sector'])
        hits = [x for x in range(len(il)) if il[x][1] == e['op'] and fill_sector_header(a, il[x][0], il[x][2])
                and fill_sector_header(a, il[x][0], il[x][2])[:2] == want]
        if 'ins' in e:
            hits = [h for h in hits if h == e['ins'] - 1]
        if len(hits) != 1:
            raise ValueError('%s: sector %s found %d times' % (funk_label, want, len(hits)))
        off, op, length = il[hits[0]]
        if 'spawn' in e:
            old, new = spawn_bytes(e['spawn']['old']), spawn_bytes(e['spawn']['new'])
            check_range(a, out, off, length, FILLSECTOR_HEADER, old, new, 'the spawn table')
        if 'set_sector' in e:
            check_range(a, out, off, length, SECTOR_AT, struct.pack('<2i', *e['sector']), struct.pack('<2i', *e['set_sector']), 'the sector')
        return
    if 'var' in e:
        hits = [x for x in range(len(il)) if il[x][1] == e['op'] and (set_var(a, il[x][0], il[x][2]) or ('',))[0] == e['var']]
        if len(hits) != 1:
            raise ValueError('SetVar %s found %d times' % (e['var'], len(hits)))
        off, op, length = il[hits[0]]
        at = set_var(a, off, length)[1] - off
        check_range(a, out, off, length, at, struct.pack('<i', e['old']), struct.pack('<i', e['new']), 'the value')
        return
    off, op, length = il[e['ins'] - 1]
    if op != e['op']:
        raise ValueError('%s ins %d is opcode %d, not %d' % (funk_label, e['ins'], op, e['op']))
    check_range(a, out, off, length, e['at'], bytes.fromhex(e['old']), bytes.fromhex(e['new']), 'the bytes')


def apply_funk(a, vectoren, edits):
    index = collections.defaultdict(list)
    for f in V.functions(vectoren):
        index[f[0]].append(f)
    out = bytearray(a)
    for e in edits:
        hits = index.get(e['fn'], [])
        if len(hits) != 1:
            raise ValueError('function %s found %d times' % (e['fn'], len(hits)))
        apply_edit(a, out, V.instructions(a, hits[0][1], hits[0][1] + hits[0][2]), e, e['fn'])
    return bytes(out)


def apply_start(a, edits):
    il = V.instructions(a)
    out = bytearray(a)
    for e in edits:
        apply_edit(a, out, il, e, 'StartCode')
    return bytes(out)


# ---- Lua output ----

def lua_creature(c, names):
    return 'CREATURE.%s' % names[c] if c in names else str(c)


def lua_entries(entries, names, indent):
    pad = ' ' * indent
    rows = []
    for e in entries:
        rows.append('%s{creature = %s, weight = %d, group = %d},' % (pad, lua_creature(e['creature'], names), e['weight'], e['group']))
    return '\n'.join(rows)


def lua_edit(e, funk, names):
    op = 'OPCODE.%s' % OPCODES.get(e['op'], str(e['op']))
    if 'sector' in e:
        lines = ['        -- %s: %s' % (e['fn'], e['desc']),
                 "        {fn = '%s', op = %s, sector = {%d, %d}%s," % (e['fn'], op, e['sector'][0], e['sector'][1],
                                                                        (', ins = %d' % e['ins']) if 'ins' in e else '')]
        if 'set_sector' in e:
            lines.append('         set_sector = {%d, %d},   -- ReBorn fills the sector next to it (the game has the coordinates of this one)' % tuple(e['set_sector']))
        if 'spawn' in e:
            lines += ['         spawn = {', '             old = {', lua_entries(e['spawn']['old'], names, 17), '             },',
                      '             new = {', lua_entries(e['spawn']['new'], names, 17), '             }}},']
        else:
            lines[-1] = lines[-1].rstrip(',') + '},'
        return '\n'.join(lines)
    if 'var' in e:
        return "        {op = %s, var = '%s', old = 0x%X, new = 0x%X}," % (op, e['var'], e['old'], e['new'])
    note = e.get('note') or ''
    head = ("fn = '%s', " % e['fn'] if funk else '') + 'op = %s, ins = %d' % (op, e['ins'])
    text = "        {%s, at = %d, old = '%s', new = '%s'}," % (head, e['at'], e['old'], e['new'])
    return (('        -- %s\n' % note) if note else '') + text


def lua_file(title, edits, funk, names):
    lines = ['-- %s' % title,
             "-- Generated by tools/script_edits.py: ReBorn's changes to the compiled scripts, with the names of constants/*.lua. Gear finds the instruction",
             "-- itself (function name + sector for FillSector, variable name for SetVar), checks `old` and writes `new` (kind = 'script', gear/overlay.cpp).",
             'return {', "    kind = 'script',", "    file = '%s'," % ('funk' if funk else 'start'), '    edits = {']
    lines += [lua_edit(e, funk, names) for e in edits]
    lines += ['    },', '}', '']
    return '\n'.join(lines)


def script_files(reborn):
    out = []
    for root, _, names in os.walk(reborn):
        for n in names:
            if n.lower() in ('funkcode.bin', 'startcode.bin'):
                out.append(os.path.relpath(os.path.join(root, n), reborn).replace(os.sep, '/'))
    return sorted(out)


def group_name(rels):
    kind = 'funkcode' if rels[0].lower().endswith('funkcode.bin') else 'startcode'
    parts = sorted({r.rsplit('/', 1)[0].lower() for r in rels})
    if len(parts) == 1:
        return '%s_%s' % (parts[0].replace('/', '_'), kind)
    if all(p.startswith('addon/type_npc_') for p in parts):
        return 'addon_type_npc_%s' % kind
    if all(p.startswith('type_npc_') for p in parts):
        return 'type_npc_%s' % kind
    if len(parts) > 3:
        return kind
    return '%s_%s' % ('_'.join(p.replace('/', '_') for p in parts), kind)


def emit(result, out_dir, constants):
    """One Lua file per distinct edit list of {rel: (funk, edits)}; returns {rel: file name}."""
    names = {v: k for k, v in constants.get('CREATURE', {}).items()}
    groups = collections.OrderedDict()
    for rel, (funk, edits) in sorted(result.items()):
        groups.setdefault(json.dumps([funk, edits], sort_keys=True), []).append(rel)
    fnames, used = {}, collections.Counter()
    for key, rels in groups.items():
        name = group_name(rels)
        used[name] += 1
        fnames[key] = name if used[name] == 1 else '%s_%d' % (name, used[name])
    os.makedirs(out_dir, exist_ok=True)
    mapping = {}
    for key, rels in groups.items():
        funk, edits = json.loads(key)
        title = '%s (%d files: %s)' % (fnames[key], len(rels), ', '.join(rels[:3]) + (', ...' if len(rels) > 3 else ''))
        with open(os.path.join(out_dir, fnames[key] + '.lua'), 'w', encoding='utf8', newline=chr(10)) as f:
            f.write(lua_file(title, edits, funk, names))
        for rel in rels:
            mapping[rel] = fnames[key] + '.lua'
    return mapping


def build(reborn, gog):
    result = {}
    for rel in script_files(reborn):
        a = open(gog + '/' + rel, 'rb').read()
        b = open(reborn + '/' + rel, 'rb').read()
        if a == b:
            continue
        if len(a) != len(b):
            raise SystemExit('%s: the size differs (%d vs %d): not an in-place edit' % (rel, len(a), len(b)))
        if rel.lower().endswith('funkcode.bin'):
            result[rel] = (True, edits_funk(a, b, open(os.path.dirname(gog + '/' + rel) + '/Vectoren.bin', 'rb').read()))
        else:
            result[rel] = (False, edits_start(a, b))
    return result


def write_all(reborn, gog, out_dir, constants_dir, check):
    result = build(reborn, gog)
    constants = load_constants(constants_dir)
    mapping = emit(result, out_dir, constants)
    if check:
        bad = 0
        for rel, (funk, edits) in result.items():
            a = open(gog + '/' + rel, 'rb').read()
            b = open(reborn + '/' + rel, 'rb').read()
            got = (apply_funk(a, open(os.path.dirname(gog + '/' + rel) + '/Vectoren.bin', 'rb').read(), edits) if funk else apply_start(a, edits))
            if got != b:
                bad += 1
                print('MISMATCH', rel)
        print('self-check: %d script files rebuilt from %d edit files, %d mismatches' % (len(result), len(set(mapping.values())), bad))
        if bad:
            raise SystemExit(1)
    return mapping


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--reborn', required=True)
    ap.add_argument('--gog', required=True)
    ap.add_argument('--constants', default=None)
    ap.add_argument('--out', required=True)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    for rel, name in sorted(write_all(args.reborn, args.gog, args.out, args.constants, args.check).items()):
        print(rel, '->', name)


if __name__ == '__main__':
    main()
