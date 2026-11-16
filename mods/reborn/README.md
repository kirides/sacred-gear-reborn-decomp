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

The mod does not ship ReBorn's data files whole, and no byte-run patches either. `patches/` has Lua data files with only what differs from the game's shipped
file, and `overlay.txt` has a `patch:` rule per file: Gear applies the patch the first time the game opens the file and keeps the result in `cache/`.
All of them are readable:

- `kind = 'words'` (`balance.lua`, `sets.lua`): the changed 32 bit words; `sets.lua` and the starting items of `balance.lua` with named fields, the rest as
  words (floats as `{f = x}`) with their position;
- `kind = 'texts'` (`texts/us.lua`, `de.lua`, `ru.lua`): the new and changed texts by text id. Only the languages the game ships (`de`, `us`) plus `ru`
  have a patch: the other seven of ReBorn have no file in the game to compare with and are dropped;
- `kind = 'script'` (`scripts/*.lua`, 5 files for the 40 script files): edits of `FunkCode.bin` / `StartCode.bin` by function name and sector, mostly the
  spawn tables of the sectors (`Sector88067Enter`: `{creature = CREATURE.SKELETON, weight = 40, group = 1}` lists), a few variables (`SoldatCnt`) and two
  small `CreateObj` edits (hex, with a comment saying what they are); the old values are checked before the new ones are written;
- `constants/*.lua` (`CREATURE`, `ITEM`, `OPCODE`, made by `tools/gen_constants.py` from the game's data) are the names the patches use; Gear reads them when it
  applies a patch; `meta/constants.lua` is for the editor (LuaLS);
- `DefPos.bin`: nothing. ReBorn's files hold the game's positions; the game derives the rest itself (`docs/file-formats.md`).

Format notes, sources and checks: `docs/file-formats.md`.

They are made mechanically: `tools/reborn_port.py ... --mod out-test/fullmod --data bin --copy` writes ReBorn's full files, then
`tools/make_patches.py --full out-test/fullmod --gog <game folder> --out mods/reborn` compares them with the game's files (every patch is applied again in memory
and must give ReBorn's file before it is written). The checked-in result was verified in the game: all 42 patched files built by Gear (40 scripts, balance, sets) are byte-identical to ReBorn's (`tools/verify_cache.py`).

Everything above in one command (also after a new ReBorn release): `python tools/regenerate_mod.py --reborn <ReBorn folder> --base <German sacred.exe> --gog <English GOG folder> --map <map_de_eng.json> [--total ... --versions ...]`;
running it again on the same inputs gives the checked-in files unchanged.

### More languages

ReBorn has ten languages, the English GOG install ships two (`de`, `us`), so only those two have a patch from the GOG install alone; `ru` was added from a Russian install (`B:/spiele/gog games/sacred-gold-RUS`). For another language you need the game's own
`scripts/<lang>/global.res` of that language (from an install in that language): put it in a folder with the same layout (`<folder>/scripts/fr/global.res`),
pass the folder with `--extra <folder>` to `tools/regenerate_mod.py` (or `tools/make_patches.py`) and the tool writes `patches/texts/fr.lua`. The same file must
be in the game folder (`scripts/fr/global.res`) when the mod runs: the patch is applied to it (and refused if its size or crc32 differ).
