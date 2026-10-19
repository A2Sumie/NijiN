# C2 fix plan — the four fixes the V11 line needs

> **Status 2026-10-19 (thread `v111-an`)**: all four fixes are now **landed offline** as the
> **V11.1 candidate** (`he_star/build/bricking-edge_v11.1/`, `Z_8_0311.bin` sha
> `f25c505d…`, identity 03.11.p0). Per-fix verdicts and the 预案 vs 落地 table live in
> `scratch/expeed7_v2/100_BUILD_LOG.md` § "V11.1 候选". Short version: Fix 1 landed (same-base
> bound + header-length plausibility clamp), Fix 4 landed (all six walk sites clamped, xref
> coverage gate), Fix 3 = **deleted** (option A — no consumer could be named: static triad 0,
> watchpoint 0, 628-slot cross-check shows T4 is not the card list), Fix 2 = **option B**
> (all three count sources back to 617). Not flashed, not released; C2's on-paper status is
> for the owner to close per [unfreeze-criteria.md](unfreeze-criteria.md) — nothing here
> unfreezes the line.

> **STATUS: LANDED (2026-10-19, build `bricking-edge_v11.1`, `f25c505d…`).**
> All four fixes are implemented and offline-verified; criterion C2 is
> **met**. Landed forms differ from the plan in four ways, named below.
> The plan text is kept as written — it is the standard the landing was
> checked against.

