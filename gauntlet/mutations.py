#!/usr/bin/env python3
"""Mutation battery: systematic corruption of build artefacts; every mutation must be
intercepted by its designated gate. Any leak is a defect of the gate set and fails
the gauntlet (mutation × interception matrix).

Mutation classes:
  窗口内 / 窗口外 bit flips, checksum-chain tampering (EG CRC16 / body CRC16 / outer SHA1),
  identity tampering, directory tampering, truncation, CFG bit flips, kit hygiene,
  input fingerprint drift, combination-rule violations (built artefacts).
"""
import hashlib
import json
import shutil
import struct
import tempfile
import zlib
from pathlib import Path

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from z8prores.base import at as _at          # noqa: E402


def _A(addr):
    """Recipe EG address -> address in the base under test."""
    return EG + _at(addr - EG)


import cfgcheck as cc
import gates as G
import pkgcodec as pc

EG = pc.EG_START


def _flip(body, at):
    body[at] ^= 1


def _set(body, at, raw):
    body[at:at + len(raw)] = raw


# --- package mutations -------------------------------------------------------
# stage: 'pre' = edit body before chain repair; 'post' = edit after repair (the
# checksum field itself is corrupted); 'raw' = edit the outer raw after encoding.
PKG = [
    dict(id='M01', cls='窗口内', title='precapture 代码 blob 内翻 1bit @EG 0x800100（全链修好）',
         expect={'G1.2'}, stage='pre', at=EG + 0x800100, op='flip', repair='all'),
    dict(id='M02', cls='窗口内', title='prores 窗口内翻 1bit @EG 0x398DA0（全链修好）',
         expect={'G1.2'}, stage='pre', at=EG + 0x398da0, op='flip', repair='all'),
    dict(id='M03', cls='窗口内', title='opengate 尺寸 case 窗口内翻 1bit @EG 0x573120（全链修好）',
         expect={'G1.2'}, stage='pre', at=EG + 0x573120, op='flip', repair='all'),
    dict(id='M04', cls='窗口外', title='窗口外翻 1bit @EG 0x2400000（全链修好）',
         expect={'G1.3', 'G1.5'}, stage='pre', at=EG + 0x2400000, op='flip', repair='all'),
    dict(id='M05', cls='其它模块', title='li2070 模块内翻 1bit + 模块 CRC16 修好',
         expect={'G1.4'}, stage='pre', at=83228219 + 1000, op='flip', repair='all'),
    dict(id='M06', cls='其它模块', title='vr2070 模块内翻 1bit + 模块 CRC16 修好',
         expect={'G1.4'}, stage='pre', at=82389555 + 1000, op='flip', repair='all'),
    dict(id='M07', cls='校验链', title='EG CRC16 尾直接篡改（链断）',
         expect={'G2.4'}, stage='post', at=EG + pc.EG_LEN - 2, op='flip', repair='all'),
    dict(id='M08', cls='校验链', title='body CRC16 字段直接篡改（EG CRC 修好）',
         expect={'G2.4'}, stage='post', at=pc.BODY_BYTES - 16, op='flip', repair='all'),
    dict(id='M09', cls='校验链', title='全链修好后外层 SHA1 字段篡改（重算 SHA1 夹带）',
         expect={'G2.5'}, stage='raw', at=0, op='flip', repair='all'),
    dict(id='M10', cls='校验链', title='body 尾部 14B 置非零（trailer 违规）',
         expect={'G2.4'}, stage='post', at=pc.BODY_BYTES - 14, op='set', value=b'\x01', repair='all'),
    dict(id='M11', cls='身份', title='身份整体篡改为 04.01.p0（runtime+trailer+目录名一致、全链修好）',
         expect={'G2.1'}, stage='identity0401', repair='all'),
    dict(id='M12', cls='身份', title='仅尾部身份改 03.11.p1（与 runtime 不一致）',
         expect={'G2.2'}, stage='pre', at=EG + pc.EG_LEN - 11, op='set', value=b'03.11.p1', repair='all'),
    dict(id='M13', cls='身份', title='公开版本指令 0xEB29FC 翻 1bit（三方不一致）',
         expect={'G2.2'}, stage='pre', at=EG + 0xeb29fc, op='flip', repair='all'),
    dict(id='M14', cls='目录', title='段目录 EG 名改 eg2070_0401p0.bi（身份未动）',
         expect={'G2.3'}, stage='dirname', repair='all'),
    dict(id='M15', cls='目录', title='段目录 li2070 size 字段 +1（边界不一致）',
         expect={'G2.3'}, stage='pre', at=48 + 32 * 4 + 20, op='plus4', repair='all'),
    dict(id='M16', cls='截断', title='整包截断 1 字节',
         expect={'G2.5'}, stage='truncate', repair='none'),
    dict(id='M31', cls='组合规则', title='LOADER 8B 打回 prores 形态 0x4094F000（08009ed28812a8f2）+ 全链修好',
         expect={'G1.2', 'G3.2'}, stage='pre', at=EG + 0x1024d8c, op='set',
         value=bytes.fromhex('08009ed28812a8f2'), repair='all'),
    dict(id='M32', cls='组合规则', title='LOADER 8B 打回 stock 形态 0x408BF8F0（081e9fd26811a8f2）+ 全链修好',
         expect={'G1.2', 'G3.2'}, stage='pre', at=EG + 0x1024d8c, op='set',
         value=bytes.fromhex('081e9fd26811a8f2'), repair='all'),
    dict(id='M33', cls='缺窗口', title='opengate 全部 10 窗口回退 stock 字节（manifest 仍宣称含 opengate）',
         expect={'G1.2'}, stage='revert_windows', windows='opengate', repair='all'),
    dict(id='M34', cls='组合规则', title='预拍入口 hook 0xE0FE90 回退 stock（字节面伪装 precapture 缺失、opengate 在）',
         expect={'G3.1'}, stage='revert_windows', windows='precapture_hook', repair='all'),
]

