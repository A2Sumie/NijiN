"""z8menuh: 轮0基建 — DS 表重定位（P2-A）+ 自定义设定 h 组外壳。

设计（120_BANK_P2_POC §2 + 119 §2）：
  1. meta 表（0x114B 条 ×0x18B）与组表（0x7C 条 ×0x30B）整体搬入 text-gap 空区（loader 覆盖内），
     尾部留扩展空隙 ⇒ 新 DS 项/新组"零成本注册"（追加记录 + 组计数，不动代码）。
  2. bank 项表 listA（465 项）同搬，尾部留空隙；3 处指针链 + 3 处计数立即数跟随。
  3. 首个注册实例：ProRes 档位选择字节（RAM 0xA03D5C029）→ 扩展组 0x08 项 0x0800
     （默认值 = 组默认镜像字节，零扩展）；v6 双 hook 并存保留（老文件 high=0 自动回默认）。
  4. h 组外壳：A/B/C/D 组表各扩第 8 项（h 标题=原厂串 id 0x72A 'Custom'，字母=0xD99），
     5 处组边界立即数放宽，根页组行表 9→10 行（h 行模板=g 行），页记录计数跟随。
     本版 h 组"可见、可进、暂无条目"（条目行 = 轮 1，走 119 §4 流程卡）。

配方锁（G3.4）：resources/menuh.json 冻结输入区 sha 与每窗 old/new sha；
  构建期本模块重生成全部字节并 require 与配方一致。
"""
import json
import struct
from pathlib import Path

from z8prores.package import RESOURCES, require, sha

from z8prores.base import at as _at, profile_path, adopt as _adopt

HERE = Path(__file__).resolve().parent
BASE = 0x40160000
PAYLOAD = 81807709                    # eg 模块去尾 CRC16 后长度

# ---- stock 源区（eg 文件偏移）----
META_SRC, META_REC, META_N = 0x3EAA5C0, 0x18, 0x114B
GRP_SRC, GRP_REC, GRP_N = 0x3EC44C8, 0x30, 0x7C
LISTA_SRC, LISTA_N = 0x4CA9888, 465
LISTA_COUNTS = (0xF7D27C, 0xF7D300, 0xF7DB0C)   # recipe offsets, translated at use
ROWS_SRC, ROW_SZ = 0x3939258, 44
EVPTR_SRC = 0x39393E4
PAGE_REC = 0x4BC3390
ARRAYS = (
    ('A', 0x29AD490, (0xAA, 0x216, 0xB4, 0xB9, 0xBE, 0xC3, 0xC8)),
    ('B', 0x29AD4B0, (0x8C9, 0x1EF, 0x1FD, 0x21C, 0x23B, 0x26E, 0x2D5)),
    ('C', 0x29AD4D0, (0x315E, 0x3171, 0x3184, 0x31A9, 0x31BA, 0x31DB, 0x31E5)),
    ('D', 0x29AD4F0, (0x315F, 0x34D3, 0x31EC, 0x32E3, 0x31BB, 0x3205, 0x3206)),
)
BOUNDS = (
    (0x3B86D8, 6, 7, 'cmp w20,#6 -> #7'),
    (0x3B8860, 6, 7, 'cmp w21,#6 -> #7'),
    (0x3B880C, 7, 8, 'cmp w8,#7 -> #8'),
)
# 0x3CEEEC 的 `mov w0,#8` 是 ORR 位掩码编码（0x321D03E0），9 非合法位掩码 ⇒ 整指令换 MOVZ 形态
RAW_BOUNDS = ((0x3CEEEC, 0x321D03E0, 0x52800120, 'mov w0,#8 -> #9 (查表未命中哨兵, ORR→MOVZ)'),)
LOADER_SITE = 0x1024D8C
LOADER_END_VA = 0x4098F000

META_AT = 0x810000
GRP_AT = 0x82C000
LISTA_AT = 0x82E000
MENU_AT = 0x82E800

