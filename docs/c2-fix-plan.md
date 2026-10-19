# C2 Fix Plan — V11 Line

**Status (2026-10-19)**: Implemented in **V11.1 candidate** (`he_star/build/bricking-edge_v11.1/`, `Z_8_0311.bin`, SHA `f25c505d…`, version `03.11.p0`). All four fixes are landed and verified offline. See `scratch/expeed7_v2/100_BUILD_LOG.md` (§ "V11.1 候选") for build logs. References: `126_BOOTLOOP_FORENSICS.md`, `123_T4_CHAIN.md`. Closes [open-items #2–5](open-items.md).

### Summary: Plan vs. Landed

| Fix | Original Plan | Landed Implementation |
|---|---|---|
| **1. Guard bound** | Compare within the same memory region: `bound = file_base + header_len` | Implemented via `end_off = (ptr − base) + size` vs `total = [x25, #0x10]`. Added base underflow check, header-length clamp `[0x80, 2MiB]`, and a `ret`-style skip path for multi-site reuse. |
| **2. Count sources** | Sync all three count sources (grow all to 618, or shrink all to 617). | **Shrank to 617**. Reverted both hardcoded immediates to 617 to match the ROM table. Added static check G3.8 and mutation test M35. |
| **3. Table-boundary write** | Delete the 8B write, or prove a consumer exists. | **Deleted**. Reverted to zeros after static scans, watchpoints, and table cross-checks confirmed zero consumers — the write either hit an alignment gap (harmless) or `rec0`'s pad field, corrupting the record. |
| **4. Walk coverage** | Add bounds check to all 6 loop sites. | **6/6 sites hooked** (L2/LC → `_guard`, L1/LB → `_s28`, LS/L3 → `_s24`). Added xref check G3.6, mutation tests M38/M39, and unit tests — any site left unguarded stays a crash risk. |

---

## Fix 1 — Guard Bound: Compare Within One Memory Region

* **Problem**: The bounds check stub (`0x40967B84`, hooked at `0xF7F9D4`) calculates `bound = x25 + header_len`, where `x25` (`0xA0480dc78`) is the 32-byte header copy. However, the item buffer `x3` points into the file-image buffer (base stored at `*(u64*)0xA0480dc70`). Comparing `item_end <= bound` compares pointers across two different heap allocations. Depending on heap layout, this silently skips all items or allows out-of-bounds reads.
* **Fix**: Calculate the bound using the file-image base: `bound = *(u64*)0xA0480dc70 + header_len`, and clamp `header_len` to `[0x80, 2MiB]`. Keep register contracts (`w9/x9/x10/x16` scratch, `x30` preserved) and fail-safe behavior (skip out-of-range items) unchanged.
* **Verification**:
  1. Unit test: Verify `item_end <= bound` per item on both valid and truncated files.
  2. Static check: Enforce that both comparison operands derive from the same base pointer.
  3. Fault injection: Confirm out-of-bounds directory entries are skipped individually without dropping valid items.
  4. Regression: Pass settings-file suite (R1/R2/R3) and verify binary diff is isolated to the stub.

## Fix 2 — Settings Count: Synchronize All Three Sources

The settings item count is defined in three places:

| Source | Location | Default (Variants 1–4) | V10 State |
|---|---|---|---|
| ROM variant table (R1 load path) | `0x44182f90..0x44182ff0` (S3 at `0x44182fe0`) | 472, 572, 586, **617** | **617** (unchanged) |
| R2 boot registration hardcoded value | VA `0x410e0f04` (Variant 3) | S3 = **617** (COUNT1 1112 / COUNT2 184 / COUNT3 331 / COUNT4 79 / S2 11 / len 340346) | Changed to **618** |
| Save-side immediate | `0xF803D4` | **617** | Changed to **618** |

* **Problem**: V10 updated two sources to 618, while the ROM table and the underlying data arrays (`0x299xxxx`) remained at 617 entries. Loops relying on the 618 count overrun the array by one entry during boot (between R2 and R1) and during save operations.
* **Fix**: 
  * *Option A (Grow)*: Set all three to 618 and extend the underlying data arrays. Requires defining a valid 618th entry.
  * *Option B (Shrink — Landed)*: Revert all three sources to 617. Rely on the Fix 1 guard to handle bounds.
* **Verification**:
  1. Static check: Assert all three count locations have identical values at build time.
  2. Emulator: Verify table walks complete 617 iterations cleanly and the guard rejects a forged 618th item.
  3. Regression: Pass settings suite and verify binary diff is isolated to the count addresses.

## Fix 3 — Table-Boundary 8-Byte Write: Revert

* **Problem**: V10 writes 8 bytes (`00 08 00 00 00 01 00 00`) to `0x4CBC9B8`. This address sits at the boundary between a 628×8B table (`0x4CBB618..0x4CBC9B8`) and a 32-byte record table (`0x4CBC9C0`). It is either unused alignment padding or it overwrites the first record's padding field. Static analysis across all five firmware segments found zero references to this table.
* **Fix**:
  * *Option A (Delete — Landed)*: Revert the 8 bytes to zeros.
  * *Option B (Prove)*: Place watchpoints on `0x4CBC9B8` during save/load cycles. Keep the write only if an active consumer is identified. (Note: Watchpoints and structural cross-checks confirmed 0 hits; Option A was executed).
* **Verification**:
  1. Binary diff confirms the 8 bytes are reverted to zero with no unintended changes.
  2. Build rule: Reject patches that write to unreferenced memory regions.
  3. Regression: Pass settings save/load test suite.

## Fix 4 — Loop Coverage: Guard All Six Walk Sites

The settings apply functions (`0x410E1AA8` and `0x410E1790`) are called from six loops, five of which lacked bounds checks in V10:

| Loop | Hook Site | Target Function | V10 Guard Status |
|---|---|---|---|
| L2 blob (S0/S1) | `0xF7F9D4` | `0x410E1AA8` | Guarded (buggy bound, see Fix 1) |
| LC blob (bank) | `0xF7FBF8` | `0x410E1AA8` | **Unprotected** |
| L1 scalar (S0/S1) | `0xF7F8D4` | `0x410E1790` | **Unprotected** |
| LB scalar (bank) | `0xF7FB2C` | `0x410E1790` | **Unprotected** |
| LS scalar (S2 record) | `0xF7FCA8` | `0x410E1790` | **Unprotected** |
| L3 scalar (S3 bank) | `0xF7FE28` | `0x410E1790` | **Unprotected** |

* **Fix**: Apply the corrected bounds guard from Fix 1 to all six sites. LC shares L2's register convention (`x3` = buffer, `w2` = size, `x25` = header copy, `x30` = LR) and reuses the same stub. The four scalar loops use adapted stubs matching their stride (`4B × count`).
* **Verification**:
  1. Static check: Xref scan must confirm every `bl 0x410E1AA8` and `bl 0x410E1790` call site is hooked.
  2. Emulator & Fault Injection: Confirm forged oversized items are skipped in each of the six loops without affecting subsequent items.
  3. Regression: Full settings suite pass, binary diff check, and boot-path smoke test ([unfreeze-criteria.md](unfreeze-criteria.md) C4).

## Execution Order

1. **Fix 1**: Fix the bounds calculation logic first.
2. **Fix 4**: Deploy the corrected bounds check across all six loop sites.
3. **Fix 3**: Remove the unreferenced 8-byte write.
4. **Fix 2**: Revert the item counts back to 617.

---

## 简体中文

**状态（2026-10-19）**：四项修复均已合入 **V11.1 候选版本**（`Z_8_0311.bin`，SHA `f25c505d…`）并通过离线验证。详细构建记录见 `100_BUILD_LOG.md`，底层分析参考 `126_BOOTLOOP_FORENSICS.md` 与 `123_T4_CHAIN.md`。用于关闭 [open-items #2–5](open-items.md)。

**① 修正边界检查（Guard Bound）的跨区指针比较**（漏防即崩溃风险）
* **问题**：现有边界检查桩代码将 `x25`（`0xA0480dc78` 处的 32 字节文件头副本）加上长度作为上限（`bound`），但实际被检查的数据指针 `x3` 位于文件镜像缓冲区（基址存于 `0xA0480dc70`）。这导致两个不同内存区域的指针直接比较，实际运行结果取决于堆内存分配位置，表现为“全部跳过”或“全部放行”。
* **修复**：统一使用文件镜像基址计算上限：`bound = *(u64*)0xA0480dc70 + header_len`，并将 `header_len` 限制在合理范围 `[0x80, 2MiB]` 内。保持原有的寄存器约定和跳过越界项的容错逻辑不变。
* **验证**：长短文件逐项单元测试；新增静态检查规则（强制比较两端同基址）；故障注入测试（验证越界项被单独跳过）；R1/R2/R3 设置回归测试与二进制差分检查。

**② 统一三处设置项计数（Count）**
* **问题**：设置项总数存在三个数据源：ROM 变体表 `0x44182fe0`（R1 载入用，值为 617）、R2 开机注册硬编码 `0x410e0f04`、以及保存路径立即数 `0xF803D4`。V10 版本仅将后两处改为了 618，而 ROM 表及底层数据数组（`0x299xxxx`）仍为 617 项，导致循环读取时发生单步越界。
* **修复**：
  * *方案 A（扩容）*：三处统一改为 618，并扩充底层数组（需明确第 618 项的数据结构定义）。
  * *方案 B（回退 — 已落地）*：三处全部恢复为 617，依赖修复 ① 的边界检查拦截异常数据。
* **验证**：构建时静态断言三处数值相等；模拟器验证 617 次循环无越界且能拦截伪造的第 618 项；回归测试通过。

**③ 撤销表边界的 8 字节写入**
* **问题**：V10 在 `0x4CBC9B8` 处写入了 8 字节数据，该地址夹在 628×8B 表末尾与 `0x4CBC9C0` 记录表开头之间，可能是对齐空隙，也可能覆盖了首条记录的字段。全固件静态扫描显示该表为 0 引用。
* **修复**：
  * *方案 A（删除 — 已落地）*：将该 8 字节回退清零。（注：经模拟器硬件断点监测及表结构交叉核对，确认无任何代码读取该地址，已执行删除）。
  * *方案 B（取证）*：通过模拟器断点追踪读写操作，确认存在消费者后再保留写入。
* **验证**：二进制差分确认仅回退该 8 字节；新增构建规则“禁止向无明确归属的内存表写入数据”。

**④ 补全其余 5 个循环的边界检查**
* **问题**：调用设置应用函数（`0x410E1AA8` 和 `0x410E1790`）的循环共有 6 处。V10 仅在 L2（`0xF7F9D4`）挂载了检查，其余 5 处——LC（`0xF7FBF8`）、L1（`0xF7F8D4`）、LB（`0xF7FB2C`）、LS（`0xF7FCA8`）、L3（`0xF7FE28`）均无保护。
* **修复**：修复 ① 完成后，将边界检查挂载到全部 6 个循环。LC 与 L2 寄存器约定相同，直接复用同一桩代码；其余 4 个标量循环按各自步长（`4B × count`）适配检查逻辑。
* **验证**：新增交叉引用（xref）静态扫描，漏挂任何一处即拒绝构建；针对每个循环做超长项跳过测试；由于修改位于开机必经路径，需逐字节审查汇编并完成 C4 冒烟测试。

**执行顺序**：①（修复计算逻辑）→ ④（铺开到所有循环）→ ③（清理无用写入）→ ②（回退计数至 617）。
