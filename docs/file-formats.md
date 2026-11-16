# File formats behind the ReBorn mod

What the tools in `tools/` know about the game's data files, and where it comes from. Every address is in the **English GOG `Sacred.exe`**
(the Ghidra program `/Sacred.exe (GOG)`, decompiled in `decomp-sacred`) and was read there; facts that came from outside are marked
**[ref]** and were checked against the game's files and the decompilation before they were used.

**[ref]** = [Aytackydln/SacredEngineRemake](https://github.com/Aytackydln/SacredEngineRemake) (no licence: used as a reference only, no code
copied). It documents `Sacred.Core/GameBin/Scripts/*` (instruction layout, operand tags, opcode names, the function table). Our own code
(`tools/script_vm.py`, `script_edits.py`, `defpos.py`) is written from the facts below.

## Script files: `FunkCode.bin`, `StartCode.bin`, `Vectoren.bin`

Found in `bin/<hero type>/`, `bin/Addon/<hero type>/`, `bin/NetScript`, `bin/NetScriptCamp` (and `Addon/...`). Loader: `0x46F9B0` (opens
`StartCode.bin`, `FunkCode.bin`, `QuestCode.bin`, `QuestPoolCode.bin`, `DefPos.bin`, `Vectoren.bin` of the chosen script set).

**Instruction stream.** The code files are a flat sequence of instructions: `u16 opcode, u16 length, operands...`, `length` including the four
header bytes. The reader is `0x45F220` (reads the four bytes, then `length - 4` more), the executor `0x475680` (a `switch` on the opcode; opcode
`0x33` goes to `0x47C610`, the sector fill). Checked on all 40 script files of ReBorn and the game: the instructions of every function tile its
bytes exactly.

**Functions (`Vectoren.bin`)** **[ref]**: `u32 count`, then `count` records of 84 bytes: `char name[64]`, `i32 start` (byte offset in
`FunkCode.bin`), `i32 length` (bytes), `i32 quest`, `i32 number`, `u32 deleted` (first byte tested). More data follows the table (not used by the
tools). The functions cover `FunkCode.bin` without gaps (checked for `netscript`, `type_npc_elve`, `addon/type_npc_elve`); names are unique for the
functions ReBorn changes (the tools refuse a name that is not).

**Operands** are tagged: a tag byte, then a payload whose size depends on the tag **[ref]**. The ones that matter here:

| Tag | Payload | Meaning |
|---|---|---|
| `0x19` | 3 x i32 | sector spawn entry: resource (creature) type, signed weight, group **[ref]** |
| `0x33` | 2 x i32 | spawn level range **[ref]** |
| `0x34` | 2 x i32 | sector grid X, Y **[ref]** |
| `0x35` | 3 x i32 | min count, max count, area divisor **[ref]** |
| `0x36` | i32 | value copied to each generated creature **[ref]** |

**Opcodes** used by ReBorn's edits: `51` (`0x33`) **FillSector** and `8` **CreateObj**. The names come from the script vocabulary of the
Armalion editor, as listed in **[ref]**; both strings also exist in `Sacred.exe` (`FillSector` at file offset `0x54D370`, `CreateObj` at `0x54D4BC`),
which is how the names were confirmed.

**What ReBorn changes.** Per script file about 20 instructions (`StartCode.bin`: two bytes in two instructions), the same ones in every hero
type's file because they all compile the same library: the spawn tables of the sector functions `Sector<N>Enter` (`FillSector`: a 40 byte
header, then the `0x19` entries: `{creature type, weight, group}`), and two small `CreateObj` edits. `tools/script_edits.py` writes them as
`patches/scripts/*.lua` (5 files for all 40 script files; `FillSector` edits name the function and the sector, `StartCode.bin` edits the variable); Gear's `kind = 'script'` applies them (see `docs/Gear.md` in sacred-bild).

## `DefPos.bin` (named positions)

