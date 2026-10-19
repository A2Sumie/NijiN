"""Merged capture configuration (CFG v4); never accesses a card."""
import struct
import zlib

CONFIG_NAME = 'Z8PRE.CFG'
MAGIC = b'Z8PRECFGv4'
# v4 layout: 0 ENABLE, 1 C30, 2 FULL, 3 FOOTER, 4 DCF, 5 RAWONLY,
#            6 NOTHUMB (drop 1620x1080 + fixed raw_at), 7 MINITHUMB (keep 160x120),
#            8 PVQ, 9 MENU, 10 PVFIX (reserved)
F_ENABLE, F_C30, F_FULL, F_FOOTER = 1, 2, 4, 8
F_DCF, F_RAWONLY, F_NOTHUMB, F_MINITHUMB = 0x10, 0x20, 0x40, 0x80
F_PVQ, F_MENU, F_PVFIX = 0x100, 0x200, 0x400


def build_config(diagnostic_footer=False, frames=20, c30=True, raw_only=False,
                 preview_quality=False, menu=True, dcf=True, no_thumb=False,
                 mini_thumb=True, pvfix=False, bit_depth=14):
    """frames<=20 (HE* ring ceiling, 109 basis); menu=True -> follow Image quality menu;
    bit_depth: NEF BitsPerSample label (12/14); 0 = leave the build default."""
    assert 1 <= frames <= 20
    flags = F_ENABLE | (F_C30 if c30 else 0) | (F_FOOTER if diagnostic_footer else 0)
    if dcf:
        flags |= F_DCF
    if raw_only:
        flags |= F_RAWONLY | F_FULL
    if preview_quality and raw_only:
        flags |= F_PVQ
    if menu:
        flags |= F_MENU
    if no_thumb:
        flags |= F_NOTHUMB
    if mini_thumb:
        flags |= F_MINITHUMB
    if pvfix:
        flags |= F_PVFIX
    b = bytearray(64)
    b[:16] = MAGIC.ljust(16, b'\0')
    struct.pack_into('<4I', b, 16, flags, frames, 1500000, bit_depth & 0xff)
    struct.pack_into('<I', b, 60, zlib.crc32(b[:60]) & 0xffffffff)
    return bytes(b)
