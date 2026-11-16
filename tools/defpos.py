"""DefPos.bin: the named positions of a script set (facts from Sacred.exe 0x46F9B0, checked against the game's and ReBorn's files).

Two layouts exist side by side in the game's own files:
  * written by the game (magic): u32 1234, then three tables `u32 count, count records`: 100 byte positions, 80 byte, 76 byte records;
  * older (no magic): the two first tables only; the game does not use it as it is: it makes the written layout from it and the scripts
    the first time it needs the file (and writes it back), a few seconds.
A 100 byte position record is: u32 flag (0), char name[60], 4 bytes of leftover stack, i32 x, i32 y, i32 -1, i32 (-1/0), 16 bytes of leftover
memory / heap pointers. What the engine uses is the flag, the name and the four values; the rest differs from run to run.
"""
import struct

MAGIC = 1234


def tables(data):
    """[list of records] per table (100, 80, 76 byte records); the magic is optional."""
    o = 4 if data[:4] == struct.pack('<I', MAGIC) else 0
    out = []
    for stride in (100, 80, 76):
        if o + 4 > len(data):
            break
        n, = struct.unpack_from('<I', data, o)
        o += 4
        if o + n * stride > len(data):
            raise ValueError('DefPos.bin: a table is longer than the file')
        out.append([data[o + i * stride:o + (i + 1) * stride] for i in range(n)])
        o += n * stride
    if o != len(data):
        raise ValueError('DefPos.bin: %d bytes left over' % (len(data) - o))
    return out


def positions(data):
    """The meaningful part of the position table: [(flag, name, x, y, v1, v2)]."""
    out = []
    for r in tables(data)[0]:
        name = r[4:64].split(b'\0', 1)[0]
        out.append((struct.unpack_from('<I', r, 0)[0], name) + struct.unpack_from('<4i', r, 68))
    return out


def same_positions(a, b):
    return positions(a) == positions(b)
