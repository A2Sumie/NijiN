# Open Items

## V11 / V12 Blockers & Known Defects

See [unfreeze-criteria.md](unfreeze-criteria.md) for acceptance criteria and [c2-fix-plan.md](c2-fix-plan.md) for the fix plans covering items 2–5.

> **⚠️ V11.1 Status (2026-10-19):** V11.1 is marked **UNSAFE** due to a pre-capture defect family (silent non-retention, sticky STP file; see [risks.md](risks.md#known-unsafe-v111-2026-10-19)). Although items 2–5 are fixed in V11.1, **do not flash V11.1**. This defect family is fixed in **V12** (formerly V11.2, `bcf5c47f`, `03.11.p1`), which is awaiting hardware verification.

| # | Item | Status | Docs |
|---|---|---|---|
| 19 | Three-state gate defect: silent pre-capture non-retention (dual-config gate, sticky STP file never retried/deleted, fail-closed config gate) | **Fixed in V12** (formerly V11.2, `bcf5c47f`, `03.11.p1`). Added STP self-heal (session latch + evidence preservation; foreign files still stop) and gate-loss observability (status block with landing codes and per-gate counters). Passed all tests (mutations 44/44, behaviour gate 19 vectors/33 checks). **Released 2026-10-20 as NijiN V12 (EXPERIMENTAL), tag `toolkit-20261020`. Awaiting hardware verification.** | [risks.md](risks.md#known-unsafe-v111-2026-10-19), [bricking-edge.md](bricking-edge.md) |
| 1 | Exact faulting instruction of the V10 boot loop | **Root cause identified 2026-10-19** (136 §0): S3 slot count 618/617 overrun in the settings-load walk; first overrun load at `0x410DFDF8` (layout-related UB). Recorded in [risks.md](risks.md#c1-evidence-slot); dynamic reproduction (poisoned layout) in progress. | [risks.md](risks.md), [upstream-issue-3.md](upstream-issue-3.md) |
| 2 | Load-time guard bound computed across two regions | **Fixed in V11.1** (`f25c505d`), awaiting hardware. Uses same-base compare plus a header-length clamp; unit tests 9/9 (including v10 negative control). | [bricking-edge.md](bricking-edge.md), [c2-fix-plan.md](c2-fix-plan.md) |
| 3 | Settings count has three sources of truth; only two were updated | **Fixed in V11.1** (`f25c505d`), awaiting hardware. Reverted all three sources to 617 (shrink option); verified by gate G3.8 + mutation M35. | [bricking-edge.md](bricking-edge.md), [c2-fix-plan.md](c2-fix-plan.md) |
| 4 | Ownership of the table-boundary write (`0x4CBC9B8`) | **Fixed in V11.1** (`f25c505d`), awaiting hardware. Write deleted after confirming no consumers; verified by gate G3.7 + mutation M36. | [bricking-edge.md](bricking-edge.md), [c2-fix-plan.md](c2-fix-plan.md) |
| 5 | Second code path reaching the same apply function | **Fixed in V11.1** (`f25c505d`), awaiting hardware. 6/6 walk sites hooked (L2/LC, L1/LB, LS/L3); verified by gate G3.6 + mutations M38/M39. | [bricking-edge.md](bricking-edge.md), [c2-fix-plan.md](c2-fix-plan.md) |

## Unverified on Hardware

| # | Item | Status | Docs |
|---|---|---|---|
| 6 | All features except early-build HE★ / C15 | Verified offline only; never installed on hardware | [features.md](features.md), [verification.md](verification.md), [c4-smoke-plan.md](c4-smoke-plan.md) |
| 7 | Same-version update acceptance (`03.11.p0`) | Untested; bumping version number is the fallback | [versions.md](versions.md) |
| 8 | Lossless strip-length field | Static estimate, low confidence | [features.md](features.md) |
| 9 | Lens-correction block in Adobe/NX Studio | Untested (templates cover 7 lenses) | [features.md](features.md) |
| 10 | D5 placeholder block parser acceptance | Untested | [features.md](features.md) |
| 11 | Bit-depth menu wiring | Backend implemented; UI menu item not yet identified | [features.md](features.md) |
| 12 | Menu-group logo and entry behaviour | Untested on hardware | [features.md](features.md) |

## Won't Fix / Dropped Features

| # | Item | Reason | Docs |
|---|---|---|---|
| 13 | ISO 0.5 EV steps | Value consumer is unreachable in the package; degraded workaround rejected | [features.md](features.md) |
| 14 | OSD text hints | No text slot available in the display descriptor | [features.md](features.md) |
| 15 | Selectable D3 "Max." duration | Value-range record semantics undecided | [features.md](features.md) |
| 16 | C60/C120 pre-cut capture | Dropped from scope | [features.md](features.md) |

## Release & Upstream

| # | Item | Status | Docs |
|---|---|---|---|
| 17 | Toolkit package (V11.1) | **Published 2026-10-19 as experimental** (tag `toolkit-20261019`), never on hardware (untested on hardware). **Marked ⛔ UNSAFE on 2026-10-19** due to the pre-capture defect family (see [risks.md](risks.md#known-unsafe-v111-2026-10-19)); warning added to release notes. | [release-packaging.md](release-packaging.md), [releasing.md](releasing.md) |
| 18 | Upstream Issue #3 | Open; root cause still unknown upstream | [upstream-issue-3.md](upstream-issue-3.md) |

## Next Steps (November)

| Task | Prerequisite | Completion Criteria |
|---|---|---|
| **C4 Smoke Test** | Camera returned from service and verified working on official firmware | Complete [c4-smoke-plan.md](c4-smoke-plan.md) and log the test record (or explicit waiver). |
| **Unfreeze (`bricking-edge`)** | C4 completed | Criteria C1–C5 met and recorded. |
| **Release (Toolkit)** | Ready for release | Follow [releasing.md](releasing.md): pass 4 checks, rebuild kit, double reconciliation, create annotated tag, and publish via `gh release create --verify-tag`. |

---

## 简体中文

本页汇总项目当前的未完成事项、待上机验证项及已放弃的功能。

> **⚠️ V11.1 安全警告（2026-10-19）：** V11.1 存在已知预拍缺陷（三态门静默失效、STP 粘性文件残留，详见 [risks.md](risks.md#known-unsafe-v111-2026-10-19)），已标记为 **⛔ UNSAFE（不可刷机）**。虽然下表第 2–5 项已在 V11.1 中修复，但**请勿刷入 V11.1**。上述预拍缺陷已在 **V12**（原 V11.2 构建，`bcf5c47f`，第 19 项）中修复，目前待真机验证。

* **阻塞项与已知缺陷（第 1–5、19 项）：**
  * **V10 启动死循环（#1）：** 已于 2026-10-19 定位根因（设置加载遍历时 S3 槽位计数 618/617 越界，首处越界位于 `0x410DFDF8`），动态复现进行中。
  * **V11.1 修复项（#2–#5）：** 跨区边界检查、设置计数三处数据源同步、表边界写入清理、第二代码路径 Hook 均已在 V11.1 中修复，待真机验证。
  * **V12 修复项（#19）：** 修复了 V11.1 的预拍缺陷（加入 STP 自愈与状态可观测性），已于 2026-10-20 作为试验品发布（tag `toolkit-20261020`），待真机验证。
* **待真机验证（第 6–12 项）：** 除早期构建的 HE★ / C15 外，其余功能（平级版本号刷机、无损条带长度、Adobe/NX Studio 镜头校正块、D5 占位块解析、位深菜单绑定、菜单组图标）均仅完成离线开发，尚未上机测试。
* **已放弃功能（第 13–16 项）：** ISO 0.5 EV 步进、OSD 文本提示、D3 "Max." 时长选项、C60/C120 预录制因底层限制或范围裁剪不再开发。
* **发布与上游追踪（第 17–18 项）：** V11.1 工具包（`toolkit-20261019`，从未上机）已在发布说明中追加不安全警告；正式发布走 `gh release create --verify-tag`；上游 Issue #3 持续跟进中。
* **11 月后续计划：** 待相机返修归还并确认官方固件运行正常后，依次执行 **C4 真机冒烟测试**（按 [c4-smoke-plan.md](c4-smoke-plan.md)）、**分支解冻**（满足 C1–C5 条件后）及**正式发布**（按 [releasing.md](releasing.md) 流程）。
