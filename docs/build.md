# Build your own

This repository does not contain ready-made firmware. You build the update package locally using your own copy of the official release. This page outlines the complete workflow.

## What you need

- Python 3.10 or newer, and the pinned dependency in `requirements.txt` (Capstone, used to inspect generated instructions).
- For `precapture` (and anything utilizing its loader): Clang targeting AArch64. The build compiles the C sources in `z8precapture/` and `z8opengate/`, rejecting any compiler output that differs from the reviewed bytes. Building `prores` alone requires no compiler.
- A few hundred MB of free space for the output directory. The build tooling never overwrites an existing output directory.

## Your input

The only publicly supported input is the **official Nikon Z8 C 3.11 update package**. Download it directly from [Nikon's download center](https://downloadcenter.nikonimglib.com/en/download/fw/606.html) under Nikon's terms. An update package from one version is not interchangeable with that of another.

Expected properties (the tools check them):

| Property | Value |
|---|---|
| File size | 99,051,117 bytes |
| SHA-256 | `d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96` |
| Modules | five, each with its own SHA-256 in `z8prores/package.py` |
| Payload (EG) size | 81,807,711 bytes inside the package |

These values serve as fingerprints only; this repository stores no payload bytes from that file. An unsupported input might pass partial checks by coincidence, but that provides neither compatibility nor a safety guarantee.

## Steps

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

# 1. read-only compatibility check of your input against the recipe hashes
python patch.py "/path/to/Z_8_0311.bin" --features prores precapture --check

# 2. build (output directory must not exist yet)
python patch.py "/path/to/Z_8_0311.bin" --features prores precapture \
    --version 03.11 --tag p0 --output build/mybuild

# 3. independent re-verification of the produced pair
python verify.py "/path/to/Z_8_0311.bin" "build/mybuild/Z_8_0311.bin" \
    --features prores precapture

# 4. offline test suites
python tests/validate.py --stock "/path/to/Z_8_0311.bin" --report build/validate.json
python tests/validate_features.py --stock "/path/to/Z_8_0311.bin" --report build/features.json

# 5. the mandatory battery (gates, mutations, combinations, structural)
python gauntlet/gauntlet.py run --kit build/mybuild \
    --stock "/path/to/Z_8_0311.bin" --out build/gauntlet
```

`--features` accepts any combination of `prores`, `precapture`, `opengate`, and `menuh`, without duplicates. Note that `opengate` requires `precapture`: only the pre-capture loader window maps its hook code. Without `--features` or `--interactive`, the tool defaults to building `prores` alone.

The build halts on any mismatch: wrong input, modified source bytes, compiler output differing from the reviewed recipe, a pre-existing output directory, or a target patch window failing the published `old_sha256` fingerprint. There is no force or bypass switch.

## Output

| File | What it is |
|---|---|
| `Z_8_<version>.bin` | The locally generated update package |
| `manifest.json` | What was edited, where, and the source hashes of the recipe used |
| `SHA256SUMS.txt` | Checksums for the output directory |
| `Z8PRE*.CFG` | Pre-capture configuration files (only with `precapture`) |
| `Z8OG.CFG` | OpenGate enable file (only with `opengate`) |

Always build from a fresh official package, never from an earlier output. Regenerate and replace old configuration files whenever the recipe revision changes.

## Version numbers and identity

`--version NN.NN` sets the version written into the package; `--tag` accepts a lowercase letter followed by a digit (defaults to `p0`). The tools stamp an internal identity in the format `NN.NN.xN`.

Where upstream strictly required a higher version number, this fork deliberately accepts an output version **equal to or higher than** the input version. This adjustment is based on hardware observations where a lower-numbered package was accepted by the camera; the relaxed check is marked as `LOCAL DEVIATION` in the source. This is provided for convenience rather than as a compatibility claim: modifying the number adds no functionality, and camera acceptance for any given version number is **not guaranteed and, for the same-number case, not tested**. If an update is refused, rebuild using a higher number.

Never stamp `04.01`: it is a placeholder value that the test battery explicitly treats as a defect.

## The gauntlet

`gauntlet/gauntlet.py run` executes the mandatory test battery. In brief: byte-level verification of every declared patch window and all regions outside them, package identity and integrity-chain checks, feature-combination rules, configuration file validation, offline test suites, output-directory hygiene checks, and pre-flash checklist generation. It then stress-tests its own output: a mutation suite that rebuilds structurally valid yet intentionally corrupted packages, an exhaustive combination matrix covering rejected feature combinations, and structural stress tests (round-trip serialization, single-byte mutations with repaired integrity chains, reverse chain traversals, and cross-tool decode comparisons).

Exit code 0 confirms that every gate passed. Items marked `SKIPPED` are checks that require a local input or an external tool you did not provide; they are never counted as green.

## If you ever put this on a camera

Read [risks.md](risks.md) first, and understand that the current stable line is the one that caused a boot loop during development. If you proceed anyway: keep a verified official package ready to reflash, work with a single dedicated test card, change one variable at a time, and stop at the first sign of an anomaly instead of pushing through it. The generated `PREFLIGHT_CHECKLIST.md` serves as the operational checklist. Flashing and camera operation are entirely your own responsibility; the tools never interface with hardware.

## 简体中文

- 需要 Python 3.10+ 与固定版本的依赖项。预拍及依赖其加载器的功能需要支持 AArch64 目标的 Clang；若编译产物与已审阅字节不一致，构建会直接报错中止。仅构建 ProRes 时不需要编译器。
- 输入必须是自行下载的官方 Z8 C 3.11 更新包（文件大小 99,051,117 字节，sha256 为 `d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96`）；本仓库不包含该文件的任何数据，仅用于指纹核验。
- 构建流程：`--check` 只读检查 → `patch.py` 执行构建（输出目录此前不得存在）→ `verify.py` 独立复核产物 → `tests/` 运行两套离线测试 → `gauntlet/gauntlet.py run` 运行完整测试集。
- 构建输出包括更新包、`manifest.json`、`SHA256SUMS.txt` 与 CFG 配置文件。每次构建都必须以原始官方固件包为输入，切勿在之前生成的产物上叠加修改；配方更新时须重新生成并替换旧配置文件。
- 版本标识通过 `--version NN.NN` 与 `--tag`（默认 `p0`）指定。上游要求输出版本号必须严格高于输入版本，本分支主动放宽为“≥”（源码内标注为 `LOCAL DEVIATION`，改动依据为真机可接受较低版本包的实际观察）；此放宽仅为操作便利，不代表兼容性承诺，且同版本号受理情况**未实测**；任何情况下都不要打 `04.01`。
- 若要写入相机，请先阅读 [risks.md](risks.md)：当前稳定分支在早期开发阶段曾引发过开机循环。刷机与相机操作的风险完全由个人承担，工具链本身不直接接触任何硬件。
