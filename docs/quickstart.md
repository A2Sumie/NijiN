# Quickstart

Build and verify a patched firmware package from the official Nikon Z8 update.

**⚠️ WARNING**
- **V11.1 (`03.11.p1`) is UNSAFE** — known defects, see [risks.md](risks.md#known-unsafe-v111-2026-10-19). **Do not flash.**
- **WIP. Owner's Z8 bricked! Use at your own risk.** Read [risks.md](risks.md) before proceeding.
- QQ Group: `1108781835`

## Prerequisites

- macOS or Linux
- Python 3.10 or newer
- ~500 MB free disk space
- Official **Nikon Z8 C 3.11** firmware (`Z_8_0311.bin`) from the [Nikon Download Center](https://downloadcenter.nikonimglib.com/en/download/fw/606.html)
- *(Optional)* Clang with AArch64 target support — required for `precapture`; not needed if only building `prores`

## Build Steps

**1. Verify the official firmware**

Ensure the file size is `99,051,117` bytes and the SHA-256 hash matches:

```sh
shasum -a 256 /path/to/Z_8_0311.bin
# Expected: d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96
```

**2. Install the tools**

```sh
git clone https://github.com/A2Sumie/NijiN.git
cd NijiN
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

**3. Check compatibility (read-only)**

```sh
python patch.py "/path/to/Z_8_0311.bin" --features prores precapture --check
```

A JSON output confirms the input file is supported.

**4. Build the package**

Select features (`prores`, `precapture`, `opengate`, `menuh`), set a version string, and specify a **new** output directory:

```sh
python patch.py "/path/to/Z_8_0311.bin" --features prores precapture \
    --version 03.11 --tag p1 --output build/first
```

**5. Verify the build**

```sh
python verify.py "/path/to/Z_8_0311.bin" "build/first/Z_8_0311.bin" \
    --features prores precapture
```

**6. Run validation tests (optional)**

```sh
python tests/validate.py --stock "/path/to/Z_8_0311.bin" --report build/validate.json
```

### Output

The `build/first/` directory will contain:
- `Z_8_0311.bin` (patched firmware)
- `manifest.json` and `SHA256SUMS.txt`
- `Z8PRE*.CFG` / `Z8OG.CFG` (configuration files for the selected features)

> **Build Status:** The commands above build the **V11.1** (`03.11.p1`) line, which is marked **⛔ UNSAFE** due to known defects ([risks.md](risks.md#known-unsafe-v111-2026-10-19)). Wait for the **V12** build to be finalized before building firmware for actual use. V12 (formerly V11.2) fixes these defects ([bricking-edge.md](bricking-edge.md)), but remains experimental and untested on hardware. See [features.md](features.md) for current feature status.

## Troubleshooting

| Error Message | Cause | Fix |
|---|---|---|
| `Input must be a regular firmware file` | Invalid path or not a regular file | Check the file path. |
| `Unsupported firmware length` | File is not 99,051,117 bytes | Use the official Nikon Z8 C 3.11 file. |
| `Unsupported outer package context` | Correct size, invalid file header/content | Re-download the firmware package. |
| `Package body CRC mismatch` / `Package SHA1 mismatch` | File is corrupted or modified | Re-download and verify the SHA-256 hash in Step 1. |
| `Incompatible region: …` | Firmware fingerprint mismatch | Only official Z8 C 3.11 is supported. |
| `Output directory already exists; use a new directory` | Target directory already exists | Specify a non-existent `--output` directory. |
| `AArch64 compilation failed: …` | Missing or broken Clang AArch64 toolchain | Install Clang with AArch64 support, or build `prores` only. |
| `Compiler output differs from the reviewed recipe` | Compiler produced unexpected binary output | Use the supported Clang version. |
| `opengate needs precapture: …` | Missing feature dependency | Add `precapture` to `--features`. |
| `Select prores, precapture, opengate, or any combination, without duplicates` | Duplicate or invalid feature name | List each feature once. Valid names: `prores`, `precapture`, `opengate`, `menuh`. |
| `Tag must be a lowercase letter and digit` | Invalid `--tag` format | Use `p1` (see [versions.md](versions.md)). |
| `Version must be two digits, a dot and two digits, e.g. 04.01` | Invalid `--version` format | Use `03.11`. *(Note: `04.01` is only a format example; never use `04.01` in practice. See [build.md](build.md)).* |
| `Building requires --version and --output; use --check for read-only inspection` | Missing required build flags | Add `--version 03.11 --output <new_dir>`. |
| `--check cannot be combined with output options` | Conflicting flags | Use either `--check` or build flags, not both. |
| `pytest` prints `skipped` | `NIJIN_EG_SLICE` is not set | Normal behavior; those tests require a local file slice. |

## Next Steps

- [build.md](build.md) — Full build workflow and versioning rules
- [features.md](features.md) — Feature descriptions and status
- [raw-precapture.md](raw-precapture.md) — RAW pre-capture usage guide and limitations
- [verification.md](verification.md) — Verification details and scope
- [risks.md](risks.md) — Incident report, risks, and rollback procedures

---

## 简体中文

**⚠️ 警告**
- **V11.1（`03.11.p1`）= 不安全**——存在已知缺陷（该线构建从未上机），详见 [risks.md](risks.md#known-unsafe-v111-2026-10-19)，**请勿刷入**。
- **施工中。作者的 Z8 已经刷砖！风险自担。** 操作前请先阅读 [risks.md](risks.md)。
- QQ 群：`1108781835`

### 环境要求

- macOS 或 Linux
- Python 3.10+
- 约 500 MB 可用磁盘空间
- 从[尼康下载中心](https://downloadcenter.nikonimglib.com/en/download/fw/606.html)获取的官方 **Nikon Z8 C 3.11** 固件包（`Z_8_0311.bin`）
- *(可选)* 支持 AArch64 的 Clang——仅构建 `precapture` 时需要；只构建 `prores` 则不需要

### 构建步骤

**1. 校验官方固件**

确认文件大小为 `99,051,117` 字节，且 SHA-256 校验和完全一致：

```sh
shasum -a 256 /path/to/Z_8_0311.bin
# 预期输出：d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96
```

**2. 安装工具与依赖**

```sh
git clone https://github.com/A2Sumie/NijiN.git
cd NijiN
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

**3. 兼容性检查（只读）**

```sh
python patch.py "/path/to/Z_8_0311.bin" --features prores precapture --check
```

若输出 JSON 报告，则说明输入固件受支持。

**4. 构建固件包**

选择功能（`prores`、`precapture`、`opengate`、`menuh`），指定版本号和一个**尚未存在**的输出目录：

```sh
python patch.py "/path/to/Z_8_0311.bin" --features prores precapture \
    --version 03.11 --tag p1 --output build/first
```

**5. 校验构建结果**

```sh
python verify.py "/path/to/Z_8_0311.bin" "build/first/Z_8_0311.bin" \
    --features prores precapture
```

**6. 运行测试（可选）**

```sh
python tests/validate.py --stock "/path/to/Z_8_0311.bin" --report build/validate.json
```

### 构建产物

生成的 `build/first/` 目录包含：
- `Z_8_0311.bin`（修改后的固件）
- `manifest.json` 与 `SHA256SUMS.txt`
- 所选功能对应的配置文件：`Z8PRE*.CFG` / `Z8OG.CFG`

> **版本状态说明**：上述命令构建的是 **V11.1**（`03.11.p1`）分支，状态为 **⛔ UNSAFE（已知缺陷）**，问题详见 [risks.md](risks.md#known-unsafe-v111-2026-10-19)。**建议等待 V12 验收后再构建实际使用的固件。** V12（原 V11.2）已修复该系列缺陷（见 [bricking-edge.md](bricking-edge.md)），但仍处于试验阶段，尚未上机实测。各功能状态见 [features.md](features.md)。

### 常见报错排查

| 报错信息 | 原因 | 解决方法 |
|---|---|---|
| `Input must be a regular firmware file` | 路径错误或不是常规文件 | 检查传入的文件路径。 |
| `Unsupported firmware length` | 文件大小不是 99,051,117 字节 | 使用官方 C 3.11 固件文件。 |
| `Unsupported outer package context` | 大小正确，但文件头或内容无效 | 重新下载官方固件包。 |
| `Package body CRC mismatch` / `Package SHA1 mismatch` | 文件已损坏或被修改 | 重新下载，并按步骤 1 核对 SHA-256。 |
| `Incompatible region: …` | 固件特征码不匹配 | 仅支持官方 Z8 C 3.11 固件。 |
| `Output directory already exists; use a new directory` | 输出目录已存在 | 指定一个新的 `--output` 目录。 |
| `AArch64 compilation failed: …` | 缺少可用的 Clang AArch64 工具链 | 安装支持 AArch64 的 Clang，或仅构建 `prores`。 |
| `Compiler output differs from the reviewed recipe` | 编译器生成的字节码与预期不一致 | 更换为受支持的 Clang 版本。 |
| `opengate needs precapture: …` | 缺少前置依赖功能 | 在 `--features` 中加上 `precapture`。 |
| `Select prores, precapture, opengate, or any combination, without duplicates` | 功能名称重复或拼写错误 | 有效名称为 `prores`、`precapture`、`opengate`、`menuh`，切勿重复。 |
| `Tag must be a lowercase letter and digit` | `--tag` 格式错误 | 使用 `p1`（详见 [versions.md](versions.md)）。 |
| `Version must be two digits, a dot and two digits, e.g. 04.01` | `--version` 格式错误 | 使用 `03.11`。*(注：`04.01` 仅为格式示例，实际切勿使用 `04.01`，详见 [build.md](build.md))。* |
| `Building requires --version and --output; use --check for read-only inspection` | 缺少构建参数 | 补上 `--version 03.11 --output <新目录>`。 |
| `--check cannot be combined with output options` | 混用了检查模式与构建模式参数 | `--check` 与输出参数二选一。 |
| `pytest` 输出 `skipped` | 未设置环境变量 `NIJIN_EG_SLICE` | 正常现象，被跳过的测试需要本地固件切片。 |

### 相关文档

- [build.md](build.md) — 完整构建流程与版本号规则
- [features.md](features.md) — 功能说明与当前状态
- [raw-precapture.md](raw-precapture.md) — RAW 预拍使用指南（准备、步骤与限制）
- [verification.md](verification.md) — 校验机制与覆盖范围
- [risks.md](risks.md) — 变砖事故说明、风险与回退方案
