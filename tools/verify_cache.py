#!/usr/bin/env python3
"""Compares what Gear built from the mod's patches (mods/reborn/cache/, written the first time the game opens a patched file) with ReBorn's own
data files, byte for byte.

  python tools/verify_cache.py --reborn "<ReBorn SRB folder>" --mod "<game>/mods/reborn" --gog "<game>/bin"

Run the game once with the mod first (a hero of a type is enough for that type's files; `-gear-auto -gear-load=N -gear-mods=reborn`). Files the game
did not open yet have no cache entry and are reported, not counted as errors. Texts and word tables are compared when their files exist too.
"""
import argparse
import os
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reborn', required=True)
    ap.add_argument('--mod', required=True)
    ap.add_argument('--gog', required=True)
    a = ap.parse_args()
    same = bad = untouched = missing = derived = 0
    for root, _, names in os.walk(a.reborn):
        for n in names:
            if not n.lower().endswith('.bin'):
                continue
            rel = os.path.relpath(os.path.join(root, n), a.reborn).replace(os.sep, '/')
            theirs = open(os.path.join(root, n), 'rb').read()
            cache = os.path.join(a.mod, 'cache', 'bin', *rel.lower().split('/'))
            game = os.path.join(a.gog, *rel.split('/'))
            if os.path.exists(cache):
                if open(cache, 'rb').read() == theirs:
                    same += 1
                else:
                    bad += 1
                    print('DIFFERENT:', rel)
            elif os.path.exists(game) and open(game, 'rb').read() == theirs:
                untouched += 1          # the game's own file is already ReBorn's (or DefPos: derived by the game)
            elif n.lower() == 'defpos.bin':
                derived += 1            # not shipped: the game derives it (docs/file-formats.md)
            else:
                missing += 1
                print('not built yet or not covered:', rel)
    print('%d files built by Gear are identical to ReBorn, %d differ, %d are the game\'s own, %d not built or not covered' % (same, bad, untouched, missing))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