# --- CFG mutations (kit Z8PRE*/Z8OG files) -----------------------------------
CFG_M = [
    dict(id='M17', cls='CFG', title='Z8PRE_RECOMMENDED flags 置未知位 bit15 + CRC 修好',
         file='Z8PRE_RECOMMENDED.CFG', expect={'G4.2'}, kind='pre', field='flags_or', value=0x8000),
    dict(id='M18', cls='CFG', title='Z8PRE_SAFE frames=21（>RING_CAP）+ CRC 修好',
         file='Z8PRE_SAFE.CFG', expect={'G4.3'}, kind='pre', field='frames', value=21),
    dict(id='M19', cls='CFG', title='Z8PRE_SLIM CRC32 篡改（不修）',
         file='Z8PRE_SLIM.CFG', expect={'G4.4'}, kind='crc_broken'),
    dict(id='M20', cls='CFG', title='Z8PRE_RAWONLY magic 降为 Z8PRECFGv3',
         file='Z8PRE_RAWONLY.CFG', expect={'G4.1'}, kind='magic', value=b'Z8PRECFGv3'),
    dict(id='M21', cls='CFG', title='Z8OG 保留位 u32@0x14 置 1 + CRC 修好（A.2 整文件拒收）',
         file='Z8OG.CFG', expect={'G4.2'}, kind='og', field='reserved', value=1),
    dict(id='M22', cls='CFG', title='Z8OG flags=3（bit1 越界）+ CRC 修好',
         file='Z8OG.CFG', expect={'G4.2'}, kind='og', field='flags', value=3),
    dict(id='M23', cls='CFG', title='Z8PRE_RAWONLY 清 F_FULL 保留 F_RAWONLY（config.py 不变量）',
         file='Z8PRE_RAWONLY.CFG', expect={'G4.2'}, kind='pre', field='flags_and', value=~0x4 & 0xFFFFFFFF),
]

# --- kit hygiene mutations ---------------------------------------------------
KIT_M = [
    dict(id='M24', cls='卫生', title='flash_kit 加塞第二个 .bin（Z_8_0401.bin）', expect={'G6.1'}, kind='extra_bin'),
    dict(id='M25', cls='卫生', title='SHA256SUMS_ALL.txt 一行哈希篡改', expect={'G6.2'}, kind='sums'),
    dict(id='M26', cls='卫生', title='manifest output_sha256 漂移', expect={'G6.4'}, kind='manifest_sha'),
    dict(id='M27', cls='卫生', title='manifest output_identity 改 04.01.p0（0401 残留）', expect={'G6.3'}, kind='manifest_id'),
]

