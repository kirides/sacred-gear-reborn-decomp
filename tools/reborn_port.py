# Sacred ReBorn -> Sacred Gear mod, mechanically.
#
#   python tools/reborn_port.py --reborn "<ReBorn folder>" --base "<German sacred.exe>" --target "<English Sacred.exe>"
#                               --map <map_de_eng.json> --out mods/reborn [--vanilla "<German install folder>"]
#
# ReBorn (by the Sacred ReBorn Overlookers group) is the German sacred.exe patched in place, plus data files beside
# the originals. This tool diffs the two exes, cuts the difference into patches at instruction boundaries, classifies
# them (hd: screen size / UI layout, which SacredBild already does; gameplay; cave: code ReBorn appended; data;
# string), checks where each lands in the English exe through the German -> English address map, and compares the
# data folders. Output: patches.json, manifest.json, report.md (+ summary on stdout).
import argparse, bisect, hashlib, json, os, re, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import capstone
from exeimg import Image, FuncTable, masked, cs
from analysis import write_analysis
import datamap

# ReBorn's globals for the screen size and everything derived from it (a block in the zero-filled part of .data)
HD_GLOBALS = (0xA1EF00, 0xA1F200)
# Where ReBorn put new code: the zero-filled part of .data and the tail of .rsrc
GAP = 3


def runs(a, b, lo, hi, gap=GAP):
    """Merged runs [start, end) where the images differ in [lo, hi)."""
    out, i = [], lo
    base = a.base
    A, B = a.img, b.img
    while i < hi:
        if A[i - base] != B[i - base]:
            j = i
            last = i
            while j < hi and j - last <= gap:
                if A[j - base] != B[j - base]:
                    last = j
                j += 1
            out.append((i, last + 1))
            i = last + 1
        else:
            i += 1
    return out


