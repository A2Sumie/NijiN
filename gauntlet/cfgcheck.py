#!/usr/bin/env python3
"""CFG legality for Z8PRE.CFG v4 / Z8OG.CFG v1 (independent parser; no builder imports).

Z8PRE v4 (64B):  char[16] "Z8PRECFGv4"; u32 flags, u32 frames, u32 budget_us, u32 bit_depth;
                 0x20..0x3B zero reserved; u32 CRC32(IEEE) @0x3C over [0x00..0x3B].
  flags bits (F_KNOWN=0x7FF): 0 ENABLE, 1 C30, 2 FULL, 3 FOOTER, 4 DCF, 5 RAWONLY,
                              6 NOTHUMB, 7 MINITHUMB, 8 PVQ, 9 MENU, 10 PVFIX(reserved).
  semantic rules from z8precapture/config.py: PVQ requires RAWONLY; RAWONLY requires FULL.

Z8OG v1 (64B):   char[16] "Z8OGCFGv1"; u32 flags (bit0 = OpenGate enable, else 0);
                 0x14..0x3B ALL ZERO (non-zero -> whole file refused, 110 §A.2 fail-safe);
                 u32 CRC32 @0x3C. Any failure at runtime = feature off (fail-safe).

Orthogonality (110 §E.3): distinct magics/formats, independent CRCs, no shared mutable
state; absence of either file = that feature falls back to stock behaviour.
"""
import struct
import zlib

PRE_MAGIC = b'Z8PRECFGv4'
OG_MAGIC = b'Z8OGCFGv1'
CFG_BYTES = 64
PRE_F_KNOWN = 0x7FF
OG_F_KNOWN = 0x1
BUDGET_US = 1500000
BIT_DEPTHS = (0, 12, 14)
PRE_FLAGS = {'ENABLE': 0x1, 'C30': 0x2, 'FULL': 0x4, 'FOOTER': 0x8, 'DCF': 0x10,
             'RAWONLY': 0x20, 'NOTHUMB': 0x40, 'MINITHUMB': 0x80, 'PVQ': 0x100,
             'MENU': 0x200, 'PVFIX': 0x400}


class CfgError(ValueError):
    def __init__(self, message, check='G4.4'):
        super().__init__(message)
        self.check = check


def _need(ok, message, check='G4.4'):
    if not ok:
        raise CfgError(message, check)


def parse_pre(raw, ring_cap):
    """Validate a Z8PRE v4 file; returns facts dict or raises CfgError with the red reason."""
    _need(len(raw) == CFG_BYTES, 'Z8PRE length %d != 64' % len(raw), 'G4.1')
    _need(raw[:16] == PRE_MAGIC.ljust(16, b'\0'), 'Z8PRE magic/version mismatch (want Z8PRECFGv4)', 'G4.1')
    flags, frames, budget, bit_depth = struct.unpack_from('<4I', raw, 16)
    _need(flags & ~PRE_F_KNOWN == 0, 'Z8PRE flags has unknown bits: 0x%x (F_KNOWN=0x7FF)' % flags, 'G4.2')
    _need(raw[0x20:0x3C] == bytes(0x1C), 'Z8PRE reserved tail not zero', 'G4.2')
    _need(zlib.crc32(raw[:60]) & 0xffffffff == struct.unpack_from('<I', raw, 60)[0], 'Z8PRE CRC32 mismatch', 'G4.4')
    _need(1 <= frames <= ring_cap, 'Z8PRE frames %d outside 1..RING_CAP(%d)' % (frames, ring_cap), 'G4.3')
    _need(budget == BUDGET_US, 'Z8PRE budget_us %d != %d' % (budget, BUDGET_US), 'G4.3')
    _need(bit_depth in BIT_DEPTHS, 'Z8PRE bit_depth %d not in %s' % (bit_depth, (BIT_DEPTHS,)), 'G4.3')
    if flags & PRE_FLAGS['PVQ']:
        _need(flags & PRE_FLAGS['RAWONLY'], 'Z8PRE F_PVQ without F_RAWONLY (config.py invariant)', 'G4.2')
    if flags & PRE_FLAGS['RAWONLY']:
        _need(flags & PRE_FLAGS['FULL'], 'Z8PRE F_RAWONLY without F_FULL (config.py invariant)', 'G4.2')
    names = [n for n, b in PRE_FLAGS.items() if flags & b]
    return dict(kind='Z8PRE', magic='Z8PRECFGv4', flags=flags, flag_names=names, frames=frames,
                budget_us=budget, bit_depth=bit_depth,
                crc32=struct.unpack_from('<I', raw, 60)[0])


def parse_og(raw):
    """Validate a Z8OG v1 file; returns facts dict or raises CfgError with the red reason."""
    _need(len(raw) == CFG_BYTES, 'Z8OG length %d != 64' % len(raw), 'G4.1')
    _need(raw[:16] == OG_MAGIC.ljust(16, b'\0'), 'Z8OG magic/version mismatch (want Z8OGCFGv1)', 'G4.1')
    (flags,) = struct.unpack_from('<I', raw, 16)
    _need(flags & ~OG_F_KNOWN == 0, 'Z8OG flags has unknown bits: 0x%x (F_KNOWN=0x1)' % flags, 'G4.2')
    _need(raw[0x14:0x3C] == bytes(0x28), 'Z8OG reserved fields non-zero (110 §A.2: whole file refused)', 'G4.2')
    _need(zlib.crc32(raw[:60]) & 0xffffffff == struct.unpack_from('<I', raw, 60)[0], 'Z8OG CRC32 mismatch', 'G4.4')
    return dict(kind='Z8OG', magic='Z8OGCFGv1', flags=flags,
                flag_names=['ENABLE'] if flags & 1 else [],
                crc32=struct.unpack_from('<I', raw, 60)[0])


def orthogonality(facts_list):
    """Cross-file rule (110 §E.3): Z8PRE tier files coexist (pick one per card), at most
    one Z8OG, distinct magics/formats, independent CRCs, no shared state."""
    kinds = [f['kind'] for f in facts_list]
    _need(kinds.count('Z8OG') <= 1, 'two Z8OG on card (duplicate kind)')
    pre = {f['magic'] for f in facts_list if f['kind'] == 'Z8PRE'}
    og = {f['magic'] for f in facts_list if f['kind'] == 'Z8OG'}
    _need(len(pre) <= 1 and len(og) <= 1, 'CFG magic collision within kind')
    _need(not (pre & og), 'Z8PRE/Z8OG magic collision')
    return dict(kinds=sorted(kinds), z8pre_tiers=kinds.count('Z8PRE'))