# --- input fingerprint -------------------------------------------------------
INPUT_M = [
    dict(id='M28', cls='指纹', title='输入固件翻 1bit（官方原件字节漂移）', expect={'G1.6', 'G2.6'}),
]

# --- combination-rule violations (built artefacts; see combos.py) -----------
BUILD_M = [
    dict(id='M29', cls='组合规则', features=('opengate',), title='opengate 单选构建产物（缺 precapture）',
         expect={'G3.1', 'G3.2'}),
    dict(id='M30', cls='组合规则', features=('prores', 'opengate'), title='prores+opengate 构建产物（缺 precapture）',
         expect={'G3.1', 'G3.2'}),
]

# --- v11.1 c2-fix-plan mutations (one per fix; gate each must intercept) -----
C2_M = [
    dict(id='M35', cls='计数三真源', title='保存侧计数立即数改 618（ROM 表/R2 仍 617 ⇒ 三源不一致）',
         expect={'G3.8'}, stage='pre', at=EG + 0xF803D4, op='set',
         value=struct.pack('<I', 0x52804D46), repair='all'),
    dict(id='M36', cls='无主表写', title='T4 边界 8B 写回 v10 字节（归属未闭环的表边界，123 §5）',
         expect={'G3.7'}, stage='pre', at=EG + 0x4CBC9B8, op='set',
         value=struct.pack('<II', 0x00000800, 0x00000100), repair='all'),
    dict(id='M37', cls='guard 语义', title='guard 桩改回 v10 跨区 bound（add x9,x25,x9 顶替同基址 sub）',
         expect={'G3.5'}, stage='guard_defect', entry='precapture_ncset_guard', repair='all'),
    dict(id='M38', cls='覆盖缺口', title='LC blob walk 站点 0xF7FBF8 漏挂（复原 stock bl 0x410E1AA8）',
         expect={'G3.6'}, stage='pre', at=EG + 0xF7FBF8, op='stock', bytes=4, repair='all'),
    dict(id='M39', cls='覆盖缺口', title='L3 标量 walk 站点 0xF7FE28 漏挂（复原 stock bl 0x410E1790）',
         expect={'G3.6'}, stage='pre', at=EG + 0xF7FE28, op='stock', bytes=4, repair='all'),
]

# --- 补检门 mutations（G3.9/G3.10/G4.6 各配变异，证明“注入必拦”）-------------
SUPP_M = [
    dict(id='M40', cls='多源一致', title='E 容量表行 0x4d2ffc0 +0x200（孪生行 0x4d2ffcc 未动 ⇒ 族分叉）',
         expect={'G3.9'}, stage='alloc_row', at=0x4d2ffc0, delta=0x200, repair='all'),
    dict(id='M41', cls='多源一致', title='E 容量表行 0x4d2ffc0 −0x200（反向漂移；漏报双向测）',
         expect={'G3.9'}, stage='alloc_row', at=0x4d2ffc0, delta=-0x200, repair='all'),
    dict(id='M42', cls='guard 行为', title='guard 桩 fail-open：尾 cmp x9,x10 + b.hi 双 NOP（全放行）',
         expect={'G3.5', 'G3.10'}, stage='guard_words', entry='precapture_ncset_guard',
         word_lo=11, word_hi=12, value=0xD503201F, repair='all'),
    dict(id='M43', cls='guard 行为', title='guard 桩 fail-closed：apply br x16→ret（全跳过）',
         expect={'G3.5', 'G3.10'}, stage='guard_words', entry='precapture_ncset_guard',
         word_lo=15, word_hi=15, value=0xD65F03C0, repair='all'),
    dict(id='M44', cls='包络', title='recipe ring_cap=30 + Z8PRE_SAFE frames=30（862MB 整环失败级）',
         expect={'G4.6'}, kind='envelope', file='Z8PRE_SAFE.CFG', value=30),
]