**Plan vs landed** (details in the crash workstream's `100_BUILD_LOG.md §V11.1`):

| Fix | Plan said | Landed | Delta |
|---|---|---|---|
| 1 guard bound | same-base compare, `bound = file-image base + header length` | same-base compare via `end_off = (ptr − base) + size` vs `total=[x25,#0x10]`, base underflow counted out-of-range, **plus a header-length plausibility clamp `[0x80, 2MiB]`** and a `ret`-style skip path so one stub serves several sites | **stronger than plan** (the plan's residual "header length must be validated" is closed) |
| 4 walk coverage | clamp every walk site, xref gate | 6/6 sites hooked (L2/LC → `_guard`, L1/LB → `_s28`, LS/L3 → `_s24`), new xref-coverage gate G3.6, mutations M38/M39, per-family unit tests | as planned |
| 3 table-boundary write | delete, or prove an owner first | **deleted** after three proofs (static: 0 references across three scan families; watchpoint: 0 hits through boot+menu on both aliases; 628-slot cross-check: the two tables are not isomorphic — 624 vs 286 entries, 40 overlapping) | as planned, option A |
| 2 count sources | grow all three or shrink all three; shrink recommended | **shrank** (both immediates back to 617, ROM table untouched → all three agree), new gate G3.8, mutation M35 | as planned, recommended direction |

Every anchor below is cited from the crash-forensics records
(`126_BOOTLOOP_FORENSICS.md`, `123_T4_CHAIN.md`) and is checkable against
the local evidence. Closes [open-items #2–5](open-items.md).

## Fix 1 — guard bound: compare within one region

| | |
|---|---|
| **Now (wrong)** | The bounds stub (code at `0x40967B84`, hooked at eg `0xF7F9D4`) computes `bound = x25 + header_len`, where `x25 = 0xA0480dc78` is the **32-byte header copy**. The item buffer `x3` lives in the **file-image buffer**, whose base is at `*(u64*)0xA0480dc70`. `item_end <= bound` therefore compares addresses from two different regions. Result depends on where the heap put the file buffer: silently **skip everything or allow everything** (126 §2) |
| **Change** | Make both operands share one base: `bound = *(u64*)0xA0480dc70 + header_len` (file-image base + header length field), or replace `x25` with the file-image buffer pointer and keep the arithmetic identical. Nothing else in the stub changes: same register promises (w9/x9/x10/x16 scratch, x30 untouched, tail-branch return), same fail-safe behaviour (out-of-range item → skip it, keep defaults) |
| **Verify offline** | ① Unit check on the stub: with a short file and a long file, `item_end <= bound` is true exactly for in-range items (assert per item, not per file). ② New gauntlet content gate: the guard's two comparison operands must derive from the same base symbol. ③ Mutation battery: over-long and short segment-directory entries must be skipped **individually**, all other items applied. ④ Regression: the settings-file regression suite (R1/R2/R3) stays green on the real sample. ⑤ A/B diff vs the previous build confined to the guard code window |
| **Risk** | Low. The stub was proven incapable of crashing (126 §2, A-grade); this is a semantics fix. Residual: the header length field itself must be validated as plausible before use, or a corrupt header could still pass |

## Fix 2 — settings count: three sources, changed together or not at all

The count has **three** sources of truth (123 §2/§3, A-grade):

| Source | Location | Value (variant 1/2/3/4) | v10 |
|---|---|---|---|
| ROM variant table (used by the load path, R1) | u32 table `0x44182f90..0x44182ff0`, S3 count at `0x44182fe0` | [472, 572, 586, **617**] | **not changed** |
| R2 hard-code (boot registration chain) | VA `0x410e0f04`, variant-3 only | S3 = **617** (with COUNT1 1112 / COUNT2 184 / COUNT3 331 / COUNT4 79 / S2 11 / len 340346) | changed to 618 |
| Save-side immediate | eg `0xF803D4` | 617 | changed to 618 |

| | |
|---|---|
| **Now (wrong)** | Two of three sources say 618 while the backing lists (the variant list family at eg `0x299xxxx`, the real per-item lists) still hold 617 entries. Any walk trusting the count overruns by one entry. R1 re-registers 617 from the ROM table at load time, but between R2 (boot) and R1, and in base+offset consumers, 618 leaks out |
| **Change — option A (grow)** | Change all three sources **in one build** and extend the backing lists to 618 entries. Requires a real 618th entry definition; without it, option A is speculation |
| **Change — option B (shrink)** | Revert **all three** to 617 and let the fixed guard from Fix 1 clamp by file-in-bounds. This is the minimal-risk option: it restores the previous build's semantics and removes the overrun class entirely |
| **Verify offline** | ① Static gate: all three sources equal, asserted from the recipe. ② Emulator: a walk over the table with each count value; option A must complete 618 iterations without overrun, option B must complete 617 and the guard must reject a forged 618th item. ③ Mutation battery: any mismatch between the three sources is a new refused mutation. ④ Settings-file regression green. ⑤ A/B diff confined to the declared count windows |
| **Risk** | Option A is invasive: a wrong 618th entry corrupts state at save time, not boot time. Option B gives up the card-serialization gain v10 was after (that gain is unproven anyway — see Fix 3). **Recommendation: option B unless Fix 3 proves ownership first** |

## Fix 3 — the table-boundary 8B write: delete it, or prove the owner

The write at eg `0x4CBC9B8` (8 bytes, `00 08 00 00 00 01 00 00`) sits
between two tables: the 628×8B table `0x4CBB618..0x4CBC9B8` and a 32-byte
record table starting at `0x4CBC9C0` (records shaped `{id,9},{size,0},
{ram,10},{pad,0}`, 24/24 matched). So the address is **either** the tail
alignment gap (harmless) **or** `rec0`'s pad field (the write corrupts a
record). Static scanning found **zero** code references to that table —
movz/movk dual aliases, ADRP and raw literals across all five segments
(123 §5) — so ownership cannot be closed statically.

| | |
|---|---|
| **Option A (delete)** | Revert the 8B to the previous build's zeros. Always safe; the card-persistence question returns to its earlier, honestly-unresolved state |
| **Option B (prove, then write)** | Close the consumer chain first: emulator watchpoint on `0x4CBC9B8` during save/load, runtime traces where static xrefs fail, and cross-check the 628/628 slot correspondence (tag = segment-class marker, A-grade) against the `0x299xxxx` list family. Only if a real consumer of that address appears does the write stay — otherwise the serialization attempt moves to the real card list family |
| **Verify offline** | ① For option A: A/B diff shows the 8B reverted and nothing else. ② For option B: a named consumer observed in the emulator (read or write at that address during a save/load cycle), plus a gauntlet rule that **every written range must name its owner** — a recipe that writes an unowned table is refused. ③ In both cases: settings regression green, including "the new item survives card save/load" for the state the design intends |
| **Risk** | Option B without a consumer is exactly how v10 got here. Option A costs a feature that was never proven to work |

## Fix 4 — second and sibling walk loops: same clamp everywhere

The apply function `0x410E1AA8` is reached from **two** loops; only one is
guarded (123 §15/§4):

| Loop | Hook site | Apply | Guard state |
|---|---|---|---|
| L2 blob (S0/S1 family) | eg `0xF7F9D4` | `0x410E1AA8` | v10 guard present (**bound defective**, Fix 1) |
| LC blob (bank loop) | eg `0xF7FBF8` | `0x410E1AA8` | **none** |
| L1 scalar (S0/S1) | eg `0xF7F8D4` | `0x410E1790` | none |
| LB scalar (bank) | eg `0xF7FB2C` | `0x410E1790` | none |
| LS scalar (S2, record loop) | eg `0xF7FCA8` family | `0x410E1790` family | none |
| L3 scalar (S3, bank loop) | eg `0xF7FE28` | `0x410E1790` | none |

| | |
|---|---|
| **Change** | After Fix 1, install the same clamp at every unclamped walk site. LC shares L2's register convention (x3 = item buffer, w2 = size, x25 = header copy, x30 = return), so the corrected stub is directly reusable there. The four scalar loops need the equivalent check on their own operand shape (4B/step × count). A single clamp at the parse entry is an alternative only if it provably cannot change behaviour for valid files |
| **Verify offline** | ① Static gate: xref sweep shows **every** `bl 0x410E1AA8` / `0x410E1790` walk site covered by a clamp; the gauntlet refuses a build with an uncovered site. ② Emulator: a forged over-long item is skipped in each loop family, others applied. ③ Mutation battery gains one case per loop family. ④ Settings regression green; A/B diff confined to the declared hook/code windows |
| **Risk** | More hooks in boot-reachable code — the exact place where the incident lived. Each hook needs its own byte-level review with register promises, and the smoke-test bar of [unfreeze-criteria.md](unfreeze-criteria.md) C4 applies to the whole set |

## Order and dependency

1. Fix 1 first: everything else leans on a correct bound.
2. Fix 4 next: coverage of all walk sites, same stub family.
3. Fix 3: decide delete-vs-prove (option A is compatible with any outcome).
4. Fix 2 last, and in the direction Fix 3 chose: prove-first ⇒ option A (grow), delete ⇒ option B (shrink).

## 简体中文

**这是预案，不是代码**：不落码不构建；在四项修复真正落地并离线验证之前，
[unfreeze-criteria.md](unfreeze-criteria.md) 的 C2 维持**未达成**。锚点全部引自
`126_BOOTLOOP_FORENSICS.md`／`123_T4_CHAIN.md`，可对照本地证据核查。销
[open-items #2–5](open-items.md)。

**① guard bound 修正**：现状是跨区比较（`x25=0xA0480dc78` 头副本 + 长度 当 bound，
而被检的 item 缓冲在 `[0xA0480dc70]` 指向的文件镜像缓冲里）⇒ 真机行为"全跳过 or
全放行"。改法：两端同基址——`bound = *(u64*)0xA0480dc70 + 头长度`，或把 x25 换成
文件镜像缓冲指针，寄存器承诺与 fail-safe 语义不动。验证：单测长短文件逐项判定、
新 gauntlet 内容门（比较两端须同基址）、变异电池逐项跳过语义、设置回归 R1/R2/R3
保持绿、A/B 差分收敛。风险低（该桩已 A 级排除致崩）；残留=头长度字段本身要先判合理。

**② 计数三真源同步**：ROM 变体表 `0x44182fe0`（载入 R1 用，未改）、R2 硬编码
`0x410e0f04`（开机注册链，v10 改了）、保存侧 `0xF803D4`（v10 改了）——现状 618/617
不一致，背衬列表仍是 617 项。两个方向：**A 扩**=三源同改+背衬列表（`0x299xxxx` 族）
扩到 618 槽（须先定义第 618 项，否则是臆测）；**B 缩**=三源全回 617，靠修好的 guard
按文件内边界钳制（最小风险）。验证：三源相等静态门、模拟器走查两种计数、变异电池
新增"三源不一致即拒"、设置回归绿。**建议：除非 ③ 先证明归属，否则走 B**。

**③ 表边界 8B 写归属**：`0x4CBC9B8` 夹在 628×8B 表尾与 32B 记录表（`0x4CBC9C0` 起）
之间，**或**是对齐隙（无害）**或**是 rec0 的 pad（写坏记录）；全固件 0 引用，静态
闭环不了。两解：**删**（回退为零，永远安全）或**证**（模拟器 watchpoint+运行期 trace
+628/628 槽对应交叉核对，见到真实消费者才写，否则改走 `0x299xxxx` 卡路列表族）。
验证：A/B 差分只落声明窗；新增 gauntlet 规则"每个写区间必须点名归属，写无主表即拒"。

**④ 第二循环补点**：`bl 0x410E1AA8` 全图两处（L2 `0xF7F9D4` 已挂、**LC `0xF7FBF8`
未挂**），另有四个标量循环走 `0x410E1790`（L1 `0xF7F8D4`/LB `0xF7FB2C`/LS `0xF7FCA8`
族/L3 `0xF7FE28`）全无钳制。LC 与 L2 同寄存器约定，修正 bound 后可直接复用同型桩。
验证：xref 扫描全覆盖门（漏一处即拒构建）、每循环族一条变异、设置回归绿、A/B 收敛。
风险：又在开机可达路径加 hook——正是事故所在处；每个 hook 要逐字节审，且 C4 冒烟
门槛适用于整组。

**顺序**：① 先（一切靠正确 bound）→ ④ → ③（选删或证，删与任何结局兼容）→ ② 最后，
方向跟 ③ 走：证到归属 ⇒ 扩；删了 ⇒ 缩。
