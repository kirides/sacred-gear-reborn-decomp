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
`patches/scripts/*.lua` (5 files for all 40 script files); Gear's `kind = 'script'` applies them (see `docs/Gear.md` in sacred-bild).

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

## Checks

* `python tools/script_edits.py --reborn <SRB folder> --gog <game>/bin --out <dir> --check`: rebuilds all 40 script files from the edits (reference
  implementation of Gear's loader) and compares them with ReBorn's.
* `python tools/verify_cache.py --reborn <SRB folder> --mod <game>/mods/reborn`: after a run with the mod, compares the files Gear built (`cache/`) with
  ReBorn's own files, byte for byte.
