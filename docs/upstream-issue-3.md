# Same-family symptoms: our V10 boot loop vs upstream Issue #3

This page compares two independent incidents involving modified Nikon Z8 firmware that occurred within one day of each other on different builds:

- **ours**: the V10 build of this repository — boot loop on a test camera (recorded in [risks.md](risks.md));
- **upstream's**: [XinmiaoZhao/NikonFirmwarePatch Issue #3](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/3), "[Critical] Z8 C 4.03: RAW pre-capture stops working after card reinsertion; another camera fails to boot", opened 2026-10-18, still open with no replies as of 2026-10-19.

We are not affiliated with that project. The comparison below is strictly at symptom level, taken from the public issue text as of 2026-10-19. No firmware, builds, or files were exchanged between the two situations, and nothing from that project is reproduced here beyond the linked public report.

## Side by side

| | Upstream Issue #3 (their C 4.03 build) | Our V10 incident (`03.11.p0` build) |
|---|---|---|
| Camera | Nikon Z8, two units | Nikon Z8, one test unit |
| Build identity | `Z_8_0403.bin`, C 4.03 | `Z_8_0311.bin`, identity `03.11.p0` |
| Feature set | ProRes + C15/C30 HE RAW pre-capture | ProRes + pre-capture + OpenGate + menu group, plus settings-table changes |
| Pre-flash checks | Their independent offline verification passed | Our full offline battery passed, twice |
| Boot symptom | Second camera **fails to boot** after flashing | Camera **boot loops**: display on, loader alive, crash during application initialisation, restart |
| Other symptom | First camera: pre-capture worked, then after removing the card it **could not be re-enabled**; survived card swap, formatting and rewriting `Z8PRE.CFG` | Not observed |
| Trigger | Flashing + card operations | Immediately at first boot after flashing, with a settings file and config files on the card |
| Recovery | Not stated in the issue | Software recovery attempts failed; unit sent for service |
| Forensics | None published | Partial: three suspect changes identified, one overrun mechanism proven; the faulting point on hardware is **not** identified |

## What the two incidents have in common

1. **The build passed every offline check before it was installed.** Both cases prove the same rule: offline verification shows the bytes match the recipe, not that the camera survives running them.
2. **The failure class is the same.** A modified Z8 firmware reaches application initialisation and does not get through it. Whether the report says "won't boot" or "boot loop" depends on how far execution progressed and who is watching the screen.
3. **Both feature sets touch the same area.** Pre-capture and settings-file handling are in both builds. Our work on settings-count registration and the settings-file load path is exactly the area where our forensics found a proven defect (below).
4. **Both incidents recommend the same discipline**: stop flashing, and isolate the trigger with one variable at a time.

## What our forensics found (transferable hypotheses)

These are our findings on **our** build. They are hypotheses for anyone debugging a similar symptom, not conclusions about anyone else's code.

1. **Count vs backing table mismatch (proven mechanism in our build).** We raised a settings count from 617 to 618 in two places while the backing table stayed at 617. Any walk that trusts the count overruns by one entry. The count has **three** sources of truth in our target (ROM variant table, hard-coded registration, save-side immediate) and we had updated only two. Symptom class: memory corruption at boot, or silent misbehaviour in anything that walks that table.
2. **A load-time bounds guard that cannot crash but can do nothing.** Our guard compared an item end against a bound computed from a different memory region. Depending on where the file buffer lands, it either skips every entry or allows every entry — silently. Symptom class: a settings item that is **never applied again, no matter what file you feed it**, which matches what Issue #3's first camera describes after the card was removed. We do not claim that is their cause; we claim it is the first thing we would check.
3. **A write at a table boundary whose ownership was never closed.** Zero code references to that table anywhere in the package. If a table adjacent to it is consumed at boot, this is a plausible fault. Lesson: do not write into a table you cannot prove ownership of.
4. **A clean exclusion matters as much as a suspicion.** One of our suspect stubs was inspected instruction by instruction and ruled out (no undefined pointer dereference, register contract intact). Excluding it narrowed the search instead of widening uncertainty.

## Practical steps we would take on a symptom like Issue #3

1. **Zero-build discriminant first.** Boot the camera with no settings file and no config file on the card; then with each file alone. One minute of testing, no rebuild, and it cuts the trigger surface in half.
2. **Bisect by build generation**, oldest to newest, keeping one variable per step. For us the ladder was V10 → hotfix → V9 → V8 → …
3. **Scan the patch set for count immediates** (settings counts, table lengths) and check each one against its backing table and every other source of truth. A one-entry overrun is invisible to checksums and to every offline gate.
4. **Read any bounds guard on the settings load path** and ask what happens when the file is shorter or longer than expected. "Skip everything" and "allow everything" are both wrong and both silent.
5. **Treat "works after flashing, stops after card change" as a persistence bug**: something in camera-side state (settings, counters, caches) is being written or interpreted wrongly, not the card file itself.

## Differences that must not be blurred

- Different builds, different feature sets, different version identities. A mechanism found in one binary says nothing proven about the other.
- Their first symptom (pre-capture permanently disabled) is a failure mode we have not observed; our incident had no such phase.
- Their boot symptom is reported as "no boot"; ours was a restart loop with the loader still alive. The internal stage may differ.
- We have no access to their build, their source delta or their camera, and we are not drawing conclusions about their code.

## 简体中文

- 本文对照两起独立事件：本仓 V10 构建引发的测试机开机循环（见 [risks.md](risks.md)）与上游 [XinmiaoZhao/NikonFirmwarePatch Issue #3](https://github.com/XinmiaoZhao/NikonFirmwarePatch/issues/3)（2026-10-18 开，Z8 C 4.03：一台取卡后预拍永久失效、一台刷后不开机）。仅做症状层面对照，内容均取自截至 2026-10-19 的公开 issue 原文；双方无项目隶属关系，亦无固件或文件往来。
- **相同点**：均在通过全部离线检查后才上机（离线绿 ≠ 上机安全）；同属“修改版 Z8 固件无法完成应用层初始化”这一类故障；修改点均触及预拍与设置文件处理链路；处置原则一致：先停手别刷，以单变量控制逐步剥离触发面。
- **我们的取证结论（可迁移的假设）**：① 计数与背衬表不一致（618/617，已证实机理：目标内计数存在三个真源，此前只改了两个，遍历时越界 1 项）。② 载入路径 bounds guard 跨区比较——代码不会崩溃，但会导致配置项“全跳过”或“全放行”，**直观症状正是“无论喂什么文件都不生效”**，与 Issue #3 第一台相机的现象同型（仅为同型，并非断定同因）。③ 写入了归属未闭环的表边界（该表在整个固件包中无任何代码引用；若相邻表在开机时被读取，即为潜在故障点；切勿写入无法证明归属的表）。④ 逐字节排除一个嫌疑点与定位一个嫌疑点同样有价值（核对并排除可疑 stub 后，收窄了排查范围，避免盲目猜测）。
- **实操建议**：先做零构建判据（无设置文件/无 CFG 各开机一次，快速切分触发面）→ 按构建世代向前二分 → 扫描补丁集里的计数立即数并与底层背衬表核对（单项越界无法被离线检查发现）→ 审查载入路径上的 bounds guard，明确“短文件会怎样” → 将“换卡后失效”视为持久化 bug，优先排查相机侧状态而非卡内文件。
- **不许模糊的差异**：不同的构建、功能集与版本标识；对方第一台机器的失效症状我们从未观察到；“不开机”与“开机循环”所处的内部执行阶段可能不同；我们没有对方的构建产物与源码，不对对方的代码下任何定性结论。