def build_pkg_mutant(codec, base_body, spec, stock_eg=None):
    """Apply one package mutation; returns (raw, body_or_None)."""
    body = bytearray(base_body)
    stage = spec['stage']
    if stage == 'truncate':
        raw = codec.encode(bytes(body))[:-1]
        return raw, None
    if stage == 'guard_defect':
        # v10's defective bound: replace the stub's same-base normalization with add x9,x25,x9
        at = _A(spec['at'])
        body[at + spec['defect_off']:at + spec['defect_off'] + 4] = struct.pack('<I', 0x8B090329)
    elif stage == 'pre':
        if spec['op'] == 'flip':
            _flip(body, _A(spec['at']))
        elif spec['op'] == 'set':
            _set(body, _A(spec['at']), spec['value'])
        elif spec['op'] == 'stock':
            _set(body, _A(spec['at']), stock_eg[_A(spec['at']) - EG:_A(spec['at']) - EG + spec['bytes']])
        elif spec['op'] == 'plus4':
            at = _A(spec['at'])
            body[at:at + 4] = (int.from_bytes(body[at:at + 4], 'big') + 1).to_bytes(4, 'big')
    elif stage == 'revert_windows':
        for at, n, old in spec['patches']:
            _set(body, EG + at, old)
    elif stage == 'identity0401':
        _set(body, EG + pc.IDENTITY_AT, b'04.01.p0')
        _set(body, EG + pc.EG_LEN - 11, b'04.01.p0')
        _set(body, 112, b'eg2070_0401p0.bi')
    elif stage == 'dirname':
        _set(body, 112, b'eg2070_0401p0.bi')
    if spec.get('repair') == 'all':
        body = bytearray(pc.repair_chain(bytes(body)))
    if stage == 'post':
        if spec['op'] == 'flip':
            _flip(body, _A(spec['at']))
        elif spec['op'] == 'set':
            _set(body, _A(spec['at']), spec['value'])
    raw = codec.encode(bytes(body))
    if stage == 'raw':
        raw = bytearray(raw)
        _flip(raw, _A(spec['at']))
        raw = bytes(raw)
    return raw, bytes(body)


def apply_cfg_mutation(raw, spec):
    out = bytearray(raw)
    if spec['kind'] == 'crc_broken':
        out[60] ^= 0x5A
        return bytes(out)
    if spec['kind'] == 'magic':
        _set(out, 0, spec['value'])
    elif spec['kind'] in ('pre', 'og'):
        if spec['field'] == 'flags_or':
            v = struct.unpack_from('<I', out, 16)[0] | spec['value']
            struct.pack_into('<I', out, 16, v)
        elif spec['field'] == 'flags_and':
            v = struct.unpack_from('<I', out, 16)[0] & spec['value']
            struct.pack_into('<I', out, 16, v)
        elif spec['field'] == 'flags':
            struct.pack_into('<I', out, 16, spec['value'])
        elif spec['field'] == 'frames':
            struct.pack_into('<I', out, 20, spec['value'])
        elif spec['field'] == 'reserved':
            struct.pack_into('<I', out, 0x14, spec['value'])
    struct.pack_into('<I', out, 60, zlib.crc32(bytes(out[:60])) & 0xffffffff)
    return bytes(out)


def catchers_of(runs):
    """Failing check IDs, excluding checks that could not execute (decode-failed)."""
    out = []
    for g in runs.values() if isinstance(runs, dict) else runs:
        for c in g.checks:
            if not c.ok and not c.detail.startswith('候选包无法解码'):
                out.append(c.cid)
    return out


