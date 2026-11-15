# sacred-gear-reborn-decomp

Sacred ReBorn as a Sacred Gear mod, generated mechanically from the user's own ReBorn install.

**Credit:** Sacred ReBorn is made by the Sacred ReBorn Overlookers group, a non-commercial mod group. It is their
work; this repository only contains the tooling that turns the difference between ReBorn and the original game into
a mod for Sacred Gear / SacredBild, with attribution to them.

## How it works

`tools/reborn_port.py` compares ReBorn's `SacredReborn.exe` with the German `sacred.exe` it was patched from, cuts the
difference into patches at instruction boundaries, classifies them (screen size/UI layout `hd`, `gameplay`, `table`
edits in the exe's data tables, `string`, `cave-hook` jumps into code ReBorn appended, `new-data`), finds each site in
the English `Sacred.exe` through the German -> English address map of
[sacred-bild](https://github.com/kirides/sacred-bild) (`tools/map_de_eng.py`), and lists the data files ReBorn adds or
changes. Run again for a new ReBorn release.

```
python tools/reborn_port.py --reborn "<ReBorn folder>" --base "<German sacred.exe>" --target "<English Sacred.exe>" \
    --map <sacred-bild>/tools/data/map_de_eng.json --out mods/reborn
```

Output: `hunks.json` (every hunk with its German and English address, class and bytes), `analysis.md` (per English
function and data table: vanilla and ReBorn disassembly side by side, decompile location), `manifest.json` (data files
with SHA-256). The hunks are **not applied** to a game: ReBorn is re-created as Lua on Sacred Gear's APIs, and
`behaviours.md` lists the behaviours that Lua has to reproduce. After a new ReBorn release the tool is run again and the
hunks are diffed against the previous set to see which behaviours changed.

Requires Python 3 with `capstone` and `pefile`.
