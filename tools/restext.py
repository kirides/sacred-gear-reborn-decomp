"""The text table of Sacred (scripts/<lang>/global.res): reading, a delta between two tables and applying it.

Format (little endian): u32 count; count entries of 16 bytes {u32 id, u32 offset, u32 flags, u32 length}, ascending by id; then the texts, one after
the other in the order of the entries, UTF-16LE without a terminator. An entry's offset is relative to the file start plus 4 (the first text starts
at 16 * count). The delta is `{set = {[id] = text | {text = ..., flags = n} | {hex = ...}}, remove = {id, ...}}`: the texts that are new or differ,
and the ids that are gone; entries not named stay as they are.
"""
import struct


def parse(data):
    count = struct.unpack_from('<I', data, 0)[0]
    out = {}
    for i in range(count):
        ident, offset, flags, length = struct.unpack_from('<IIII', data, 4 + 16 * i)
        out[ident] = (flags, bytes(data[offset + 4:offset + 4 + length]))
    return out


def build(entries):
    ids = sorted(entries)
    head = bytearray(struct.pack('<I', len(ids)))
    pool = bytearray()
    offset = 16 * len(ids)
    for ident in ids:
        flags, text = entries[ident]
        head += struct.pack('<IIII', ident, offset + len(pool), flags, len(text))
        pool += text
    return bytes(head + pool)


def delta(new, old):
    a, b = parse(new), parse(old)
    set_ = {i: v for i, v in a.items() if b.get(i) != v}
    remove = sorted(i for i in b if i not in a)
    return set_, remove


def apply(old, set_, remove):
    entries = parse(old)
    for i in remove:
        entries.pop(i, None)
    for i, v in set_.items():
        entries[i] = v
    return build(entries)


def lua_string(s):
    out = ["'"]
    for ch in s:
        o = ord(ch)
        if ch == '\\':
            out.append('\\\\')
        elif ch == "'":
            out.append("\\'")
        elif ch == '\n':
            out.append('\\n')
        elif ch == '\r':
            out.append('\\r')
        elif o < 32 or o == 127:
            out.append('\\%03d' % o)
        else:
            out.append(ch)
    out.append("'")
    return ''.join(out)


def lua_table(set_, remove, old_flags):
    """The `set` and `remove` parts as Lua source lines."""
    lines = ['    set = {']
    for ident in sorted(set_):
        flags, data = set_[ident]
        try:
            text = data.decode('utf-16-le')
            if text.encode('utf-16-le') != data or any(0xD800 <= ord(c) <= 0xDFFF for c in text):
                raise ValueError
            body = lua_string(text)
            if flags != old_flags.get(ident, 0):
                lines.append('        [%d] = {text = %s, flags = %d},' % (ident, body, flags))
            else:
                lines.append('        [%d] = %s,' % (ident, body))
        except (UnicodeDecodeError, ValueError):
            lines.append("        [%d] = {hex = '%s', flags = %d}," % (ident, data.hex(), flags))
    lines.append('    },')
    lines.append('    remove = {%s},' % ', '.join(str(i) for i in remove))
    return lines
