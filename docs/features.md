# Feature inventory

Everything the toolchain can build, with its honest state. Nothing is
hidden: items that do not work, are unverified, or were judged not
deliverable are listed here next to the ones that do work.

Status legend:

| Symbol | Meaning |
|---|---|
| ✅ | Verified working **on hardware** (which build is named) |
| ⚠️ | Verified **offline only** — build, byte-verification, tests, gauntlet. Never confirmed on a camera |
| ❌ | Known problem, or judged not deliverable |
| 🧪 | Experimental: implemented as a sketch, treat as unproven |

The rule behind the table: offline green means the bytes are what the recipe
says they are. It says nothing about what a camera does with them. During
development a build with a fully green offline record caused a boot loop on
hardware (see [risks.md](risks.md)).

---

## `precapture` — RAW pre-capture

Build with `--features precapture`. Produces the pre-capture module plus
`Z8PRE*.CFG` configuration files. Needs Clang.

| Feature | Control | Status | Verification depth |
|---|---|---|---|
| HE★ pre-capture (history frames recorded as true HE★ RAW) | Feature flag; tier 14 selected automatically | ✅ | On hardware, **early build**: real HE★ NEFs produced and checked against camera-made references. Later changes to this area are ⚠️ only |
| C15 pre-capture window | Automatic in C15 | ✅ | On hardware, **early build** |
| C30 pre-capture window, 1 s clamp, frame cap | Constant in the capacity tables | ⚠️ | Offline (tables, disassembly read-back). The clamp behaviour itself was probed on hardware once to establish the root cause; the shipped values were not |
| History frame cap per tier (8 lossless / 30 HE / 20 HE★) | Automatic per tier | ⚠️ | Offline only |
| Image-quality menu drives RAW / RAW+JPEG / JPEG for both pre-release and full-press frames | Camera menu | ⚠️ | Offline (menu structures, patch recipes). Never exercised on a camera |
| Full-size 8256×5504 embedded preview in the NEF | Automatic | ⚠️ | Offline only |
| Files enter the stock photo database, direct playback | Feature flag | ⚠️ | Offline; the upstream project's hardware record belongs to its own builds and is not evidence for these |
| RAW-only (no JPEG written) | `Z8PRE*.CFG` flag | ⚠️ | Offline (code-level proof of the no-write path). Not confirmed on hardware |
| Preview family: fixed-size small previews | `Z8PRE*.CFG` flag | ⚠️ | Offline (exact sizes pinned). Playback untested |
| File modification time = capture time | Always on (correctness fix) | ⚠️ | Offline, disassembly level. File-times on hardware never checked |
| Remaining-frames display correction | Automatic | ⚠️ | Offline, disassembly read-back. Scales the displayed value; the producer is untouched, so other configurations may need retuning |
| Lens correction block (NEF metadata) for 7 known lenses | Automatic, fail-safe on unknown lenses | 🧪 | Offline proof-of-concept + disassembly. **No** Adobe Lightroom / Camera Raw / NX Studio acceptance test |
| D5 compatibility placeholder blocks | Automatic | 🧪 | Offline: byte-shaped like the camera's own empty blocks. Parser acceptance untested |
| Bits per sample 12/14 | Configuration field | 🧪 | Consumption implemented; the menu wiring that would set it is not identified |
| Lossless pre-capture tier | Camera menu = lossless | 🧪 | Offline. The strip-length field is a static estimate and marked low-confidence |
| HE pre-capture tier | Camera menu = HE | 🧪 | Offline only (tier dispatch and thresholds) |
| D3 "Max." pre-capture duration entry | Would be a camera menu value | ❌ | Not deliverable yet: the value-range record semantics are unresolved, so the entry cannot be made selectable. The tables are ready |
| i-menu / dial / shooting display consistency | — | ❌ | Known inherited problem: those displays still show the HSFC quality and can disagree with the menu this feature uses |

## `prores` — ProRes quality

Build with `--features prores`. No compiler needed.

| Feature | Control | Status | Verification depth |
|---|---|---|---|
| Four quality tiers (HQ / 422 / LT / Proxy), MOV identifiers and playback labels | Camera menu | ⚠️ | Patch bytes are the upstream project's reviewed bytes, unchanged. Never confirmed on hardware here |
| Per shooting-menu bank A/B/C/D persistence | Camera menu banks | ⚠️ | Offline (two-hook path). Settings-file save/load of this value is a known gap |
| Quality-dependent recording-time estimates | Automatic | ⚠️ | Offline only |
| Shooting-screen icon for the selected tier | — | ❌ | Known gap: the icon does not show which tier is selected |

