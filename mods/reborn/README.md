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

The mod does not ship ReBorn's data files whole. `patches/*.lua` are Lua data files with only what differs from the game's shipped file, and `overlay.txt`
has a `patch:` rule per file: Gear applies the patch the first time the game opens the file, keeps the result in `cache/` and checks the size and crc32 of the
original. Kinds of patch: tables of 32 bit words (`kind = 'words'`: `balance`, `sets`; the changed words as numbers, floats as `{f = x}`), byte runs (`ops`, with
insertions and deletions where the size differs: `scripts/<hero type or campaign>`, `defpos/...`) and text tables (`kind = 'texts'`: the new and changed texts by text id, readable: `patches/texts/us.lua`, `de.lua`). Only the languages the game ships (`de`, `us`)
have a patch: the other eight of ReBorn have no file in the game to compare with and are dropped.

They are made mechanically: `tools/reborn_port.py ... --mod out-test/fullmod --data bin --copy` writes ReBorn's full files, then
`tools/make_patches.py --full out-test/fullmod --gog <game folder> --out mods/reborn` compares them with the game's files (every patch is applied again in memory
and must give ReBorn's file before it is written). The checked-in result was verified in the game: all 52 patched files built by Gear are byte-identical to ReBorn's.

Everything above in one command (also after a new ReBorn release): `python tools/regenerate_mod.py --reborn <ReBorn folder> --base <German sacred.exe> --gog <English GOG folder> --map <map_de_eng.json> [--total ... --versions ...]`;
running it again on the same inputs gives the checked-in files unchanged.