def printable(bs):
    return len(bs) >= 4 and all(32 <= c < 127 or c == 0 for c in bs) and sum(1 for c in bs if c) >= 4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reborn', required=True)
    ap.add_argument('--exe', default='SacredReborn.exe')
    ap.add_argument('--base', required=True, help="the German sacred.exe ReBorn was patched from")
    ap.add_argument('--target', required=True, help="the English Sacred.exe the mod runs on")
    ap.add_argument('--map', required=True, help="map_de_eng.json (tools/map_de_eng.py of sacred-bild)")
    ap.add_argument('--vanilla', help="the vanilla install the data is compared with (default: the folder of --target, the English install the mod runs on)")
    ap.add_argument('--bild-sites', help="sacred-bild's src/game/resolution_sites.inc (marks patches on its sites)")
    ap.add_argument('--eng-names', help="sacred-bild's tools/data/functions_eng.tsv (function names)")
    ap.add_argument('--decomp', help="decomp-sacred folder (English decompile)")
    ap.add_argument('--out', default='out')
    ap.add_argument('--mod', help="the mod folder to generate (overlay.txt, data/, abilities_edits.json), e.g. mods/reborn")
    ap.add_argument('--data', default='bin', choices=['none', 'bin', 'all'], help="which data files the overlay serves: the SRB data and text (bin), or all (also the PAKs)")
    ap.add_argument('--copy', action='store_true', help="copy the data files instead of hard-linking them")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    de = Image(args.base)
    rb = Image(os.path.join(args.reborn, args.exe))
    eng = Image(args.target)
    # 1. inputs: ReBorn's base must be the German exe (same timestamp and section layout)
    if de.timestamp != rb.timestamp or [s[:3] for s in de.sections[:3]] != [s[:3] for s in rb.sections[:3]]:
        sys.exit(f'the base exe (timestamp {de.timestamp:08X}) is not the build ReBorn was patched from '
                 f'({rb.timestamp:08X}): give --base the matching German sacred.exe')
    fmap = json.load(open(args.map))
    de_funcs = {f[0]: f for f in fmap['functions']}
    ft = FuncTable(de, de_funcs.keys())
    gmap = {int(k, 16): int(v[0], 16) for k, v in fmap['globals'].items()}
    gkeys = sorted(k for k in gmap if de.section_of(k) in ('.rdata', '.data'))
    gkeys = sorted(k for k in gmap if de.section_of(k) in ('.rdata', '.data'))
    bild = set()
    if args.bild_sites and os.path.exists(args.bild_sites):
        for m in re.finditer(r'// ([0-9A-F]{8}), ([0-9A-F]{8})', open(args.bild_sites).read()):
            bild.add(int(m.group(2), 16))

    patches = []
    stats = {}

    def add(p):
        patches.append(p)

    # 2. diff the sections both exes have in common (.text, .rdata, .data)
    for name, lo, size, _ in de.sections[:3]:
        hi = lo + size
        for s, e in runs(de, rb, lo, hi):
            if name == '.text':
                # snap to the vanilla instruction boundaries of the function containing the run
                f, insns = ft.insns(s)
                if f is None:
                    add({'section': name, 'de': s, 'len': e - s, 'old': de.rd(s, e - s), 'new': rb.rd(s, e - s),
                         'func': None, 'class_hint': 'raw'})
                    continue
                first = last = None
                for i in insns:
                    if i.address < e and i.address + i.size > s:
                        first = i.address if first is None else first
                        last = i.address + i.size
                if first is None:
                    first, last = s, e
                last = max(last, e)
                add({'section': name, 'de': first, 'len': last - first, 'old': de.rd(first, last - first),
                     'new': rb.rd(first, last - first), 'func': f})
            else:
                add({'section': name, 'de': s, 'len': e - s, 'old': de.rd(s, e - s), 'new': rb.rd(s, e - s), 'func': None})
    # merge text patches that touch the same or adjacent instructions
    patches.sort(key=lambda p: p['de'])
    merged = []
    for p in patches:
        q = merged[-1] if merged else None
        if q and p['section'] == '.text' == q['section'] and p['de'] <= q['de'] + q['len'] and p['func'] == q['func']:
            end = max(q['de'] + q['len'], p['de'] + p['len'])
            q['len'] = end - q['de']
            q['old'] = de.rd(q['de'], q['len'])
            q['new'] = rb.rd(q['de'], q['len'])
        else:
            merged.append(p)
    patches = merged
    stats = {}

    # 3. classify, translate the site
    new_code_targets = set()
    for p in patches:
        old, new = p['old'], p['new']
        feats = []
        # 4-byte words of the new bytes that point to ReBorn's screen-size globals
        words = [struct.unpack_from('<I', new, k)[0] for k in range(max(0, len(new) - 3))]
        if any(HD_GLOBALS[0] <= w < HD_GLOBALS[1] for w in words):
            feats.append('reads-hd-globals')
        if p['section'] == '.text':
            # jumps/calls into code ReBorn appended
            for i in cs.disasm(new, p['de']):
                if i.bytes[0] in (0xE8, 0xE9) and len(i.bytes) == 5:
                    t = (i.address + 5 + struct.unpack_from('<i', i.bytes, 1)[0]) & 0xFFFFFFFF
                    sec = rb.section_of(t)
                    if sec in ('.rsrc',) or (sec == '.data' and t >= 0x8E0000 and t < 0x8F0000) or t >= 0x1430000:
                        feats.append('jump-to-cave')
                        new_code_targets.add(t)
        if any(p['de'] <= b < p['de'] + p['len'] for b in bild):
            feats.append('bild-site')
        sec = p['section']
        if sec == '.text':
            if 'jump-to-cave' in feats:
                cls = 'hd' if ('reads-hd-globals' in feats or 'bild-site' in feats) else 'cave-hook'
            elif 'reads-hd-globals' in feats or 'bild-site' in feats:
                cls = 'hd'
            else:
                cls = 'gameplay'
        elif sec == '.rdata':
            cls = 'string' if printable(new) or printable(old) else 'data'
        else:
            if printable(new):
                cls = 'string'
            elif p['de'] >= HD_GLOBALS[0]:
                cls = 'new-data'        # ReBorn's own globals and blobs in the zero-filled end of .data
            else:
                cls = 'table'           # an edit in the exe's data tables (items, creatures, skills ...)
        p['class'] = cls
        p['features'] = sorted(set(feats))
        stats[cls] = stats.get(cls, 0) + 1

        # translation of the site
        status, eng_va = 'review', None
        if sec == '.text' and p['func'] in de_funcs:
            f = de_funcs[p['func']]
            cand = f[1] + (p['de'] - f[0])
            eb = eng.rd(cand, p['len'])
            # compare the vanilla bytes with the English ones, operands that are addresses excepted
            ok = True
            for i in cs.disasm(old, p['de']):
                m = masked(de, i)
                off = i.address - p['de']
                for k, b in enumerate(m):
                    if b is not None and eb[off + k] != b:
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                status, eng_va = 'auto', cand
        elif sec in ('.rdata', '.data'):
            if p['de'] in gmap:
                status, eng_va = 'auto', gmap[p['de']]
            elif cls == 'string':
                # find the vanilla string in the English exe
                key = old.rstrip(b'\0')
                if len(key) >= 6:
                    at = bytes(eng.img).find(key)
                    if at >= 0 and bytes(eng.img).find(key, at + 1) < 0:
                        status, eng_va = 'auto', eng.base + at
        if status == 'review' and sec in ('.rdata', '.data') and cls in ('table', 'string', 'data'):
            # context search: the 16 vanilla bytes before and after the patch, the patch itself left open
            pre, post = de.rd(p['de'] - 16, 16), de.rd(p['de'] + p['len'], 16)
            rx = re.compile(re.escape(pre) + b'.{%d}' % p['len'] + re.escape(post), re.DOTALL)
            hits = [m.start() for m in rx.finditer(bytes(eng.img))]
            if len(hits) == 1:
                status, eng_va = 'auto', eng.base + hits[0] + 16
            elif gkeys:
                # repeating records: the table keeps its layout, so the nearest paired global below the patch gives the
                # offset between the builds; accepted when the vanilla bytes around the patch agree there
                k = bisect.bisect_right(gkeys, p['de']) - 1
                while k >= 0 and de.section_of(gkeys[k]) != sec:
                    k -= 1
                if k >= 0:
                    g = gkeys[k]
                    want = p['de'] + (gmap[g] - g)
                    if eng.rd(want - 16, 16 + p['len'] + 16) == de.rd(p['de'] - 16, 16 + p['len'] + 16):
                        status, eng_va = 'auto', want
        p['eng'] = eng_va
        p['status'] = status

    # caves: the code ReBorn appended, cut at the jump targets
    caves = sorted(new_code_targets)

    # 4. data manifest
    van = args.vanilla or os.path.dirname(os.path.abspath(args.target))
    renames = datamap.derive_renames(patches, de, rb)
    manifest = datamap.build_manifest(args.reborn, van, renames)

    # 5. output
    def jp(p):
        d = dict(p)
        d['de'] = f"{p['de']:08X}"
        d['func'] = f"{p['func']:08X}" if p['func'] else None
        d['eng'] = f"{p['eng']:08X}" if p['eng'] else None
        d['old'] = p['old'].hex()
        d['new'] = p['new'].hex()
        return d

    with open(os.path.join(args.out, 'hunks.json'), 'w', newline='\n') as f:
        json.dump({'base': os.path.basename(args.base), 'target': os.path.basename(args.target),
                   'patches': [jp(p) for p in patches], 'caves': [f'{c:08X}' for c in caves]}, f, indent=0)
    with open(os.path.join(args.out, 'manifest.json'), 'w', newline='\n') as f:
        json.dump(manifest, f, indent=0)

    by = {}
    for p in patches:
        by.setdefault(p['class'], {'auto': 0, 'review': 0})[p['status']] += 1
    write_analysis(args, patches, de, rb, eng, fmap, gmap, caves, manifest, by)
    if args.mod:
        n = datamap.write_overlay(args.mod, args.reborn, manifest, args.data, link=not args.copy)
        print(json.dumps({'overlay_files': n, 'renames': manifest['renames']}))
    print(json.dumps({'patches': len(patches), 'by_class': by, 'caves': len(caves), 'data_files': len(manifest['files'])}))


