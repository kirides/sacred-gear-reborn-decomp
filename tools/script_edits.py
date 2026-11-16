#!/usr/bin/env python3
"""ReBorn's changes to the compiled scripts (FunkCode.bin, StartCode.bin) as readable edits instead of byte-run patches.

The files are streams of instructions (see script_vm.py and docs/script-files.md). ReBorn changes about twenty instructions per file, nearly all
of them `FillSector` (opcode 51) in the functions `Sector<N>Enter`: the spawn table of a sector, a list of `0x19` operands = {creature type,
weight, group}. An edit names the function (FunkCode.bin: from Vectoren.bin) and the instruction in it, and either replaces the spawn table
(`spawn = {old = {...}, new = {...}}`) or a byte range inside the instruction (`at`, `old`, `new`, hex). Gear checks the opcode and `old`
before it writes `new`; a file that is not the expected one is left alone.

  python tools/script_edits.py --reborn "<ReBorn SRB folder>" --gog "<game folder>/bin" --out mods/reborn/patches/scripts [--check]
"""
import argparse
import bisect
import collections
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import script_vm as V

OP_FILLSECTOR = 51          # 0x33; Armalion's name for it, see docs/script-files.md
OP_NAMES = {51: 'FillSector', 8: 'CreateObj'}
FILLSECTOR_HEADER = 40      # bytes before the spawn table in a FillSector instruction (checked against every file)
TAG_SPAWN = 0x19
TRIPLE = 13
# the 40 byte header of a FillSector instruction: 4 byte instruction header, then tagged operands (offsets in the instruction)
FILLSECTOR_FIELDS = [('creature value', 5), ('sector X', 10), ('sector Y', 14), ('min count', 19), ('max count', 23), ('area divisor', 27),
                     ('min level', 32), ('max level', 36)]


def header_note(a, b, off, rel):
    """'sector X 73 -> 72' for the FillSector header fields among the changed bytes `rel` (offsets in the instruction)."""
    parts = []
    for name, at in FILLSECTOR_FIELDS:
        if any(at <= r < at + 4 for r in rel):
            parts.append('%s %d -> %d' % (name, struct.unpack_from('<i', a, off + at)[0], struct.unpack_from('<i', b, off + at)[0]))
    return ', '.join(parts)


def spawn_table(raw):
    return [list(struct.unpack_from('<3i', raw, k + 1)) for k in range(0, len(raw), TRIPLE)]


def spawn_bytes(table):
    return b''.join(bytes([TAG_SPAWN]) + struct.pack('<3i', *t) for t in table)


def is_spawn_tail(a, b, off, length):
    """Whether the instruction [off, off+length) is a FillSector whose last operands are a spawn table in both files."""
    body = length - FILLSECTOR_HEADER
    if body <= 0 or body % TRIPLE:
        return False
    return all(a[off + FILLSECTOR_HEADER + k] == TAG_SPAWN and b[off + FILLSECTOR_HEADER + k] == TAG_SPAWN
               for k in range(0, body, TRIPLE))


def edits_funk(a, b, vectoren):
    """Edits of FunkCode.bin: [{fn, ins, op, spawn | at/old/new}]; `ins` counts from 1 inside the function."""
    fns = V.functions(vectoren)
    starts = [f[1] for f in fns]
    names = collections.Counter(f[0] for f in fns)
    changed = [i for i in range(len(a)) if a[i] != b[i]]
    per = collections.OrderedDict()
    cache = {}
    for p in changed:
        k = bisect.bisect_right(starts, p) - 1
        st, ln = fns[k][1], fns[k][2]
        if k not in cache:
            cache[k] = V.instructions(a, st, st + ln)
        il = cache[k]
        j = bisect.bisect_right([x[0] for x in il], p) - 1
        off, op, length = il[j]
        per.setdefault((k, j), [off, op, length, []])[3].append(p - off)
    out = []
    for (k, j), (off, op, length, rel) in per.items():
        name = fns[k][0]
        if names[name] != 1:
            raise SystemExit('function name %s is not unique' % name)
        if op == OP_FILLSECTOR and is_spawn_tail(a, b, off, length):
            head = [r for r in rel if r < FILLSECTOR_HEADER]
            if head:
                lo, hi = min(head), max(head) + 1
                out.append({'fn': name, 'ins': j + 1, 'op': op, 'at': lo, 'old': a[off + lo:off + hi].hex(), 'new': b[off + lo:off + hi].hex(),
                            'note': 'FillSector header: ' + header_note(a, b, off, head)})
            if any(r >= FILLSECTOR_HEADER for r in rel):
                lo = FILLSECTOR_HEADER
                out.append({'fn': name, 'ins': j + 1, 'op': op,
                            'spawn': {'old': spawn_table(a[off + lo:off + length]), 'new': spawn_table(b[off + lo:off + length])}})
            continue
        lo, hi = min(rel), max(rel) + 1
        out.append({'fn': name, 'ins': j + 1, 'op': op, 'at': lo, 'old': a[off + lo:off + hi].hex(), 'new': b[off + lo:off + hi].hex()})
    return out


