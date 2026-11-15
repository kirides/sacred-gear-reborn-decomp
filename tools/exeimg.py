# Minimal PE image helper for the port tool: mapped image, section table, instruction masking (capstone).
import bisect
import capstone
import pefile

cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
cs.detail = True


class Image:
    def __init__(self, path):
        pe = pefile.PE(path, fast_load=True)
        self.path = path
        self.base = pe.OPTIONAL_HEADER.ImageBase
        self.size = pe.OPTIONAL_HEADER.SizeOfImage
        self.timestamp = pe.FILE_HEADER.TimeDateStamp
        self.entry = pe.OPTIONAL_HEADER.AddressOfEntryPoint + self.base
        self.sections = []
        for s in pe.sections:
            self.sections.append((s.Name.rstrip(b'\0').decode(), self.base + s.VirtualAddress, s.Misc_VirtualSize,
                                  s.Characteristics))
        self.img = bytearray(pe.get_memory_mapped_image())
        text = self.sections[0]
        self.tlo, self.thi = text[1], text[1] + text[2]

    def section_of(self, va):
        for n, lo, size, _ in self.sections:
            if lo <= va < lo + size:
                return n
        return None

    def rd(self, va, n):
        return bytes(self.img[va - self.base:va - self.base + n])

    def in_image(self, v):
        return self.base <= v < self.base + self.size

    def u32(self, va):
        return int.from_bytes(self.rd(va, 4), 'little')


def masked(img, insn):
    """Instruction bytes with build-specific operands (absolute addresses, rel32 targets) replaced by None."""
    b = list(insn.bytes)
    op = b[0]
    if op in (0xE8, 0xE9) and len(b) == 5:
        b[1:5] = [None] * 4
    elif op == 0x0F and len(b) == 6 and 0x80 <= b[1] <= 0x8F:
        b[2:6] = [None] * 4
    if insn.disp_size == 4 and img.in_image(insn.disp & 0xFFFFFFFF):
        b[insn.disp_offset:insn.disp_offset + 4] = [None] * 4
    if insn.imm_size == 4 and op not in (0xE8, 0xE9) and not (op == 0x0F and 0x80 <= b[1] <= 0x8F):
        imms = [o.imm & 0xFFFFFFFF for o in insn.operands if o.type == capstone.x86.X86_OP_IMM]
        if imms and img.in_image(imms[-1]):
            b[insn.imm_offset:insn.imm_offset + 4] = [None] * 4
    return b


class FuncTable:
    """Sorted function entries with a sweep that yields instruction boundaries of the function containing an address."""

    def __init__(self, img, entries):
        self.img = img
        self.entries = sorted(entries)
        self._cache = {}

    def func_of(self, va):
        i = bisect.bisect_right(self.entries, va) - 1
        return self.entries[i] if i >= 0 else None

    def insns(self, va):
        lo = self.func_of(va)
        if lo is None:
            return None, []
        got = self._cache.get(lo)
        if got is None:
            i = bisect.bisect_right(self.entries, lo)
            hi = self.entries[i] if i < len(self.entries) else self.img.thi
            got = list(cs.disasm(self.img.rd(lo, hi - lo), lo))
            self._cache[lo] = got
        return lo, got
