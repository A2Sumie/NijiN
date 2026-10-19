**WIP. Owner's Z8 bricked! Use at your own risk.**
**施工中。作者的 Z8 已经刷砖！风险自担。**

<p align="center">
  <img src="assets/lockup/nijin-lockup-transparent.png" alt="NijiN" width="420">
</p>

# NijiN

**QQ Group / QQ 群：`1108781835`**

[English](#english) · [简体中文](#简体中文)

An open-source toolchain for building custom Nikon Z8 (C 3.11) firmware packages locally. 

---

## English

### ⚠️ Warning

**Flashing firmware built with this tool can brick your camera.** 

During development, a V10 build passed all offline verification checks but caused an unrecoverable boot loop when flashed to hardware, requiring factory repair. **Passing offline checks does not guarantee hardware safety.**

- All features are experimental. Do not use this on cameras needed for production or critical shoots.
- See [docs/risks.md](docs/risks.md) for current risk assessments and [docs/upstream-issue-3.md](docs/upstream-issue-3.md) for forensics on a similar bricking incident in another Z8 project.
- Provided as-is with no warranty. You assume all risks for hardware damage or data loss. See [NOTICE.md](NOTICE.md).

### How It Works

NijiN takes an official Nikon Z8 C 3.11 firmware file (`Z_8_0311.bin`, 99,051,117 bytes) and generates a patched firmware package containing the features you select.

**Bring your own firmware.** This repository contains **no firmware and no prebuilt binaries** (see [NOTICE.md](NOTICE.md)); download the official package from Nikon's download center under Nikon's terms and hand it to the tool. The tools never talk to a camera or a card: no downloader, no card writer, no flashing utility.

1. **Input verification**: Checks the stock firmware against SHA-256 fingerprint windows.
2. **Compilation**: Compiles custom C and AArch64 assembly routines from source.
3. **Patching**: Applies selected feature patches and a shared loader modification.
4. **Output verification**: Independently verifies that all bytes outside target patch windows remain untouched, and all patched windows match expected recipe hashes byte-for-byte.
5. **Validation**: Runs an automated test suite (`gauntlet/`) to verify structural integrity.

### Features

Status legend: **✅ Tested on hardware** · **⚠️ Verified offline only** · **🧪 Experimental / incomplete** · **❌ Blocked / dropped**

| Feature | Description | Status | Notes |
|---|---|---|---|
| `precapture` — HE★ pre-capture | Records pre-release frames as true HE★ RAW | ✅ (early build) | Tested on hardware in an early build; subsequent changes to this module are ⚠️ |
| `precapture` — C15/C30 window | Pre-capture buffer window, 1s limit, and frame cap for C15/C30 | ✅ (C15) / ⚠️ (C30) | C30 1-second clamp and 20-frame ring buffer cap are only verified offline |
| `precapture` — Image quality menu | Applies RAW / RAW+JPEG / JPEG settings to both pre-capture and full-press frames | ⚠️ | Offline verified; menu behavior not yet tested on hardware |
| `precapture` — Full-size preview & playback | Embeds 8256×5504 previews in NEFs and registers files in the camera's playback database | ⚠️ | Offline verified; not tested on hardware |
| `precapture` — RAW-only, thumbnails, timestamps | Skips JPEG writes, writes fixed-size small previews, sets file timestamp to capture time | ⚠️ | Offline verified only |
| `precapture` — Lossless / HE tiers | Allows pre-capture in Lossless RAW or HE instead of HE★ | 🧪 | Lossless strip length uses an unconfirmed static estimate |
| `prores` — ProRes quality | Adds HQ / 422 / LT / Proxy selection per shooting menu bank | ⚠️ | Identical to upstream patch bytes; UI icon does not reflect the selected tier |
| `opengate` — OpenGate 3:2 video | Experimental 8256×5504 video recording configured via `Z8OG.CFG` | 🧪 | Unconfirmed whether the sensor readout window actually scales to the new dimensions |
| `menuh` — Custom menu group | Adds a new menu group shell and a persistent setting item | ⚠️ | Group is visible but empty; UI behavior not tested on hardware |
| Shot counter fix | Updates remaining frame counter based on actual output settings | ⚠️ | Patches the display readout rather than the underlying calculation; may need tuning for other configs |
| Lens correction block | Writes NEF lens correction blocks for 7 known lenses | 🧪 | Not tested in Adobe ACR / NX Studio; skips writing on unknown lenses (fail-safe) |
| D5 metadata placeholders | Writes empty metadata blocks expected by certain RAW parsers | 🧪 | Parser compatibility untested |
| Bit-depth selection | 12-bit / 14-bit switching via configuration | 🧪 | Backend logic implemented; menu UI not yet wired up |
| D3 "Max." duration | Adds a maximum pre-capture duration option | ❌ Blocked | Value-range definitions unresolved; option cannot be selected in UI |
| OSD text hints | On-screen help text for new options | ❌ Blocked | Display descriptors lack text slots; no safe implementation found |
| ISO 0.5 EV steps | Finer ISO step increments | ❌ Blocked | Target control logic is unreachable within the firmware package |
| C60/C120 pre-capture | Pre-capture for high-speed burst modes | ❌ Dropped | Not planned |

For full implementation details and verification scope, see [docs/features.md](docs/features.md).

### Branches & Releases

| Line | Branch / Tag | Description | Status |
|---|---|---|---|
| **V10** | `main` | Passes all offline checks and reproducible build tests. | **❌ Do not flash** — caused the hardware boot loop incident. |
| **V11 `bricking-edge`** | `bricking-edge` (branch and tag) | Forensics/hotfix line: strips the 3 suspect V10 changes and rolls back 4 patch windows. Ships as `03.11.p1` packages (`p0` = the historical smoke/incident generation). See [docs/bricking-edge.md](docs/bricking-edge.md). | **⛔ V11.1 = UNSAFE (known defects, under investigation) — do not flash.** Built and byte-verified offline, published 2026-10-19 as a toolkit trial only; never on hardware; the line stays frozen until the V10 boot-loop cause is settled. See [docs/risks.md](docs/risks.md#known-unsafe-v111-2026-10-19). |

See [docs/versions.md](docs/versions.md) for version history and [docs/unfreeze-criteria.md](docs/unfreeze-criteria.md) for the checklist required to lift the release freeze.

### Quick Start

1. Download the official Nikon Z8 firmware 3.11 (`Z_8_0311.bin`) from the [Nikon Download Center](https://downloadcenter.nikonimglib.com/en/download/fw/606.html).
2. Install Python 3.10+. Building `precapture` also requires Clang with AArch64 target support (`prores`-only builds do not require Clang).

```sh
git clone https://github.com/A2Sumie/NijiN.git
cd NijiN
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

# 1. Check input firmware compatibility
python patch.py "/path/to/Z_8_0311.bin" --features prores precapture --check

# 2. Build patched firmware into a new directory
python patch.py "/path/to/Z_8_0311.bin" --features prores precapture \
    --version 03.11 --tag p1 --output build/mybuild

# 3. Independently verify the output binary
python verify.py "/path/to/Z_8_0311.bin" "build/mybuild/Z_8_0311.bin" \
    --features prores precapture

# 4. Run validation suites
python tests/validate.py --stock "/path/to/Z_8_0311.bin" --report build/validate.json
python tests/validate_features.py --stock "/path/to/Z_8_0311.bin" --report build/features.json
python gauntlet/gauntlet.py run --kit build/mybuild --stock "/path/to/Z_8_0311.bin" --out build/gauntlet
```

For detailed build instructions and verification explanations, see [docs/quickstart.md](docs/quickstart.md), [docs/build.md](docs/build.md), and [docs/verification.md](docs/verification.md).

### Repository Layout

| Path | Description |
|---|---|
| `patch.py`, `verify.py`, `features.py`, `configure.py` | Build script, verifier, feature composer, and config file generator |
| `z8prores/`, `z8precapture/`, `z8opengate/`, `z8menuh/` | Feature modules (patch recipes, C/AArch64 assembly sources, linker scripts) |
| `resources/` | SHA-256 fingerprint windows, file offsets, entry addresses, and constants |
| `tests/` | Offline unit and feature validation suites |
| `gauntlet/` | Automated integration test suite (gate checks, mutation testing, combination matrix, stress tests) |
| `tools/` | Repository maintenance scripts and pre-push compliance scanner ([tools/redline_scan.py](tools/redline_scan.py)) |
| `recipes/` | Patch recipes for specific research branches |
| `docs/` | Project documentation |
| `assets/` | The NijiN wordmark and icon, created for this project |

### Contributing & License

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting pull requests. Do not commit proprietary firmware binaries, dumps, extracted assets, or personal data.

Licensed under [GPL-3.0-only](LICENSE). Derived from NikonFirmwarePatch (GPL-3.0-only); see [NOTICE.md](NOTICE.md) for full attribution. This project is not affiliated with or endorsed by Nikon.

---

## 简体中文

### ⚠️ 警告

**刷入本项目构建的固件可能导致相机变砖。**

在开发过程中，V10 分支的一个构建版本通过了所有离线校验，但刷入测试机后直接导致无限重启（Boot loop），最终只能返厂维修。**离线校验全绿不代表真机安全。**

- 所有功能均处于实验阶段，切勿用于工作机或重要拍摄。
- 当前风险评估见 [docs/risks.md](docs/risks.md)；另一个 Z8 改装项目的同类变砖故障对比与排查分析见 [docs/upstream-issue-3.md](docs/upstream-issue-3.md)。
- 本项目不提供任何担保，刷机、硬件损坏或数据丢失的风险完全由使用者自行承担。详见 [NOTICE.md](NOTICE.md)。

### 工作原理

NijiN 以用户自备的官方 Nikon Z8 C 3.11 固件包（`Z_8_0311.bin`，99,051,117 字节）为输入，在本地生成打好补丁的固件包。

**自带固件（bring your own firmware）。** 本仓**不含固件、不含预编译产物**（见 [NOTICE.md](NOTICE.md)）；请自行从 Nikon 下载中心按其条款获取官方升级包再交给工具。工具不与相机或存储卡通信：不下载、不写卡、不带任何刷写程序。

1. **输入校验**：通过 SHA-256 指纹窗口校验原厂固件。
2. **代码编译**：从源码编译新增的 C 与 AArch64 汇编程序。
3. **写入补丁**：写入所选功能的补丁窗口及共享加载器修改。
4. **输出复核**：独立校验输出文件，确保补丁窗口之外的所有字节与原厂完全一致，且补丁窗口内的字节与预设配方哈希严格匹配。
5. **集成测试**：运行自动化测试套件（`gauntlet/`）检验固件结构完整性。

### 功能列表

状态图例：**✅ 已上机验证** · **⚠️ 仅离线验证** · **🧪 实验性 / 未完成** · **❌ 受阻 / 已放弃**

| 功能 | 说明 | 状态 | 备注 |
|---|---|---|---|
| `precapture` — HE★ 预拍 | 将预拍帧保存为真正的 HE★ RAW | ✅（早期构建） | 早期版本已在真机拍出 HE★ NEF；后续对此模块的改动属 ⚠️ |
| `precapture` — C15/C30 预拍窗口 | C15/C30 连拍的缓存窗口、1 秒时长限制与帧数上限 | ✅ (C15) / ⚠️ (C30) | C30 的 1 秒限制与 20 帧环形缓冲上限仅做过离线验证 |
| `precapture` — 画质菜单联动 | RAW / RAW+JPEG / JPEG 设置同时作用于预拍帧与正式拍摄帧 | ⚠️ | 已通过离线验证，菜单表现在真机上尚未确认 |
| `precapture` — 全尺寸预览与机内回放 | NEF 内嵌 8256×5504 预览图，并写入原厂相册数据库以支持回放 | ⚠️ | 已通过离线验证，未做真机回放测试 |
| `precapture` — 纯 RAW / 缩略图 / 时间戳 | 跳过 JPEG 写入、生成固定尺寸缩略图、文件时间设为实际拍摄时间 | ⚠️ | 仅通过离线验证 |
| `precapture` — 无损 / HE 预拍档位 | 预拍支持选择无损压缩 RAW 或 HE 格式 | 🧪 | 无损格式的条带长度（strip length）目前为静态估算值，未经验证 |
| `prores` — ProRes 画质选择 | 支持按拍摄菜单库分别保存 HQ / 422 / LT / Proxy 四档画质 | ⚠️ | 补丁字节与上游项目一致；机内图标不会随所选档位变化 |
| `opengate` — OpenGate 3:2 录像 | 通过 `Z8OG.CFG` 启用 8256×5504 实验性视频录制 | 🧪 | 传感器实际读出区域是否跟随新分辨率变化尚未证实 |
| `menuh` — 自定义菜单组 | 新增菜单组框架及一个支持保存/加载的设置项 | ⚠️ | 菜单组可见且可进入，但尚无实际功能条目；未上机测试 |
| 剩余张数显示修正 | 根据实际输出配置修正剩余可拍张数显示 | ⚠️ | 仅修改了显示端的读取值，未改底层计算逻辑；切换其他配置可能需重新调整 |
| 镜头校正数据块 | 为 7 支已知型号镜头写入 NEF 镜头校正信息 | 🧪 | 未在 ACR / NX Studio 中测试兼容性；遇到未知镜头则不写入（安全回退） |
| D5 兼容元数据占位 | 写入部分第三方解析器所需的空元数据块 | 🧪 | 第三方软件的实际兼容性未测试 |
| 位深选择 | 通过配置切换 12-bit / 14-bit 输出 | 🧪 | 底层消费逻辑已实现，但尚未对接机内菜单 |
| D3 “Max.” 预拍时长 | 增加一档最大预拍时长选项 | ❌ 受阻 | 参数范围定义尚未解析完成，机内菜单无法选中 |
| OSD 文本提示 | 为新增选项显示屏幕提示文字 | ❌ 受阻 | 显示描述符中没有预留文本槽位，未找到安全的实现方式 |
| ISO 0.5 EV 步进 | 更精细的 ISO 调节步长 | ❌ 受阻 | 固件包内无法触达该参数的底层控制逻辑 |
| C60/C120 预拍 | 高速连拍模式下的预拍功能 | ❌ 已放弃 | 无计划支持 |

各功能的详细实现与验证范围见 [docs/features.md](docs/features.md)。

### 分支与版本状态

| 版本线 | 分支 / 标签 | 说明 | 状态 |
|---|---|---|---|
| **V10** | `main` | 离线校验、集成测试与可复现构建全部通过。 | **❌ 请勿刷入** —— 导致测试机无限重启变砖的版本。 |
| **V11 `bricking-edge`** | `bricking-edge`（分支与标签） | 故障排查与热修线：移除 V10 中 3 处嫌疑改动、4 个补丁窗口回退到上一构建。以 `03.11.p1` 包发布（`p0` = 历史冒烟／事故代）。详见 [docs/bricking-edge.md](docs/bricking-edge.md)。 | **⛔ V11.1 = 不安全（已知缺陷，调查中）——勿刷，请勿刷写。** 仅做过离线构建与字节级比对，2026-10-19 只以 toolkit 试验品身份放出；从未上机；V10 开机循环定谳前保持冻结。详见 [docs/risks.md](docs/risks.md#known-unsafe-v111-2026-10-19)。 |

版本演进历史见 [docs/versions.md](docs/versions.md)，解除冻结所需的验收标准见 [docs/unfreeze-criteria.md](docs/unfreeze-criteria.md)。

### 快速开始

1. 从 [Nikon 下载中心](https://downloadcenter.nikonimglib.com/en/download/fw/606.html) 下载官方 Z8 3.11 固件包（`Z_8_0311.bin`）。
2. 安装 Python 3.10+。若需构建 `precapture` 功能，还需安装支持 AArch64 目标架构的 Clang（仅构建 `prores` 则不需要 C 编译器）。

```sh
git clone https://github.com/A2Sumie/NijiN.git
cd NijiN
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

# 1. 检查原厂固件兼容性
python patch.py "/path/to/Z_8_0311.bin" --features prores precapture --check

# 2. 构建改装固件到新建的空目录
python patch.py "/path/to/Z_8_0311.bin" --features prores precapture \
    --version 03.11 --tag p1 --output build/mybuild

# 3. 独立复核生成的固件
python verify.py "/path/to/Z_8_0311.bin" "build/mybuild/Z_8_0311.bin" \
    --features prores precapture

# 4. 运行自动化测试套件
python tests/validate.py --stock "/path/to/Z_8_0311.bin" --report build/validate.json
python tests/validate_features.py --stock "/path/to/Z_8_0311.bin" --report build/features.json
python gauntlet/gauntlet.py run --kit build/mybuild --stock "/path/to/Z_8_0311.bin" --out build/gauntlet
```

完整的构建说明与校验原理解析见 [docs/quickstart.md](docs/quickstart.md)、[docs/build.md](docs/build.md) 与 [docs/verification.md](docs/verification.md)。

### 目录结构

| 路径 | 内容 |
|---|---|
| `patch.py`、`verify.py`、`features.py`、`configure.py` | 构建脚本、独立校验器、功能组合器、配置文件生成工具 |
| `z8prores/`、`z8precapture/`、`z8opengate/`、`z8menuh/` | 各功能模块源码（补丁配方、C 与 AArch64 汇编代码、链接脚本） |
| `resources/` | 补丁定位数据：SHA-256 指纹窗口、文件偏移量、入口地址与常量 |
| `tests/` | 离线单元测试与功能验证脚本 |
| `gauntlet/` | 自动化集成测试套件（准入检查、变异测试、功能组合测试与结构压力测试） |
| `tools/` | 仓库维护工具与提交前合规扫描脚本（[tools/redline_scan.py](tools/redline_scan.py)） |
| `recipes/` | 特定研究分支的构建配方 |
| `docs/` | 项目文档 |
| `assets/` | 本项目自有的 NijiN 文字标与图标 |

### 参与贡献与开源许可

讨论、提问与互助：**QQ 群 `1108781835`**。

提交代码前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。严禁向仓库或交流群提交任何原厂固件二进制文件、内存转储（dump）、提取的受版权保护资源或个人隐私路径。

本项目工具源码采用 [GPL-3.0-only](LICENSE) 协议开源，派生自 NikonFirmwarePatch（GPL-3.0-only）。完整的署名信息与许可边界说明见 [NOTICE.md](NOTICE.md)。本项目与 Nikon（尼康）无任何隶属或合作关系。