EXT_GROUP = 0x08
GRADE_RAM = 0x03D5C029
NEW_ITEM = 0x0800
NEW_META_IDX = META_N
TITLE_STR = 0x72A                     # 原厂 'Custom'
LETTER_ID = 0xD99
H_ROW_ITEM_CANDIDATES = (0x35BD, 0x35BE, 0x35C0, 0x35C1, 0x31E7, 0x31E8)


def _w(img, off):
    return struct.unpack_from('<I', img, off)[0]


def _chain_sites(img, target):
    """全值解码：定位 materialize `target` 的 movz/movk 常量链（8 指令窗），返回链首址。"""
    sites = []
    for off in range(0, 0x14E4000, 4):
        w = _w(img, off)
        if (w & 0xFF800000) != 0xD2800000:      # movz xN
            continue
        reg = w & 0x1F
        val = ((w >> 5) & 0xFFFF) << (((w >> 21) & 3) * 16)
        for k in range(1, 9):
            w2 = _w(img, off + 4 * k)
            if (w2 & 0xFF80001F) == (0xF2800000 | reg):   # movk xN, same reg
                val |= ((w2 >> 5) & 0xFFFF) << (((w2 >> 21) & 3) * 16)
        if val == target:
            sites.append(off)
    return sites


def _chain_edit(img, off, new_val, purpose):
    """把链（movz + 同 reg 的 movk×≤3）重编码为 materialize `new_val`，返回编辑行。"""
    w0 = _w(img, off)
    reg = w0 & 0x1F
    sites = [off]
    for k in range(1, 9):
        w2 = _w(img, off + 4 * k)
        if (w2 & 0xFF80001F) == (0xF2800000 | reg):
            sites.append(off + 4 * k)
    rows = []
    for a in sites:
        w = _w(img, a)
        sh = ((w >> 21) & 3) * 16
        new = (w & ~(0xFFFF << 5)) | (((new_val >> sh) & 0xFFFF) << 5)
        if new != w:                                  # 只发变化字（高位 movk 恒 0 不动）
            rows.append((a, struct.pack('<I', w), struct.pack('<I', new), f'{purpose} +{a - off:#x}'))
    return rows


