# Risks, Post-Mortems, and Rollback

This project modifies camera firmware. **A bad build can permanently brick your camera.** 

During development, the V10 build bricked a test camera even though all offline checks passed. Software recovery failed, and the unit had to be sent to Nikon for repair. If you rely on your camera, use official firmware.

---

## Known Broken Builds

### Known unsafe: V11.1 (2026-10-19)
* **Status: ⛔ UNSAFE (已知缺陷 / known defects) — DO NOT FLASH（勿刷）.** Broken (pre-capture silently fails). Does not brick the camera, but breaks functionality.
* **Fix status:** Fixed in **V12** (`bcf5c47f…`, `03.11.p1`, formerly V11.2), which adds self-healing for sticky files and status reporting. V12 passes all offline tests but has **not** been tested on hardware yet.

#### Bug Details: Silent Pre-Capture Failure
In V11.1, the pre-capture retention function (`precapture_tdec_release`, called on every HSFC Tdec release) only saves frames if three card-side checks pass. If any check fails, it silently drops the pre-capture frames (`keep=0`) with no error or UI indicator:

| Check | Failure Condition |
|---|---|
| 1. Dual-config check | Both cards have a valid `Z8PRE.CFG`, or neither does (`a == b`). |
| 2. STP sticky file | `Z8PRESTP.BIN` exists on the card. The firmware **never retries or deletes** this file. |
| 3. Config validation | Any mismatch in magic v4, flags, grade, CRC, or reserved bytes marks the card as unconfigured, triggering Check 1. |

**Impact:**
* **Failures are completely silent.** The camera appears to work normally while dropping all pre-capture data.
* **Persistent across reboots.** The camera itself stores no persistent state for this (the 120s freshness timer resets on reboot). If the bug persists across reboots or card swaps, it is caused by leftover files on the card (`Z8PRESTP.BIN`, duplicate configs, or corrupted configs).

**Test Coverage:**
Offline tests now cover multi-source consistency (G3.9), stub behavior (G3.10), and memory bounds (G4.6). However, card-filesystem state (Check 2) cannot be tested statically; full reproduction in the emulator (G-EMU-C) is still pending filesystem driver support. 

*(References: `141_GEMUC_C2_VERDICT.md` §0/§1/§3, `138_DETECTION_VALIDATION.md` §4.3/§8)*

### 中文说明：V11.1 已知缺陷

* **状态**：**V11.1 存在功能缺陷，请勿刷入**（不会变砖，但会导致预拍功能静默失效）。
* **修复进展**：**V12**（原 V11.2，`bcf5c47f…`，`03.11.p1`）已修复此问题（增加 STP 残留文件自愈与状态可见性），离线测试全过，但**尚未上机实测**。
* **缺陷机制（预拍静默失效）**：预拍保留函数（`precapture_tdec_release`）在每次释放时检查存储卡状态。以下任一条件触发即静默丢弃预拍画面（`keep=0`，无报错）：
  1. **双卡配置冲突**：两张卡同时存在有效 `Z8PRE.CFG`，或同时没有。
  2. **STP 文件残留**：卡上存在 `Z8PRESTP.BIN`（固件不会重试或清理该文件）。
  3. **配置校验失败**：`Z8PRE.CFG` 的 magic v4、flags、grade、CRC 或保留区校验不通过，直接退回条件 1。
* **表现**：除预拍不保存外，相机一切显示正常。相机端无持久化状态（120 秒计时器重启即清零），若换卡或重启后依然失效，说明卡上仍有残留文件或配置错误。
* **测试盲区**：离线工具已补齐 G3.9 / G3.10 / G4.6 检测，但存储卡文件状态无法通过静态检查覆盖，模拟器完整复现（G-EMU-C）仍待完成。

---

## Incident Post-Mortem: V10 Boot Loop (2026-10)

### What Happened
1. The V10 build passed all offline verification checks (byte-level diff, 33 checkpoints, 34 mutation tests, 17 combination tests, and reproducible build verification).
2. Upon flashing to a test camera, the bootloader started and powered the display, but the camera crashed during application init and entered a permanent boot loop.
3. All software recovery methods (card recovery files, button combos, service modes, USB) failed. The camera was sent to Nikon for repair.

### Root Cause (Confirmed 2026-10-19)
Offline forensics and RAM inspection (`136_CRASH_VERDICT.md`) pinned the crash to an out-of-bounds read/write during the settings load loop:

* **The Bug:** V10 increased two immediate values for the S3 settings slot count from `617` to `618`, while the underlying backing table and ROM variant table remained at `617` entries.
* **The Crash:** The settings loader (`0x410DF358`, loop `0x410DFD98..0x410DFE4C`) iterates one element past the end of the table. The first out-of-bounds read occurs at `0x410DFDF8` (`ldrb w11,[x10,#5]`, reading `0xA029B1BB8+5`), followed by `0x410DFE10` (`ldr w1,[x9,x29]` with offset `0x1348` = 617×8), feeding garbage into the apply function at `0x410E1790`.
* **Why it varies by layout:** Because this is an out-of-bounds access, whether it crashes immediately or silently corrupts memory depends on the heap/memory layout. **A V10 build that doesn't crash on one specific setup is still corrupting memory.** Never flash V10 or earlier builds.

