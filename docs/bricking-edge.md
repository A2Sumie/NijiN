# The `bricking-edge` line (V11)

This branch serves as the hotfix and forensics line, created in response to the V10
incident: a build from the stable line was installed on a test camera, causing it
to enter a boot loop and require service. See [risks.md](risks.md) for the full
record.

**Verdict reached (2026-10-19).** The crash point is the S3 slot count
618/617 overrun in the settings-load walk (layout-related UB), not the
table write, the guard stub or the menu code — see the C1 slot in
[risks.md](risks.md#c1-evidence-slot). The verdict states that this line's
fix — reverting the two count immediates to 617 — is **correct and
sufficient**: it returns to the same counts as the previous and stock
builds. Unfreezing is still the owner's call (criterion C6 in
[unfreeze-criteria.md](unfreeze-criteria.md)); the remaining criteria keep
their course.

The name is deliberate dark humor. The usual term is "bleeding edge"; this line is
named after what the previous line actually did.

## Where the recipe lives

| Item | What it is |
|---|---|
| `recipes/revert_v10_tails.py` | The line's recipe: take a local V10 build and a local previous build, revert the four suspect payload windows to their previous values, rebuild the checksum chain, and verify that the result differs from V10 strictly within those windows |
| `docs/bricking-edge.md` | This page |

Both files are also tracked on `main` to keep the line readable and reviewable
everywhere. **Changes to the V11 line land on the `bricking-edge` branch**, which
is what the name marks.

## What the recipe reverts

| Payload offset | Bytes | Change removed | Why it is suspect |
|---|---|---|---|
| `0xF803D4` | 4 | settings-count immediate 617 → 618 | The count now conflicts with its backing table (617 entries); any traversal relying on it overruns by one entry. Mechanism verified offline |
| `0xF80F68` | 4 | same count change in the boot-registration path | Sits inside a function that runs during application initialization—precisely where the boot loop occurs |
| `0x4CBC9B8` | 8 | settings-table tail write | The address marks the boundary between two adjacent tables. Table ownership could not be resolved statically: zero code references exist anywhere in the package |
| `0xF7F9D4` | 4 | load-time bounds guard hook | The guard cannot crash, but its bound is computed across two different regions, so it may silently skip or allow every entry |

All other bytes in the output remain identical to the V10 input, including the
recompiled code blob. The script refuses to run unless the A/B differences are
confined strictly to the declared windows plus the checksum chain.

## State of this line

