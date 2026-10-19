# Unfreeze criteria for the `bricking-edge` line

The V11 line is frozen. This document writes down the bar it must clear
before anyone even proposes unfreezing it. Meeting every criterion here
does **not** unfreeze anything: **unfreezing is the owner's decision**, and
this page only makes the threshold explicit so the decision is made against
a written standard instead of a mood.

Each criterion names the [open items](open-items.md) it closes.

## The criteria

| # | Criterion | What counts as met | Closes |
|---|---|---|---|
| C1 | **Root cause closed.** The V10 boot loop has an identified faulting instruction or path | A verdict recorded in [risks.md](risks.md) with its evidence grade, reproducible either on hardware or by static-plus-dynamic analysis that leaves no alternative in the delta. "Plausible story" is not a verdict. **Mechanically: the C1 evidence slot in [risks.md](risks.md#c1-evidence-slot) is filled field by field** — verdict, grade, record and code anchors, delta-exhaustion statement, reproduction status, what stays unproven | [open-items #1](open-items.md) |
| C2 ✅ | **Fix designed and verified offline.** *Met 2026-10-19:* build `bricking-edge_v11.1` (`f25c505d…`), four fixes landed, unit tests 9/9, gates G3.5–G3.8, evidence in `100_BUILD_LOG.md §V11.1`.* Every known defect in the boot-reachable changes is corrected | Guard bound computed from the correct region; the settings count changed in all three sources of truth together; the table-boundary write either removed or its ownership proven; the second path to the apply function guarded. Each with before/after evidence, not just a rebuilt binary. The recipe-level plan is [c2-fix-plan.md](c2-fix-plan.md) | [open-items #2–5](open-items.md) |
| C3 ✅ | **Offline all green, and reproducibly so.** *Met 2026-10-19:* gauntlet ALL GREEN (gates 7/7, mutations 39/39 incl. five new ones, combinations 17/17, structural 4/4), rebuild byte-identical, four repository checks green, recipe hashes locked.* The candidate passes the full battery | Full gauntlet run green (gates, mutation battery, combination matrix, structural torture), rebuild reproducible byte for byte, the repository's four checks green, recipe source hashes locked | [open-items #2–5](open-items.md) |
| C4 | **One on-device smoke, or an explicit waiver.** Either the candidate boots and shoots on a test body under single-variable discipline, or the owner waives hardware smoke in writing | A smoke record (what was flashed, what was tried, what was observed) in the ledger — **or** a ledger entry from the owner explicitly accepting the risk of skipping it. Silence is not a waiver. The smoke's executable shape is [c4-smoke-plan.md](c4-smoke-plan.md) | [open-items #6](open-items.md) |
| C5 | **The paper trail matches.** Docs, open items and the tracking log are updated before the change | Closed rows in [open-items.md](open-items.md) with evidence links; the state table in [bricking-edge.md](bricking-edge.md) rewritten; the [upstream tracking log](upstream-issue-3.md) reconciled if upstream found something | [open-items](open-items.md) |
| C6 | **The owner decides.** An explicit instruction to unfreeze, recorded | A ledger entry. No process, checklist or green run unfreezes anything on its own | — |

## What does not count

- The emulator boots. A model reaching the photo menu says nothing about
  flashing, the boot ROM, persistent settings or the real startup chain.
- Another project could not reproduce its own incident. That is their
  evidence, about their build.
- The bytes are the same as some previous build. The previous builds are
  exactly what bricked a camera.
- Time passing, or the absence of new reports.

## If the line is unfrozen

The discipline does not relax:

1. The first candidate is the V11 revert, never V10.
2. One variable at a time, with the official package verified and ready to
   reflash, per the generated pre-flash checklist.
3. Stop at the first anomaly; do not push through it to "get more data".
4. If anything recurs, refreeze first and investigate second.

## 简体中文

V11 线（`bricking-edge`）目前**冻结**。本文把"达到什么门槛才谈解冻"写清楚：
**全部满足也不自动解冻——解冻是你的决定**，本文只让这个决定对着一份白纸黑字的
门槛做，而不是对着感觉做。每条判据挂上 [open-items](open-items.md) 里它要销掉的项。

**六条门槛**：C1 **炸点定谳**——V10 开机循环有明确的出事指令或路径，判词进
[risks.md](risks.md) 并带证据分级，要么真机复现、要么静态+动态分析把 delta 里的
其它可能全部排除（"说得通的故事"不算定谳），销 #1；C2 **修复方案落地并离线验证**——
guard bound 用正确区域算、计数三真源同改、表边界写删掉或证明归属、第二路径补防护点，
每件要有前后证据而不是"重新编译了一遍"，销 #2–5；C3 **离线全绿且可复现**——全套
gauntlet 绿、重建逐字节一致、仓内四查绿、配方源码哈希锁住，销 #2–5；C4 **一次上机
冒烟或你明示豁免**——单变量纪律下真机开机拍照存台账，**或者**你在台账里明示承担
跳过冒烟的风险（沉默不算豁免），销 #6；C5 **纸面对账**——open-items 逐项销账挂证据、
[bricking-edge.md](bricking-edge.md) 状态表改写、上游 [tracking log](upstream-issue-3.md)
有变先对齐；C6 **你下令解冻**并记台账——任何流程、清单、全绿都不构成解冻本身。

**不算数的**：模拟器能开机（不测刷写/boot ROM/保留设置/真实上电链）；别的项目没能
复现它自己的事故（那是他们的构建、他们的证据）；字节和以前某版一样（以前那几版
正是刷砖的那几版）；时间过去了、没人再报障。

**若解冻**，纪律不松：第一个候选是 V11 回退包而不是 V10；单变量、官方包核好待刷、
按生成的上机前检查单走；首个异常即停，不为"多拿数据"硬闯；复发就先重新冻结再查。