Loader: `0x46F9B0`. The game reads a first `u32`: if it is `1234` (`0x4D2`) the file is the layout the game itself writes, else it makes that layout
from the plain file and the scripts (a few seconds the first time) and writes it back (the same code writes: `1234`, then the three tables).

* written layout: `u32 1234`, then three tables `u32 count, count records`: 100 byte position records, 80 byte records, 76 byte records;
* plain layout (the older one, no magic): the first two tables only.

A position record (100 bytes) is `u32 flag` (0), `char name[60]`, 4 bytes of leftover stack, `i32 x`, `i32 y`, `i32` (-1), `i32` (-1 or 0), 16 bytes of
leftover memory and heap pointers (`0xCCCCCCCC` or garbage that differs between runs of the same game). The tool `defpos.py` compares the part the
engine uses (flag, name, the four values).

**ReBorn needs no DefPos files.** All 20 DefPos files of ReBorn have exactly the game's positions (flag, name, x, y and the two values of every
record). They differ from the game's own files only in the layout (some are in the written layout where the game's is the plain one and the other way
round) and in leftover bytes, i.e. they are copies of the same data that were written by the game at some time. Where the game has the plain layout it
makes the written one itself: tested with the Seraphim hero in the test copy, the game's own regeneration of the plain file gave a file whose tables
equal ReBorn's own written file in every meaningful field (positions, the 80 byte table whole, the 76 byte table except the pointer words), also with ReBorn's
own scripts. `make_patches.py` therefore ships nothing for DefPos and stops if a future ReBorn release has other positions.

## Names (`mods/reborn/constants/`)

The patches use names instead of numbers: `CREATURE.ANIMATED_CONJURER`, `ITEM.LARGE_TORCH`, `OPCODE.FILL_SECTOR`. The tables are written by
`tools/gen_constants.py` from the game's own data; Gear defines them as globals (`CREATURE`, `ITEM`, `OPCODE`: the upper case file name) when it reads
a patch, so the patch files stay plain Lua data. `meta/constants.lua` holds LuaLS annotations of them.

* **Creatures**: the object type catalogue of the game (`gear.data.object_types`, 0x80 byte records; the record's dword at +0x20 is the type id, which is
  also the key of its name text; kind byte +0x2E is 3 for creatures). `data/object_types.tsv` is a dump of the types that have a name (id, kind, model
  file, German name; made in the running game with Sacred Gear). The English name is the text of `scripts/us/global.res` with the same key as the
  German text in `scripts/de/global.res`; where several keys have that German text and their English texts differ, the first key is used and the table
  says "also: ..." in a comment. Names are upper case; duplicates get `_2`, `_3` in id order.
* **Items**: the types named in `sets.bin` and the starting items of `balance.bin`, named the same way.
* **Opcodes**: `CREATE_OBJ` (8), `FILL_SECTOR` (51) and `SET_VAR` (67): the instructions the patches use; names as in the references above, confirmed by
  the strings in `Sacred.exe` (`FillSector` 0x54D370, `CreateObj` 0x54D4BC, `SetVar` 0x54D104).

## `balance.bin` and `sets.bin` (what is named)

* `sets.bin` (read by 0x42C3E0): a count word, then 66 records of 28 words: ten item type ids (`item_1`..`item_10`), `set_identifier` (word 10),
  `count_and_index` (word 11: the count of items in the low byte, the index of the set above it **[ref]**), 16 words not named. ReBorn changes one thing: the
  `set_identifier` of sets 1..65 is 0 (the game's file has a counter 0x9821F1CE + n there; the item code at 0x42C3E0 reads the item ids and the count
  byte only).