| Aspect | State |
|---|---|
| Built | Yes, once, as a local trial |
| Byte-level comparison | Passed: diff against V10 is limited strictly to the four windows plus the trailing checksum |
| Released into a build kit | **No, deliberately not** |
| Tested on hardware | **No** |
| Recommended to flash | **No** |
| **V12 (原 V11.2 构建)** | Build `bricking-edge_v11.2_p1`, `Z_8_0311.bin` sha **`bcf5c47f5aedd873d7292381ea747d7f794c634dbf628ba5272a8ae2c5d9fb03`**, identity **`03.11.p1`** — three-state gate fixes on top of V11.1 (STP sticky-file self-heal with a session latch and evidence preservation; gate-loss observability: readable status block with landing codes and per-gate counters where failures used to be silent) **plus V11.1 no regression** (its four fixes byte-verified unchanged, settings regression green). Offline: gauntlet **ALL GREEN** (gates 7/7, mutations 44/44, combinations 17/17, structural 4/4, new three-state behaviour gate 19 vectors/33 checks). **未上机 / never on hardware, 未发布 / not released** — not in a flash kit, candidate awaiting verification |
| **V11.1 candidate** | **⛔ UNSAFE（已知缺陷，调查中）/ known defects, under investigation** — 已知问题见 [risks.md](risks.md#known-unsafe-v111-2026-10-19)，勿刷 / known issues in [risks.md](risks.md#known-unsafe-v111-2026-10-19), do not flash. **V12（原 V11.2 构建）已修其已知缺陷（三态门家族）/ V12 fixes its known defects.** Build `bricking-edge_v11.1`, `Z_8_0311.bin` sha **`f25c505d0daf9b1f16e345d10d5e82e85b8e8a77d0e4a89153620d5f77e7251a`** (that build's identity `03.11.p0`; **the experimental line packages as `03.11.p1` — `p0` is the historical smoke/incident generation, `p1` the V11.1 generation**) — the four C2 fixes landed (count sources back to 617, unowned table write deleted, 6/6 walk sites clamped, same-base guard with a header-length clamp). Offline: gauntlet ALL GREEN, 39/39 mutations, rebuild reproducible. **未上机 / never on hardware**, **released 2026-10-19 as an experimental trial** (tag `toolkit-20261019`, toolkit objects only — still no firmware here) |
| Frozen | Yes — the bar for unfreezing is written down in [unfreeze-criteria.md](unfreeze-criteria.md); clearing it does not unfreeze anything by itself |

The trial output hash recorded at the time was `0da2b2b0…`. That records a single
local build, not a release: no package from this line has ever been published,
and none will be until the conditions below are met.

## What must be settled before this line moves

1. The load-time guard's bound must be computed from the correct region, not
   across two different ones.
2. The settings count has **three** sources of truth (ROM variant table,
   hard-coded registration, save-side immediate). All three must be updated
   together, or none of them.
3. Ownership of the table-boundary write must be closed: determine which table
   owns `0x4CBC9B8`, and whether any consumer exists at all.
4. The second code path that reaches the same apply function must get its own
   guard point.
5. Above all: the instruction that actually faults on hardware is **not known**.
   Until it is, this line remains a hypothesis, not a fix.

Reverting the four windows may well allow the camera to boot. It may also be that
one of the remaining differences is the real root cause. Nobody knows yet, and
this line does not pretend otherwise.

## If you build from this branch anyway

You are on your own: bring both input builds, run the recipe, inspect its
verification output, run the full gauntlet, and accept that the last build with a
green gauntlet is the one that bricked a camera. Keep the official package
verified and ready. See [build.md](build.md) and [verification.md](verification.md).

## 简体中文

- 本分支定位为**热修／取证线**，因 V10 上机引发开机循环故障而设立；`bricking-edge` 这一命名是有意保留的黑色幽默（常规叫法为 bleeding edge，此处直接以既往版本导致的实际后果命名）。
- 配方脚本与本文档在 `main` 分支上同步保留，确保公开且可复核（`recipes/revert_v10_tails.py` 仅将四个嫌疑窗口回退至上一构建对应的字节，其余逐字节保持不变，并强制校验 A/B 差分必须落在声明窗口内）；**V11 线路本身的变更直接提交至 `bricking-edge` 分支**，这也是分支名的含义。
- 四个嫌疑窗口及改动理由（设置项计数 617→618 与底层表不一致且位于开机注册路径、表边界 8B 写入归属未闭环、guard 跨区比较可能导致全部跳过或全部放行）已逐条在上表中列出。
- **状态**：仅在本地构建过一次试验包（`0da2b2b0…`），字节级比对已通过；**从未进过 flash_kit、从未上机测试、不建议刷写**（判词另注：v10 属布局相关 UB，"某台机器没炸"≠安全，V11 之前的构建一律不回灌）。**V12（原 V11.2 构建）**（`bricking-edge_v11.2_p1`，sha `bcf5c47f…`，身份 `03.11.p1`）：**三态门修复 + V11.1 无回归**（STP 粘性文件自愈＝会话闩+证据保全、失守可观测＝状态块可读含落点码与分门计数；V11.1 四修复字节未动、回归绿）；gauntlet **全绿**（七门 7/7、变异 44/44、组合 17/17、结构 4/4、三态门行为回归 19 向量 33 checks）；**未上机、未发布、未进 flash_kit，候选待验**。
**V11.1 候选**（`bricking-edge_v11.1`，sha `f25c505d…`；该构建身份 `03.11.p0`，**试验品线封包身份 `03.11.p1`**——`p0` 系=历史冒烟/事故代、`p1`=V11.1 代）**状态：⛔ UNSAFE（已知缺陷，调查中）——已知问题见 [risks.md](risks.md#known-unsafe-v111-2026-10-19)，勿刷**。已把 C2 四修复落地：计数三真源回 617（炸点机理根除）、无主表写已删、6/6 走查站点挂钩、guard 同基址+头长钳（强于预案）；离线 gauntlet 全绿、变异 39/39、重建可复现；**未上机、未进 flash_kit**；已于 2026-10-19 按发布令以**试验品**身份随 toolkit 发布（tag `toolkit-20261019`，仍零固件字节）。解冻门槛见 [unfreeze-criteria.md](unfreeze-criteria.md)：门槛全过也不自动解冻，解冻是用户的决定。
- 解冻前置条件：guard bound 修复、计数三真源同步修改、表边界写入归属完成闭环、第二代码路径补充防护点，最根本的前提——**真机炸点已于 2026-10-19 定谳**（S3 槽计数 618/617 越界、布局相关 UB）：本线"撤两个计数立即数回 617"被终审判为**修法正确且充分**（与 v9/官方同轨）。**解冻仍等用户令（C6）**，其余判据照走；毒化崩溃实跑（约 0.5–1 人日）在途。
