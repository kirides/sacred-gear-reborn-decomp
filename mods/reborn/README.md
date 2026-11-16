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

## Version and the Changes screen

The mod re-creates **Sacred ReBorn HD 4.6** (the version of `SacredReborn.exe` it was generated from). Its page in the Mods screen (F11) has a **Changes**
button that opens a window with what ReBorn changes, section by section (`changes.json`). Make that file from the group's changelist documents with
`python tools/changelog_from_docx.py --total <TOTAL changelist.docx> --versions <changelist by versions.docx> --out mods/reborn/changes.json`; the
version shown is the last version of the "by versions" document. The mod's description in `mod.lua` names the version too: update both after a new release.