| Reference | Details |
|---|---|
| Source Document | `136_CRASH_VERDICT.md` §0 (SHA-256: `465a8885bbfc2bea7eea3375be7021e37e14fe09e66fc33d3a34813839ca9f2e`) |
| Key Offsets | Loader: `0x410DF358` \| Loop: `0x410DFD98..0x410DFE4C` \| OOB Read: `0x410DFDF8`, `0x410DFE10` \| Apply: `0x410E1790` \| Other audited sites: `0xF7F9D4`, `0xF803D4`, `0xF80F68`, `0x4CBC9B9`, `0x4CBC9BD`, `0x44182FE0`, `0x410E0F38`, `0x40874284`, `0x4086871C` |
| Other V10 Issues | 1. An unverified write at the boundary of an unreferenced table.<br>2. A load-time bounds check that compared addresses across two different memory regions, rendering the check ineffective. |
| Emulator Status | Static and RAM structure proof is complete. Dynamic crash reproduction in QEMU requires stubbing the filesystem read context to feed the 98-byte settings payload, followed by `--poison-at` at the table tail. |

*(Note: A similar post-flash failure was reported on an independent Z8 project. See [upstream-issue-3.md](upstream-issue-3.md) for comparison.)*

### V10 Crash Fixes (Landed in V11.1+)
Build `bricking-edge_v11.1` (`f25c505d…`, `03.11.p0`) and later builds land the four fixes of [c2-fix-plan.md](c2-fix-plan.md): revert the slot count back to `617`, remove the unowned table write, and fix the bounds checks across all six walk sites (enforcing same-base comparisons and header-length clamps).

## C1 evidence slot

Status: **filled 2026-10-19 from the crash verdict record**, mechanically by `tools/fill_c1.py`. The verdict arrived from the crash-forensics workstream (evidence chain `126_BOOTLOOP_FORENSICS.md` → `132_Z9QEMU_PORT.md` → `134_EXPLOIT_TESTBED.md` → `136_CRASH_VERDICT.md` §0) and is copied here **verbatim, with its anchors**.

| Field | Value |
|---|---|
| Verdict | **是它。** v10 真机 boot loop 的炸点 = **S3 槽计数 618/617 越界**：v10 的两个计数立即数把注册计数改成 618，而背衬表/ROM 变体表仍是 617 ⇒ 设置装载走查环多走 1 项，越界读写紧邻对象。**炸点函数 = 设置装载走查环**（装载器 `0x410DF358` 内 `0x410DFD98..0x410DFE4C`）；**第一口越界 = `0x410DFDF8`**（`ldrb w11,[x10,#5]`，元素 `0xA029B1BB8+5`），紧随 `0x410DFE10`（`ldr w1,[x9,x29]`，x29=`0x1348`=617×8），下游 apply `0x410E1790`。**形态 = 布局相关的越界 UB** ⇒ 真机炸、模拟器默认布局不炸，不矛盾；v11 撤掉两个计数即根除（运行态已验：617 与表一致）。**置信度**：机理 A 级（字节+运行态 RAM 直接观测）；受害者 PC 指令级 A 级（结构+唯一消费者），动态复现见 §2（布局毒化）。 |
| Evidence grade | A (bytes / disassembly measured) |
| Record anchor | `136_CRASH_VERDICT.md` §0 终审判词, sha256 `465a8885bbfc2bea7eea3375be7021e37e14fe09e66fc33d3a34813839ca9f2e` |
| Code anchors | `0x410DF358`; `0x410DFD98`; `0x410DFE4C`; `0x410DFDF8`; `0xA029B1BB8`; `0x410DFE10`; `0x1348`; `0x410E1790`; `0x410DFE1C`; `0x410DFE24`; `0xF7F9D4`; `0xF803D4`; `0xF80F68`; `0x4CBC9B9`; `0x4CBC9BD`; `0xA04812848`; `0xA04812850`; `0xA029B0670`; `0x44182FE0`; `0x410E0F38`; `0xA047E6B3C`; `0x40874284`; `0x40001000`; `0xA04842160`; `0x40FFFFFF`; `0x4086871C`; `0x410DF3F8`; `0x410DF4F4` |
| Delta exhaustion | present in `136_CRASH_VERDICT.md` §3 (8 lines), method named per line |
| Hardware reproduction | no — the dynamic re-run in the emulator is stuck at the file-read step (synthetic card + a forced-open gate is not the real file-service context) |
| What stays unproven | let a real FS read hand over the 98-byte settings body (~0.5–1 person-day: patch the `FS_open` call site / file-object context, or use `--skipcall` to force the fd), then `--poison-at` the list tail to make the overrun visible |
| Filled by / date | 2026-10-19, copied verbatim by `tools/fill_c1.py` |

