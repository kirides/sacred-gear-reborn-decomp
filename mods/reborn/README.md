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

## Data: delta patches against the game's own files

The mod does not ship ReBorn's data files whole. `patches/*.lua` are Lua data files with only the bytes that differ from the game's shipped file
(`bin/balance.bin`, `bin/sets.bin`, the script code of every hero type and campaign, the default positions), and `overlay.txt` has a `patch:` rule per
file: Gear applies the patch the first time the game opens the file, keeps the result in `cache/` and checks the size and crc32 of the original. They
are made mechanically: `tools/reborn_port.py ... --mod out-test/fullmod --data bin --copy` writes ReBorn's full files, then
`tools/make_patches.py --full out-test/fullmod --gog <game folder> --out mods/reborn` compares them with the game's files. Still full files in
`data/`: the language texts (`scripts/<lang>/SRglbl.res`) and three `DefPos.bin` whose size differs from the game's (a raw memory dump).
