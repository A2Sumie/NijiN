#!/usr/bin/env python3
"""Gauntlet report card + human pre-flash checklist rendering (G7)."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

import gates as G


def _now():
    return datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z')


def render_report(results, ctx, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'gauntlet_report.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')

    def status_of(x):
        return x.get('status', '-')

    lines = ['# GAUNTLET 报告卡 — %s' % _now(), '']
    tot = results.get('stats', {})
    lines += ['## 0. 总判', '',
              '| 阶段 | 状态 | 统计 |', '|---|---|---|']
    for stage in results.get('stages', []):
        lines.append('| %s | **%s** | %s |' % (stage['name'], stage['status'], stage.get('stats', '')))
    lines += ['', '**总体：%s**（%s）' % (results.get('status'), tot), '']

    lines += ['## 1. 七道门逐项', '']
    for g in results.get('gates', []):
        lines += ['### %s %s — %s' % (g['id'], g['title'], g['status']), '',
                  '| # | 检查 | 状态 | 详情 |', '|---|---|---|---|']
        for c in g['checks']:
            detail = c['detail'].replace('|', '\\|')
            lines.append('| %s | %s | %s | %s |' % (c['id'], c['title'], c['status'], detail[:220]))
        lines.append('')

    mut = results.get('mutations')
    if mut:
        lines += ['## 2. 变异×拦截矩阵（mutation battery）', '',
                  '统计：**%d/%d 拦截，漏拦 %d**' % (mut['summary']['intercepted'], mut['summary']['total'],
                                                    mut['summary']['leaked']), '',
                  '| ID | 类 | 变异 | 预期门 | 实际拦截门 | 拦截 |', '|---|---|---|---|---|---|']
        for r in mut['rows']:
            lines.append('| %s | %s | %s | %s | %s | **%s** |' % (
                r['id'], r['cls'], r['title'], ','.join(r['expect']), ','.join(r['caught']), r['intercepted']))
        lines.append('')

    combo = results.get('combos')
    if combo:
        lines += ['## 3. 组合穷举矩阵（feature × CFG 档位）', '',
                  '| 组合 | 状态 | sha256/说明 | verify | 锚点 |', '|---|---|---|---|---|']
        for r in combo['rows']:
            lines.append('| %s | **%s** | %s | %s | %s |' % (
                r.get('combo', '-'), r.get('status'), str(r.get('sha256', r.get('detail', '')))[:70],
                r.get('verify', '-'), str(r.get('anchor', ''))[:60]))
        lines += ['', 'CFG 档位单元格（每组合 × 5 档 + 无 CFG）：', '']
        for r in combo['rows']:
            if 'cells' in r:
                for c in r['cells']:
                    lines.append('- `%s` × `%s`: **%s**（%s）' % (r['combo'], c['tier'], c['status'], c['detail'][:140]))
        lines += ['', '旧世代族谱/回退锚（he-star / he-star-plus）：', '']
        for r in combo.get('legacy', []):
            lines.append('- `%s`: **%s** — %s' % (r['family'], r['status'], r['detail'][:180]))
        lines.append('')

    if results.get('structural'):
        lines += ['## 4. 结构酷刑', '',
                  '| # | 项目 | 状态 | 详情 |', '|---|---|---|---|']
        for r in results['structural']:
            lines.append('| %s | %s | %s | %s |' % (r['id'], r['title'], r['status'], r['detail'][:220]))
        lines.append('')

    if results.get('findings'):
        lines += ['## 5. 发现/缺口（须处置）', '']
        for f in results['findings']:
            lines.append('- %s' % f)
        lines.append('')

    lines += ['## 6. 上机纪律', '',
              '- 单变量、有判据、有回退；拿不准的宁可不上机。',
              '- 刷机由用户执行；本报告只做离线字节判据（scope: not a camera test）。',
              '- 回退锚：官方原件 `d67413c2…`（85 runbook）、v5 基线 `79fa7b32…`、`d91e30de…`（prores+precapture）。']
    path = out_dir / 'GAUNTLET_REPORT.md'
    path.write_text('\n'.join(lines) + '\n')
    return path


def render_checklist(results, ctx, out_dir):
    """G7: human-readable pre-flash checklist with single-variable test cards."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    kit = Path(ctx['kit'])
    all_green = str(results.get('status', '')).startswith('GREEN')
    lines = ['# 上机前检查单（preflight G7）— %s' % _now(), '']
    lines.append('**门禁总判：%s** — %s' % (
        results.get('status'), '允许进入上机流程' if all_green else '⛔ 未全绿：不得上机，先处置红项'))
    lines += ['', '## A. 产物与校验和', '', '| 文件 | 字节 | sha256 |', '|---|---|---|']
    for p in sorted(kit.iterdir()):
        if p.is_file():
            lines.append('| %s | %d | `%s` |' % (p.name, p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest()))
    cand = ctx.get('cand')
    if cand:
        lines += ['', '- 构建身份：**%s**（严禁 04.01）；feature 面：%s' % (
            pc_identity(cand), ', '.join(ctx.get('features') or ['-']))]
        lines.append('- A/B 基线：`%s`（v5 `79fa7b32…`）；输入原件：`%s`（`d67413c2…`）' % (
            ctx.get('baseline_path', '-'), ctx.get('stock_path', '-')))
    lines += ['', '## B. 建议先测什么（单变量 / 有判据 / 有回退）', '',
              '| 步 | 单变量（只动这一个） | 判据（过/不过） | 回退 |', '|---|---|---|---|',
              '| 1 | **不插任何 CFG** 开机 + 拍照/录像一轮 | 开机正常、拍照录像正常、回放正常（= stock 行为面） | 不用回退（基线行为） |',
              '| 2 | 只放 `Z8PRE_SAFE.CFG`（frames=15） | 预拍可出 NEF、可回放、无卡写异常；任何异常=删 CFG 重测 | **删卡上 Z8PRE*.CFG** 即回 stock |',
              '| 3 | 换 `Z8PRE_RECOMMENDED.CFG`（frames=20） | 与步 2 同判据 + 连拍张数≥15；锁死/写卡慢=回 SAFE 档 | 删/换回 SAFE.CFG |',
              '| 4 | SLIM/RAWONLY 档逐个（每次只换一个文件） | 对应 flag 语义生效且无副作用 | 删该 CFG |',
              '| 5 | 只放 `Z8OG.CFG`（OG 试验档） | 录像尺寸=3:2 元数据、码率行正常；异常=删 Z8OG.CFG | **删 Z8OG.CFG = OG 关** |',
              '| 6 | Z8PRE×Z8OG 同卡组合 | 两 feature 互不干扰（正交性上机确认） | 逐个删 CFG 定位 |',
              '| 7 | 固件级异常（不开机/锁死） | — | **立即重刷官方 03.11**（sha `d67413c2…`）；不要带病继续 |']
    lines += ['', '## C. 回退命令（离线准备，刷机由用户执行）', '',
              '```bash',
              '# 校验官方原件（重刷回退用）',
              'shasum -a 256 <你的路径>/Z_8_0311.bin   # 期望 d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96',
              '# 校验本包',
              'cd %s && shasum -a 256 -c SHA256SUMS_ALL.txt' % kit,
              '# 一键关闭所有改造行为（不刷机）',
              'rm <CARD_ROOT>/Z8PRE*.CFG <CARD_ROOT>/Z8OG.CFG',
              '```',
              '', '回退锚文件（离线副本）：',
              '- 官方原件：`%s`（`d67413c2…`）' % ctx.get('stock_path', '-'),
              '- 本地基线构建（NIJIN_BASELINE 指定；v5 `79fa7b32…`）：`%s`' % ctx.get('baseline_path', '-'),
              '- prores+precapture 参照：`d91e30de9945a92a8cbb51d9c4a85a727264b5ef42365edefa10a759a5fabe8f`（110 §E.5）',
              '', '## D. 本检查单随包交付', '',
              '- 完整报告卡：`GAUNTLET_REPORT.md`（每项 PASS/FAIL + 变异矩阵 + 组合矩阵）',
              '- 机器可读：`gauntlet_report.json`',
              '- 上机批次按上表步 1→7 推进，每步留一轮实测记录再进下一步。']
    path = out_dir / 'PREFLIGHT_CHECKLIST.md'
    path.write_text('\n'.join(lines) + '\n')
    return path


def pc_identity(cand):
    try:
        return cand.eg[0x14eaa90:0x14eaa98].decode('ascii')
    except Exception:
        return '(decode-failed)'
