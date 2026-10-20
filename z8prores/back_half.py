"""Recording and display side of the ProRes quality patch: the stored choice 0..3 selects what is
recorded and what the text displays call it.

Six one-word hooks into stock code, each jumping to a short routine in the text gap:
  type    40d1eb88  ProRes record service, 4:2:2 branch: hardware type = stored value instead of the
                    unused quality flag; the stock range check `cmp w8,#2` becomes `cmp w8,#4`
  rate    40d1e5f4  bit-rate lookup, 4:2:2 branch: one of four mode tables (stock table for HQ,
                    three copies with scaled bit rates for 422, LT, Proxy)
  label   40cee4d0  sample-description writer: FourCC apch/apcn/apcs/apco and the encoder name
  parser  40ce9acc  playback: accept the four FourCCs instead of apch only, and remember the grade
                    of the clip just opened (one byte next to the stored choice)
  shoot   404f8da0  shooting display, CODEC text: the name table entry of file type 4 gives the
                    name of the stored choice (the table itself is not changed)
  play    4064d054  playback information: the ProRes 422 case writes the name of the remembered
                    grade into the same 14-byte stack buffer the stock code fills with "ProRes 422 HQ"
Menu-bank hook (bank=True):
  bank    410162ec  DS item copy between menu banks (410161f0, called only from the bank list loop
                    41013578): when the item is WbMovieSameStill (120Bh, one byte) the copy takes two
                    bytes, so the stored choice in the next byte moves with the bank like any setting.
                    The remembered playback grade (the byte after) is not copied.
Hardware types 0/1/2/3 select HQ/422/LT/Proxy.
Used by menu.build_main; offline only.
"""
import struct

from .a64 import Block
from .base import at as _at

BASE = 0x40160000
TYPE_SITE, TYPE_CHECK, TYPE_RESUME = 0xBBEB88, 0xBBEB90, 0x40D1EB8C
RATE_SITE, RATE_RESUME, RATE_TABLE, RATE_ROWS = 0xBBE5F4, 0x40D1E650, 0x2953A50, 9
LABEL_SITE, LABEL_NEXT = 0xB8E4D0, 0x40CE40A4
PARSER_SITE, PARSER_ACCEPT, PARSER_REJECT = 0xB89ACC, 0x40CE9ADC, 0x40CE9BBC
SHOOT_SITE, SHOOT_RESUME, SHOOT_KEY = 0x398DA0, 0x404F8DA4, 4      # key 4 = file type ProRes 422
PLAY_SITE, PLAY_RESUME, PLAY_BUFFER = 0x4ED054, 0x4064D0D8, 0x118   # buffer: 14 bytes at sp+118h
BANK_SITE, BANK_RESUME, BANK_DONE, BANK_ITEM = 0xEB62EC, 0x410162F0, 0x41016338, 0x120B
BANK_STOCK = 0xA94023EA                                  # ldp x10,x8,[sp]  (x10 = target item, x8 = source item)
STOCK = {TYPE_SITE: 0xB9406AE8,      # ldr w8,[x23,#0x68]
         TYPE_CHECK: 0x7100091F,     # cmp w8,#2
         RATE_SITE: 0xD2874A0A,      # mov x10,#0x3a50
         LABEL_SITE: 0x97FFD6F5,     # bl 0x40ce40a4
         PARSER_SITE: 0x528C6D08,    # mov w8,#0x6368
         SHOOT_SITE: 0xF9400521,     # ldr x1,[x9,#8]
         PLAY_SITE: 0xD299330A}      # mov x10,#0xc998
FOURCC_LAST = b'hnso'                                    # apch apcn apcs apco
NAMES = (b'Apple ProRes 422 HQ', b'Apple ProRes 422', b'Apple ProRes 422 LT', b'Apple ProRes 422 Proxy')
# Text displays: at most 13 characters, the length of the two stock names ("ProRes 422 HQ",
# "ProRes RAW HQ"), so the playback buffer and both widgets get nothing longer than they do now.
DISPLAY = (b'ProRes 422 HQ', b'ProRes 422', b'ProRes 422 LT', b'ProRes Proxy')
GRADE_BY_DIFF = bytes([0, 0, 0, 0, 0, 0, 1, 3, 0, 0, 0, 2])   # FourCC - 'apch': h 0, n 6, o 7, s 11
# Apple's published target rates at one frame size, relative to HQ (220 : 147 : 102 : 45 Mb/s).
RATE_SCALE = ((1, 1), (147, 220), (102, 220), (45, 220))
MIBIT = 1 << 20


def va(offset):
    return BASE + offset


def _va(address):
    """A stock code address in the base under construction (recipe address in)."""
    return BASE + _at(address - BASE)