def edits(eg):
    _adopt(eg)
    require(len(eg) == PAYLOAD, f'Unsupported EG length {len(eg)}')
    out = []

    def add_bytes(at, new, purpose, expect_zero=False):
        old = eg[at:at + len(new)]
        require(len(old) == len(new), 'window out of range: ' + purpose)
        if expect_zero:
            require(old == b'\x00' * len(new), 'target not zero: ' + purpose)
        out.append((at, old, new, purpose))

    # ---- 1. meta 表重定位 + 扩展组 0x08 项 0x0800 ----
    grp08_defimg_at = MENU_AT + 0x600
    meta = bytearray(eg[META_SRC:META_SRC + META_N * META_REC])
    meta += struct.pack('<6I', 0, 1, GRADE_RAM, 0xa, BASE + grp08_defimg_at, 0)
    meta += b'\x00' * (0x20E0 - META_REC)
    add_bytes(META_AT, bytes(meta), 'meta table relocated + item 0x0800', expect_zero=True)
    sites = _chain_sites(eg, BASE + META_SRC)
    require(len(sites) == 16, f'meta chains: expected 16, got {len(sites)}')
    for s in sites:
        out += _chain_edit(eg, s, BASE + META_AT, 'meta base chain')

    # ---- 2. 组表重定位 + 扩展组 0x08 ----
    grp = bytearray(eg[GRP_SRC:GRP_SRC + GRP_N * GRP_REC])
    grp[EXT_GROUP * GRP_REC:EXT_GROUP * GRP_REC + GRP_REC] = struct.pack(
        '<12I', 2, 0, GRADE_RAM, 0xa, BASE + grp08_defimg_at, 0,
        (NEW_META_IDX & 0xFFFF) | (1 << 16), 0, 0, 0xa, 1, 0)
    grp += b'\x00' * 0x8C0
    add_bytes(GRP_AT, bytes(grp), 'group table relocated + extension group 0x08', expect_zero=True)
    sites = _chain_sites(eg, BASE + GRP_SRC)
    require(len(sites) == 28, f'group chains: expected 28, got {len(sites)}')
    for s in sites:
        out += _chain_edit(eg, s, BASE + GRP_AT, 'group base chain')

    # ---- 3. bank 项表 listA 重定位 + 追加 ----
    lst = bytearray(eg[LISTA_SRC:LISTA_SRC + LISTA_N * 4])
    require(struct.unpack_from('<I', lst, 343 * 4)[0] & 0xFFFF == 0x120B, 'listA anchor 0x120B@343')
    lst += struct.pack('<I', 0x00700000 | NEW_ITEM) + b'\x00' * 0xB8
    add_bytes(LISTA_AT, bytes(lst), 'bank list relocated + 0x0800', expect_zero=True)
    sites = _chain_sites(eg, 0xA0299E888)
    require(len(sites) == 7, f'listA chains: expected 7, got {len(sites)}')  # MenuBank 3 + 其它消费 4，全部重指向
    for s in sites:
        out += _chain_edit(eg, s, BASE + LISTA_AT, 'bank list base chain')
    for s0 in LISTA_COUNTS:
        s = _at(s0)
        w = _w(eg, s)
        require((w >> 5) & 0xFFFF == 0x1D1, f'stock count at {s:#x}')
        out.append((s, struct.pack('<I', w), struct.pack('<I', (w & ~(0xFFFF << 5)) | (0x1D2 << 5)),
                    f'bank list count 465->466 @{s:#x}'))

    # ---- 4. 组表 A/B/C/D 扩第 8 项 + h 行 + evptr + 页记录 ----
    menu = bytearray(0x800)
    used = eg[0x29AC000:0x3C20000]
    h_item = next((c for c in H_ROW_ITEM_CANDIDATES if struct.pack('<I', c) not in used), None)
    require(h_item is not None, 'no free h-row item id')
    a7 = (0xAA, TITLE_STR, h_item, 0)
    for i, (nm, src, stock) in enumerate(ARRAYS):
        vals = list(struct.unpack_from('<7I', eg, src))
        require(tuple(vals) == stock, f'array {nm} stock mismatch')
        menu[i * 0x20:(i + 1) * 0x20] = struct.pack('<8I', *vals, a7[i])
        out += _chain_edit(eg, _chain_sites(eg, BASE + src)[0], BASE + MENU_AT + i * 0x20,
                           f'array {nm} base chain')
    row = struct.pack('<11I', TITLE_STR, 0xFFFF, 0xFFFF, 0, 0x101840, LETTER_ID, h_item,
                      0x130013, 0xFFFFFFFF, 0xFFFFFFFF, 2)
    rows = eg[ROWS_SRC:ROWS_SRC + 9 * ROW_SZ] + row
    evp = eg[EVPTR_SRC:EVPTR_SRC + 72] + struct.pack('<Q', struct.unpack_from('<Q', eg, EVPTR_SRC + 64)[0])
    menu[0x80:0x80 + len(rows)] = rows
    menu[0x340:0x340 + len(evp)] = evp
    menu[0x600:0x602] = b'\x00\x00'
    add_bytes(MENU_AT, bytes(menu), 'group arrays + h row + evptr + defaults', expect_zero=True)
    add_bytes(PAGE_REC + 0x10, struct.pack('<QQ', BASE + MENU_AT + 0x80, BASE + MENU_AT + 0x340),
              'page record rows/evptr pointers')
    require(struct.unpack_from('<H', eg, PAGE_REC + 0x20)[0] == 9, 'page row count')
    add_bytes(PAGE_REC + 0x20, struct.pack('<H', 10), 'page row count 9->10')

    # ---- 5. 组边界立即数 ----
    for at, oldw, neww, desc in RAW_BOUNDS:
        require(_w(eg, at) == oldw, f'stock mismatch {desc} @{at:#x}')
        out.append((at, struct.pack('<I', oldw), struct.pack('<I', neww), desc))
    for at, oldv, newv, desc in BOUNDS:
        w = _w(eg, at)
        if ((w >> 5) & 0xFFFF) == oldv:                    # MOV wide: imm16 @ bit5
            new = (w & ~(0xFFFF << 5)) | (newv << 5)
        elif ((w >> 10) & 0xFFF) == oldv:                  # CMP/SUBS imm: imm12 @ bit10
            new = (w & ~(0xFFF << 10)) | (newv << 10)
        else:
            require(False, f'stock mismatch {desc} @{at:#x}: {w:#x}')
        out.append((at, struct.pack('<I', w), struct.pack('<I', new), desc))

    # ---- 6. LOADER 覆盖（多特性共享 8B 窗，单调上调）----
    loader_site = _at(LOADER_SITE)
    words = _chain_edit(eg, loader_site, LOADER_END_VA, 'loader end')
    require([w[0] for w in words] == [loader_site, loader_site + 4], 'loader chain shape')
    out.append((loader_site, words[0][1] + words[1][1], words[0][2] + words[1][2],
                f'loader end -> {LOADER_END_VA:#x}'))
    out.sort(key=lambda e: e[0])
    for i in range(1, len(out)):
        require(out[i - 1][0] + len(out[i - 1][2]) <= out[i][0], 'menuh windows overlap')
    return [{'offset': o, 'old': a, 'new': b, 'purpose': p} for o, a, b, p in out]


