# Feature inventory

A complete inventory of what this toolchain can build, alongside its actual status. Nothing is withheld: items that do not work, remain unverified, or were deemed undeliverable are listed next to those that do.

Status legend:

| Symbol | Meaning |
|---|---|
| ✅ | Verified working **on hardware** (specific build identified) |
| ⚠️ | Verified **offline only** — build, byte-verification, tests, gauntlet. Never confirmed on a camera |
| ❌ | Known problem, or judged not deliverable |
| 🧪 | Experimental: implemented as a sketch, treat as unproven |

The ground rule for this table: an offline green status only confirms that the output bytes match the patch recipe. It indicates nothing about how camera hardware executes them. During development, a build with a fully green offline test record caused a boot loop on hardware (see [risks.md](risks.md)).

---

## `precapture` — RAW pre-capture

Build with `--features precapture`. Produces the pre-capture module plus `Z8PRE*.CFG` configuration files. Needs Clang.

| Feature | Control | Status | Verification depth |
|---|---|---|---|
| HE★ pre-capture (history frames recorded as true HE★ RAW) | Feature flag; tier 14 selected automatically | ✅ | On hardware, **early build**: real HE★ NEFs produced and checked against camera-made references. Later changes to this area are ⚠️ only |
| C15 pre-capture window | Automatic in C15 | ✅ | On hardware, **early build** |
| C30 pre-capture window, 1 s clamp, frame cap | Constant in the capacity tables | ⚠️ | Offline verification (tables, disassembly inspection). The clamping behavior itself was probed on hardware once to establish the root cause; the shipped values were not |
| History frame cap per tier (8 lossless / 30 HE / 20 HE★) | Automatic per tier | ⚠️ | Offline only |
| Image-quality menu drives RAW / RAW+JPEG / JPEG for both pre-release and full-press frames | Camera menu | ⚠️ | Offline verification (menu structures, patch recipes). Never tested on hardware |
| Full-size 8256×5504 embedded preview in the NEF | Automatic | ⚠️ | Offline only |
| Files enter the stock photo database, direct playback | Feature flag | ⚠️ | Offline only; upstream hardware validation applies solely to their own builds and is not valid evidence here |
| RAW-only (no JPEG written) | `Z8PRE*.CFG` flag | ⚠️ | Offline verification (code-level trace of the no-write path). Not confirmed on hardware |
| Preview family: fixed-size small previews | `Z8PRE*.CFG` flag | ⚠️ | Offline verification (exact dimensions pinned). Playback untested |
| File modification time = capture time | Always on (correctness fix) | ⚠️ | Offline disassembly analysis. File timestamps on hardware were never verified |
| Remaining-frames display correction | Automatic | ⚠️ | Offline disassembly inspection. Scales the displayed value only; the underlying calculation is untouched, so other configurations may require retuning |
| Lens correction block (NEF metadata) for 7 known lenses | Automatic, fail-safe on unknown lenses | 🧪 | Offline proof-of-concept and disassembly analysis. **No** acceptance testing performed in Adobe Lightroom / Camera Raw / NX Studio |
| D5 compatibility placeholder blocks | Automatic | 🧪 | Offline verification: formatted identically to native empty blocks. Parser acceptance untested |
| Bits per sample 12/14 | Configuration field | 🧪 | Handling logic implemented; the corresponding menu wiring to configure it remains unidentified |
| Lossless pre-capture tier | Camera menu = lossless | 🧪 | Offline verification. The strip-length field is a static estimate marked as low-confidence |
| HE pre-capture tier | Camera menu = HE | 🧪 | Offline verification only (tier dispatch and thresholds) |
| D3 "Max." pre-capture duration entry | Would be a camera menu value | ❌ | Not deliverable yet: value-range record semantics remain unresolved, preventing the entry from being selectable. The data tables are ready |
| i-menu / dial / shooting display consistency | — | ❌ | Known inherited problem: these displays still reflect HSFC quality settings and can conflict with the menu used by this feature |

## `prores` — ProRes quality

Build with `--features prores`. No compiler needed.

| Feature | Control | Status | Verification depth |
|---|---|---|---|
| Four quality tiers (HQ / 422 / LT / Proxy), MOV identifiers and playback labels | Camera menu | ⚠️ | Patch bytes match the upstream project's reviewed bytes without change. Never confirmed on hardware here |
| Per shooting-menu bank A/B/C/D persistence | Camera menu banks | ⚠️ | Offline verification (two-hook path). Saving/loading this value via settings files remains a known gap |
| Quality-dependent recording-time estimates | Automatic | ⚠️ | Offline only |
| Shooting-screen icon for the selected tier | — | ❌ | Known gap: the on-screen icon does not indicate which tier is selected |

## `opengate` — OpenGate 3:2 recording