def rate_tables(img):
    stock = img.old[RATE_TABLE:RATE_TABLE + 0x18 * RATE_ROWS]
    out = []
    for num, den in RATE_SCALE[1:]:
        table = bytearray(stock)
        for row in range(RATE_ROWS):
            rate = struct.unpack_from('<Q', stock, 0x18 * row + 0x10)[0]
            if rate % (10 * MIBIT):
                raise ValueError('stock bit rate is not a multiple of 10 Mibit/s')
            scaled = (rate * num + den * MIBIT // 2) // (den * MIBIT) * MIBIT      # nearest whole Mibit/s
            struct.pack_into('<Q', table, 0x18 * row + 0x10, scaled)
        out.append(bytes(table))
    return out


def apply(img, cs, value_ram, stash_ram, code_at, limit, bank=False):
    if any(len(n) > 13 for n in DISPLAY) or DISPLAY[0] != b'ProRes 422 HQ':
        raise ValueError('display names must fit the stock 14-byte buffer')
    for site, word in STOCK.items():
        if img.u32(site) != word:
            raise ValueError(f'stock word at {site:#x} differs')
    if bank and (img.u32(_at(BANK_SITE)) != BANK_STOCK or value_ram != 0xA03D5C029):
        raise ValueError('bank hook: stock word or value byte differs')
    code_at = (code_at + 3) & ~3
    blk = Block(va(code_at))

    def value(reg):
        blk.mov_x64(reg, value_ram)
        blk.ldrb_w(reg, reg)
        blk.and_w3(reg, reg)

    # type: w8 = stored value, then back to the stock `str w9,[x20,#0x10]`
    blk.label('type')
    value(8)
    blk.b(_va(TYPE_RESUME))
    # rate: x10 = table for the stored value, w8 = row size, then the stock row copy (w9 = row index)
    blk.label('rate')
    value(10)
    blk.adr(8, 'rate_pointers')
    blk.ldr_x_idx8(10, 8, 10)
    blk.mov_w(8, 0x18)
    blk.b(_va(RATE_RESUME))
    # label: x0 = sample description just copied from the apch template, w1 = its size (both kept)
    blk.label('label')
    value(9)
    blk.cbz_w(9, 'label_done')
    blk.adr(10, 'fourcc')
    blk.ldrb_idx(11, 10, 9)
    blk.strb_w(11, 0, 7)
    blk.adr(10, 'names')
    blk.add_x(10, 10, 9, lsl=5)
    blk.add_xi(12, 0, 0x32)
    blk.mov_w(13, 32)
    blk.label('label_copy')
    blk.ldrb_post(11, 10, 1)
    blk.strb_post(11, 12, 1)
    blk.subs_wi(13, 13, 1)
    blk.b_cond('ne', 'label_copy')
    blk.label('label_done')
    blk.b(_va(LABEL_NEXT))
    # parser: w0 = FourCC; accept apch, apcn, apco, apcs (differences 0, 6, 7, 11 -> mask 0x8c1)
    blk.label('parser')
    blk.mov_w(8, 0x6368)
    blk.movk_w16(8, 0x6170)
    blk.sub_w(9, 0, 8)
    blk.cmp_wi(9, 11)
    blk.b_cond('hi', 'parser_reject')
    blk.mov_w(10, 0x8C1)
    blk.lsr_wv(10, 10, 9)
    blk.tbz_w(10, 0, 'parser_reject')
    blk.adr(10, 'grade_by_diff')
    blk.ldrb_idx(10, 10, 9)
    blk.mov_x64(11, stash_ram)
    blk.strb_w(10, 11)
    blk.b(_va(PARSER_ACCEPT))
    blk.label('parser_reject')
    blk.b(_va(PARSER_REJECT))
    # shoot: x9 = matched {key, name} entry of the stock table; x1 = name for the text widget
    blk.label('shoot')
    blk.ldr_x(1, 9, 8)                                # the replaced stock instruction
    blk.ldr_w(10, 9, 0)
    blk.cmp_wi(10, SHOOT_KEY)
    blk.b_cond('ne', 'shoot_done')
    value(10)
    blk.cbz_w(10, 'shoot_done')
    blk.adr(11, 'display')
    blk.add_x(1, 11, 10, lsl=4)
    blk.label('shoot_done')
    blk.b(_va(SHOOT_RESUME))
    # play: fill the stock buffer with the name of the remembered grade, then the stock widget call
    blk.label('play')
    blk.mov_x64(10, stash_ram)
    blk.ldrb_w(10, 10)
    blk.and_w3(10, 10)
    blk.adr(11, 'display')
    blk.add_x(10, 11, 10, lsl=4)
    blk.ldr_x(12, 10, 0)
    blk.str_x(12, 31, PLAY_BUFFER)
    blk.ldr_w(12, 10, 8)
    blk.str_w(12, 31, PLAY_BUFFER + 8)
    blk.ldrh_w(12, 10, 12)
    blk.strh_w(12, 31, PLAY_BUFFER + 12)
    blk.b(_va(PLAY_RESUME))
    if bank:
        # bank: one-byte item copy; w20 = item id (low 16 bits count), x8 = source, x10 = target item
        blk.label('bank')
        blk.ldp(10, 8, 0)                                 # the replaced stock instruction
        blk.lsl_wi(9, 20, 16)
        blk.mov_w(11, 0)
        blk.movk_w16(11, BANK_ITEM)
        blk.cmp_w(9, 11)
        blk.b_cond('eq', 'bank_pair')
        blk.b(_va(BANK_RESUME))                                # any other one-byte item: the stock copy
        blk.label('bank_pair')
        blk.ldrh_w(9, 8)                                  # WbMovieSameStill and the stored choice
        blk.strh_w(9, 10)
        blk.ldrb_w(8, 8)                                  # value reported to the caller, as in the stock path
        blk.b(_va(BANK_DONE))
    # data, 8-byte aligned
    while blk.here % 8:
        blk.nop()
    code_words = len(blk.items)
    tables = rate_tables(img)
    data_at = blk.here
    blk.labels['rate_pointers'] = data_at
    first_table = data_at + 4 * 8
    pointers = struct.pack('<4Q', va(RATE_TABLE), *(first_table + len(tables[0]) * i for i in range(3)))
    blk.labels['fourcc'] = first_table + sum(map(len, tables))
    blk.labels['names'] = blk.labels['fourcc'] + 8
    blk.labels['grade_by_diff'] = blk.labels['names'] + 32 * len(NAMES)
    blk.labels['display'] = blk.labels['grade_by_diff'] + 16
    names = b''.join((bytes([len(n)]) + n).ljust(32, b'\0') for n in NAMES)
    data = pointers + b''.join(tables) + FOURCC_LAST.ljust(8, b'\0') + names + GRADE_BY_DIFF.ljust(16, b'\0') + \
        b''.join(n.ljust(16, b'\0') for n in DISPLAY)
    listing = blk.listing(cs)[:code_words]
    blob = blk.bytes() + data
    if code_at + len(blob) > limit:
        raise ValueError('code area too small for the recording side')
    img.put(code_at, blob, 'code and tables: hardware type, bit-rate table, container label, playback check, '
            'shooting and playback display names', expect_zero=True)

    def branch(site, target):
        return struct.pack('<I', 0x14000000 | (((target - va(site)) >> 2) & 0x3FFFFFF))
    img.put(_at(TYPE_SITE), branch(_at(TYPE_SITE), blk.labels['type']), 'record service: type from the stored choice',
            expect=struct.pack('<I', STOCK[TYPE_SITE]))
    img.put(_at(TYPE_CHECK), struct.pack('<I', 0x7100111F), 'record service: accept types 0..3 (cmp w8,#4)',
            expect=struct.pack('<I', STOCK[TYPE_CHECK]))
    img.put(_at(RATE_SITE), branch(_at(RATE_SITE), blk.labels['rate']), 'bit-rate lookup: table by the stored choice',
            expect=struct.pack('<I', STOCK[RATE_SITE]))
    img.put(_at(LABEL_SITE), struct.pack('<I', 0x94000000 | (((blk.labels['label'] - va(_at(LABEL_SITE))) >> 2) & 0x3FFFFFF)),
            'sample-description writer: FourCC and encoder name by the stored choice',
            expect=struct.pack('<I', STOCK[LABEL_SITE]))
    img.put(_at(PARSER_SITE), branch(_at(PARSER_SITE), blk.labels['parser']),
            'playback: accept apch, apcn, apcs, apco and remember the grade',
            expect=struct.pack('<I', STOCK[PARSER_SITE]))
    img.put(_at(SHOOT_SITE), branch(_at(SHOOT_SITE), blk.labels['shoot']), 'shooting display: CODEC name by the stored choice',
            expect=struct.pack('<I', STOCK[SHOOT_SITE]))
    img.put(_at(PLAY_SITE), branch(_at(PLAY_SITE), blk.labels['play']), 'playback information: name by the remembered grade',
            expect=struct.pack('<I', STOCK[PLAY_SITE]))
    if bank:
        img.put(_at(BANK_SITE), branch(_at(BANK_SITE), blk.labels['bank']),
                'menu bank copy: item 120Bh carries the stored choice (two bytes)', expect=struct.pack('<I', BANK_STOCK))
    rows = []
    for i, name in enumerate(('HQ (stock table)', '422', 'LT', 'Proxy')):
        table = img.old[RATE_TABLE:RATE_TABLE + 0x18 * RATE_ROWS] if i == 0 else tables[i - 1]
        rows.append(dict(grade=name, bit_rates=[struct.unpack_from('<Q', table, 0x18 * r + 0x10)[0] for r in range(RATE_ROWS)]))
    return dict(labels={k: hex(v) for k, v in blk.labels.items()},
                code=[dict(va=hex(x), word=w, text=t) for x, w, t in listing],
                sites={hex(va(s)): hex(w) for s, w in STOCK.items()},
                fourcc=['apc' + chr(c) for c in FOURCC_LAST], names=[n.decode() for n in NAMES],
                display_names=[n.decode() for n in DISPLAY], stash=hex(stash_ram),
                **({'bank': dict(site=hex(va(_at(BANK_SITE))), stock_word=hex(BANK_STOCK), item=hex(BANK_ITEM),
                                 resume=hex(_va(BANK_RESUME)), done=hex(_va(BANK_DONE)), bytes_copied=2)} if bank else {}),
                rate_scale=[f'{n}/{d}' for n, d in RATE_SCALE], rate_tables=rows)