* `balance.bin`: a count word (the byte size of the global block), then the global block, which the game copies to memory at 0xAD4490 (0x711F64, **[ref]**).
  Every word ReBorn changes is named in `patches/balance.lua` (`ops` is empty):
  * words 361..424 (block +0x5A0): the starting items of the heroes, 8 records (`HERO.SERAPHIM` .. `HERO.DAEMON`) of 8 slots: the game gives three lesser
    healing potions and a torch, ReBorn six potions, a torch and the class's combat art item;
  * words 453..482: five tables of six floats, one per **difficulty index** (0x56AA10 and others map the difficulty variable 1..4 to 0..3 and every other
    value to 5; index 4 is never selected; bronze, silver, gold, platinum, unused_4, niobium; `constants/difficulty.lua`). Their readers (found by scanning
    `Sacred.exe` for the addresses): 0xAD4BA0 **rating factor**: attack value / defence value of creatures above level 16 (0x56AA10, 0x56AA90, called with the
    "HP .. AW .. VW .. DP .. DF" debug string of 0x627180) and a value of the damage calculation 0x56B130; 0xAD4BB8 **hit point factor** (0x5658F0 computes
    a creature's hit points through a level band table at 0xAD4778 and this factor; the decompiler drops the x87 reads, so this one is read from the
    disassembly); 0xAD4BD0 and 0xAD4BE8 **damage factors** (0x56B130: four damage values each, one for a creature of level 17+ hitting one below 17, the
    other the other way round); 0xAD4C00 **experience factor** (0x57D860, one `switch` over the difficulty). A sixth table (0xAD4C18, integers 0, 35, 70, 128)
    is the level a difficulty adds (0x47C610 and others); ReBorn leaves it. That index 5 is Niobium is inferred (the game maps difficulty 5 and 0 to it);
  * words 622..626 (0xAD4E44): the multiplayer level limits: the UI (0x707220, 0x707540) shows Silver from `silver_min_level` to `platinum_min_level`, Gold
    from `gold_min_level` to `niobium_min_level`, Platinum from `platinum_min_level` to `platinum_max_level`, Niobium from `niobium_min_level`, Bronze up to
    `gold_min_level` (ReBorn: Silver from level 1 instead of 20);
  * words 5598..: nine region records of 16 words (`REGION.NORTHKERN` .. `REGION.REGION_9`): a counter (twice), the region number and `UI_REGION_<NAME>`
    (char[32]). ReBorn sets both counters to 2000 in every region, which its changelist calls "the counter of region bosses"; the code that reads this table was
    not traced, so the field names `boss_counter` and `boss_counter_copy` come from the changelist and the two equal values in the game's file.

## Script operand tags (the CreateObj edits)

A `CreateObj` instruction (opcode 8) is a list of tagged operands. The tag names come from the Armalion editor vocabulary as listed by **[ref]** (they are
not strings of `Sacred.exe`; the payload shapes were checked against the files): `NIX` 0x00, `SET_NAME` 0x01 (string), `SET_TYPE` 0x02 (type id),
`SET_WPOS` 0x20 (three int32), `FLY_TO` 0x3C (a position; X = -2 means a symbolic one: a string such as `cpos:hero`), `QUEST_ITEM` 0x61. ReBorn's two edits:
the object `fillchest_chestQJ_03` loses its `FLY_TO "cpos:hero"` (the tag becomes `NIX`), and in `Sector22052Init` two tag bytes 0x9E (a tag that is in no list)
come in front of `SET_WPOS`, which moves the instruction's last two bytes out; both are kept as the bytes ReBorn has, with a comment.

## What has no name, and why

* `unused_4` of the difficulty tables: the index the game never selects (ReBorn edits it anyway).
* `word_1`, `word_4`..`word_7` of a region record, `word_12`..`word_27` of a set record: leftover memory or unknown, not changed by ReBorn.
* Sets have no names: the set records name their items and an index only; the set's display name is not in `sets.bin` (not traced).
* The 0x9E bytes of the second `CreateObj` edit: no tag of that value is known.

## Checks

* `python tools/script_edits.py --reborn <SRB folder> --gog <game>/bin --out <dir> --check`: rebuilds all 40 script files from the edits (reference
  implementation of Gear's loader) and compares them with ReBorn's.
* `python tools/verify_cache.py --reborn <SRB folder> --mod <game>/mods/reborn`: after a run with the mod, compares the files Gear built (`cache/`) with
  ReBorn's own files, byte for byte.
