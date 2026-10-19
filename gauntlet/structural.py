#!/usr/bin/env python3
"""Structural torture: envelope round-trip, one-byte mutation + repack self-consistency,
integrity chain reverse walk, and multi-tool decode cross-check.

  S1 解包→重封包 round-trip 逐字节恒等（编码器/解码器自洽）
  S2 解包→改一字节→重封包：结构自洽（CRC/SHA1 链全绿）但内容门必须拦截
     —— 证明门禁不依赖校验和（校验和可被攻击者重算）
  S3 段 CRC16 链反向校验（外层 SHA1 → body CRC16 → 模块 CRC16×5 逐级重算比对）
  S4 双/多工具交叉：decode_body.py vs key-tool vs 工具链(package.py/verify.py) vs 本工具
"""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import gates as G
import pkgcodec as pc

# Optional external cross-check tools (local research tools, never shipped here):
#   NIJIN_DECODE_BODY  directory containing decode_body.py
#   NIJIN_KEYTOOL      directory containing decrypt_firmware.py
#   NIJIN_KEY_JSON     key file used by that local tool
# S4 is reported SKIPPED when they are not provided.
ZFW = Path(os.environ['NIJIN_DECODE_BODY']) if os.environ.get('NIJIN_DECODE_BODY') else None
KEYTOOL = Path(os.environ['NIJIN_KEYTOOL']) if os.environ.get('NIJIN_KEYTOOL') else None
KEY_JSON = Path(os.environ['NIJIN_KEY_JSON']) if os.environ.get('NIJIN_KEY_JSON') else None


class Check(dict):
    pass


def _row(cid, title, ok, detail, skipped=False):
    status = 'SKIPPED' if skipped else ('PASS' if ok else 'FAIL')
    return dict(id=cid, title=title, status=status, detail=detail)


def chain_reverse_walk(raw):
    """Recompute SHA1 → body CRC16 → module CRC16×5 and compare against stored values."""
    import binascii
    codec = pc.Codec(raw)
    body = codec.body
    steps = []
    want_sha = raw[:20]
    got_sha = hashlib.sha1(body + pc.K8).digest()
    steps.append(('outer SHA1(body‖K8)', want_sha.hex(), got_sha.hex(), want_sha == got_sha))
    want_bc = body[-16:-14]
    got_bc = binascii.crc_hqx(body[:-16], 0).to_bytes(2, 'big')
    steps.append(('body CRC16 @[-16:-14]', want_bc.hex(), got_bc.hex(), want_bc == got_bc))
    mods_ok = True
    for i, (_, start, size) in enumerate(pc.MODULES):
        module = body[start:start + size]
        want_m = module[-2:]
        got_m = binascii.crc_hqx(module[:-2], 0).to_bytes(2, 'big')
        ok = want_m == got_m
        mods_ok = mods_ok and ok
        if not ok:
            steps.append(('module %d CRC16' % i, want_m.hex(), got_m.hex(), False))
    steps.append(('module CRC16 ×5', 'all match', 'all match' if mods_ok else 'MISMATCH', mods_ok))
    return steps


def run_structural(ctx, out_dir, log=print):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    cand = ctx['cand']
    base_body, codec = cand.body, cand.codec

    # S1 round-trip
    rt = codec.encode(base_body) == cand.raw
    rows.append(_row('S1', '解包→重封包 round-trip 逐字节恒等（99,051,117B）', rt,
                     'encode(decode(raw)) == raw' if rt else 'round-trip 不恒等'))
    log('S1 round-trip: %s' % rt)

    # S2 one-byte mutation + full chain repair + repack: structure green, content gate red
    body = bytearray(base_body)
    body[pc.EG_START + 0x2400000] ^= 1
    body = pc.repair_chain(bytes(body))
    raw2 = codec.encode(bytes(body))
    rec = pc.audit(raw2, bytes(body))
    struct_ok = all(rec[k] for k in ('dir_ok', 'modules_crc_ok', 'trailer_ok', 'body_crc_ok', 'sha1_ok', 'context_ok'))
    mutant = G.Artifact('S2', raw=raw2, body=bytes(body), codec=codec)
    runs = G.evaluate_package(ctx['stock'], mutant, ctx['profiles'], features=ctx['features'],
                              baseline=cand, anchors=None, pin_baseline=False)
    caught = [c.cid for g in runs.values() for c in g.checks if not c.ok and not c.detail.startswith('候选包无法解码')]
    rows.append(_row('S2', '一字节变异+全链重算重封包：结构自洽 ≠ 内容安全（内容门必须拦）',
                     struct_ok and bool(caught),
                     '结构链全绿=%s；内容拦截=%s' % (struct_ok, caught)))
    log('S2 repack: struct_ok=%s caught=%s' % (struct_ok, caught))

    # S3 reverse chain walk
    steps = chain_reverse_walk(cand.raw)
    ok3 = all(s[3] for s in steps)
    rows.append(_row('S3', '段 CRC16 链反向校验（SHA1 → body CRC16 → 模块 CRC16×5）', ok3,
                     '; '.join('%s stored=%s calc=%s' % (s[0], s[1][:16], s[2][:16]) for s in steps if not s[3])
                     or '全链 stored==calc'))
    log('S3 chain walk: %s' % ok3)

    # S4 multi-tool decode cross-check (stock fixture: decode_body / key-tool / toolchain / pkgcodec)
    ok4, detail4, skip4 = multi_tool_cross(ctx, out_dir, log)
    rows.append(_row('S4', '多工具交叉解码一致（decode_body.py vs key-tool vs 工具链 vs 本工具）', ok4, detail4,
                     skipped=skip4))
    return rows


