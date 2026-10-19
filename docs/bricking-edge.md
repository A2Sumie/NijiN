# The `bricking-edge` line (V11)

This branch is the hotfix and forensics line. It exists because of the V10
incident: a build from the stable line was installed on a test camera and the
camera entered a boot loop and went to service. See
[risks.md](risks.md) for the full record.

The name is dark humour kept on purpose. The usual word is "bleeding edge";
this line is named after what the previous line actually did.

## What this branch contains, on top of `main`

| Item | What it is |
|---|---|
| `recipes/revert_v10_tails.py` | The line's recipe: take a local V10 build and a local previous build, revert the four suspect payload windows to their previous values, rebuild the checksum chain, and prove the result differs from V10 only in those windows |
| `docs/bricking-edge.md` | This page |

Everything else is identical to `main`.

## What the recipe reverts

| Payload offset | Bytes | Change removed | Why it is suspect |
|---|---|---|---|
| `0xF803D4` | 4 | settings-count immediate 617 → 618 | The count now disagrees with its backing table (617 entries); any walk that trusts it overruns by one entry. Mechanism proven offline |
| `0xF80F68` | 4 | same count change in the boot-registration path | Sits inside a function that runs during application initialisation — exactly where the boot loop happens |
| `0x4CBC9B8` | 8 | settings-table tail write | The address is the boundary between two adjacent tables. Which table owns it could not be closed statically: zero code references anywhere in the package |
| `0xF7F9D4` | 4 | load-time bounds guard hook | The guard cannot crash, but its bound is computed across two different regions, so it may silently skip or allow every entry |

Everything else in the output stays byte-identical to the V10 input,
including the recompiled code blob. The script refuses to run unless the A/B
differences are exactly the declared windows plus the checksum chain.

## State of this line

| Aspect | State |
|---|---|
| Built | Yes, once, as a local trial |
| Byte-level comparison | Passed: exactly the four windows plus the trailing checksum differ from V10 |
| Released into a build kit | **No, deliberately not** |
| Tested on hardware | **No** |
| Recommended to flash | **No** |
| Frozen | Yes — until the boot-loop cause is settled |

The trial output hash recorded at the time was `0da2b2b0…`. That is a record
of one local build, not a release: no package from this line has ever been
published, and none will be until the conditions below are met.

## What must be settled before this line moves

1. The load-time guard's bound must be computed from the right region, not
   across two different ones.
2. The settings count has **three** sources of truth (ROM variant table,
   hard-coded registration, save-side immediate). All three must be updated
   together, or none of them.
3. The ownership of the table-boundary write must be closed: which table
   owns `0x4CBC9B8`, and is there a consumer at all?
4. The second code path that reaches the same apply function must get its
   own guard point.
5. Above all: the instruction that actually faults on hardware is **not
   known**. Until it is, this line is a hypothesis, not a fix.

A revert of four windows may well boot. It may also be that one of the
remaining differences is the real cause. Nobody knows yet, and this line
does not pretend otherwise.

## If you build from this branch anyway

You are on your own: bring both input builds, run the recipe, read its
verification output, run the full gauntlet, and accept that the last build
with a green gauntlet is the one that bricked a camera. Keep the official
package verified and ready. See [build.md](build.md) and
[verification.md](verification.md).

## 简体中文

- 这条分支是**热修／取证线**，因 V10 上机开机循环事故而生；`bricking-edge` 是
  故意保留的黑色幽默（正常说法是 bleeding edge，这里按它实际干过的事命名）。
- 分支只比 `main` 多两样：`recipes/revert_v10_tails.py`（把四个嫌疑窗口回退到
  上一构建的字节，其余逐字节不动，并强制 A/B 差分只能落在声明窗口内）和本文。
- 四个嫌疑窗口及理由（计数 617→618 与背衬表不一致且位于开机注册路径、表边界
  8B 写归属未闭环、guard 跨区比较可能全跳过/全放行）逐条列在上表。
- **状态**：只本地构建过一次试验包（`0da2b2b0…`），字节比对通过；**从未进过
  flash_kit、从未上机、不建议刷、事故定谳前冻结**。
- 解冻前置：guard bound 修好、计数三真源同改、表边界写归属闭环、第二循环补点，
  以及最根本的——**真机炸点至今未定谳**。四窗回退可能开机，也可能不是根因；
  这条线不装懂。
