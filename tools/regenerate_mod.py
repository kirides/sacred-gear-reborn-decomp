#!/usr/bin/env python3
"""Regenerates mods/reborn from a ReBorn install in one go (run it again after a new ReBorn release):

  python tools/regenerate_mod.py --reborn "<ReBorn game folder>" --base "<German sacred.exe ReBorn was patched from>" \
      --gog "<the English GOG game folder the mod runs on>" --map <map_de_eng.json of sacred-bild> \
      [--total <TOTAL changelist.docx> --versions <changelist by versions.docx>]

  1. tools/reborn_port.py writes ReBorn's full data files and the rules (out-test/fullmod),
  2. tools/gen_constants.py writes the constant tables (CREATURE, ITEM, OPCODE) from the game's data, then
     tools/make_patches.py turns the files into readable patches against the GOG files (mods/reborn/patches, overlay.txt),
  3. tools/changelog_from_docx.py (when the documents are given) writes changes.json.
The Lua of the mod (main.lua, mod.lua) and abilities_edits.json are not touched by this script.
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def run(args):
    print('>', ' '.join(args))
    subprocess.check_call([sys.executable] + args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reborn', required=True)
    ap.add_argument('--base', required=True)
    ap.add_argument('--gog', required=True)
    ap.add_argument('--map', required=True)
    ap.add_argument('--extra', action='append', default=[], help='more folders with the game files of other languages (scripts/<lang>/global.res)')
    ap.add_argument('--total')
    ap.add_argument('--versions')
    ap.add_argument('--out', default=os.path.join(ROOT, 'mods', 'reborn'))
    a = ap.parse_args()
    full = os.path.join(ROOT, 'out-test', 'fullmod')
    run(['-I', os.path.join(HERE, 'reborn_port.py'), '--reborn', a.reborn, '--base', a.base, '--target', os.path.join(a.gog, 'Sacred.exe'),
         '--map', a.map, '--out', os.path.join(ROOT, 'out-test'), '--mod', full, '--data', 'bin', '--copy'])
    run([os.path.join(HERE, 'gen_constants.py'), '--gog', a.gog, '--out', os.path.join(a.out, 'constants'),
         '--balance', os.path.join(full, 'data', 'SRB', 'balance.bin')])
    run([os.path.join(HERE, 'make_patches.py'), '--full', full, '--gog', a.gog, '--out', a.out] + sum([['--extra', e] for e in a.extra], []))
    if a.total and a.versions:
        run([os.path.join(HERE, 'changelog_from_docx.py'), '--total', a.total, '--versions', a.versions, '--out', os.path.join(a.out, 'changes.json')])


if __name__ == '__main__':
    sys.exit(main())
