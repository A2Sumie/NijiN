# Feature inventory

Overview of features supported by this toolchain and their verification status.

| Symbol | Status |
|---|---|
| ✅ | **Tested on hardware** (verified in a specific build) |
| ⚠️ | **Verified offline only** (passes build and byte checks; untested on camera hardware) |
| 🧪 | **Experimental** (proof of concept, incomplete or unproven) |
| ❌ | **Broken or unimplemented** |

> **Warning:** Passing offline checks only confirms that the output bytes match the patch definitions—it does not guarantee the firmware will run safely on the camera. One build that passed all offline tests caused a hardware boot loop (see [risks.md](risks.md)).

---

## `precapture` — RAW pre-capture

Build with `--features precapture` (requires Clang). Generates the pre-capture module and `Z8PRE*.CFG` configuration files. For usage instructions and limitations, see [raw-precapture.md](raw-precapture.md).

| Feature | Control | Status | Notes |
|---|---|---|---|
| HE★ pre-capture (saves history frames as true HE★ RAW) | Feature flag (auto-selects tier 14) | ✅ | Verified on hardware in an early build against native reference NEFs. Later changes to this code are only verified offline (⚠️). |
| C15 pre-capture window | Automatic in C15 | ✅ | Verified on hardware in an early build. |
| C30 pre-capture window (1 s clamp, frame cap) | Capacity table constant | ⚠️ | Clamping logic was probed on hardware, but the shipped table values are only verified offline. |
| Per-tier history frame cap (8 lossless / 30 HE / 20 HE★) | Automatic per tier | ⚠️ | Verified via disassembly and table checks. |
| Image-quality menu controls RAW / RAW+JPEG / JPEG for pre-release and full press | Camera menu | ⚠️ | Menu structures and patches verified offline. |
| Full-size (8256×5504) embedded NEF preview | Automatic | ⚠️ | |
| Stock photo database registration and direct playback | Feature flag | ⚠️ | Tested on hardware in the upstream project, but untested in this build. |
| RAW-only mode (skips JPEG write) | `Z8PRE*.CFG` flag | ⚠️ | Code path traced offline. |
| Fixed-size small previews | `Z8PRE*.CFG` flag | ⚠️ | Dimensions verified offline; in-camera playback untested. |
| Set file modification time to capture time | Always on | ⚠️ | Verified via disassembly; actual file timestamps untested on hardware. |
| Remaining-frames display correction | Automatic | ⚠️ | Scales the UI value only; does not change the underlying calculation. Other configurations may need retuning. |
| Lens correction metadata (NEF) for 7 known lenses | Automatic (no-op on unknown lenses) | 🧪 | Proof of concept. Not yet tested in Lightroom, Camera Raw, or NX Studio. |
| D5 compatibility placeholder blocks | Automatic | 🧪 | Matches native empty block formatting; parser compatibility untested. |
| 12-bit / 14-bit depth selection | Config field | 🧪 | Logic implemented, but not yet wired to the camera menu. |
| Lossless pre-capture tier | Camera menu (Lossless) | 🧪 | Uses a low-confidence static estimate for the strip-length field. |
| HE pre-capture tier | Camera menu (HE) | 🧪 | Tier dispatch and thresholds verified offline. |
| D3 "Max." pre-capture duration | Camera menu | ❌ | Data tables exist, but value-range record semantics are unresolved, so the menu option cannot be selected. |
| i-menu / dial / shooting display sync | — | ❌ | Displays still read from standard HSFC quality settings and may disagree with the active pre-capture quality. |

## `prores` — ProRes quality

Build with `--features prores`. Does not require a C compiler.

| Feature | Control | Status | Notes |
|---|---|---|---|
| Four quality tiers (HQ / 422 / LT / Proxy), MOV IDs, and playback labels | Camera menu | ⚠️ | Matches upstream patch bytes; untested on hardware in this build. |
| Shooting menu bank (A/B/C/D) persistence | Camera menu banks | ⚠️ | Verified offline. Saving/loading to card settings files is not supported. |
| Quality-adjusted recording time estimates | Automatic | ⚠️ | |
| Shooting screen quality icon | — | ❌ | On-screen icon does not update to reflect the selected tier. |

## `opengate` — OpenGate 3:2 recording

Build with `--features opengate` (requires `precapture`). Enables experimental 3:2 recording at 8256×5504 and two smaller resolutions when `Z8OG.CFG` is present on the card. Delete the file to disable.

