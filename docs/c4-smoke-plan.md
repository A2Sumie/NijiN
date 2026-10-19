# C4 smoke plan — the one on-device run the V11 line owes

**Plan only.** Criterion C4 of [unfreeze-criteria.md](unfreeze-criteria.md)
needs either one on-device smoke of the fixed build or an explicit written
waiver from the owner. This document is the smoke's executable shape. It is
**not** a waiver: the waiver must come from the owner, in the ledger, by
name. Closes [open-items #6](open-items.md).

Purpose: **verify the fix**, not rescue anything. The discipline style
follows the rescue playbook's rules (single variable, criteria before the
step, stop at the first anomaly) but every step here asks "does the fixed
build behave", never "how do I get data out of a broken camera".

## Preconditions (all of them, before the first flash)

| # | Precondition | Why |
|---|---|---|
| P1 | The camera is back from service and runs official firmware normally | A smoke against a damaged body proves nothing |
| P2 | The official C 3.11 package is on hand and verified: 99,051,117 bytes, SHA-256 `d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96` | It is the only rollback |
| P3 | The candidate build passed C1–C3: verdict filled, fixes landed, full gauntlet green, rebuild reproducible | Smoke is not a debugging session |
| P4 | A dedicated, empty test card; settings backed up; a full battery; uninterrupted time | Single variables need quiet conditions |
| P5 | No `Z8PRE*.CFG`, no `Z8OG.CFG` on the card at step S1 | The no-config boot is the control |
| P6 | The candidate is the V11 revert line — **never V10** | [unfreeze-criteria.md](unfreeze-criteria.md) post-unfreeze rule 1 |

## Main sequence (one variable per step)

Judgement for every step, in one word: **boot**. Then the listed checks.
A step only starts when the previous step's criteria are all met.

| Step | Action (the only variable) | Criteria = all must hold | If not |
|---|---|---|---|
| S0 | Official firmware, empty card | Boots to the shooting display; one photo writes and plays back | Body or card problem — stop, this is not a firmware question |
| S1 | Flash the candidate build, card still empty | Powers on within normal time, **no restart loop**; shooting display reachable; MENU opens and closes; one photo writes and plays back | **ABORT**, go to "first anomaly" |
| S2 | Boot with the camera's settings file on the card (save/load path) | Boots exactly like S1; settings load without error; no lost or reset items | ABORT |
| S3 | One config file, minimal (`Z8PRE` safe tier) | Boots like S2; the feature enables; one capture works | ABORT |
| S4 | Remove the config file again | Back to S2 behaviour exactly | ABORT |
| S5 | Power cycle ×3 | Boots every time, same behaviour | ABORT |
| S6 | Card swap (insert/remove, powered off), including the card with the config | Boots; the feature can be enabled again after the swap — the symptom class from the upstream report | ABORT |

S1 is the step the whole plan exists for: **does the fixed build boot**. If
S1 aborts, nothing below is attempted.

## First anomaly = stop

An anomaly is: a restart loop, a black screen, a menu that freezes, a write
error, a behaviour that differs from the step's criteria, or anything you
cannot explain. On the first one:

1. **Stop.** Do not repeat "to confirm", do not continue "to gather data".
2. Do not power-cycle in a loop. One controlled attempt at most.
3. Roll back: reflash the verified official C 3.11 package, remove all
   config files from the card.
4. Record the step, the observed behaviour and the time in the ledger
   (template below), then walk away from the camera.

If the camera does not boot at all: the rollback path is the service path.
See [risks.md](risks.md) — this has happened before.

## Record template (one line per step, into the ledger)

```text
[smoke] date/time | build identity + output sha256 | step S? | variable |
expected | observed | verdict PASS/FAIL/ABORT | evidence (file names + hashes) |
next action
```

Filled examples of the verdict words: `PASS` (criteria all met),
`FAIL` (criteria missed, anomaly), `ABORT` (stop rule fired). An unfilled
step is not a pass.