def compatibility(eg):
    p = profile_path('menuh.json')
    if not p.exists():
        return {'menuh': 'recipe not locked yet'}
    profile = json.loads(p.read_text())
    for r in profile['ranges']:
        a, b = int(r['start'], 16), int(r['end'], 16)
        require(sha(eg[a:b]) == r['sha256'], 'Incompatible region: ' + r['purpose'])
    for e in profile['patches']:
        a, n = int(e['offset'], 16), e['bytes']
        require(sha(eg[a:a + n]) == e['old_sha256'], 'menuh patch input conflicts at ' + e['offset'])
    return profile


def lock(eg):
    rows = edits(eg)
    ranges = [{'start': hex(s), 'end': hex(e), 'sha256': sha(eg[s:e]), 'purpose': p} for s, e, p in (
        (META_SRC, META_SRC + META_N * META_REC, 'meta table source'),
        (GRP_SRC, GRP_SRC + GRP_N * GRP_REC, 'group table source'),
        (LISTA_SRC, LISTA_SRC + LISTA_N * 4, 'bank list source'),
        (ROWS_SRC, ROWS_SRC + 9 * ROW_SZ, 'root rows source'),
        (EVPTR_SRC, EVPTR_SRC + 72, 'root evptr source'))]
    lo_words = [struct.pack('<I', (_w(eg, LOADER_SITE) & ~(0xFFFF << 5)) | (((v >> 0) & 0xFFFF) << 5)) +
                struct.pack('<I', (_w(eg, LOADER_SITE + 4) & ~(0xFFFF << 5)) | (((v >> 16) & 0xFFFF) << 5))
                for v in (0x408BF8F0, 0x4094F000, 0x40970000, 0x4098F000)]
    patches = []
    for e in rows:
        row = {'offset': hex(e['offset']), 'bytes': len(e['new']), 'old_sha256': sha(e['old']),
                   'new_sha256': sha(e['new']), 'purpose': e['purpose']}
        if e['offset'] == LOADER_SITE:
            row['loader_input_sha256'] = sorted({sha(w) for w in lo_words})
        patches.append(row)
    profile = {'id': 'z8-c311-menuh-v1', 'payload_bytes': PAYLOAD,
                   'note': 'P2-A DS-table relocation + h group shell; see 120_BANK_P2_POC / 119 §2',
                   'ranges': ranges, 'patches': patches}
    (RESOURCES / 'menuh.json').write_text(json.dumps(profile, indent=1, ensure_ascii=False))
    return profile


if __name__ == '__main__':
    import sys
    eg = Path(sys.argv[1]).read_bytes()
    if len(eg) == PAYLOAD + 2:
        eg = eg[:-2]
    p = lock(eg)
    print('menuh recipe locked:', len(p['patches']), 'patches,',
          sum(x['bytes'] for x in p['patches']), 'bytes')
