# Symptom Comparison: V10 Boot Loop vs. Upstream Issue #3

This document compares two Nikon Z8 modified firmware failures that occurred on different builds:

- **This repository (V10 build, `03.11.p0`)**: Boot loop on a test camera (see [risks.md](risks.md)).
- **Upstream ([XinmiaoZhao/NikonFirmwarePatch Issue #3](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/3), `04.03.p0`)**: Opened 2026-10-18. Reports one camera where RAW pre-capture permanently stopped working after reinserting the memory card, and a second camera that failed to boot after flashing.

We are not affiliated with that project. The comparison is strictly at symptom level, taken from the public issue text as of 2026-10-19. **No firmware, builds, or files were exchanged** between the two situations, and nothing from that project is reproduced here beyond the linked public report.

## Upstream Timeline

| Date | Event |
|---|---|
| 2026-10-17 | Upstream releases toolkit `v0.1.0` (source + 30,301-byte precompiled binary `479f4e37…` + validation scripts). Their precompiled-distribution model is close to our own [release plan](release-packaging.md): same trade-off, decided independently. |
| 2026-10-18 | Issue #3 opened: one camera fails to boot after flashing; another permanently loses RAW pre-capture after a card change. |
| 2026-10-18 | [Upstream validation update](https://github.com/XinmiaoZhao/NikonFirmwarePatch/blob/main/docs/validation.md):<br>1. **Hardware test**: The maintainer's Z8 booted `04.03.p0` normally, handled card hot-plugging without issue, and enabled pre-capture via a CFG card. The reporter's source-built binary matched the maintainer's precompiled binary byte-for-byte.<br>2. **QEMU test**: Official firmware and three patched builds reached the shooting menu in QEMU (proves basic execution, but does not test flash routines, boot ROM, or persistent NVRAM state). |

**Current status (as of 2026-10-19)**: The boot failure was not reproduced on the maintainer's hardware. Root cause, recovery methods, and the persistent pre-capture failure remain unresolved. The affected camera's flash has not been dumped.

## Comparison

| | Upstream Issue #3 (`04.03.p0`) | Our V10 Incident (`03.11.p0`) |
|---|---|---|
| **Hardware** | Nikon Z8 (2 units) | Nikon Z8 (1 test unit) |
| **Base Firmware** | `Z_8_0403.bin` (C 4.03) | `Z_8_0311.bin` (C 3.11) |
| **Modified Features** | ProRes + C15/C30 HE RAW pre-capture | ProRes + pre-capture + OpenGate + menu group + settings table |
| **Offline Checks** | Passed | Passed |
| **Boot Failure** | Unit 2: Fails to boot after flashing | Boot loops (display turns on, loader runs, crashes during app init, restarts) |
| **Config/Card Failure** | Unit 1: Pre-capture stops working after removing the card; persists across card swaps, formatting, and rewriting `Z8PRE.CFG` | Not observed |
| **Trigger** | Flashing + card removal/reinsertion | First boot after flashing (with settings and config files on the card) |
| **Recovery** | Unknown | Software recovery failed; sent to service center |

## Common Factors

1. **Offline checks passed**: Static verification only confirms that patches were applied as written; it does not catch runtime initialization bugs.
2. **Same failure stage**: Both builds crash or hang during application-level initialization.
3. **Overlapping code areas**: Both patches modify pre-capture logic and config/settings file handling.

## Bugs Found in Our V10 Build

Analysis of our V10 binary identified three specific defects in the settings-handling code that explain these types of symptoms:

1. **Settings table count mismatch (buffer overrun)**: We increased the settings count from 617 to 618 in two places (ROM variant table and hardcoded registration), but missed the third (the backing table itself remained at 617 entries). Any routine iterating over the table using the updated count reads or writes one entry out of bounds, corrupting memory at boot.
2. **Broken bounds check on settings load**: A bounds guard compared the end of a settings item against a limit calculated from a different memory region. Depending on where the file buffer is allocated in RAM, the check silently skips all entries or allows all entries. If it skips all entries, **config files on the card are permanently ignored**—matching the symptom on Upstream Unit 1.
3. **Write to an unreferenced table boundary**: We modified the end of a table that has zero code references in the firmware. If an adjacent table is read during startup, this write corrupts its data.

## Troubleshooting Steps for Similar Symptoms

1. **Test without card files**: Boot the camera with a blank card (no settings file, no `.CFG` file), then test with each file individually to isolate file-parsing bugs without rebuilding firmware.
2. **Bisect builds**: Roll back patch versions one change at a time to isolate the breaking commit.
3. **Audit table counts**: Search the patch set for hardcoded count immediates and verify that every reference matches the actual size of the underlying data table. Off-by-one overruns pass all checksum and packaging checks.
4. **Inspect load-path bounds checks**: Verify how the settings loader handles files that are shorter or longer than expected, and ensure pointer comparisons happen within the same memory region.
5. **Check persistent state**: When a feature breaks after a card swap and formatting the card does not fix it, the corruption is in the camera's persistent state (NVRAM settings, counters, or caches), not the card file.

---

## 简体中文

本文对比两起尼康 Z8 修改版固件故障：
- **本仓库（V10 构建，`03.11.p0`）**：测试机无限重启（详见 [risks.md](risks.md)）。
- **上游仓库（[XinmiaoZhao/NikonFirmwarePatch Issue #3](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/3)，`04.03.p0`）**：2026-10-18 提交。一台机器在拔插存储卡后 RAW 预拍永久失效；另一台刷机后无法开机。

### 上游进展记录

| 日期 | 事件 |
|---|---|
| 2026-10-17 | 发布 `v0.1.0` 工具包（含源码、30,301 字节预编译机器码 `479f4e37…` 及校验脚本）。 |
| 2026-10-18 | Issue #3 提交：一台刷后不开机，另一台换卡后预拍永久失效。 |
| 2026-10-18 | [上游更新验证文档](https://github.com/XinmiaoZhao/NikonFirmwarePatch/blob/main/docs/validation.md)：<br>1. **实机测试**：维护者自己的 Z8 刷入 `04.03.p0` 后开机正常，换卡（含热插拔）无异常，可通过 CFG 卡启用预拍。反馈者自行编译的固件与维护者预编译版本逐字节一致。<br>2. **QEMU 测试**：原厂固件与三个修改版均可在 QEMU 中进入拍摄菜单（仅证明基础逻辑可运行，无法验证刷写流程、Boot ROM 及 NVRAM 持久化状态）。 |

**当前状态（截至 2026-10-19）**：维护者实机未复现不开机故障。故障根因、恢复方法及换卡后预拍失效的原因均未查明，故障机尚未读回闪存数据。

### 故障对比

| | 上游 Issue #3 (`04.03.p0`) | 本仓 V10 事故 (`03.11.p0`) |
|---|---|---|
| **设备** | 尼康 Z8（2 台） | 尼康 Z8（1 台测试机） |
| **基础版本** | `Z_8_0403.bin` (C 4.03) | `Z_8_0311.bin` (C 3.11) |
| **修改内容** | ProRes + C15/C30 HE RAW 预拍 | ProRes + 预拍 + OpenGate + 菜单组 + 设置表 |
| **离线校验** | 全部通过 | 全部通过 |
| **启动故障** | 机器 2：刷机后无法开机 | 无限重启（屏幕亮、Loader 存活，在应用层初始化阶段崩溃重启） |
| **配置/卡故障** | 机器 1：拔卡后预拍失效；换卡、格卡、重写 `Z8PRE.CFG` 均无法恢复 | 未出现 |
| **触发条件** | 刷机 + 拔插卡操作 | 刷机后首次开机（卡内含设置文件与配置文件） |
| **恢复情况** | 未知 | 软件恢复失败，已送修 |

### 共同特征

1. **离线校验全部通过**：离线检查只能验证补丁是否按预期写入，无法发现运行时的初始化崩溃。
2. **故障阶段相同**：均在固件的应用层初始化阶段崩溃或卡死。
3. **修改区域重合**：两者的补丁都改动了预拍逻辑与配置文件（Settings/CFG）读取链路。

### 本仓 V10 查明的具体缺陷

在对 V10 固件的逆向排查中，我们在设置处理链路里定位了三个具体 bug，可解释上述同类症状：

1. **设置表计数不匹配（越界读写）**：设置项总数在固件中有三处定义（ROM 变体表、硬编码注册处、保存逻辑的立即数）。我们只将前两处从 617 改成了 618，底层数据表实际仍为 617 项。任何按新计数遍历该表的代码都会越界 1 项，导致开机内存损坏。
2. **配置加载路径的边界检查（Bounds Guard）失效**：边界检查将配置项的结束地址与另一个内存区域的指针进行了跨区比较。根据文件缓冲区在内存中分配位置的不同，该检查会静默“跳过所有配置项”或“放行所有配置项”。一旦触发全跳过，**无论卡里放什么配置文件都不会生效**——这与上游机器 1 的症状完全吻合。
3. **写入了无引用的表边界**：我们修改了一个在全固件中没有任何代码引用的表末尾。如果相邻的数据表在开机时被读取，该写入就会破坏相邻表的数据。切勿写入无法证明归属的表。

### 同类故障排查建议

1. **拔卡/清空文件测试**：先用空卡（不放设置文件和 `.CFG` 文件）开机，再逐个放入文件测试。无需重新编译即可快速确认是否由文件解析触发。
2. **按版本二分回退**：按构建历史逐个版本回退，每次只保留单一变量，定位引入问题的具体改动。
3. **核对所有表计数立即数**：扫描补丁中所有的计数立即数，确保它们与底层数据表的实际大小、以及固件内其他引用点完全一致。差一错误（Off-by-one）无法被校验和或打包脚本检出。
4. **审查加载路径的边界检查**：检查设置文件加载代码如何处理过短或过长的文件，确认指针比较是否在同一内存区域内进行。
5. **排查机身持久化状态**：“刷机后正常、拔卡后永久失效且格卡无效”，说明损坏发生在机身持久化状态（NVRAM 设置项、计数器或缓存）中，而非存储卡文件本身。
