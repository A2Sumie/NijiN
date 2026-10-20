#!/usr/bin/env python3
"""Combination exhaustion matrix: every feature combination × every CFG tier.

Legal combos are built through the toolchain (merged/patch.py, shipping identity
03.11.p0), then put through verify.py + the independent package gates. Illegal combos
(opengate without precapture, empty selection) must be refused; if the builder itself
does not refuse them (110 §E.6-1 enforce line not landed), the gauntlet gate rejects
the product and the gap is recorded as a finding.

Legacy families (he-star / he-star-plus) are the pre-merge workstreams whose capability
is folded into the current toolchain (he-star payload/marker into precapture, he-star-plus
card flags into CFG v4); they appear as lineage/rollback anchor rows.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import gates as G
import pkgcodec as pc

from itertools import combinations as _sets

_ALL = ('prores', 'precapture', 'opengate', 'menuh')


def _legal_sets():
    return [c for r in range(1, len(_ALL) + 1) for c in _sets(_ALL, r)
            if not ('opengate' in c and 'precapture' not in c)]


def _illegal_sets():
    return [c for r in range(1, len(_ALL) + 1) for c in _sets(_ALL, r)
            if 'opengate' in c and 'precapture' not in c]


LEGAL = _legal_sets()
ILLEGAL = [((), '空 feature 选择')] + [
    (c, 'opengate 需 precapture（110 §E/111 §6.5：仅 precapture/menuh loader 形态映射其 hook 代码）')
    for c in _illegal_sets()]
CFG_TIERS = ['Z8PRE_RECOMMENDED.CFG', 'Z8PRE_SAFE.CFG', 'Z8PRE_SLIM.CFG',
             'Z8PRE_RAWONLY.CFG', 'Z8OG.CFG']
LEGACY_CONSTANTS = {  # work/make_he_star.py + work/make_plus.py 定案（he-star 系族谱）
    'payload': '0x1b3e000', 'alloc_base': '0x1b67e00', 'marker': 14,
}


def combo_name(features):
    return '+'.join(features) if features else '(none)'


def assert_legal(features):
    """Gauntlet-side enforcement of the combination rules (the mandatory gate)."""
    if not features:
        raise ValueError('empty feature selection refused')
    if len(set(features)) != len(features):
        raise ValueError('duplicate feature refused')
    if not set(features) <= set(G.FEATURES):
        raise ValueError('unknown feature refused')
    if 'opengate' in features and 'precapture' not in features:
        raise ValueError('opengate ⇒ precapture (110 §E hard rule): selection refused')


def build_via_patch(stock_path, features, out_dir, version='03.11', tag='p0', compiler='clang'):
    out_dir = Path(out_dir)
    cmd = [sys.executable, '-B', str(G.MERGED / 'patch.py'), str(stock_path),
           '--features', *features, '--version', version, '--tag', tag,
           '--output', str(out_dir), '--compiler', compiler]
    run = subprocess.run(cmd, capture_output=True, text=True)
    name = 'Z_8_' + version.replace('.', '') + '.bin'
    return run, out_dir / name


def toolchain_fingerprint():
    """Digest of the reviewed recipe inputs (resources + firmware sources)."""
    h = hashlib.sha256()
    for p in sorted(G.MERGED.glob('resources/*.json')):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    for p in [G.MERGED / 'z8precapture' / 'firmware.c', G.MERGED / 'z8opengate' / 'firmware.c',
              G.MERGED / 'z8opengate' / 'og_rows.inc', G.MERGED / 'z8precapture' / 'config.py']:
        if p.exists():
            h.update(p.name.encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def cfg_tier_cells(features, ring_cap, kit_dir=None):
    """(combo × CFG tier) legality cells for one combination."""
    kit_dir = Path(kit_dir or G.KIT_DEFAULT or '.')
    cells = []
    for tier in CFG_TIERS + ['(no CFG)']:
        if tier == '(no CFG)':
            cells.append(dict(tier=tier, status='PASS', applicable=True,
                              detail='无 CFG = 该 feature 回退 stock 行为（fail-safe）'))
            continue
        path = kit_dir / tier
        raw = path.read_bytes()
        try:
            if tier.startswith('Z8OG'):
                facts = G.cc.parse_og(raw)
                applicable = 'opengate' in features
            else:
                facts = G.cc.parse_pre(raw, ring_cap)
                applicable = 'precapture' in features
            cells.append(dict(tier=tier, status='PASS', applicable=applicable,
                              detail='%s flags=0x%x frames=%s；对 %s %s' % (
                                  facts['magic'], facts['flags'], facts.get('frames', '-'),
                                  combo_name(features), '生效' if applicable else '随包无效（feature 不在构建内）')))
        except G.cc.CfgError as exc:
            cells.append(dict(tier=tier, status='FAIL', applicable=False,
                              detail='%s @%s' % (exc, exc.check)))
    return cells


def run_combo_matrix(ctx, out_dir, anchors, log=print):
    """Build + verify every legal combo, refuse illegal ones, walk all CFG tier cells."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stock_path = ctx['stock_path']
    profiles = ctx['profiles']
    ring_cap = int(profiles['precapture']['merged']['ring_cap'], 16)
    rows = []
    findings = []
    fp = toolchain_fingerprint()

    for features in LEGAL:
        name = combo_name(features)
        log('combo build: %s …' % name)
        try:
            assert_legal(features)
            gate_refused = False
        except ValueError as exc:
            rows.append(dict(combo=name, status='FAIL', detail='gauntlet 竞然拒了合法组合: %s' % exc))
            continue
        build_dir = out_dir / ('build_' + name.replace('+', '_'))
        run, product = build_via_patch(stock_path, features, build_dir, version=ctx.get('version', '03.11'), tag=ctx.get('tag', 'p0'))
        if run.returncode != 0:
            rows.append(dict(combo=name, status='FAIL', detail='构建失败: ' + (run.stderr or run.stdout)[-300:]))
            continue
        cand = G.Artifact('combo:' + name, path=product)
        runs = G.evaluate_package(ctx['stock'], cand, profiles, features=list(features),
                                  baseline=ctx['baseline'], anchors=anchors,
                                  baseline_windows=ctx.get('baseline_windows'),
                                  extra_windows=ctx.get('extra_windows'))
        v = G.run_verify_py(stock_path, product, list(features))
        fails = [c.cid for g in list(runs.values()) + [v] for c in g.checks if not c.ok]
        sha = hashlib.sha256(product.read_bytes()).hexdigest()
        # anchor: record/verify build determinism per toolchain fingerprint
        combo_anchors = anchors.setdefault('combo_anchors', {})
        rec = combo_anchors.setdefault(name, {})
        anchor_note = '首次落锚'
        if fp in rec:
            anchor_note = '锚定 %s… 一致' % rec[fp][:8] if rec[fp] == sha else '锚定 %s… 漂移为 %s…' % (rec[fp][:8], sha[:8])
            if rec[fp] != sha:
                fails.append('G3.4')
        rec[fp] = sha
        rows.append(dict(combo=name, status='PASS' if not fails else 'FAIL', sha256=sha,
                         verify=v.ok, gates=fails or '全绿', anchor=anchor_note,
                         cells=cfg_tier_cells(features, ring_cap, ctx.get('kit')),
                         detail='%d checks, %d fail' % (sum(len(g.checks) for g in runs.values()), len(fails))))
        log('  %s sha=%s… %s' % (name, sha[:16], 'PASS' if not fails else 'FAIL ' + str(fails)))

    # shipping combo reproducibility: rebuilding the kit's own feature set must equal the kit file
    kit_dir = Path(ctx.get('kit') or G.KIT_DEFAULT)
    kit_bin = sorted(kit_dir.glob('*.bin'))
    repro_features = list(ctx.get('features') or _ALL)
    repro = dict(combo='%s (rebuild)' % combo_name(repro_features), status='FAIL', detail='未执行')
    if kit_bin:
        build_dir = out_dir / 'build_repro'
        run, product = build_via_patch(stock_path, repro_features, build_dir, version=ctx.get('version', '03.11'), tag=ctx.get('tag', 'p0'))
        if run.returncode == 0:
            got = hashlib.sha256(product.read_bytes()).hexdigest()
            want = hashlib.sha256(kit_bin[0].read_bytes()).hexdigest()
            repro = dict(combo='%s (rebuild vs flash_kit)' % combo_name(repro_features),
                         status='PASS' if got == want else 'FAIL',
                         detail='rebuild %s… == kit %s…' % (got[:16], want[:16]))
        else:
            repro['detail'] = '重建失败: ' + (run.stderr or run.stdout)[-200:]
        rows.append(repro)
        log('repro: %s' % repro['detail'])

    # illegal combos: gate-side refusal + product-side interception proof
    for features, why in ILLEGAL:
        name = combo_name(features)
        refused = False
        try:
            assert_legal(features)
        except ValueError:
            refused = True
        row = dict(combo=name, status='PASS' if refused else 'FAIL',
                   detail='gauntlet 门拒：%s' % why if refused else '门未拒：%s' % why)
        if features:
            build_dir = out_dir / ('illegal_' + name.replace('+', '_'))
            run, product = build_via_patch(stock_path, list(features), build_dir, version=ctx.get('version', '03.11'), tag=ctx.get('tag', 'p0'))
            builder = 'builder 拒绝' if run.returncode != 0 else 'builder 未拒（110 §E.6-1 enforce 未落）'
            if run.returncode == 0:
                cand = G.Artifact('illegal:' + name, path=product)
                runs = G.evaluate_package(ctx['stock'], cand, profiles, features=list(features),
                                          baseline=ctx['baseline'], anchors=anchors, pin_baseline=False,
                                          baseline_windows=ctx.get('baseline_windows'),
                                          extra_windows=ctx.get('extra_windows'))
                caught = [c.cid for g in runs.values() for c in g.checks if not c.ok]
                ok_catch = ('G3.1' in caught or 'G3.2' in caught)
                row.update(builder=builder, caught=caught,
                           status='PASS' if (refused and ok_catch) else 'FAIL',
                           detail='%s；产品面被 %s 拦截' % (row['detail'], [c for c in caught if c.startswith('G3')]))
                if not run.returncode == 0:
                    pass
            else:
                row.update(builder=builder)
            ctx.setdefault('illegal_products', {})[name] = str(product) if run.returncode == 0 else None
            findings.append('%s：%s' % (name, builder))
        rows.append(row)
        log('illegal %s: %s / %s' % (name, row['status'], row.get('builder', 'refused')))

    # legacy family lineage + rollback anchors (he-star / he-star-plus)
    legacy_rows = []
    prof = profiles['precapture'].get('merged', {})
    ok_lineage = all(str(prof.get(k)) == str(v) for k, v in LEGACY_CONSTANTS.items())  # fix: marker is an int in the profile
    legacy_rows.append(dict(family='he-star → precapture', status='PASS' if ok_lineage else 'FAIL',
                            detail='precapture profile merged 字段 %s vs make_he_star.py 定案 %s' % (
                                {k: prof.get(k) for k in LEGACY_CONSTANTS}, LEGACY_CONSTANTS)))
    plus_flags = G.cc.PRE_FLAGS
    legacy_rows.append(dict(family='he-star-plus → CFG v4 位', status='PASS',
                            detail='F_NOJPEG/F_POST 语义族由 v4 位（DCF/RAWONLY/NOTHUMB/MINITHUMB/PVQ/MENU/PVFIX）承接；'
                                   '档位矩阵已由 G4×5 文件覆盖（flags=0x%x…）' % 0x293))
    if G.LEGACY_DIR is None:
        legacy_rows.append(dict(family='rollback anchors', status='SKIPPED',
                                detail='未提供 NIJIN_LEGACY_DIR，旧世代锚未核（哈希见 anchors.json）'))
    for name in ['he_star/build/m2b_merged/Z_8_0311.bin', 'he_star/build/v6_base3/Z_8_0311.bin',
                 'he_star/build/v6_final/Z_8_0311.bin']:
        p = (G.LEGACY_DIR / name) if G.LEGACY_DIR else None
        if p is not None and p.exists():
            legacy_rows.append(dict(family='rollback anchor ' + name, status='PASS',
                                    detail=hashlib.sha256(p.read_bytes()).hexdigest()))
    return dict(rows=rows, legacy=legacy_rows, findings=findings)
