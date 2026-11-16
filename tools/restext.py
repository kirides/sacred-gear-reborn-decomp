"""The text table of Sacred (scripts/<lang>/global.res): reading, a delta between two tables and applying it.

Format (little endian): u32 count; count entries of 16 bytes {u32 id, u32 offset, u32 flags, u32 length}, ascending by id; then the texts, one after
the other in the order of the entries, UTF-16LE without a terminator. An entry's offset is relative to the file start plus 4 (the first text starts
at 16 * count). Some tables (ReBorn's Russian one) have the same id twice: an id then holds a list of entries, in file order.
The delta is `{set = {[id] = text | {text = ..., flags = n} | {hex = ...} | {list = {entry, ...}}}, remove = {id, ...}}`: the texts that are new or
differ (a `list` replaces all entries of an id), and the ids that are gone; entries not named stay as they are.
"""
import struct


def parse(data):
    """{id: [(flags, text bytes), ...]} in file order."""
    count = struct.unpack_from('<I', data, 0)[0]
    out = {}
    for i in range(count):
        ident, offset, flags, length = struct.unpack_from('<IIII', data, 4 + 16 * i)
        out.setdefault(ident, []).append((flags, bytes(data[offset + 4:offset + 4 + length])))
    return out


def build(entries):
    ids = sorted(entries)
    flat = [(i, f, t) for i in ids for f, t in entries[i]]
    head = bytearray(struct.pack('<I', len(flat)))
    pool = bytearray()
    offset = 16 * len(flat)
    for ident, flags, text in flat:
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
        if ch == chr(92):
            out.append(chr(92) * 2)
        elif ch == "'":
            out.append(chr(92) + "'")
        elif ch == chr(10):
            out.append(chr(92) + 'n')
        elif ch == chr(13):
            out.append(chr(92) + 'r')
        elif o < 32 or o == 127:
            out.append(chr(92) + '%03d' % o)
        else:
            out.append(ch)
    out.append("'")
    return ''.join(out)


def _entry(flags, data, old_flag):
    """One entry as Lua: a string, {text = , flags = } or {hex = , flags = }."""
    try:
        text = data.decode('utf-16-le')
        if text.encode('utf-16-le') != data or any(0xD800 <= ord(c) <= 0xDFFF for c in text):
            raise ValueError
        body = lua_string(text)
        return body if flags == old_flag else '{text = %s, flags = %d}' % (body, flags)
    except (UnicodeDecodeError, ValueError):
        return "{hex = '%s', flags = %d}" % (data.hex(), flags)


def lua_table(set_, remove, old):
    """The `set` and `remove` parts as Lua source lines; `old` is the parsed original."""
    lines = ['    set = {']
    for ident in sorted(set_):
        entries = set_[ident]
        old_flag = old[ident][0][0] if ident in old else 0
        if len(entries) == 1:
            lines.append('        [%d] = %s,' % (ident, _entry(entries[0][0], entries[0][1], old_flag)))
        else:
            lines.append('        [%d] = {list = {%s}},' % (ident, ', '.join(_entry(f, t, 0) for f, t in entries)))
    lines.append('    },')
    lines.append('    remove = {%s},' % ', '.join(str(i) for i in remove))
    return lines