Filling rules: copy the verdict, never paraphrase it into something stronger — `tools/fill_c1.py` copies it verbatim and refuses while any field is missing. A verdict graded B or C is recorded here but does **not** meet C1 of [unfreeze-criteria.md](unfreeze-criteria.md). Anchors must be checkable from this repository plus the local evidence. The delta-exhaustion line is mandatory: a verdict that leaves another delta window unexcluded is a hypothesis, and hypotheses live in [upstream-issue-3.md](upstream-issue-3.md), not here.

---

## General Risks

| Risk | Details |
|---|---|
| **Permanent brick** | **Has happened.** If the camera crashes before USB or card recovery initializes, only Nikon service can fix it. |
| **Data loss / Card corruption** | Firmware writes custom files to the card. Always use a blank, expendable test card. |
| **Silent malfunctions** | UI indicators, metadata, or camera settings may behave incorrectly without throwing errors. |
| **Third-party software issues** | Output files are not tested against Lightroom, Adobe Camera Raw, or NX Studio. |
| **No guaranteed downgrade** | Flashing back to stock firmware only works if the camera can still boot into the firmware updater. |

## Build Safety Checks

The build scripts cannot guarantee that the firmware logic is safe to run on a camera. They only ensure the binary is built reproducibly without unintended byte changes:

* **Input verification:** Checks SHA-256 hashes of the base firmware before patching.
* **Strict compilation:** Patched code must compile to exact, pre-reviewed byte sequences.
* **Independent diffing:** A separate verifier checks that zero bytes were altered outside the declared patch regions.
* **Automated mutation tests:** The test suite injects faults into the build to verify that the checker catches them.
* **No overwrites:** Build outputs always go to a new directory; source files are never modified.

## Rollback Procedure

If a build misbehaves while the camera is still able to boot:

1. **Stop testing immediately.** Turn off the camera.
2. **Download and verify official Nikon Z8 firmware 3.11:**
   ```bash
   shasum -a 256 Z_8_0311.bin
   # Must match: d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96
   ```
3. **Remove custom config files** (`Z8PRE*.CFG`, `Z8OG.CFG`) from your memory cards. Deleting these disables the custom hooks that rely on them.
4. **Reflash the official `Z_8_0311.bin`** using the standard camera firmware update menu.
5. If the camera does not boot far enough to reach the update menu, software recovery is not possible.

## Disclaimer

This software is provided "as is", without warranty of any kind. The authors and contributors are not liable for bricked cameras, repair costs, data loss, or any other damages resulting from this repository. See [NOTICE.md](../NOTICE.md) and [LICENSE](../LICENSE). This project is not affiliated with Nikon.

---

## 简体中文总结

* **核心警告**：刷入修改版固件最坏会导致相机**彻底变砖且无法通过软件救回**。开发中 V10 版本在离线测试全绿的情况下依然把一台测试机**刷砖**（陷入开机循环），最终只能送修。需要稳定工作的相机请使用官方固件。
* **V10 变砖原因（已查明，判词见 [risks.md#c1-evidence-slot](risks.md#c1-evidence-slot)）**：V10 将设置项计数从 `617` 改为 `618`，但底层数据表长度仍为 `617`，导致开机加载设置时发生数组越界读写（位于 `0x410DF358` 循环内的 `0x410DFDF8`）。越界后果取决于当时内存布局，可能直接崩溃，也可能静默写坏内存。**严禁刷入 V10 及更早期的构建版本。**
* **V11.1 状态（不安全 / UNSAFE，勿刷、请勿刷入）**：V11.1 修复了 V10 的越界崩溃，但存在**预拍功能静默失效**的缺陷（详见 [risks.md#known-unsafe-v111-2026-10-19](#known-unsafe-v111-2026-10-19)）。修复该问题的 **V12** 版本已通过离线测试，但尚未进行真机测试。
* **其它风险**：照片丢失、存储卡损坏、相机功能静默异常、第三方后期软件（LR/ACR/NX Studio）不兼容、变砖后无法降级。测试请务必使用空卡、废卡。
* **构建检查的作用**：仓库内的校验工具只能确保“编译出的二进制字节与预期完全一致”（校验原始固件哈希、独立检查修改区间、自动变异测试），**离线测试全绿不代表上机不会变砖**。
* **回退方法**：若出现异常且相机仍能开机，请立即停用，删除存储卡上的 `Z8PRE*.CFG` 和 `Z8OG.CFG`，校验官方 03.11 固件哈希（`d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96`）后重刷官方固件。若无法进入开机菜单，则只能送修。
* **免责声明**：本项目按“原样”提供，作者不对相机损坏、维修费用或数据丢失承担任何责任。详见 [NOTICE.md](../NOTICE.md) 与 [LICENSE](../LICENSE)。本项目与尼康（Nikon）无关。