## 禁做清单 / Do not

- Do not smoke with V10. Ever.
- Do not skip S0: without the control, "boots" means nothing.
- Do not change two things between steps (no "both config files at once").
- Do not leave the step's criteria to be decided after seeing the result —
  they are written above; changing them mid-run invalidates the run.
- Do not treat "it booted twice" as qualification: this is one smoke, and
  [features.md](features.md) keeps every unverified item unverified.

## Risk gate and waiver

The risky steps are none of them: the run is designed to stop early. The
risk is inherent — this is modified firmware on a real camera.

If the owner decides to skip the hardware smoke entirely, that is the C4
waiver, and it must exist as a ledger entry that says, in the owner's
words, that the risk of skipping the smoke is accepted. **A plan is not a
waiver; silence is not a waiver.** Without either a smoke record or that
entry, C4 stays unmet and the line stays frozen.

## 简体中文

**这是预案，不是豁免。** [unfreeze-criteria.md](unfreeze-criteria.md) 的 C4
要么一次上机冒烟记录、要么**你本人在台账里明示豁免**；本文只把冒烟写成可执行步骤。
销 [open-items #6](open-items.md)。目的=**验证修复**，不是救机。

**前置（全齐才开刷）**：P1 相机送修回来、官方固件正常｜P2 官方 C 3.11 包在手且核过
（99,051,117 字节、sha256 `d67413c2…`）＝唯一回退｜P3 候选已过 C1–C3（判词填、修复落地、
gauntlet 全绿、重建可复现）｜P4 专用空测试卡＋设置已备份＋满电＋不被打断的时间｜
P5 S1 时卡上无任何 `Z8PRE*.CFG`/`Z8OG.CFG`｜P6 候选必须是 **V11 回退线，永远不是 V10**。

**主序列（一步一变量）**：S0 官方固件＋空卡（开机→拍照→写卡→回放）→ **S1 刷候选、
卡仍空**（正常时间开机、**不重启循环**、取景可达、菜单开合、拍照写卡回放）→ S2 放设置
文件开机（载入无错、无项丢失/复位）→ S3 放一个最小配置（safe 档）→ S4 删配置回退行为
→ S5 三次冷启动 → S6 换卡（含带配置的卡，即上游报告的症状类）。**S1 是整份预案存在的
理由：修复后的包到底开不开得了机；S1 中止则下面全不做。**

**首异常即停**：重启循环/黑屏/菜单卡死/写卡报错/与判据不符/说不清的行为，任一发生——
①**停**，不"再试一次确认"、不"多拿点数据"；②不反复断电重启，最多一次受控尝试；
③回退：重刷核过的官方 C 3.11、清空卡上配置文件；④按模板把步骤/现象/时间记进台账，
然后离开相机。开不了机=走送修线（见 [risks.md](risks.md)，这发生过）。

**记录模板**（每步一行入台账）：`[smoke] 日期时间 | 构建身份+输出 sha256 | 步 S? |
变量 | 判据 | 实测 | PASS/FAIL/ABORT | 证据（文件名+哈希） | 下一步`。空行不算过。

**禁做**：不冒烟 V10；不跳 S0（无对照组，"开机"没有意义）；不一步改两件事；
判据不在看到结果后才定（会废掉整轮）；"开过两次机"不算合格——这就是一次冒烟，
[features.md](features.md) 里未验证的项继续按未验证挂着。

**风险闸门与豁免**：本序列的高风险步是"没有高风险步"（设计目标=尽早停）；风险本身
来自"改装固件上真机"。若你决定整段跳过硬件冒烟，那就是 C4 豁免——**必须在台账里留下
你本人明示承担跳过风险的条目**。**预案不是豁免，沉默不是豁免**；冒烟记录与豁免条目
二者皆无，C4 维持未达成、线维持冻结。
