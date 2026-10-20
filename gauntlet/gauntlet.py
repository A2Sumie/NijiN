#!/usr/bin/env python3
"""GAUNTLET — 强检测酷刑测试电池（任何构建进 flash_kit 前的强制门；全绿才放行）。

用法：
  python3 gauntlet.py run            # 全套：七道门 + 变异电池 + 组合穷举 + 结构酷刑 + 报告卡/检查单
  python3 gauntlet.py gates          # 只跑七道门（= preflight.py 子集）
  python3 gauntlet.py mutate         # 只跑变异×拦截矩阵
  python3 gauntlet.py combos         # 只跑组合穷举矩阵（会构建，耗时数分钟）
  python3 gauntlet.py structural     # 只跑结构酷刑 + 多工具交叉
  python3 gauntlet.py checklist      # 只生成上机前检查单

通用参数：--kit DIR --stock FILE --baseline FILE|--no-baseline --out DIR
          --skip-tests --skip-mutations --skip-combos --skip-structural
退出码：0 = 全绿；非 0 = 有红项（打印红因）。
"""
import argparse
import json
import sys
import time
from pathlib import Path

import combos
import gates as G
import mutations
import pkgcodec as pc
import report as R
import structural


def _off(v):
    return int(v, 16) if isinstance(v, str) else int(v)


def build_ctx(args):
    if not args.kit or not args.stock:
        raise ValueError('缺少本地输入：--kit 与 --stock 必填（或设 NIJIN_KIT / NIJIN_STOCK）；本仓不分发任何固件')
    kit = Path(args.kit)
    stock_path = Path(args.stock)
    baseline_path = None if (args.no_baseline or not args.baseline) else Path(args.baseline)
    bins = sorted(kit.glob('*.bin'))
    identity = getattr(args, 'identity', None) or '03.11.p0'
    G.rebase(identity[:5])          # anchor the gate addresses to the base under test first
    ctx = dict(kit=kit, stock_path=stock_path, baseline_path=baseline_path,
               profiles=G.load_profiles(), out=Path(args.out),
               identity=identity, tag=identity[6:], version=identity[:5])
    ctx['stock'] = G.Artifact('stock', path=stock_path)
    if baseline_path and baseline_path.exists():
        ctx['baseline'] = G.Artifact('baseline', path=baseline_path)
        # 基线构建记录窗口（A/B 白名单 = 产物∪基线构建记录∪reviewed∪共享窗重定位族）
        bman = baseline_path.parent / 'manifest.json'
        if bman.exists():
            try:
                bm = json.loads(bman.read_text())
                ctx['baseline_windows'] = [(_off(e['offset']), _off(e['offset']) + e['bytes'])
                                           for e in bm.get('edits', [])]
            except (ValueError, KeyError):
                ctx['baseline_windows'] = None
        else:
            ctx['baseline_windows'] = None
    else:
        ctx['baseline'] = None
        ctx['baseline_windows'] = None
    manifest_path = kit / 'manifest.json'
    ctx['manifest'] = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    if bins:
        ctx['cand'] = G.Artifact('cand', path=bins[0])
        ctx['kit_bin'] = bins[0]
        try:
            ctx['features'] = G.detect_features(ctx['stock'].eg, ctx['cand'].eg)
        except pc.PackageError:
            ctx['features'] = []
    else:
        ctx['cand'] = ctx['kit_bin'] = None
        ctx['features'] = []
    try:
        ctx['anchors'] = json.loads(G.ANCHORS.read_text())
    except (OSError, ValueError):
        ctx['anchors'] = {}
    # G3.4 产物↔recipe 一致性锁：manifest 构建时 source_hashes 对现行 merged/ 复核
    if ctx['manifest'] and ctx['manifest'].get('source_hashes'):
        ctx['anchors']['manifest_source_hashes'] = ctx['manifest']['source_hashes']
    # A/B 白名单四源：产物构建记录窗 + 共享窗重定位族（EG 坐标；基线记录/reviewed 在门内并）
    extra = []
    if ctx['manifest']:
        extra += [(_off(e['offset']), _off(e['offset']) + e['bytes']) for e in ctx['manifest'].get('edits', [])]
    for a, b in ctx['anchors'].get('shared_window_family', []):
        extra.append((int(a, 16), int(b, 16)))
    ctx['extra_windows'] = extra
    return ctx