def edits_start(a, b):
    """Edits of StartCode.bin (one instruction stream, no function table): {ins (from 1), op, at, old, new}."""
    il = V.instructions(a)
    offs = [x[0] for x in il]
    per = collections.OrderedDict()
    for p in (i for i in range(len(a)) if a[i] != b[i]):
        j = bisect.bisect_right(offs, p) - 1
        per.setdefault(j, []).append(p - il[j][0])
    out = []
    for j, rel in per.items():
        off, op, length = il[j]
        lo, hi = min(rel), max(rel) + 1
        out.append({'ins': j + 1, 'op': op, 'at': lo, 'old': a[off + lo:off + hi].hex(), 'new': b[off + lo:off + hi].hex()})
    return out


def patch_instruction(a, out, off, length, e):
    if 'spawn' in e:
        lo = FILLSECTOR_HEADER
        old, new = spawn_bytes(e['spawn']['old']), spawn_bytes(e['spawn']['new'])
        if length - lo != len(old) or len(old) != len(new):
            raise ValueError('spawn table of %s has another size' % e['fn'])
    else:
        lo = e['at']
        old, new = bytes.fromhex(e['old']), bytes.fromhex(e['new'])
        if len(old) != len(new) or lo + len(old) > length:
            raise ValueError('edit does not fit in the instruction')
    if a[off + lo:off + lo + len(old)] != old:
        raise ValueError('the file has other bytes than the edit expects (%s)' % e.get('fn', e['ins']))
    out[off + lo:off + lo + len(new)] = new


def apply_funk(a, vectoren, edits):
    """The reference of Gear's `script` patch kind for FunkCode.bin (gear/overlay.cpp): same lookups, same checks."""
    index = collections.defaultdict(list)
    for f in V.functions(vectoren):
        index[f[0]].append(f)
    out = bytearray(a)
    for e in edits:
        hits = index.get(e['fn'], [])
        if len(hits) != 1:
            raise ValueError('function %s found %d times' % (e['fn'], len(hits)))
        st, ln = hits[0][1], hits[0][2]
        off, op, length = V.instructions(a, st, st + ln)[e['ins'] - 1]
        if op != e['op']:
            raise ValueError('%s ins %d is opcode %d, not %d' % (e['fn'], e['ins'], op, e['op']))
        patch_instruction(a, out, off, length, e)
    return bytes(out)


def apply_start(a, edits):
    il = V.instructions(a)
    out = bytearray(a)
    for e in edits:
        off, op, length = il[e['ins'] - 1]
        if op != e['op']:
            raise ValueError('instruction %d is opcode %d, not %d' % (e['ins'], op, e['op']))
        patch_instruction(a, out, off, length, e)
    return bytes(out)


def lua_table(rows):
    return '{' + ', '.join('{%d, %d, %d}' % tuple(r) for r in rows) + '}'


