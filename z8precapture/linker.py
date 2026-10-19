"""Small checked AArch64 ELF linker; only read-only PROGBITS sections are accepted."""
import struct
from z8prores.package import require
CAVE, CAVE_END = 0x40960000, 0x40970000

def link(raw, cave=CAVE, entry='precapture_history_entry'):
    require(raw[:6] == b'\x7fELF\x02\x01' and struct.unpack_from('<HH', raw, 16) == (1, 183), 'Invalid AArch64 object or relocation')
    shoff = struct.unpack_from('<Q', raw, 40)[0]
    sz, n, si = struct.unpack_from('<HHH', raw, 58)
    ss = [struct.unpack_from('<IIQQQQIIQQ', raw, shoff + i * sz) for i in range(n)]
    names = raw[ss[si][4]:ss[si][4] + ss[si][5]]

    def name(s):
        return names[s[0]:names.index(0, s[0])].decode()
    indexes = [i for i, s in enumerate(ss) if s[2] & 2 and s[5]]
    indexes.sort(key=lambda i: (0 if name(ss[i]) == '.text.entry' else 1, i))
    out = bytearray()
    where = {}
    sections = []
    for i in indexes:
        s = ss[i]
        require(s[1] == 1 and (not s[2] & 1), ('mutable or non-PROGBITS section', name(s)))
        alignment = max(16, s[8])
        at = len(out) + alignment - 1 & -alignment
        out.extend(bytes(at - len(out)))
        where[i] = cave + at
        out.extend(raw[s[4]:s[4] + s[5]])
        sections.append(dict(index=i, name=name(s), va=hex(where[i]), bytes=s[5], executable=bool(s[2] & 4)))
    for s in ss:
        require(not (s[2] & 2 and s[5]) or ss.index(s) in where, ('unplaced allocatable section', name(s)))
    syms = []
    for s in ss:
        if s[1] != 2:
            continue
        strings = raw[ss[s[6]][4]:ss[s[6]][4] + ss[s[6]][5]]
        for at in range(s[4], s[4] + s[5], s[9]):
            nm, info, other, sec, val, size = struct.unpack_from('<IBBHQQ', raw, at)
            text = strings[nm:strings.index(0, nm)].decode()
            syms.append(dict(name=text, section=sec, va=where.get(sec, 0) + val, size=size))
    relocations = []
    for sec in ss:
        if sec[1] != 4 or not sec[5]:
            continue
        target = sec[7]
        if target not in where:
            continue
        for at in range(sec[4], sec[4] + sec[5], sec[9]):
            off, info, addend = struct.unpack_from('<QQq', raw, at)
            typ, idx = (info & 4294967295, info >> 32)
            sym = syms[idx]
            require(sym['section'] in where, ('unresolved symbol', sym))
            p = where[target] + off
            s = sym['va'] + addend
            o = p - cave
            before = struct.unpack_from('<I', out, o)[0]
            w = before
            if typ in (282, 283):
                d = s - p
                require(d % 4 == 0 and -(1 << 27) <= d < 1 << 27, 'Invalid AArch64 object or relocation')
                w = w & 4227858432 | d // 4 & 67108863
            elif typ in (274, 275):
                d = s - p if typ == 274 else ((s & ~4095) - (p & ~4095)) // 4096
                require(-(1 << 20) <= d < 1 << 20, 'Invalid AArch64 object or relocation')
                w = w & ~1627389920 | (d & 3) << 29 | (d >> 2 & 524287) << 5
            elif typ == 277:
                w = w & ~4193280 | (s & 4095) << 10
            elif typ in (278, 284, 285, 286, 299):
                shift = {278: 0, 284: 1, 285: 2, 286: 3, 299: 4}[typ]
                require(s % (1 << shift) == 0, 'Invalid AArch64 object or relocation')
                w = w & ~4193280 | (s & 4095) >> shift << 10
            elif typ in (280, 279):
                d = s - p
                require(d % 4 == 0, 'Invalid AArch64 object or relocation')
                if typ == 280:
                    require(-(1 << 20) <= d < 1 << 20, 'Invalid AArch64 object or relocation')
                    w = w & ~(524287 << 5) | (d // 4 & 524287) << 5
                else:
                    require(-(1 << 15) <= d < 1 << 15, 'Invalid AArch64 object or relocation')
                    w = w & ~(16383 << 5) | (d // 4 & 16383) << 5
            elif typ in (257, 258, 261):
                value = s - p if typ == 261 else s
                struct.pack_into('<Q' if typ == 257 else '<I', out, o, value & (1 << (64 if typ == 257 else 32)) - 1)
                relocations.append(dict(va=hex(p), type=typ, symbol=sym['name'], resolved=hex(s), addend=addend))
                continue
            else:
                raise ValueError('Unsupported relocation ' + str(typ))
            struct.pack_into('<I', out, o, w)
            relocations.append(dict(va=hex(p), type=typ, symbol=sym['name'], resolved=hex(s), addend=addend, before=hex(before), after=hex(w)))
    symbols = {s['name']: dict(va=hex(s['va']), bytes=s['size']) for s in syms if s['section'] in where and s['name']}
    require((entry is None or int(symbols[entry]['va'], 16) == cave) and cave + len(out) <= CAVE_END,
            'Invalid AArch64 object or relocation')
    return (bytes(out), sections, symbols, relocations)
