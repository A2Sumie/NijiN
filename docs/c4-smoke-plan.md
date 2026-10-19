# C4 On-Device Smoke Test Plan (V11)

This document defines the on-device smoke test procedure for the V11 build line, closing [open-items #6](open-items.md). 

To satisfy Criterion C4 of [unfreeze-criteria.md](unfreeze-criteria.md), either this test plan must be executed and logged, or the project owner must record an explicit waiver in the ledger. Passing this smoke test verifies basic boot and stability for the fix; it does not validate unrelated items in [features.md](features.md).

## Preconditions

All preconditions must be met before flashing:

* **P1 (Hardware):** The camera is in normal working order and runs official firmware without issues.
* **P2 (Rollback Package):** The official C 3.11 firmware package is available and verified (`99,051,117` bytes, SHA-256: `d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96`).
* **P3 (Candidate Build):** The target build is from the **V11 revert line** (never V10) and has passed C1–C3 (verdict recorded, fixes merged, test suite passed, build is reproducible).
* **P4 (Environment):** A dedicated, formatted test card, backed-up camera settings, and a fully charged battery.
* **P5 (Clean State):** No `Z8PRE*.CFG` or `Z8OG.CFG` files are present on the card at the start of testing.

## Test Sequence

Execute steps in order, changing only one variable per step. Do not proceed to the next step unless all pass criteria for the current step are met.

| Step | Action | Pass Criteria | On Failure |
|---|---|---|---|
| **S0** | Boot official firmware with an empty card | Boots to shooting display; captures, writes, and plays back one photo. | Stop. Troubleshoot camera body or card. |
| **S1** | Flash candidate build; boot with empty card | Normal boot time, **no boot loop**; reaches shooting display; MENU opens and closes; captures, writes, and plays back one photo. | **ABORT** (Run rollback procedure). |
| **S2** | Boot with camera settings file on card | Same boot behavior as S1; settings load without error, loss, or reset. | **ABORT** |
| **S3** | Boot with a minimal config file (`Z8PRE` safe tier) | Same boot behavior as S2; target feature enables; captures one photo. | **ABORT** |
| **S4** | Remove config file and boot | Behavior returns to S2 baseline. | **ABORT** |
| **S5** | Cold boot ×3 | Boots consistently with identical behavior all three times. | **ABORT** |
| **S6** | Power off, swap cards (including card with config), and boot | Boots normally; target feature can be re-enabled after card swap (verifies upstream issue fix). | **ABORT** |

## Abort and Rollback Procedure

Trigger this procedure immediately upon any test failure (boot loop, black screen, frozen UI, write error, or unexpected behavior):

1. **Stop testing.** Do not re-run the step or repeatedly power-cycle the camera.
2. **Clean the card.** Remove all `.CFG` files from the test card.
3. **Roll back.** Flash the verified official C 3.11 firmware package. (If the camera cannot boot to flash firmware, refer to [risks.md](risks.md) for service recovery).
4. **Log the result.** Record the failure in the ledger using the template below.

## Ledger Record Template

Log one line per executed step:

```text
[smoke] date/time | build ID + output sha256 | step S? | variable | expected | observed | verdict (PASS/FAIL/ABORT) | evidence (filenames + hashes) | next action
```

* `PASS`: All criteria met.
* `FAIL`: Criteria not met; anomaly observed.
* `ABORT`: Testing halted due to a failure.

---

## 简体中文

本文档为 V11 分支的真机冒烟测试方案，用于销项 [open-items #6](open-items.md)。

要达成 [unfreeze-criteria.md](unfreeze-criteria.md) 中的 C4 标准，需完成本测试并记录结果，或由项目负责人在台账中明确记录豁免。本测试仅验证修复后的基础开机与运行稳定性，[features.md](features.md) 中其余未验证特性仍保持未验证状态。

## 前置条件

刷机前需确认以下条件全部满足：

* **P1（硬件正常）：** 相机状态正常，运行官方固件无异常。
* **P2（回退包就绪）：** 已备好并校验官方 C 3.11 固件包（`99,051,117` 字节，SHA-256：`d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96`）。
* **P3（候选包合规）：** 候选固件必须来自 **V11 回退线**（严禁使用 V10），且已通过 C1–C3（结论已登记、修复已合入、测试全绿、构建可复现）。
* **P4（测试环境）：** 专用空测试卡、相机设置已备份、电池满电。
* **P5（初始状态）：** 执行 S1 前，测试卡上无任何 `Z8PRE*.CFG` 或 `Z8OG.CFG` 文件。

## 测试步骤

按顺序逐步执行，每步仅改变单一变量。当前步骤的通过标准全部满足后，方可进入下一步。

| 步骤 | 操作 | 通过标准 | 失败处理 |
|---|---|---|---|
| **S0** | 官方固件 + 空卡开机 | 正常进入取景界面；拍照、写卡、回放正常。 | 停止。排查机身或存储卡硬件问题。 |
| **S1** | 刷入候选固件 + 空卡开机 | 正常时间内开机，**无重启循环**；可进入取景界面；菜单正常开合；拍照、写卡、回放正常。 | **中止（ABORT）**，执行回退流程。 |
| **S2** | 放入相机设置文件开机 | 开机表现同 S1；设置加载无报错、无丢失或重置。 | **中止** |
| **S3** | 放入最小配置文件（`Z8PRE` safe 档）开机 | 开机表现同 S2；对应功能可开启；单张拍摄正常。 | **中止** |
| **S4** | 移除配置文件开机 | 恢复至 S2 的基准表现。 | **中止** |
| **S5** | 连续三次冷启动 | 三次均正常开机，表现一致。 | **中止** |
| **S6** | 关机换卡（含带配置文件的卡）后开机 | 正常开机；换卡后功能可重新开启（验证上游报告的缺陷类）。 | **中止** |

## 异常中止与回退流程

刷写与上机操作风险自担；任一异常立即中止，不“再试一次”。

测试中一旦出现重启循环、黑屏、菜单卡死、写卡报错或任何不符合通过标准的现象，立即按以下步骤处理：

1. **立即停止：** 停止后续测试，不要重复尝试或反复断电重启。
2. **清理存储卡：** 删除卡上所有 `.CFG` 配置文件。
3. **固件回退：** 重刷已校验的官方 C 3.11 固件包。（若无法开机刷机，按 [risks.md](risks.md) 走送修流程）。
4. **记录台账：** 按下方模板将失败步骤、现象及时间记入台账。

## 台账记录模板

每执行一步记录一行：

```text
[smoke] 日期时间 | 构建版本 + 输出 sha256 | 步骤 S? | 变量 | 预期结果 | 实测结果 | 结论 (PASS/FAIL/ABORT) | 证据（文件名 + 哈希） | 下一步动作
```

* `PASS`：满足所有标准。
* `FAIL`：未满足标准，出现异常。
* `ABORT`：因异常触发中止规则。