def run_battery(ctx, out_dir, anchors, log=print, skip_build=False):
    """Run every mutation; return matrix rows + summary."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = ctx['cand']
    profiles = ctx['profiles']
    features = ctx['features']
    rows = []

    def record(mid, cls, title, expect, caught, extra='', ok_override=None):
        ok = set(expect) <= set(caught) if ok_override is None else ok_override
        rows.append(dict(id=mid, cls=cls, title=title, expect=sorted(expect),
                         caught=caught or ['(无门拦截)'], intercepted='YES' if ok else 'NO', extra=extra))
        log('  %s %s expect=%s caught=%s %s' % (mid, '拦截✓' if ok else '漏拦✗', sorted(expect),
                                                ','.join(caught) if caught else '-', extra))
        return ok

    # package mutants
    stock_eg = ctx['stock'].eg

    def stock_bytes(at, n):
        return stock_eg[at:at + n]

    for spec in PKG:
        spec = dict(spec)
        if spec['stage'] == 'revert_windows':
            if spec.get('windows') == 'opengate':
                win_rows = [(int(p['offset'], 16), p['bytes']) for p in profiles['opengate']['patches']]
            else:
                win_rows = [(G.ENTRY_HOOK['precapture'], 4)]
            spec['patches'] = [(at, n, stock_bytes(at, n)) for at, n in win_rows]
        raw, body = build_pkg_mutant(base.codec, base.body, spec, stock_eg=stock_eg)
        mutant = G.Artifact(spec['id'], raw=raw, body=body, codec=base.codec)
        runs = G.evaluate_package(ctx['stock'], mutant, profiles, features=features,
                                  baseline=base, anchors=None, pin_baseline=False)
        record(spec['id'], spec['cls'], spec['title'], spec['expect'], catchers_of(runs))

    # v11.1 c2-fix-plan mutants（一修复一变异；各自的 designated 门须命中）
    entries = {k: int(v, 16) for k, v in (profiles.get('precapture', {}).get('entries') or {}).items()}
    for spec in C2_M:
        spec = dict(spec)
        if spec['stage'] == 'guard_defect':
            stub_va = entries[spec.pop('entry')]
            spec['at'] = EG + _at(stub_va - 0x40160000)
            spec['defect_off'] = 4 * len(G.GUARD_PROLOGUE)   # first body word = the normalization
        raw, body = build_pkg_mutant(base.codec, base.body, spec, stock_eg=stock_eg)
        mutant = G.Artifact(spec['id'], raw=raw, body=body, codec=base.codec)
        runs = G.evaluate_package(ctx['stock'], mutant, profiles, features=features,
                                  baseline=base, anchors=None, pin_baseline=False)
        record(spec['id'], spec['cls'], spec['title'], spec['expect'], catchers_of(runs))

    # 补检门 mutants（G3.9/G3.10）：同型修链，designated 门须命中
    for spec in SUPP_M:
        spec = dict(spec)
        if spec.get('kind') == 'envelope':
            continue                                    # CFG 族，下方单独跑（带 recipe ring_cap）
        if spec['stage'] == 'alloc_row':
            at = _A(spec['at'])
            val = (struct.unpack_from('<I', base.eg, at)[0] + spec['delta']) & 0xFFFFFFFF
            spec = dict(spec, stage='pre', at=EG + at, op='set', value=struct.pack('<I', val))
        elif spec['stage'] == 'guard_words':
            stub_va = entries[spec.pop('entry')]
            lo, hi = spec.pop('word_lo'), spec.pop('word_hi')
            at = EG + (stub_va - 0x40160000) + 4 * lo
            spec = dict(spec, stage='pre', at=at, op='set',
                        value=struct.pack('<I', spec.pop('value')) * (hi - lo + 1))
        raw, body = build_pkg_mutant(base.codec, base.body, spec, stock_eg=stock_eg)
        mutant = G.Artifact(spec['id'], raw=raw, body=body, codec=base.codec)
        runs = G.evaluate_package(ctx['stock'], mutant, profiles, features=features,
                                  baseline=base, anchors=None, pin_baseline=False)
        record(spec['id'], spec['cls'], spec['title'], spec['expect'], catchers_of(runs))

    # CFG mutants
    with tempfile.TemporaryDirectory(prefix='preflight-cfg-') as td:
        td = Path(td)
        per_frame = G.alloc_family(base.eg)['rows'][0]
        for spec in CFG_M:
            src = Path(ctx['kit']) / spec['file']
            raw = apply_cfg_mutation(src.read_bytes(), spec)
            p = td / spec['file']
            p.write_bytes(raw)
            ring_cap = int(profiles['precapture']['merged']['ring_cap'], 16)
            g, _ = G.run_cfg_gate([p], ring_cap, per_frame=per_frame)
            record(spec['id'], spec['cls'], spec['title'], spec['expect'], [c.cid for c in g.checks if not c.ok])
        for spec in [s for s in SUPP_M if s.get('kind') == 'envelope']:
            src = Path(ctx['kit']) / spec['file']
            raw = apply_cfg_mutation(src.read_bytes(), dict(kind='pre', field='frames', value=spec['value']))
            p = td / (spec['id'] + '_' + spec['file'])
            p.write_bytes(raw)
            # recipe ring_cap 同步抬 = 一值多源同改；单帧尺寸取自 G3.9 族值
            g, _ = G.run_cfg_gate([p], spec['value'], per_frame=per_frame)
            record(spec['id'], spec['cls'], spec['title'], spec['expect'], [c.cid for c in g.checks if not c.ok])

    # kit hygiene mutants (hardlink the big firmware, copy the rest)
    with tempfile.TemporaryDirectory(prefix='preflight-kit-') as td:
        td = Path(td)
        for spec in KIT_M:
            kit = td / spec['id']
            kit.mkdir()
            for p in Path(ctx['kit']).iterdir():
                dst = kit / p.name
                if p.suffix == '.bin':
                    try:
                        dst.hardlink_to(p)
                    except OSError:
                        shutil.copy2(p, dst)
                else:
                    shutil.copy2(p, dst)
            manifest = json.loads((kit / 'manifest.json').read_text())
            if spec['kind'] == 'extra_bin':
                (kit / 'Z_8_0401.bin').write_bytes(b'\x00' * 16)
            elif spec['kind'] == 'sums':
                p = kit / 'SHA256SUMS_ALL.txt'
                lines = p.read_text().splitlines()
                lines[0] = ('0' * 64) + lines[0][64:]
                p.write_text('\n'.join(lines) + '\n')
            elif spec['kind'] == 'manifest_sha':
                manifest['output_sha256'] = '0' * 64
                (kit / 'manifest.json').write_text(json.dumps(manifest, indent=2))
            elif spec['kind'] == 'manifest_id':
                manifest['output_identity'] = '04.01.p0'
                (kit / 'manifest.json').write_text(json.dumps(manifest, indent=2))
            g = G.run_hygiene_gate(kit, manifest)
            record(spec['id'], spec['cls'], spec['title'], spec['expect'], [c.cid for c in g.checks if not c.ok])

    # input fingerprint mutant
    with tempfile.TemporaryDirectory(prefix='preflight-input-') as td:
        td = Path(td)
        stock = bytearray(ctx['stock'].raw)
        stock[1000] ^= 1
        p = td / 'Z_8_0311.bin'
        p.write_bytes(bytes(stock))
        bad_stock = G.Artifact('M28-input', path=p)
        runs = G.evaluate_package(bad_stock, ctx['cand'], profiles, features=features,
                                  baseline=ctx['baseline'], anchors=None, pin_baseline=False)
        record('M28', '指纹', INPUT_M[0]['title'], INPUT_M[0]['expect'], catchers_of(runs))

    # combination-rule violations
    if not skip_build:
        import combos
        for spec in BUILD_M:
            name = combos.combo_name(spec['features'])
            product = ctx.get('illegal_products', {}).get(name)
            built_here = False
            if product is None or not Path(product).exists():
                build_dir = out_dir / ('mutbuild_' + name.replace('+', '_'))
                run, product = combos.build_via_patch(ctx['stock_path'], list(spec['features']), build_dir)
                built_here = True
                if run.returncode != 0:
                    record(spec['id'], spec['cls'], spec['title'], spec['expect'],
                           ['BUILDER(features.py enforce)'],
                           extra='非法组合在构建层被拒（最早拦截点），无非法产物落地；产品面组合规则由 M34 验证',
                           ok_override=True)
                    continue
            cand = G.Artifact(spec['id'], path=product)
            runs = G.evaluate_package(ctx['stock'], cand, profiles, features=list(spec['features']),
                                      baseline=ctx['baseline'], anchors=None, pin_baseline=False)
            record(spec['id'], spec['cls'], spec['title'], spec['expect'], catchers_of(runs),
                   extra='产物=' + Path(product).name + ('（本次构建）' if built_here else '（组合矩阵复用）'))
    else:
        for spec in BUILD_M:
            rows.append(dict(id=spec['id'], cls=spec['cls'], title=spec['title'],
                             expect=sorted(spec['expect']), caught=['SKIPPED'], intercepted='SKIP'))

    total = sum(1 for r in rows if r['intercepted'] != 'SKIP')
    ok = sum(1 for r in rows if r['intercepted'] == 'YES')
    return dict(rows=rows, summary=dict(total=total, intercepted=ok, leaked=total - ok))