| Feature | Control | Status | Notes |
|---|---|---|---|
| 3:2 resolution metadata and bit-rate tables | `Z8OG.CFG` | 🧪 | Patch windows, bit-rate tables, and dispatch logic verified offline. |
| Sensor readout window scaling | — | ❌ | Untested. May result in black bars, stretched aspect ratio, or misaligned AF boxes. |
| ProRes tier integration | Automatic | ⚠️ | Dispatch logic and combination matrix verified offline. |

## `menuh` — Custom settings menu group

Build with `--features menuh`. Adds a custom settings menu group and one persistent setting item.

| Feature | Control | Status | Notes |
|---|---|---|---|
| Menu group visible and accessible | Automatic | ⚠️ | Verified offline. Icon rendering and menu navigation are untested on hardware. |
| Functional menu items inside group | — | ❌ | Empty shell only; no items added yet. |
| Card save/load persistence for the new setting | Automatic | ⚠️ | Tested offline against a sample camera settings file. |
| Bounds check when loading older settings files | Automatic | ⚠️ | Compares addresses across two different memory regions. Prevents crashes, but may either skip validation or allow invalid values (see [risks.md](risks.md)). |

## Unimplemented & out-of-scope features

| Feature | Status | Reason |
|---|---|---|
| ISO 0.5 EV steps | ❌ | The code that consumes this value lies outside the patchable firmware package. |
| OSD text hints for new options | ❌ | Display descriptors have no text slot, and routing through a separate text widget is unsafe. |
| Selectable D3 "Max." duration in menu | ❌ | Value-range record semantics are unresolved; tables exist, but the UI option cannot be selected. |
| C60 / C120 pre-capture | ❌ | Out of scope (uses different sensor readout configurations). |
| SubIFD3 grayscale sub-image & extra NEF info blocks | ❌ | Payload generation algorithm and internal format are unknown. |
| Card-file persistence for standalone ProRes tier setting | ❌ | Setting is not written to card config files; adding it requires table-level changes. |
| Debug / diagnostic toolkit | 🧪 | Design only; not implemented. |

## Known issues

| Issue | Details |
|---|---|
| **V10 build causes a hardware boot loop** | **Do not flash.** Caused by an out-of-bounds read during table traversal. Under investigation on the `bricking-edge` branch. |
| Cross-region bounds check | The settings file bounds guard compares pointers across two memory regions, which can make the check ineffective. Fix is tracked in `bricking-edge`. |
| Incomplete settings-count update | The total settings count is updated in only two of three locations, allowing table traversal to overrun by one entry. Likely contributor to the V10 boot loop. |
| Estimated lossless strip length | Uses a static estimate that may truncate data in edge cases. |
| Remaining-frames counter | Scales the displayed number in the UI rather than fixing the underlying buffer calculation. |
| Same-version firmware flashing | Untested on hardware. If the camera rejects flashing the same version number, rebuild with a higher version. |
| Inconsistent quality indicators | The i-menu, command dials, and live shooting display read from standard quality settings and may not match the pre-capture menu. |

## 简体中文

- **状态图例**：
  - ✅ **真机实测可用**（基于特定早期构建）
  - ⚠️ **仅离线验证**（通过编译、字节比对与自动化测试，未上机实测）
  - 🧪 **实验性实现**（仅完成概念验证或草稿，未充分验证）
  - ❌ **已知缺陷或未实现**
- **风险提示**：离线测试通过仅代表生成的补丁字节符合预期，**不能保证真机运行安全**。此前曾有离线测试全绿的构建（V10）在真机上引发无限重启（详见 [risks.md](risks.md)）。
- **实测范围**：目前仅有早期构建的“HE★ 预拍”和“C15 预拍”经过真机实测；其余功能均仅完成离线验证。
- **未实现功能**：ISO 0.5 EV 步进（目标代码在固件包范围外）、OSD 文本提示（无安全文本槽位）、D3 Max 时长选项、C60/C120 预拍（传感器读出配置不同）等均未实现。
- **已知问题**：V10 构建存在越界读取导致的开机死循环（请勿刷入）；此外还存在跨内存区边界检查失效、设置项计数未全量同步（三处仅改两处）、无损 RAW 条带长度采用静态估算、剩余张数仅为 UI 缩放等问题。逐项状态表见上文英文表格（共 41 行：**3 ✅ / 18 ⚠️ / 12 ❌ / 8 🧪**），中文摘要不逐行重复，结论与英文表完全一致。