def stage_gates(ctx, args, results, log=print):
    runs = []
    if ctx['cand'] is None:
        g = G.GateRun('G1', '字节级门')
        g.add('G1.0', 'flash_kit 内存在固件文件', False, '未找到 *.bin')
        runs.append(g.as_dict())
        results['gates'] = runs
        return False
    # G1 in-memory + G2 + G3
    ev = G.evaluate_package(ctx['stock'], ctx['cand'], ctx['profiles'], features=ctx['features'],
                            baseline=ctx['baseline'], anchors=ctx['anchors'],
                            baseline_windows=ctx.get('baseline_windows'),
                            extra_windows=ctx.get('extra_windows'))
    v = G.run_verify_py(ctx['stock_path'], ctx['kit_bin'], ctx['features'])
    runs.append(v.as_dict())
    runs.extend(ev[g].as_dict() for g in ('G1', 'G2', 'G3'))
    # G4 CFG
    ring_cap = int(ctx['profiles']['precapture']['merged']['ring_cap'], 16)
    # 单帧尺寸取自 G3.9 的容量族值；无候选包则无从取，G4.6 记 SKIPPED
    try:
        per_frame = G.alloc_family(ctx['cand'].eg)['rows'][0] if ctx.get('cand') else None
    except Exception:                                  # noqa: BLE001 - undecodable candidate: G4.6 skips
        per_frame = None
    cfg_files = sorted(ctx['kit'].glob('*.CFG'))
    g4, _ = G.run_cfg_gate(cfg_files, ring_cap, per_frame=per_frame)
    runs.append(g4.as_dict())
    # G5 tests
    if args.skip_tests:
        g5 = G.GateRun('G5', '测试门')
        g5.add('G5.0', '测试栈', False, 'SKIPPED（--skip-tests）——出包前必须补跑')
        runs.append(g5.as_dict())
    else:
        log('G5: 运行上游测试栈（validate + validate_features，数分钟）…')
        runs.append(G.run_tests_gate(ctx['stock_path'], ctx['out'] / 'tests', ctx['kit_bin']).as_dict())
    # G6 hygiene
    g6 = G.run_hygiene_gate(ctx['kit'], ctx['manifest'], features=ctx['features'],
                            cand_eg=ctx['cand'].eg if ctx['cand'] else None)
    runs.append(g6.as_dict())
    results['gates'] = runs
    return all(g['status'] in ('PASS', 'SKIPPED') for g in runs)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('stage', nargs='?', default='run',
                    choices=['run', 'gates', 'mutate', 'combos', 'structural', 'checklist'])
    ap.add_argument('--kit', default=G.KIT_DEFAULT,
                    help='local build directory with the package + manifest.json (or NIJIN_KIT)')
    ap.add_argument('--stock', default=G.STOCK_DEFAULT,
                    help='user-supplied official input package (or NIJIN_STOCK)')
    ap.add_argument('--baseline', default=G.BASELINE_DEFAULT,
                    help='locally kept baseline build for A/B diffing (or NIJIN_BASELINE)')
    ap.add_argument('--no-baseline', action='store_true')
    ap.add_argument('--out', default=str(G.HERE / 'out'))
    ap.add_argument('--skip-tests', action='store_true')
    ap.add_argument('--skip-mutations', action='store_true')
    ap.add_argument('--skip-combos', action='store_true')
    ap.add_argument('--skip-structural', action='store_true')
    ap.add_argument('--skip-build-mut', action='store_true')
    args = ap.parse_args()
    t0 = time.time()
    ctx = build_ctx(args)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    results = dict(meta=dict(stage=args.stage, kit=str(ctx['kit']), stock=str(ctx['stock_path']),
                            baseline=str(ctx['baseline_path']), features=ctx['features'],
                            candidate_sha256=ctx['cand'].sha256 if ctx['cand'] else None,
                            started=time.strftime('%Y-%m-%dT%H:%M:%S%z')))
    reds = []
    skips = []

    def log(msg):
        print('[gauntlet] ' + msg, flush=True)

    do_gates = args.stage in ('run', 'gates', 'checklist')
    do_mut = args.stage in ('run', 'mutate') and not args.skip_mutations
    do_combo = args.stage in ('run', 'combos') and not args.skip_combos
    do_struct = args.stage in ('run', 'structural') and not args.skip_structural

    if do_gates:
        log('阶段 1/4：七道门 …')
        ok = stage_gates(ctx, args, results, log)
        for g in results['gates']:
            for c in g['checks']:
                if c['status'] == 'FAIL':
                    reds.append('%s %s：%s — %s' % (c['id'], c['status'], c['title'], c['detail'][:160]))
                elif c['status'] == 'SKIPPED':
                    skips.append('%s SKIPPED：%s — %s' % (c['id'], c['title'], c['detail'][:160]))

    if do_combo:
        log('阶段 2/4：组合穷举（构建×verify×CFG 档位，数分钟）…')
        results['combos'] = combos.run_combo_matrix(ctx, out / 'combos', ctx['anchors'], log)
        for r in results['combos']['rows']:
            if r.get('status') == 'FAIL':
                reds.append('组合 %s：%s' % (r.get('combo'), r.get('detail', '')))
            elif r.get('status') == 'SKIPPED':
                skips.append('组合 %s：%s' % (r.get('combo'), r.get('detail', '')))
        ctx['illegal_products'] = {}
        for p in (out / 'combos').glob('illegal_*/*.bin'):
            ctx['illegal_products'][p.parent.name.replace('illegal_', '').replace('_', '+')] = str(p)
        persist = dict(ctx['anchors'])
        persist.pop('manifest_source_hashes', None)   # 运行时注入，不落锚文件
        G.ANCHORS.write_text(json.dumps(persist, indent=2) + '\n')  # 落锚/复核

    if do_mut:
        log('阶段 3/4：变异电池（mutation × 拦截矩阵）…')
        results['mutations'] = mutations.run_battery(ctx, out / 'mutants', ctx['anchors'], log,
                                                     skip_build=args.skip_build_mut)
        for r in results['mutations']['rows']:
            if r['intercepted'] == 'NO':
                reds.append('漏拦 %s：%s（预期 %s 实拦 %s）' % (r['id'], r['title'], r['expect'], r['caught']))
            elif r['intercepted'] == 'SKIP':
                reds.append('跳过 %s：%s' % (r['id'], r['title']))

    if do_struct:
        log('阶段 4/4：结构酷刑 + 多工具交叉 …')
        results['structural'] = structural.run_structural(ctx, out / 'structural', log)
        for r in results['structural']:
            if r['status'] == 'FAIL':
                reds.append('结构 %s：%s — %s' % (r['id'], r['title'], r['detail'][:160]))
            elif r['status'] == 'SKIPPED':
                skips.append('结构 %s：%s — %s' % (r['id'], r['title'], r['detail'][:160]))

    # G7 checklist + report card
    stages = []
    if results.get('gates'):
        ng = sum(1 for g in results['gates'] if g['status'] in ('PASS', 'SKIPPED'))
        ns = sum(1 for g in results['gates'] for c in g['checks'] if c['status'] == 'SKIPPED')
        stages.append(dict(name='七道门 G1–G7', status='PASS' if ng == len(results['gates']) else 'FAIL',
                           stats='%d/%d 门全绿%s' % (ng, len(results['gates']),
                                                    '（%d 项 SKIPPED）' % ns if ns else '')))
    if results.get('mutations'):
        s = results['mutations']['summary']
        stages.append(dict(name='变异电池（%d 项）' % s['total'], status='PASS' if s['leaked'] == 0 else 'FAIL',
                           stats='%d/%d 拦截' % (s['intercepted'], s['total'])))
    if results.get('combos'):
        rows = results['combos']['rows']
        nok = sum(1 for r in rows if r.get('status') in ('PASS', 'SKIPPED'))
        nsk = sum(1 for r in rows if r.get('status') == 'SKIPPED')
        stages.append(dict(name='组合穷举（5 合法+3 非法+repro+legacy）', status='PASS' if nok == len(rows) else 'FAIL',
                           stats='%d/%d 行绿%s' % (nok, len(rows), '（%d SKIPPED）' % nsk if nsk else '')))
    if results.get('structural'):
        nok = sum(1 for r in results['structural'] if r['status'] in ('PASS', 'SKIPPED'))
        nsk = sum(1 for r in results['structural'] if r['status'] == 'SKIPPED')
        stages.append(dict(name='结构酷刑（S1–S4）', status='PASS' if nok == len(results['structural']) else 'FAIL',
                           stats='%d/%d 项绿%s' % (nok, len(results['structural']), '（%d SKIPPED）' % nsk if nsk else '')))
    results['stages'] = stages
    results['findings'] = results.get('combos', {}).get('findings', [])
    # 运行期间 kit 被并行会话改动 = 结果作废
    if ctx.get('kit_bin') and ctx.get('cand'):
        import hashlib as _h
        now = _h.sha256(ctx['kit_bin'].read_bytes()).hexdigest()
        if now != ctx['cand'].sha256:
            reds.append('flash_kit 在 gauntlet 运行期间被改动（%s→%s），本次结果作废须重跑'
                        % (ctx['cand'].sha256[:12], now[:12]))
    results['reds'] = reds
    results['skips'] = skips
    results['status'] = ('ALL GREEN' if not reds and not skips else
                         'GREEN（%d 项 SKIPPED 未核）' % len(skips) if not reds else 'RED（%d 项）' % len(reds))
    results['stats'] = dict(elapsed_sec=int(time.time() - t0), reds=len(reds), skips=len(skips))

    checklist = R.render_checklist(results, ctx, out)
    # G7 is generated; its own gate status follows the whole battery
    g7 = G.GateRun('G7', '上机前检查单生成器')
    g7.add('G7.1', 'PREFLIGHT_CHECKLIST.md 生成（构建 sha/校验和/先测什么/回退命令）',
           checklist.exists(), str(checklist))
    results.setdefault('gates', []).append(g7.as_dict())
    card = R.render_report(results, ctx, out)
    log('报告卡：%s' % card)
    log('检查单：%s' % checklist)
    log('总判：%s（%d s）' % (results['status'], results['stats']['elapsed_sec']))
    if skips:
        log('SKIPPED（缺本地输入未核，不计入绿）：')
        for s in skips:
            print('  - ' + s)
    if reds:
        log('红因清单：')
        for r in reds:
            print('  ✗ ' + r)
        return 2
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(3)
