# Sacred ReBorn for Sacred Gear

**Sacred ReBorn** is made by the **Sacred ReBorn Overlookers group**, a non-commercial mod group: a balance mod built
around damage and resistance types, levelling a hero from 1 to 216 without item transfers, and an optional exe of its own
so the original game and its characters stay untouched.

This folder re-creates it as a mod for [Sacred Gear](https://github.com/kirides/sacred-bild) on the plain English GOG
`Sacred.exe`, generated mechanically from the user's own ReBorn install by `tools/reborn_port.py`:

- `overlay.txt`, `data/`: ReBorn's data files, served where the game opens the original ones;
- `abilities_edits.json`: ReBorn's values of the exe's ability tables, applied by `main.lua`;
- `main.lua`, `mod.lua`: the mod.

Put this folder at `<game>\mods\reborn` and start the game with Sacred Gear (SacredBild's `ddraw.dll` loads it).
