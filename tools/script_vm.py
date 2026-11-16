"""Reader of Sacred's compiled script files (FunkCode.bin, StartCode.bin) and the function table of Vectoren.bin.

Layout (facts from Sacred.exe 0x45F220 / 0x46BA90, see docs/script-files.md for the sources):
  * FunkCode.bin / StartCode.bin: a flat stream of instructions `u16 opcode, u16 length (including these 4 bytes), operands`.
  * Vectoren.bin: `u32 count`, then `count` records of 84 bytes: char name[64], i32 start (byte offset in FunkCode.bin), i32 length,
    i32 quest, i32 number, u32 deleted. A function is the instruction range [start, start + length).
"""
import struct


def instructions(data, start=0, end=None):
    """[(offset, opcode, length)] over data[start:end]; raises ValueError if the stream does not tile exactly."""
    end = len(data) if end is None else end
    out, p = [], start
    while p < end:
        if p + 4 > end:
            raise ValueError('truncated instruction at %d' % p)
        opcode, length = struct.unpack_from('<HH', data, p)
        if length < 4 or p + length > end:
            raise ValueError('bad length %d at %d' % (length, p))
        out.append((p, opcode, length))
        p += length
    return out


def functions(vectoren):
    """[(name, start, length, quest, number, deleted)] of a Vectoren.bin."""
    count, = struct.unpack_from('<I', vectoren, 0)
    out = []
    for i in range(count):
        rec = vectoren[4 + i * 84:4 + (i + 1) * 84]
        name = rec[:64].split(b'\0', 1)[0].decode('latin1')
        start, length, quest, number, deleted = struct.unpack_from('<iiiiI', rec, 64)
        out.append((name, start, length, quest, number, deleted))
    return out