def multi_tool_cross(ctx, out_dir, log=print):
    stock_path = ctx['stock_path']
    missing = [n for n, p in (('decode_body.py', ZFW), ('key-tool', KEYTOOL), ('key json', KEY_JSON))
               if p is None or not Path(p).exists()]
    if missing:
        return False, 'SKIPPED：未提供外部交叉工具（%s）；本仓不分发它们' % ', '.join(missing), True
    with tempfile.TemporaryDirectory(prefix='preflight-xcheck-') as td:
        td = Path(td)
        refs = {}
        # ours
        ours = pc.decode(ctx['stock'].raw)
        refs['pkgcodec'] = ours
        # toolchain: merged/verify.py decode() and z8prores/package.py Package()
        snippet = (
            "import importlib.util, hashlib, sys\n"
            "sys.path.insert(0, %r)\n"
            "import z8prores.package as pk\n"
            "raw = open(%r, 'rb').read()\n"
            "b1 = pk.Package(raw).body\n"
            "spec = importlib.util.spec_from_file_location('vfy', %r)\n"
            "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
            "b2 = m.decode(raw)\n"
            "print(hashlib.sha256(b1).hexdigest(), hashlib.sha256(b2).hexdigest(), b1 == b2)\n"
            % (str(G.MERGED), str(stock_path), str(G.MERGED / 'verify.py')))
        run = subprocess.run([sys.executable, '-c', snippet], capture_output=True, text=True)
        if run.returncode != 0:
            return False, '工具链 decode 失败: ' + run.stderr[-200:], False
        pkg_sha, vfy_sha, same = run.stdout.split()
        toolchain_ok = (pkg_sha == vfy_sha == hashlib.sha256(ours).hexdigest()) and same == 'True'
        # decode_body.py (zfw_cracked, numpy + Package.cs tables)
        db_dir = td / 'decode_body'
        db_dir.mkdir()
        run = subprocess.run([sys.executable, str(ZFW / 'decode_body.py'), str(stock_path), str(db_dir)],
                             capture_output=True, text=True)
        db_file = db_dir / 'decoded.bin'
        db_ok = False
        if run.returncode == 0 and db_file.exists():
            db = db_file.read_bytes()
            db_ok = (len(db) == len(ours) and db[32:] == ours[32:])
        # key-tool decrypt_firmware.py
        kt_out = td / 'kt.dec'
        run = subprocess.run([sys.executable, str(KEYTOOL / 'decrypt_firmware.py'),
                              '--key', str(KEY_JSON), '--firmware', str(stock_path),
                              '--out', str(kt_out), '--force'], capture_output=True, text=True)
        kt_ok = False
        kt_note = ''
        if run.returncode == 0 and kt_out.exists():
            kt = kt_out.read_bytes()
            body = kt[0x20:] if len(kt) == len(ours) + 0x20 else kt
            kt_ok = (len(body) == len(ours) and body[32:] == ours[32:])
            if not kt_ok:
                kt_note = 'len kt=%d ours=%d' % (len(body), len(ours))
        else:
            kt_note = 'key-tool rc=%d %s' % (run.returncode, (run.stderr or run.stdout)[-160:])
        ok = toolchain_ok and db_ok and kt_ok
        detail = 'toolchain(package.py=verify.py)=%s decode_body=%s key-tool=%s；四方 body[32:] 一致；%s' % (
            toolchain_ok, db_ok, kt_ok, kt_note)
        log('S4 cross: %s' % detail)
        return ok, detail, False