def lua_edit(e, funk):
    head = ("fn = '%s', " % e['fn'] if funk else '') + "ins = %d, op = %d" % (e['ins'], e['op'])
    name = OP_NAMES.get(e['op'], 'op')
    if 'spawn' in e:
        return ("        {%s,   -- %s\n"
                "         spawn = {old = %s,\n"
                "                  new = %s}},") % (head, name, lua_table(e['spawn']['old']), lua_table(e['spawn']['new']))
    return "        {%s, at = %d, old = '%s', new = '%s'},   -- %s" % (head, e['at'], e['old'], e['new'], e.get('note', name))


def lua_file(title, edits, funk):
    lines = ['-- %s' % title,
             '-- Generated by tools/script_edits.py: ReBorn\'s changes to the compiled scripts. An edit names the instruction (%s, number from 1)' %
             ('function of Vectoren.bin and instruction in it' if funk else 'instruction of the file'),
             '-- and its opcode; `spawn` replaces the sector\'s spawn table (FillSector operands {creature type, weight, group}), `at`/`old`/`new` a byte',
             '-- range inside the instruction. Gear checks `old` before it writes `new` (kind = \'script\', gear/overlay.cpp).',
             'return {', "    kind = 'script',", "    file = '%s'," % ('funk' if funk else 'start'), '    edits = {']
    lines += [lua_edit(e, funk) for e in edits]
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


def build(reborn, gog):
    """{rel: (funk, edits)} for every script file of ReBorn that differs from the game's."""
    result = {}
    for rel in script_files(reborn):
        a = open(gog + '/' + rel, 'rb').read()
        b = open(reborn + '/' + rel, 'rb').read()
        if a == b:
            continue
        if len(a) != len(b):
            raise SystemExit('%s: the size differs (%d vs %d): not an in-place edit' % (rel, len(a), len(b)))
        if rel.lower().endswith('funkcode.bin'):
            vec = open(os.path.dirname(gog + '/' + rel) + '/Vectoren.bin', 'rb').read()
            result[rel] = (True, edits_funk(a, b, vec))
        else:
            result[rel] = (False, edits_start(a, b))
    return result


def emit(result, out_dir):
    """Writes one Lua file per distinct edit list of {rel: (funk, edits)} into out_dir; returns {rel: file name}."""
    groups = collections.OrderedDict()
    for rel, (funk, edits) in sorted(result.items()):
        groups.setdefault(json.dumps([funk, edits], sort_keys=True), []).append(rel)
    names, used = {}, collections.Counter()
    for key, rels in groups.items():
        name = group_name(rels)
        used[name] += 1
        names[key] = name if used[name] == 1 else '%s_%d' % (name, used[name])
    os.makedirs(out_dir, exist_ok=True)
    mapping = {}
    for key, rels in groups.items():
        funk, edits = json.loads(key)
        title = '%s (%d files: %s)' % (names[key], len(rels), ', '.join(rels[:3]) + (', ...' if len(rels) > 3 else ''))
        with open(os.path.join(out_dir, names[key] + '.lua'), 'w', encoding='utf8', newline=chr(10)) as f:
            f.write(lua_file(title, edits, funk))
        for rel in rels:
            mapping[rel] = names[key] + '.lua'
    return mapping


def write_all(reborn, gog, out_dir, check):
    result = build(reborn, gog)
    mapping = emit(result, out_dir)
    if check:
        bad = 0
        for rel, (funk, edits) in result.items():
            a = open(gog + '/' + rel, 'rb').read()
            b = open(reborn + '/' + rel, 'rb').read()
            got = (apply_funk(a, open(os.path.dirname(gog + '/' + rel) + '/Vectoren.bin', 'rb').read(), edits)
                   if funk else apply_start(a, edits))
            if got != b:
                bad += 1
                print('MISMATCH', rel)
        print('self-check: %d script files rebuilt from %d edit files, %d mismatches' % (len(result), len(set(mapping.values())), bad))
        if bad:
            raise SystemExit(1)
    return mapping


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--reborn', required=True, help="ReBorn's data folder (the SRB folder)")
    ap.add_argument('--gog', required=True, help="the game's bin folder")
    ap.add_argument('--out', required=True)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    for rel, name in sorted(write_all(args.reborn, args.gog, args.out, args.check).items()):
        print(rel, '->', name)


if __name__ == '__main__':
    main()