## `opengate` — OpenGate 3:2 recording

Build with `--features opengate` (requires `precapture`). Experimental
recording modes at 8256×5504 and two reduced sizes, enabled by `Z8OG.CFG`
on one card; delete the file to switch it off.

| Feature | Control | Status | Verification depth |
|---|---|---|---|
| 3:2 recording size metadata and bit-rate rows | `Z8OG.CFG` | 🧪 | Offline (patch windows, rate rows, dispatch). Recording on hardware never tried |
| Readout window follows the new size | — | ❌ unproven | Black bars, stretching or shifted AF frames are all plausible until tested |
| Combination with ProRes tiers | Automatic | ⚠️ | Offline: dispatch and combination matrix enforced |

## `menuh` — custom settings menu group

Build with `--features menuh`. Adds a group to the custom settings menu and
one settings item that survives save/load to card.

| Feature | Control | Status | Verification depth |
|---|---|---|---|
| Group visible and enterable | Automatic | ⚠️ | Offline (recipe regeneration lock, 18 pytest checks). The logo resource and entry behaviour have never been seen on hardware |
| Group has usable items | — | ❌ | Not yet: the shell has no entries. Adding entries is future work |
| New settings item survives card save/load | Automatic | ⚠️ | Offline against a real settings file sample (regression harness). Not confirmed on hardware |
| Load-time bounds guard for old settings files | Automatic | ⚠️ | Offline. The guard's bound is known to be computed across two different regions; it cannot crash but it can skip or allow everything (see [risks.md](risks.md)) |

## Not deliverable / deliberately cut

These were investigated and are presented as they are, not silently dropped.

| Item | Verdict | Reason |
|---|---|---|
| ISO 0.5 EV steps | ❌ not deliverable | The consumer of the control value cannot be reached in the package (static boundary exhausted, empirically unreachable). Without it, both the direct and the degraded route produce no real 0.5 EV steps, so the degraded route was rejected |
| OSD text hints for the new options | ❌ not deliverable | The display descriptor has no text slot (empirically bounded); a text-widget route would be needed and was not found safe |
| D3 "Max." duration selectable in the menu | ❌ not deliverable yet | Value-range record semantics undecided; the tables exist but no user can select the value |
| C60/C120 pre-capture | ❌ cut | Decided against; those modes are different readout sizes and were out of scope |
| SubIFD3 grayscale sub-image, extra NEF info blocks | ❌ not implemented | Generation algorithm and semantics unknown |
| Card-file persistence of the ProRes tier under its own item | ❌ not possible in that shape | The settings item is not stored in the card file at all; a table-level change would be needed |
| Debug/diagnostic toolkit | 🧪 design only | Deliberately not landed. If ever built it must pass the full battery and its own safety limits |

## Known problems

| Problem | State |
|---|---|
| **V10 build causes a boot loop on hardware** | Root cause partially established (an out-of-bounds walk mechanism is proven; the exact crash point is not). Forensics continue on the `bricking-edge` line. Do not flash |
| Guard bound computed across two regions | Protection can silently do nothing. Fix is in the `bricking-edge` scope |
| Settings-count change is applied in two of three places | The third source of truth was not updated; the walk can overrun by one entry. Proven mechanism, suspected contributor to the incident |
| Lossless strip-length field | Static estimate; may truncate in edge cases. Low confidence |
| Remaining-frames display | Display-side scaling, not a root-cause fix |
| Same-version update acceptance | Untested. If refused, rebuild with a higher version number |
| Menu display vs actual quality | i-menu/dial/shooting display can disagree with the selected quality (inherited) |

## 简体中文

- 图例：**✅ 上机验证可用**（注明是哪个构建）／**⚠️ 仅离线验证**（构建、字节复核、
  测试、gauntlet）／**❌ 已知有问题或判不可交付**／**🧪 实验性草稿**。
- 核心口径：**离线全绿只证明字节符合配方，不证明相机行为**。开发中确有一次
  离线全绿的构建上机后开机循环（详见 [risks.md](risks.md)）。
- 上机实证只覆盖早期构建的 HE★ 预拍、C15 预拍等少数项；其余全部只有离线证据。
- 判“不可交付”的条目（ISO 0.5EV、OSD 文本提示、D3 Max 档、C60/C120 预拍等）
  连同理由一起列在本文，不做静默删除。
- 已知问题（V10 开机循环、guard 跨区比较、计数三真源不同步、无损 strip 长度、
  同号受理未实测等）逐条在册。