Build with `--features opengate` (requires `precapture`). Experimental recording modes at 8256×5504 and two reduced sizes, enabled by `Z8OG.CFG` on one card; delete the file to switch it off.

| Feature | Control | Status | Verification depth |
|---|---|---|---|
| 3:2 recording size metadata and bit-rate rows | `Z8OG.CFG` | 🧪 | Offline verification (patch windows, bit-rate tables, dispatch logic). Recording on hardware never tried |
| Readout window follows the new size | — | ❌ unproven | Black bars, aspect stretching, or shifted AF frames are all plausible until tested |
| Combination with ProRes tiers | Automatic | ⚠️ | Offline verification: dispatch logic and combination matrix enforced |

## `menuh` — custom settings menu group

Build with `--features menuh`. Adds a group to the custom settings menu and one settings item that survives save/load to card.

| Feature | Control | Status | Verification depth |
|---|---|---|---|
| Group visible and enterable | Automatic | ⚠️ | Offline verification (recipe regeneration lock, 18 pytest checks). The icon resource and menu navigation behavior have never been observed on hardware |
| Group has usable items | — | ❌ | Not yet: the shell has no entries. Adding entries is future work |
| New settings item survives card save/load | Automatic | ⚠️ | Offline verification against a real camera settings file sample (regression harness). Not confirmed on hardware |
| Load-time bounds guard for old settings files | Automatic | ⚠️ | Offline verification. The guard boundary is known to be calculated across two distinct memory regions; while it prevents crashes, it may either bypass checks or permit arbitrary input (see [risks.md](risks.md)) |

## Not deliverable / deliberately cut

These were investigated and are presented as they are, not silently dropped.

| Item | Verdict | Reason |
|---|---|---|
| ISO 0.5 EV steps | ❌ not deliverable | The consumer of this control value cannot be reached within the package (static boundary exhausted, empirically unreachable). Without it, both the direct and fallback routes produce no real 0.5 EV steps, so the fallback route was rejected |
| OSD text hints for the new options | ❌ not deliverable | The display descriptor contains no text slot (empirically bounded); routing via a dedicated text widget would be required and was deemed unsafe |
| D3 "Max." duration selectable in the menu | ❌ not deliverable yet | Value-range record semantics remain undecided; the underlying tables exist, but the setting cannot be selected via the UI |
| C60/C120 pre-capture | ❌ cut | Intentionally dropped: those modes use distinct sensor readout configurations and were out of scope |
| SubIFD3 grayscale sub-image, extra NEF info blocks | ❌ not implemented | Payload generation algorithm and internal semantics remain unknown |
| Card-file persistence of the ProRes tier under its own item | ❌ not possible in that shape | The setting item is not written to configuration files on the card; supporting this would require table-level modifications |
| Debug/diagnostic toolkit | 🧪 design only | Intentionally not merged. If ever built, it must pass the full test battery and meet its own safety limits |

## Known problems

| Problem | State |
|---|---|
| **V10 build causes a boot loop on hardware** | Root cause partially established: an out-of-bounds traversal mechanism is confirmed, though the exact crash point is not. Forensics continue on the `bricking-edge` line. Do not flash |
| Guard bound computed across two regions | Protection can silently do nothing. Fix is in the `bricking-edge` scope |
| Settings-count change is applied in two of three places | The third source of truth was not updated; the walk can overrun by one entry. Proven mechanism, suspected contributor to the incident |
| Lossless strip-length field | Static estimate; may truncate in edge cases. Low confidence |
| Remaining-frames display | UI display-side scaling only, not a root-cause fix |
| Same-version update acceptance | Untested on hardware. If rejected by the camera, rebuild with a higher version number |
| Menu display vs actual quality | Inherited limitation: i-menu, dials, and live shooting displays can disagree with the selected quality profile |

## 简体中文

- 图例：**✅ 上机验证可用**（注明具体生效的构建）／**⚠️ 仅离线验证**（包含构建、字节复核、测试、gauntlet，未在真机确认）／**❌ 已知有问题或判不可交付**／**🧪 实验性草稿**。
- 核心口径：**离线全绿只证明字节符合配方，不证明相机行为**。开发中确有一次离线全绿的构建上机后出现开机循环（详见 [risks.md](risks.md)）。
- 上机实测仅覆盖早期构建的 HE★ 预拍、C15 预拍等少数项；其余条目均仅有离线验证记录。
- 判定为“不可交付”的条目（ISO 0.5EV、OSD 文本提示、D3 Max 档、C60/C120 预拍等）连同具体原因一并列出，不做静默删除。
- 已知问题（V10 开机循环、guard 跨区比较、计数三处数据源未同步、无损 strip 长度、同号受理未实测等）均已逐条记录在册。
