# Unfreeze criteria for the `bricking-edge` line

The V11 (`bricking-edge`) branch is currently frozen. The line exists because a V10 build bricked a camera, and building or flashing anything from it is entirely your own risk. All criteria below must be met before the owner approves unfreezing it.

## Criteria

| # | Criterion | Requirements | Closes |
|---|---|---|---|
| C1 | **Root cause identified** | Pinpoint the exact instruction or code path causing the V10 boot loop. Must be reproduced on hardware, or proven via static and dynamic analysis that rules out all other changes in the diff. Complete all fields in the [C1 section of risks.md](risks.md#c1-evidence-slot) (verdict, evidence grade, code anchors, diff exhaustion, reproduction status, and remaining unknowns). | [open-items #1](open-items.md) |
| C2 ✅ | **Fixes implemented and verified offline**<br>*(Met 2026-10-19: `bricking-edge_v11.1` / `f25c505d…`, 4 fixes landed, unit tests 9/9, gates G3.5–G3.8 passed; see `100_BUILD_LOG.md §V11.1`)* | Fix all known defects in boot-reachable code with before/after verification (see [c2-fix-plan.md](c2-fix-plan.md)):<br>- Calculate guard bounds from the correct memory region.<br>- Update the settings count across all three sources of truth.<br>- Remove the table-boundary write or prove its ownership.<br>- Add a guard to the second path calling the apply function. | [open-items #2–5](open-items.md) |
| C3 ✅ | **Offline tests pass and build is reproducible**<br>*(Met 2026-10-19: gates 7/7, mutations 39/39, combinations 17/17, structural 4/4, byte-identical rebuild, repo checks 4/4, hashes locked)* | Pass the full test suite (gates, mutation tests, combination matrix, structural tests) and all four repository checks. Rebuilds must be byte-identical with locked recipe source hashes. | [open-items #2–5](open-items.md) |
| C4 | **On-device smoke test (or written waiver)** | Boot and take a photo on a test device following [c4-smoke-plan.md](c4-smoke-plan.md) (changing one variable at a time), and log the results in the ledger. Alternatively, the owner may log a written waiver in the ledger to skip hardware testing.<br>*(Note: Emulator runs do not count, as they do not test flashing, the boot ROM, persistent settings, or the real startup sequence.)* | [open-items #6](open-items.md) |
| C5 | **Documentation updated** | Close resolved items in [open-items.md](open-items.md) with evidence links, update the status table in [bricking-edge.md](bricking-edge.md), and sync the [upstream tracking log](upstream-issue-3.md) if upstream findings changed. | [open-items](open-items.md) |
| C6 | **Owner sign-off** | Explicit approval to unfreeze recorded in the ledger by the owner. | — |

## Post-unfreeze testing rules

1. Start from the V11 revert build, not V10.
2. Change one variable at a time. Keep a verified official firmware package ready for recovery and follow the generated pre-flash checklist.
3. Stop immediately at the first anomaly.
4. If the issue recurs, re-freeze the branch before investigating.

## 简体中文

V11（`bricking-edge`）分支目前处于冻结状态——这条线因一台相机被**刷砖**而生，构建与刷写风险自担。需满足以下全部条件，并由负责人最终确认后方可解冻：

- **C1 定位根本原因**：明确导致 V10 开机循环的具体指令或代码路径。需通过真机复现，或通过静态+动态分析排除 diff 中的所有其他可能。按要求填完 [risks.md](risks.md#c1-evidence-slot) 中的 C1 证据字段（结论、证据等级、代码位置、排除说明、复现状态及未知项）。（销项：[open-items #1](open-items.md)）
- **C2 ✅ 完成修复并离线验证**（已于 2026-10-19 完成，见 `100_BUILD_LOG.md §V11.1`）：修复启动路径上的所有已知缺陷（详见 [c2-fix-plan.md](c2-fix-plan.md)），并提供修复前后的对比验证：用正确的内存区域计算 guard 边界；同步修改三处配置项计数；移除表边界写入或证明其归属；为调用 apply 函数的第二路径补充防护。（销项：[open-items #2–5](open-items.md)）
- **C3 ✅ 离线测试全绿且构建可复现**（已于 2026-10-19 完成）：通过全部测试套件（门禁 7/7、变异测试 39/39、组合测试 17/17、结构测试 4/4）及仓库四项检查，锁定配方源码哈希，且重复构建产物逐字节一致。（销项：[open-items #2–5](open-items.md)）
- **C4 真机冒烟测试（或书面豁免）**：按 [c4-smoke-plan.md](c4-smoke-plan.md) 在测试机上遵循单变量原则完成开机与拍照测试，并将结果记入台账；或由负责人在台账中明确记录豁免真机测试。*注：模拟器开机不能替代真机测试（不涉及刷写、Boot ROM、持久化设置及真实上电流程）。*（销项：[open-items #6](open-items.md)）
- **C5 更新文档**：在 [open-items.md](open-items.md) 中关闭已解决项并附上证据链接，更新 [bricking-edge.md](bricking-edge.md) 状态表，如有上游进展需同步更新 [upstream-issue-3.md](upstream-issue-3.md)。
- **C6 负责人审批**：负责人在台账中明确记录解冻指令。

**解冻后的测试要求**：

1. 首个测试版本必须基于 V11 回退包，禁止使用 V10。
2. 每次只改一个变量。刷机前备好经校验的官方恢复固件，并按生成的刷机前检查单执行。
3. 遇到任何异常立即停止测试。
4. 若问题复发，先重新冻结分支，再排查原因。
