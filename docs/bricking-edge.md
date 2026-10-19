# The `bricking-edge` Branch (V11 / V12)

This branch is the hotfix and investigation line created after the V10 build bricked a test camera in a boot loop (see [risks.md](risks.md)).

**Root Cause (2026-10-19):** The V10 crash is caused by an out-of-bounds read during the settings-load walk, where the S3 slot count was increased to 618 while the backing table remained at 617 entries (see [risks.md#c1-evidence-slot](risks.md#c1-evidence-slot)). Reverting the two count immediates to 617 resolves the issue and restores stock behavior. Branch unfreeze criteria are tracked in [unfreeze-criteria.md](unfreeze-criteria.md).

## Files and Workflow

* `recipes/revert_v10_tails.py`: Takes a local V10 build and a previous build, reverts four suspect byte windows to their previous values, rebuilds the checksum chain, and verifies that the binary diff against V10 is strictly confined to those four windows and the checksum.
* `docs/bricking-edge.md`: Documentation for this branch.

Both files are tracked on `main` for visibility. Active development for the V11/V12 line takes place on the `bricking-edge` branch.

## Reverted Byte Windows (V11 Initial Trial)

`recipes/revert_v10_tails.py` reverts the following changes from V10 while leaving all other bytes (including the recompiled code blob) untouched:

| Payload Offset | Bytes | Reverted Change | Technical Reason |
|---|---|---|---|
| `0xF803D4` | 4 | Settings count immediate (`617` → `618`) | Conflicts with the 617-entry backing table, causing any traversal relying on this count to overrun by one entry. |
| `0xF80F68` | 4 | Settings count immediate (`617` → `618`) in boot registration | Runs during application initialization, directly in the path where the boot loop occurs. |
| `0x4CBC9B8` | 8 | Settings-table tail write | Sits on the boundary between two adjacent tables. Static analysis found zero code references to this address, leaving table ownership unresolved. |
| `0xF7F9D4` | 4 | Load-time bounds guard hook | Computes its bound across two different memory regions, causing it to silently skip or allow all entries. |

## Build History and Status

None of the builds on this branch has ever been on hardware (**never on hardware**). Toolkit tags contain build scripts and verification objects only — still no firmware here.

| Version | Build / Tag | SHA-256 (`Z_8_0311.bin`) | Status & Changes |
|---|---|---|---|
| **V12** *(formerly V11.2)* | `bricking-edge_v11.2_p1`<br>Tag: `toolkit-20261020`<br>ID: `03.11.p1` | `bcf5c47f5aedd873d7292381ea747d7f794c634dbf628ba5272a8ae2c5d9fb03` | **Experimental (Untested on hardware).**<br>• Fixes V11.1 three-state gate defects: adds STP sticky-file self-healing (session latch + evidence preservation) and gate-loss observability (readable status block with landing codes and per-gate counters).<br>• Retains all four V11.1 fixes (byte-verified unchanged).<br>• Passed all offline checks (gates 7/7, mutations 44/44, combinations 17/17, structural 4/4, three-state behavior 19 vectors / 33 checks). |
| **V11.1** | `bricking-edge_v11.1`<br>Tag: `toolkit-20261019`<br>ID: `03.11.p0` (packaged as `03.11.p1`) | `f25c505d0daf9b1f16e345d10d5e82e85b8e8a77d0e4a89153620d5f77e7251a` | **⛔ UNSAFE — Do Not Flash** (see [risks.md](risks.md#known-unsafe-v111-2026-10-19); superseded by V12).<br>• Landed the four C2 fixes: reverted all three count sources to 617, removed the unowned table write, clamped 6/6 walk sites, and fixed the guard to use a same-base address with a header-length clamp.<br>• Passed offline checks (39/39 mutations, reproducible build). Untested on hardware. |
| **V11 (Trial)** | Local trial only | `0da2b2b0…` | **Deprecated.** Initial local output of `revert_v10_tails.py`. Byte-verified against V10, never packaged or released. |

## Technical Checklist for Unfreezing

The following issues identified during the V10 investigation govern the fixes in V11.1/V12 (see [unfreeze-criteria.md](unfreeze-criteria.md) for full criteria):

1. **Guard bounds calculation:** The load-time guard bound must be computed within the same memory region rather than across two different regions. *(Addressed in V11.1)*
2. **Settings count synchronization:** The settings count is defined in three places (ROM variant table, hard-coded registration, and save-side immediate). All three must be updated together or kept at 617. *(Reverted to 617 in V11.1)*
3. **Table-boundary write ownership:** Determine which table owns `0x4CBC9B8` and whether any code consumes it, or remove the write. *(Write removed in V11.1)*
4. **Secondary code path protection:** The second code path reaching the apply function requires its own guard point. *(6/6 walk sites clamped in V11.1)*
5. **Root-cause confirmation:** Confirm the exact faulting mechanism from V10. *(Confirmed on 2026-10-19 as the 618/617 S3 slot count overrun).*

For build and verification instructions, see [build.md](build.md) and [verification.md](verification.md).

---

## 简体中文

本分支为针对 V10 开机循环故障设立的热修与问题排查分支（详见 [risks.md](risks.md)）。

**根因结论（2026-10-19）：** V10 的崩溃点位于加载设置时的 S3 槽位遍历逻辑。计数值被改为 618，而底层表实际只有 617 项，导致读取越界（属内存布局相关的未定义行为，详见 [risks.md#c1-evidence-slot](risks.md#c1-evidence-slot)）。将两处计数立即数回退至 617 即可修复该问题，并与 V9 及官方固件保持一致。分支解冻条件见 [unfreeze-criteria.md](unfreeze-criteria.md)。

### 相关文件

* `recipes/revert_v10_tails.py`：回退脚本。读取本地 V10 构建与上一版构建，将 4 个可疑字节窗口回退至上一版数值，重建校验和链，并严格校验除上述窗口和校验和外无任何其他字节变动。
* `docs/bricking-edge.md`：本说明文档。

上述文件同步保留在 `main` 分支以便查阅；V11/V12 的实际修改均提交在 `bricking-edge` 分支。

### 版本与构建状态

本分支的所有构建**从未上机**。发布的 `toolkit` 标签仅包含构建与校验工具——本仓仍不含固件。

* **V12（原 V11.2，`bricking-edge_v11.2_p1`）**
  * **状态：** 试验性发布（Tag: `toolkit-20261020`，身份标识 `03.11.p1`，SHA-256: `bcf5c47f...`），**未上机测试**。
  * **改动：** 修复了 V11.1 的三态门缺陷，新增 STP 粘性文件自愈（含会话闩锁与现场保留）及失守状态可观测性（可读状态块，含落点码与分门计数器）；完整保留 V11.1 的四项修复（字节级比对无变动）。
  * **离线测试：** 全部通过（门禁 7/7、变异测试 44/44、组合测试 17/17、结构检查 4/4、三态门行为回归 19 向量 / 33 项检查）。
* **V11.1（`bricking-edge_v11.1`）**
  * **状态：** **⛔ 不安全，勿刷**（存在已知三态门缺陷，详见 [risks.md](risks.md#known-unsafe-v111-2026-10-19)，已被 V12 替代）。Tag: `toolkit-20261019`，构建标识 `03.11.p0`（封包标识 `03.11.p1`），SHA-256: `f25c505d...`，**未上机测试**。
  * **改动：** 落地 C2 四项修复——三处计数源统一回退至 617、删除无引用表尾写入、6 处遍历点全部加上边界钳制（clamp）、修复 guard 为同基址比较并加上头部长度钳制。
  * **离线测试：** 门禁测试与 39/39 变异测试通过，构建可复现。
* **V11（初始本地试验）**
  * **状态：** 已废弃（SHA-256: `0da2b2b0…`）。仅在本地通过 `revert_v10_tails.py` 生成过一次，完成字节级比对，未打包发布。

### 关键修复项清单

针对 V10 排查出的以下问题已在 V11.1 / V12 中处理（完整解冻标准见 [unfreeze-criteria.md](unfreeze-criteria.md)）：

1. **修复 Guard 边界计算：** 必须在同一内存区域内计算边界，避免跨区比较导致检查失效。
2. **统一三处设置项计数：** ROM 变体表、硬编码注册路径与保存侧立即数必须同步修改（已统一回退为 617）。
3. **清理表边界写入：** `0x4CBC9B8` 处的 8 字节写入无任何代码引用（已删除）。
4. **补全次要路径防护：** 到达设置应用函数的第二条代码路径及全部 6 处遍历点均需加上边界检查。
5. **确认崩溃根因：** 已于 2026-10-19 确认为 S3 槽位计数 618/617 越界；后续仅剩线下注入崩溃测试（约 0.5–1 人日）待完成。

构建与校验步骤见 [build.md](build.md) 与 [verification.md](verification.md)。
