# Open items (未完成)

Everything this project knows it has not finished. Nothing here is hidden
elsewhere; each row links to the document that owns the claim, and this page
invents no new facts. Items are ordered by what blocks what.

## Blocking the V11 line (unfreezing is the owner's call)

The written bar these items must clear is
[unfreeze-criteria.md](unfreeze-criteria.md); each row here maps to a
criterion there. The fix plans for rows 2–5 are written up at recipe level
in [c2-fix-plan.md](c2-fix-plan.md).

**2026-10-19 status note:** V11.1 itself is marked **⛔ UNSAFE (known
defects, under investigation)** — a known pre-capture defect family
(silent non-retention, STP sticky file) is documented in
[risks.md](risks.md#known-unsafe-v111-2026-10-19). The four fixed rows
below do **not** make V11.1 safe to flash. **Update:** the defect family is
**fixed in V12 (原 V11.2 构建)** (`bcf5c47f…`, `03.11.p1`) — see row 19;
the candidate is awaiting verification and does not lift V11.1's marker.

## Known defect family

| # | Open item | State | Where it is documented |
|---|---|---|---|
| 19 | Three-state gate scar: silent pre-capture non-retention (dual-config gate, **STP sticky file never retried or deleted**, fail-closed config gate) | **Fixed in V12 (原 V11.2 构建, `bcf5c47f…`, `03.11.p1`)** — STP self-heal (session latch + evidence preservation; foreign files still stop) + gate-loss observability (readable status block with landing codes and per-gate counters). V11.1 no regression; gauntlet ALL GREEN (mutations 44/44, three-state behaviour gate 19 vectors/33 checks). **Awaiting hardware. Released 2026-10-20 as NijiN V12 (EXPERIMENTAL), tag `toolkit-20261020`** | [risks.md](risks.md#known-unsafe-v111-2026-10-19), [bricking-edge.md](bricking-edge.md) |

| # | Open item | State | Where it is documented |
|---|---|---|---|
| 1 | The exact faulting instruction of the V10 boot loop | **Verdict reached 2026-10-19** (136 §0): S3 slot count 618/617 overrun in the settings-load walk, first overrun load at `0x410DFDF8` — layout-related UB. C1 slot filled in [risks.md](risks.md#c1-evidence-slot); dynamic re-reproduction (poisoned layout, ~0.5–1 person-day) still in flight | [risks.md](risks.md), [upstream-issue-3.md](upstream-issue-3.md) |
| 2 | Load-time guard bound computed across two regions | **Fixed 2026-10-19 (build `bricking-edge_v11.1`, `f25c505d…`), awaiting hardware.** Fixed in V11.1: same-base compare plus a header-length clamp — **stronger than planned**; unit tests 9/9 including the v10 negative control | [bricking-edge.md](bricking-edge.md), [c2-fix-plan.md](c2-fix-plan.md) |
| 3 | Settings count has three sources of truth; only two were updated | **Fixed 2026-10-19 (build `bricking-edge_v11.1`, `f25c505d…`), awaiting hardware.** Fixed in V11.1: all three sources back to 617 (shrink option); three-source gate G3.8 + mutation M35 | [bricking-edge.md](bricking-edge.md), [c2-fix-plan.md](c2-fix-plan.md) |
| 4 | Ownership of the table-boundary write (`0x4CBC9B8`) | **Fixed 2026-10-19 (build `bricking-edge_v11.1`, `f25c505d…`), awaiting hardware.** Fixed in V11.1: the write is **deleted** after three proofs of no consumer; ownership gate G3.7 + mutation M36 | [bricking-edge.md](bricking-edge.md), [c2-fix-plan.md](c2-fix-plan.md) |
| 5 | Second code path reaching the same apply function | **Fixed 2026-10-19 (build `bricking-edge_v11.1`, `f25c505d…`), awaiting hardware.** Fixed in V11.1: 6/6 walk sites hooked (L2/LC, L1/LB, LS/L3); xref-coverage gate G3.6 + mutations M38/M39 | [bricking-edge.md](bricking-edge.md), [c2-fix-plan.md](c2-fix-plan.md) |

## Unverified on hardware

| # | Open item | State | Where it is documented |
|---|---|---|---|
| 6 | Every feature except the early-build HE★ / C15 evidence | Offline only; never installed | [features.md](features.md), [verification.md](verification.md), [c4-smoke-plan.md](c4-smoke-plan.md) |
| 7 | Same-version update acceptance (`03.11.p0`) | Untested; a higher number is the fallback | [versions.md](versions.md) |
| 8 | Lossless strip-length field | Static estimate, low confidence | [features.md](features.md) |
| 9 | Lens-correction block acceptance in Adobe/NX Studio | Not tested; templates cover 7 lenses | [features.md](features.md) |
| 10 | D5 placeholder block parser acceptance | Not tested | [features.md](features.md) |
| 11 | Bit-depth menu wiring | Consumption implemented; the menu item is not identified | [features.md](features.md) |
| 12 | Menu-group logo and entry behaviour | Never seen on hardware | [features.md](features.md) |

## Judged not deliverable (kept visible on purpose)

| # | Item | Reason | Where it is documented |
|---|---|---|---|
| 13 | ISO 0.5 EV steps | The value's consumer is unreachable in the package; the degraded route was rejected | [features.md](features.md) |
| 14 | OSD text hints | No text slot in the display descriptor | [features.md](features.md) |
| 15 | D3 "Max." duration selectable | Value-range record semantics undecided | [features.md](features.md) |
| 16 | C60/C120 pre-cut capture | Deliberately cut | [features.md](features.md) |

## Publication side

| # | Open item | State | Where it is documented |
|---|---|---|---|
| 17 | The toolkit package | **Published 2026-10-19 as an experimental trial** (tag `toolkit-20261019`): V11.1 candidate objects, never on hardware, crash fix is an offline verdict. **Marked ⛔ UNSAFE 2026-10-19** (known defect family; see [risks.md](risks.md#known-unsafe-v111-2026-10-19)) — the release notes carry a dated addendum saying so | [release-packaging.md](release-packaging.md), [releasing.md](releasing.md) |
| 18 | Upstream Issue #3 | Still open, no root cause there either; tracked | [upstream-issue-3.md](upstream-issue-3.md) |

## Next batch (November): three triggers

| Item | Trigger to start | Gate before it counts | Who decides |
|---|---|---|---|
| **C4 smoke** | The camera is back from service and known-good on official firmware | The run follows [c4-smoke-plan.md](c4-smoke-plan.md) step by step; a smoke record or an explicit waiver lands in the ledger | Owner |
| **Unfreeze (`bricking-edge`)** | C4 satisfied (smoke record or written waiver) | C1–C5 all met and recorded; the decision itself is an explicit instruction in the ledger | **Owner only (C6)** |
| **Release (toolkit)** | An explicit "publish" instruction | [releasing.md](releasing.md) runbook: four checks green, rebuilt kit, double reconciliation, annotated tag, then `gh release create --verify-tag` | **Owner only** |

Everything else on this page waits on those three or on the residual work
listed above. Nothing here starts itself.

## 简体中文

本页是本项目**未完成事项的正式清单**：只做索引、不发明新事实，每行链接到拥有该
口径的文档。三组：**V11 线相关五件**（#1 炸点已于 2026-10-19 定谳、C1 槽已填；guard bound、计数三真源、
表边界归属、第二循环补点已随 V11.1 修复、待上机；解冻等用户）；**未上机验证的七件**（除早期构建 HE★/C15
外全部只离线、同号受理未实测、无损 strip 长度、镜头块/占位块/位深接线/菜单组徽标
未验）；**判不可交付的四件**（ISO 0.5EV、OSD 文本、D3 Max 档、C60/C120），连理由
一起留着看。另加发布侧两件：toolkit 已按发布令**以试验品身份发布**（tag `toolkit-20261019`，V11.1 候选、从未上机）、上游 Issue #3 仍在监护。
**⚠️ 2026-10-19：V11.1 本身已标记 ⛔ UNSAFE（已知缺陷，调查中）**——已知预拍缺陷家族
（三态静默失效、含 STP 粘性文件）见 [risks.md](risks.md#known-unsafe-v111-2026-10-19)，**该家族已修于 V12（原 V11.2 构建，`bcf5c47f…`，第 19 项）——候选待验、未上机、未发布，V11.1 的 ⛔ 标记不因此解除**；
上面四条"已修复"**不等于 V11.1 可刷**，toolkit 发布物的说明已加同日补记。
**11 月批次三件的触发条件**见上文 "Next batch (November)"：C4 冒烟（机器回来+官方固件正常→按 c4-smoke-plan 走）｜解冻（C4 成立后，**C6=仅你下令**）｜发布（**仅你给"发"字**→按 releasing.md runbook）。三件都由触发条件启动，没有一件会自己开始。
