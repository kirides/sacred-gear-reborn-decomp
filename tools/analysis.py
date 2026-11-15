# Analysis output of the port tool: hunks.json + analysis.md, what ReBorn changes grouped by English function and data
# table, with the vanilla decompile's location. For reading, and for diffing two ReBorn releases; nothing here is
# applied to a game (ReBorn is re-created as Lua on Gear's APIs, see behaviours.md).
import bisect, os, re, struct
from exeimg import cs


def names_of(path):
    out = {}
    if path and os.path.exists(path):
        for line in open(path):
            if line.startswith('#') or '\t' not in line:
                continue
            a, n = line.rstrip('\n').split('\t')[:2]
            out[int(a, 16)] = n
    return out


def disasm(img, data, va, gmap, eng_of_func):
    """Instructions of `data` as text; German addresses that map are annotated with the English one."""
    lines = []
    for i in cs.disasm(data, va):
        txt = f'{i.mnemonic} {i.op_str}'.strip()
        notes = []
        for m in re.finditer(r'0x([0-9a-f]{6,8})', txt):
            v = int(m.group(1), 16)
            if v in gmap:
                notes.append(f'{v:08X}->{gmap[v]:08X}')
            elif img.section_of(v) == '.text' and eng_of_func(v) is not None:
                notes.append(f'{v:08X}->{eng_of_func(v):08X}')
        lines.append(f'{i.address:08X}  {i.bytes.hex():<16} {txt}' + (f'   ; {", ".join(notes)}' if notes else ''))
    return lines


def describe_words(b):
    """A table edit's bytes as an integer and float, whichever reads naturally."""
    if len(b) == 4:
        return f'{struct.unpack("<I", b)[0]} / {struct.unpack("<f", b)[0]:.4g}'
    if len(b) == 2:
        return str(struct.unpack('<H', b)[0])
    if len(b) == 1:
        return str(b[0])
    return b.hex()


def write_analysis(args, patches, de, rb, eng, fmap, gmap, caves, manifest, by):
    names = names_of(args.eng_names)
    de2eng = {f[0]: f[1] for f in fmap['functions']}
    de_keys = sorted(de2eng)

    def eng_func(v):
        i = bisect.bisect_right(de_keys, v) - 1
        return de2eng[de_keys[i]] + (v - de_keys[i]) if i >= 0 else None

    def decomp_path(va):
        if not args.decomp:
            return None
        d = os.path.join(args.decomp, 'src', f'{va >> 16:04X}'.replace('0x', ''))
        d = os.path.join(args.decomp, 'src', f'{va >> 16:04x}')
        for n in (names.get(va), f'FUN_{va:08x}'):
            if n:
                f = os.path.join(d, f'{va:08x}_{n}.c')
                if os.path.exists(f):
                    return f
        return None

    out = ['# ReBorn: what the exe changes', '',
           f'ReBorn exe `{os.path.basename(rb.path)}` against `{os.path.basename(de.path)}`: {len(patches)} hunks, '
           f'{len(caves)} jumps into appended code, {len(manifest["files"])} data files new or changed.', '',
           '| class | hunks | with English site | no English site |', '|---|---|---|---|']
    for cls, c in sorted(by.items()):
        out.append(f'| {cls} | {c["auto"] + c["review"]} | {c["auto"]} | {c["review"]} |')
    out += ['', '`hd` hunks (screen size, UI layout) are not listed below: SacredBild does that job.', '']

    out += ['## Code, per English function', '',
            'Vanilla = the German exe, ReBorn = its patched copy; German addresses are annotated with the English ones. '
            'The decompile of the English function is at the path given (Ghidra, no per-instruction mapping).', '']
    byf = {}
    for p in patches:
        if p['section'] == '.text' and p['class'] in ('gameplay', 'cave-hook') and p['func'] in de2eng:
            byf.setdefault(p['func'], []).append(p)
    for f in sorted(byf, key=lambda f: de2eng[f]):
        ef = de2eng[f]
        dp = decomp_path(ef)
        nlines = sum(1 for _ in open(dp, errors='ignore')) if dp else 0
        out += [f'### {ef:08X} {names.get(ef, "")} (DE {f:08X})', '',
                f'{len(byf[f])} hunk(s). Decompile: `{dp or "-"}`' + (f' ({nlines} lines)' if dp else ''),
                '', '| behaviour |', '|---|', '| _to describe_ |', '']
        for p in byf[f]:
            out += [f'#### {p["de"]:08X} -> {p["eng"] or 0:08X} [{p["class"]}] {p["len"]} bytes', '', 'Vanilla:', '```']
            out += disasm(de, p['old'], p['de'], gmap, eng_func)
            out += ['```', 'ReBorn:', '```']
            out += disasm(rb, p['new'], p['de'], gmap, eng_func)
            out += ['```', '']

    out += ['## Data tables in the exe', '',
            'Hunks in `.data` below 0xA00000 (tables of items, creatures, skills, ...), merged when closer than 0x40 bytes.', '']
    tabs = sorted((p for p in patches if p['class'] == 'table'), key=lambda p: p['de'])
    clusters = []
    for p in tabs:
        if clusters and p['de'] - (clusters[-1][-1]['de'] + clusters[-1][-1]['len']) < 0x40:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    out += [f'{len(tabs)} table hunks in {len(clusters)} clusters.', '',
            '| DE | ENG | span | hunks | first edits (vanilla -> ReBorn) |', '|---|---|---|---|---|']
    for c in clusters:
        lo, hi = c[0]['de'], c[-1]['de'] + c[-1]['len']
        edits = '; '.join(f'+{p["de"] - lo:X}: {describe_words(p["old"])} -> {describe_words(p["new"])}' for p in c[:4])
        out.append(f'| {lo:08X} | {c[0]["eng"] or 0:08X} | {hi - lo:#x} | {len(c)} | {edits}{" ..." if len(c) > 4 else ""} |')

    out += ['', '## Strings', '', '| DE | ENG | vanilla | ReBorn |', '|---|---|---|---|']
    for p in patches:
        if p['class'] == 'string':
            o = p['old'].rstrip(bytes(1)).decode('latin1')
            n = p['new'].rstrip(bytes(1)).decode('latin1')
            out.append(f'| {p["de"]:08X} | {p["eng"] or 0:08X} | `{o!r}` | `{n!r}` |')
    out += ['', '## Appended code', '',
            f'{len(caves)} jumps from the vanilla code into code ReBorn appended (in `.rsrc`, made executable): '
            + ', '.join(f'{c:08X}' for c in caves), '']
    with open(os.path.join(args.out, 'analysis.md'), 'w', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
