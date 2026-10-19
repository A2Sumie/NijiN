# Open items (未完成)

Everything this project knows it has not finished. Nothing here is hidden
elsewhere; each row links to the document that owns the claim, and this page
invents no new facts. Items are ordered by what blocks what.

## Blocking the V11 line (unfreezing is the owner's call)

The written bar these items must clear is
[unfreeze-criteria.md](unfreeze-criteria.md); each row here maps to a
criterion there.

| # | Open item | State | Where it is documented |
|---|---|---|---|
| 1 | The exact faulting instruction of the V10 boot loop | **Not identified.** Three suspect changes isolated, one overrun mechanism proven. C1 evidence slot prepared and empty in [risks.md](risks.md#c1-evidence-slot) | [risks.md](risks.md), [upstream-issue-3.md](upstream-issue-3.md) |
| 2 | Load-time guard bound computed across two regions | Fix designed, not landed; guard is inert or all-permissive until then | [bricking-edge.md](bricking-edge.md) |
| 3 | Settings count has three sources of truth; only two were updated | Must be changed together or not at all | [bricking-edge.md](bricking-edge.md) |
| 4 | Ownership of the table-boundary write (`0x4CBC9B8`) | Unresolved statically: zero code references to that table | [bricking-edge.md](bricking-edge.md) |
| 5 | Second code path reaching the same apply function | No guard point there yet | [bricking-edge.md](bricking-edge.md) |

## Unverified on hardware

| # | Open item | State | Where it is documented |
|---|---|---|---|
| 6 | Every feature except the early-build HE★ / C15 evidence | Offline only; never installed | [features.md](features.md), [verification.md](verification.md) |
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
| 17 | The prepared toolkit package | Built, reconciled, **not published** — waiting for the word | [release-packaging.md](release-packaging.md), [releasing.md](releasing.md) |
| 18 | Upstream Issue #3 | Still open, no root cause there either; tracked | [upstream-issue-3.md](upstream-issue-3.md) |

## 简体中文

本页是本项目**未完成事项的正式清单**：只做索引、不发明新事实，每行链接到拥有该
口径的文档。三组：**卡住 V11 线的五件**（炸点未定谳、guard bound、计数三真源、
表边界归属、第二循环补点；解冻等用户）；**未上机验证的七件**（除早期构建 HE★/C15
外全部只离线、同号受理未实测、无损 strip 长度、镜头块/占位块/位深接线/菜单组徽标
未验）；**判不可交付的四件**（ISO 0.5EV、OSD 文本、D3 Max 档、C60/C120），连理由
一起留着看。另加发布侧两件：toolkit 已备好**未发布**、上游 Issue #3 仍在监护。
