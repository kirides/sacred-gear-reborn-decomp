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

Output: `patches.json`, `manifest.json` (data files with SHA-256), `report.md` (one row per patch: German and English
address, function, class, status `auto` / `review`).

Requires Python 3 with `capstone` and `pefile`.
