**WIP. Owner's Z8 bricked! Use at your own risk.**
**施工中。作者的 Z8 已经刷砖！风险自担。**

<p align="center">
  <img src="assets/lockup/nijin-lockup-transparent.png" alt="NijiN — the project wordmark with its icon" width="420">
</p>

# NijiN

**QQ group / QQ 群：`1108781835`** — 讨论与互助 / discussion and help

[English](#english) · [简体中文](#简体中文)

An open-source, source-only toolchain to build an **experimental Nikon Z8
firmware update on your own machine, from your own copy of the official
update package**. Select your target features; the tools generate the modified
package locally and verify it byte by byte.

**This repository contains no firmware and no prebuilt binaries.** See
[NOTICE.md](NOTICE.md).

---

## English

**WIP. Owner's Z8 bricked! Use at your own risk.**

### Read this first

**Building or installing this can brick your camera. This is not a
theoretical warning.** During development, a test build (line V10) was
flashed to a test camera; the body went into a boot loop and never came back
into service — the unit was sent for repair. All offline checks on that
build were green. Offline green does not mean safe on hardware.

- Nothing here is a finished product; every feature is experimental.
- Flashing, hardware operation, and device recovery are entirely your own
  responsibility. The tools never interact directly with a camera or card.
- Do not use this for production or irreplaceable shoots.
- If you need a reliable camera, run the official firmware.

A similar post-flash failure was reported independently on another Z8
modification project; the symptom comparison and what our forensics suggest
checking are in [docs/upstream-issue-3.md](docs/upstream-issue-3.md).

To the extent permitted by law, the authors and contributors provide no
warranty and accept no liability for data loss, card corruption, camera
malfunction, a bricked camera, or any other loss arising from building,
installing, or using anything produced from this repository. See
[NOTICE.md](NOTICE.md) and [docs/risks.md](docs/risks.md).

### What this is

NijiN takes a **user-supplied official Nikon Z8 C 3.11 update package**
(99,051,117 bytes, five modules) and produces a locally modified package
containing only the features you select. The toolchain:

- verifies the input against **SHA-256 fingerprint windows** (hashes and
  offsets only; no proprietary firmware bytes are stored here);
- compiles added routines from the C and assembly sources in this repository;
- applies a limited set of reviewed patch windows and a shared loader modification;
- independently re-verifies the output: every byte outside the target patch
  windows must remain unmodified, and all patched windows must match published
  recipe hashes byte for byte;
- runs a strict test battery (`gauntlet/`) before any build is considered valid.

The tools do not download firmware, do not write files to a card, do not
interface with a camera, and include no updater or flashing utilities.

### Bring your own firmware

Download the official package directly from
[Nikon's download center](https://downloadcenter.nikonimglib.com/en/download/fw/606.html),
subject to Nikon's terms, and supply the file to the tool. Update packages
are not interchangeable with other files. This repository supplies no keys,
no decryption service, and no extraction utility. The open-source license here
grants no rights to Nikon proprietary firmware.

### What you can build

Feature status legend: **✅ verified working on hardware** · **⚠️ verified
offline only, never confirmed on a camera** · **❌ known problem** ·
**🧪 experimental, treat as a sketch**.

| Feature | What it does | Status | Notes |
|---|---|---|---|
| `precapture` — HE★ pre-capture | Pre-release history frames are recorded as true HE★ RAW | ✅ (early build, on hardware) | A test shoot on an early build produced real HE★ NEFs; later changes to this area are ⚠️ |
| `precapture` — C15/C30 pre-capture window | History window, one-second clamp and frame budget for C15/C30 bursts | ✅ (C15, early build) / ⚠️ (C30, frame cap) | C30 one-second clamp and the 20-frame ring cap are offline-verified only |
| `precapture` — image quality menu | RAW / RAW+JPEG / JPEG choice drives both pre-release and full-press frames | ⚠️ | Offline verified; menu behaviour on hardware not confirmed |
| `precapture` — full-size embedded preview, stock playback | 8256×5504 preview inside the NEF, files enter the stock photo database | ⚠️ | Offline verified; no hardware playback test |
| `precapture` — RAW-only, preview family, file timestamps | Skips JPEG writes; fixed-size small previews; file time = capture time | ⚠️ | Offline verified only |
| `precapture` — lossless / HE pre-capture tiers | Pre-capture in lossless or HE instead of HE★ | 🧪 | Lossless strip length is a static estimate, not confirmed |
| `prores` — ProRes quality | HQ / 422 / LT / Proxy selection, per shooting-menu bank | ⚠️ | Upstream patch bytes unchanged; icon does not show the selected tier |
| `opengate` — OpenGate 3:2 recording | Experimental 8256×5504 video modes via `Z8OG.CFG` | 🧪 | Whether the readout window follows the new size is unproven |
| `menuh` — custom settings menu group | New menu group shell plus a settings item that survives save/load | ⚠️ | Group is visible and enterable but has no items yet; logo/entry behaviour never seen on hardware |
| Shot counter correction | Remaining-frames display follows the configured output | ⚠️ | Corrects the displayed value, not the producer; other configurations may need retuning |
| Lens correction block | Writes the NEF lens-correction block for 7 known lenses | 🧪 | No Adobe/NX Studio acceptance test; unknown lenses write nothing (fail-safe) |
| D5 compatibility placeholders | Empty metadata blocks some parsers expect | 🧪 | Byte-identical copies of empty blocks; parser acceptance untested |
| Bits-per-sample selection | 12/14-bit from configuration | 🧪 | Consumption is implemented; the menu wiring is not identified |
| D3 "Max." duration | Extra pre-capture duration entry | ❌ not deliverable yet | The value-range record semantics are unresolved, so no one can select it |
| OSD text hints | On-screen text for the new options | ❌ not deliverable | The display descriptor has no text slot; no safe route found |
| ISO 0.5 EV steps | Smaller ISO increments | ❌ not deliverable | The consumer of the control value is unreachable in the package; the degraded route was rejected |
| C60/C120 pre-capture | Pre-capture in the high-speed modes | ❌ cut | Deliberately not pursued |

Full detail, including every "verified offline only" claim and what it was
checked against, is in [docs/features.md](docs/features.md).

### Release lines

| Line | Branch / tag | Meaning | Status |
|---|---|---|---|
| **V10** | `main` | The current stable line. Every offline check passes: byte-level verification, the full gauntlet battery, reproducible rebuilds. | ⚠️ offline green; **❌ do not flash** — the V10 build is the one that caused the boot loop described above |
| **V11 `bricking-edge`** | `bricking-edge` (branch and tag) | The hotfix / forensics line, named after the V10 incident. It strips the three suspect V10 changes and reverts four patch windows to the previous build. See [docs/bricking-edge.md](docs/bricking-edge.md) | 🧪 built and byte-verified offline as a trial only; deliberately never released; frozen until the boot-loop cause is settled |

The name `bricking-edge` is dark humour kept on purpose: the line exists
because a camera was bricked. See [docs/versions.md](docs/versions.md).

### Build your own

Requires Python 3.10+ and the pinned dependency. Pre-capture features also
require Clang targeting AArch64; the build refuses any compiler output that
deviates from the reviewed recipe bytes. ProRes-only builds require no C compiler.

```sh
git clone https://github.com/A2Sumie/NijiN.git
cd NijiN
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

# Read-only compatibility check against your own input package
python patch.py "/path/to/Z_8_0311.bin" --features prores precapture --check

# Build into a new, empty output directory
python patch.py "/path/to/Z_8_0311.bin" --features prores precapture \
    --version 03.11 --tag p0 --output build/mybuild

# Independently re-verify the result
python verify.py "/path/to/Z_8_0311.bin" "build/mybuild/Z_8_0311.bin" \
    --features prores precapture
```

Then run the test battery before considering the build complete:

```sh
python tests/validate.py --stock "/path/to/Z_8_0311.bin" --report build/validate.json
python tests/validate_features.py --stock "/path/to/Z_8_0311.bin" --report build/features.json
python gauntlet/gauntlet.py run --kit build/mybuild --stock "/path/to/Z_8_0311.bin" --out build/gauntlet
```

Full flow, version-number policy, and the on-device checklist:
[docs/build.md](docs/build.md). What those checks do and do not prove:
[docs/verification.md](docs/verification.md).

### What is not in this repository

Following the practice of the upstream projects we build on, the following
are deliberately excluded and must never be added: firmware or decrypted
program bytes, extracted fonts, icon bitmaps, string tables, device
settings files, third-party commercial software, manuals, sample photographs,
camera UI screenshots, personal data, or local file paths. Runtime folders can
contain proprietary binaries even in a source-only repository—keep
them local. See [CONTRIBUTING.md](CONTRIBUTING.md); the pre-push scanner is
[tools/redline_scan.py](tools/redline_scan.py).

### Repository layout

| Path | Contents |
|---|---|
| `patch.py`, `verify.py`, `features.py`, `configure.py` | Build driver, independent verifier, feature composition, config file generator |
| `z8prores/`, `z8precapture/`, `z8opengate/`, `z8menuh/` | Feature modules: patch recipes and added code sources (C, AArch64 emitter, linker, patch scripts) |
| `resources/` | Patch definitions: SHA-256 fingerprint windows, offsets, entry addresses, constants. Hashes and offsets only |
| `tests/` | Offline validation suites (no camera required, no firmware shipped) |
| `gauntlet/` | The mandatory test battery: seven gates, mutation battery, combination matrix, structural torture |
| `tools/` | Repository hygiene checks and the red-line scanner |
| `recipes/` | Build recipes for research lines (this branch: the `bricking-edge` revert recipe) |
| `docs/` | Build, features, verification, risks, version policy and the upstream symptom comparison |
| `assets/` | The NijiN wordmark and icon, created for this project |

Source comments may cite note numbers from the development log; those notes
are internal and are not distributed here.

### Community

Discussion, questions, and mutual help: **QQ group `1108781835`**. Please keep
the red lines of [CONTRIBUTING.md](CONTRIBUTING.md) there too: no firmware,
no dumps, no personal data.

### License and attribution

Original tool source is licensed under [GPL-3.0-only](LICENSE). This work is derived
from and builds on NikonFirmwarePatch (GPL-3.0-only); full attribution, the
references consulted, and licensing boundaries are in
[NOTICE.md](NOTICE.md). Nikon firmware is not relicensed, and the generated
output is not represented as GPL-licensed. This project is not affiliated
with or endorsed by Nikon.

---

## 简体中文

**施工中。作者的 Z8 已经刷砖！风险自担。**

### 先读这一段

**使用本项目构建或刷机，存在相机变砖的真实风险——这绝非理论层面的警示。** 开发
过程中，V10 分支的一次构建刷入测试机后直接陷入开机重启循环（boot loop），硬件
未能恢复并最终送修。而该构建在离线校验中全部通过。**离线全绿 ≠ 上机安全。**

- 本项目不提供任何成品；所有功能均为实验性质。
- 固件刷入、相机操作与救砖恢复完全由个人负责。工具本身不与相机通信、不对存储卡执行写入。
- 切勿用于不可重拍的重要工作。
- 若需要一台稳定工作的相机，请使用官方固件。

另一个 Z8 改装项目也独立报告过同类的刷后故障；症状对照与我们取证建议排查的方向见
[docs/upstream-issue-3.md](docs/upstream-issue-3.md)。

在适用法律允许的范围内，作者与贡献者不作任何担保，不对因构建、安装或使用
本仓库产物造成的数据丢失、卡损坏、相机故障、设备报废或其他任何损失承担责任。
详见 [NOTICE.md](NOTICE.md) 与 [docs/risks.md](docs/risks.md)。

### 这是什么

NijiN 以**你自备的官方 Nikon Z8 C 3.11 更新包**（99,051,117 字节、五个模块）
为输入，在本地生成包含所选功能的改装更新包。工具会：

- 基于 **sha256 指纹窗口**校验输入文件——仅记录哈希与偏移，本仓不含任何固件原始字节；
- 由本仓的 C 与汇编源码编译新增代码；
- 仅写入少量经审阅的补丁窗口及一处共享装载修改；
- 对生成结果执行独立复核：声明窗口之外的所有字节严格保持原样，声明窗口之内的数据必须与公布的配方哈希完全匹配；
- 完整运行强制测试套件（`gauntlet/`）进行全面验收。

工具不下载固件、不写卡、不操作相机，亦不包含任何刷机或升级程序。

### 自带固件（bring your own firmware）

请自行从 [Nikon 下载中心](https://downloadcenter.nikonimglib.com/en/download/fw/606.html)
获取官方更新包并遵守其条款，随后将文件交由工具处理。升级包与其他文件不可互换。
本仓不提供密钥，不提供任何解密或提取服务；本仓的源码许可不授予对 Nikon 固件的任何权利。

### 能构建什么

状态图例：**✅ 上机验证可用** · **⚠️ 只做过离线验证、从未上机确认** ·
**❌ 已知有问题** · **🧪 实验性，当草稿看**。

| 功能 | 做什么 | 状态 | 备注 |
|---|---|---|---|
| `precapture` — HE★ 预拍 | 预拍历史帧按真 HE★ RAW 记录 | ✅（早期构建，上机） | 早期构建真机拍出过真 HE★ NEF；该区域后来的改动属 ⚠️ |
| `precapture` — C15/C30 预拍窗口 | C15/C30 连拍的历史窗口与帧预算 | ✅（C15，早期构建）/ ⚠️（C30、帧上限） | C30 1 秒钳制、20 帧环容量只有离线验证 |
| `precapture` — 画质菜单三路 | RAW／RAW+JPEG／JPEG，预拍帧与正式帧同规则 | ⚠️ | 离线验证过；菜单行为未上机确认 |
| `precapture` — 全尺寸内嵌预览、入册回放 | NEF 内嵌 8256×5504 预览、进原厂照片库 | ⚠️ | 离线验证过；未做上机回放 |
| `precapture` — RAWONLY／预览家族／文件时间戳 | 不写 JPEG、定长小图、文件时间=拍摄时间 | ⚠️ | 仅离线验证 |
| `precapture` — 无损／HE 预拍档 | 预拍可选无损或 HE | 🧪 | 无损 strip 长度是静态估计，未经确认 |
| `prores` — ProRes 画质 | HQ／422／LT／Proxy 四档，按拍摄菜单库保存 | ⚠️ | 补丁字节与上游一致；图标不显示所选档位 |
| `opengate` — OpenGate 3:2 录像 | 经 `Z8OG.CFG` 启用的 8256×5504 试验录像 | 🧪 | 读出窗是否跟随新尺寸未证实 |
| `menuh` — 自定义设定菜单组 | 新菜单组外壳 + 一个存/载不丢的设定项 | ⚠️ | 组可见可进、暂无条目；徽标与进入行为从未上机 |
| 张数显示修正 | 剩余张数按实际输出配置显示 | ⚠️ | 修的是显示读值点，不是产生方；换配置可能需再调 |
| 镜头校正块 | 为 7 支已知镜头写 NEF 镜头校正块 | 🧪 | 未做 ACR／NX Studio 验收；未知镜头不写块（fail-safe） |
| D5 兼容占位 | 部分解析器期望的空元数据块 | 🧪 | 空块 1:1 复刻；解析器接受度未测 |
| 位深选择 | 按配置出 12/14-bit | 🧪 | 消费端已落码；菜单接线未定位 |
| D3 “Max.” 时长 | 预拍时长多一档 | ❌ 暂不可交付 | 值域记录语义未定案，用户根本选不到 |
| OSD 文本提示 | 新选项的屏幕文字 | ❌ 不可交付 | 显示描述符没有文本槽，没找到安全路线 |
| ISO 0.5EV 步进 | 更细的 ISO 档 | ❌ 不可交付 | 包内找不到消费端；退化方案已判“不可交付” |
| C60/C120 预拍 | 高速模式预拍 | ❌ 已砍 | 主动不做 |

逐条细节（包括每个“仅离线验证”到底核了什么）见 [docs/features.md](docs/features.md)。

### 版本线

| 线 | 分支 / 标签 | 含义 | 状态 |
|---|---|---|---|
| **V10** | `main` | 当前稳定线。离线验证全绿：字节级复核、全套 gauntlet、可复现重建 | ⚠️ 离线绿；**❌ 请勿刷机**——上文的开机循环事故就是 V10 构建造成的 |
| **V11 `bricking-edge`** | `bricking-edge`（分支与标签） | 热修／取证线，因事故得名：剥掉 V10 三处嫌疑改动、四个补丁窗回退到上一构建。见 [docs/bricking-edge.md](docs/bricking-edge.md) | 🧪 只做过离线构建与字节级比对的试验包，从未放出；事故定谳前冻结 |

`bricking-edge` 这个名字是故意留下的黑色幽默：这条线存在的原因，就是有一台
相机被刷成了砖。见 [docs/versions.md](docs/versions.md)。

### 自己构建（build your own）

需要 Python 3.10+ 与固定依赖。预拍功能还需支持 AArch64 的 Clang：只要编译器
生成的代码字节与已审阅配方不一致，构建立即中止。只构建 ProRes 不需要 C 编译器。

```sh
git clone https://github.com/A2Sumie/NijiN.git
cd NijiN
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

# 只读兼容性检查（对你的输入包）
python patch.py "/path/to/Z_8_0311.bin" --features prores precapture --check

# 构建到一个全新的空输出目录
python patch.py "/path/to/Z_8_0311.bin" --features prores precapture \
    --version 03.11 --tag p0 --output build/mybuild

# 独立复核结果
python verify.py "/path/to/Z_8_0311.bin" "build/mybuild/Z_8_0311.bin" \
    --features prores precapture
```

然后运行测试套件，全部通过才算构建完成：

```sh
python tests/validate.py --stock "/path/to/Z_8_0311.bin" --report build/validate.json
python tests/validate_features.py --stock "/path/to/Z_8_0311.bin" --report build/features.json
python gauntlet/gauntlet.py run --kit build/mybuild --stock "/path/to/Z_8_0311.bin" --out build/gauntlet
```

完整流程、版本号口径与上机前检查单见 [docs/build.md](docs/build.md)；
这些检查能证明什么、不能证明什么，见 [docs/verification.md](docs/verification.md)。

### 本仓不含什么

沿用上游项目的处置惯例，以下内容严格排除、且严禁提交：固件或解密后的
程序字节、提取的字体、图标位图、字符串表、设备设置文件、第三方商业软件、手册、
拍摄样张、相机界面截图、个人数据或本机路径。运行目录即使在源码仓里也可能包含专有
二进制文件——务必保留在本地。见 [CONTRIBUTING.md](CONTRIBUTING.md)；push 前扫描脚本为
[tools/redline_scan.py](tools/redline_scan.py)。

### 目录结构

| 路径 | 内容 |
|---|---|
| `patch.py`、`verify.py`、`features.py`、`configure.py` | 构建驱动、独立核验器、功能组合器、配置文件生成 |
| `z8prores/`、`z8precapture/`、`z8opengate/`、`z8menuh/` | 各功能模块：补丁配方与新增代码源码（C、AArch64 编码器、链接器、补丁脚本） |
| `resources/` | 补丁定义：sha256 指纹窗口、偏移、入口地址、常量——只有哈希与偏移 |
| `tests/` | 离线验证套件（不访问相机、不带固件） |
| `gauntlet/` | 强制测试电池：七道门、变异电池、组合穷举、结构酷刑 |
| `tools/` | 仓库卫生检查与红线扫描器 |
| `recipes/` | 研究线的构建配方（本分支：`bricking-edge` 回退配方） |
| `docs/` | 构建、功能、验证、风险、版本口径与上游病症对照 |
| `assets/` | 本项目自有的 NijiN 文字标与图标 |

源码注释中引用的开发笔记编号属于内部记录，不随本仓对外分发。

### 社区

讨论、提问与互助：**QQ 群 `1108781835`**。群内同样遵守
[CONTRIBUTING.md](CONTRIBUTING.md) 的红线要求：不传固件、不传 dump、不传个人数据。

### 许可与署名

原创工具源码采用 [GPL-3.0-only](LICENSE) 协议发布。本工作派生自并建立在
NikonFirmwarePatch（GPL-3.0-only）之上；完整署名、参考来源与许可边界见
[NOTICE.md](NOTICE.md)。Nikon 官方固件未被重新许可，生成的输出也不代表以
GPL 许可分发。本项目与 Nikon 无隶属关系，亦未获其官方背书。