SKIP_DIRS = {'_backup', '_reborn-test', 'gearautomation', 'capture', 'logs-before', 'save', 'sacredbild', 'mods'}
SKIP_EXT = {'.log', '.dmp', '.pdb', '.lnk', '.pdf', '.dll', '.exe', '.ico', '.ini', '.cfg', '.txt', '.html', '.rtf',
            '.dat', '.msg', '.script', '.info', '.hashdb', '.jpg', '.zip'}


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def data_manifest(reborn, vanilla):
    """New or changed data files of the ReBorn folder against the vanilla install."""
    files = []
    for root, dirs, fs in os.walk(reborn):
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS and not d.lower().startswith('_')]
        for name in fs:
            if os.path.splitext(name)[1].lower() in SKIP_EXT:
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, reborn).replace('\\', '/')
            vpath = os.path.join(vanilla, rel)
            size = os.path.getsize(path)
            if os.path.exists(vpath) and os.path.getsize(vpath) == size and sha(vpath) == sha(path):
                continue
            files.append({'path': rel, 'size': size, 'sha256': sha(path), 'status': 'new' if not os.path.exists(vpath) else 'changed'})
    files.sort(key=lambda f: f['path'].lower())
    return {'reborn': os.path.basename(reborn), 'files': files}


if __name__ == '__main__':
    main()
