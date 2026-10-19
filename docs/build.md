# Build your own

Nothing in this repository is a ready-made firmware. You build a package
locally from your own copy of the official update. This page is the whole
flow.

## What you need

- Python 3.10 or newer, and the pinned dependency in `requirements.txt`
  (Capstone, used to inspect generated instructions).
- For `precapture` (and anything that rides its loader): Clang with an
  AArch64 target. The build compiles the C sources in `z8precapture/` and
  `z8opengate/` and refuses any compiler whose output differs from the
  reviewed bytes. `prores` alone needs no compiler.
- A few hundred MB of free space for the output directory. The tools never
  overwrite an existing output directory.

## Your input

The publicly supported input is the **official Nikon Z8 C 3.11 update
package**. Get it from
[Nikon's download center](https://downloadcenter.nikonimglib.com/en/download/fw/606.html)
yourself, under Nikon's terms. An upgrade package is not the same file as
another version's package.

Expected properties (the tools check them):

| Property | Value |
|---|---|
| File size | 99,051,117 bytes |
| SHA-256 | `d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96` |
| Modules | five, each with its own SHA-256 in `z8prores/package.py` |
| Payload (EG) size | 81,807,711 bytes inside the package |

These are fingerprints only. This repository stores no bytes of that file.
A different input may pass some regional checks by coincidence; that is
neither support nor a safety guarantee.

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

`--features` accepts any combination of `prores`, `precapture`, `opengate`,
`menuh`, without duplicates. `opengate` requires `precapture`: only the
pre-capture loader window maps its hook code. Without `--features` or
`--interactive` the tool builds `prores` alone.

The build stops on any mismatch: wrong input, changed source bytes,
compiler output that differs from the reviewed recipe, an output directory
that already exists, or a patch window whose current bytes do not match the
published `old_sha256` fingerprint. There is no force or bypass switch.

## Output

| File | What it is |
|---|---|
| `Z_8_<version>.bin` | The locally generated update package |
| `manifest.json` | What was edited, where, and the source hashes of the recipe used |
| `SHA256SUMS.txt` | Checksums for the output directory |
| `Z8PRE*.CFG` | Pre-capture configuration files (only with `precapture`) |
| `Z8OG.CFG` | OpenGate enable file (only with `opengate`) |

Build from a fresh official package every time, never from an earlier
output. Regenerate and replace old configuration files when the recipe
revision changes.

## Version numbers and identity

`--version NN.NN` sets the version written into the package; `--tag` is a
lowercase letter plus a digit (default `p0`). The tools stamp an internal
identity of the form `NN.NN.xN`.

This fork deliberately accepts an output version **equal to or higher
than** the input version, where upstream required strictly higher. The
reason is a real-camera observation that a lower-numbered package was
accepted; the looser check is marked `LOCAL DEVIATION` in the source. It is
a convenience, not a compatibility claim: changing the number adds no
function, and acceptance of any given number by a camera is **not
guaranteed and, for the same-number case, not tested**. If an update is
refused, rebuild with a higher number.

Never stamp `04.01`: it is a placeholder value and the test battery treats
it as a defect.

## The gauntlet

`gauntlet/gauntlet.py run` is the mandatory battery. Roughly: byte-level
verification of every declared window and everything outside them, package
identity and integrity-chain checks, feature-combination rules, configuration
file checks, the offline test suites, output-directory hygiene, and a
generated pre-flash checklist. It then attacks its own result: a mutation
battery that rebuilds structurally valid but wrong packages, an exhaustive
combination matrix including refused combinations, and structural torture
(round-trip, one-byte mutation with the whole integrity chain repaired,
reverse chain walk, cross-tool decode comparison).

Exit code 0 means every gate passed. Items marked `SKIPPED` are checks that
need a local input or an external tool you did not provide; they are never
counted as green.

## If you ever put this on a camera

Read [risks.md](risks.md) first and understand that the current stable line
is the one that caused a boot loop during development. If you proceed
anyway: keep the official package verified and ready to reflash, work with a
single test card, change one variable at a time, and stop at the first
anomaly instead of pushing through it. The generated `PREFLIGHT_CHECKLIST.md`
is the operational checklist. Flashing and camera operation are yours alone;
the tools never touch hardware.

## 简体中文

- 需要 Python 3.10+ 与固定依赖；预拍相关功能还需支持 AArch64 的 Clang，编译产物
  与已审阅字节不一致则停止构建；仅 ProRes 不需要编译器。
- 输入必须是自备的官方 Z8 C 3.11 更新包（99,051,117 字节，sha256
  `d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96`）；本仓只存指纹。
- 流程：`--check` 只读检查 → `patch.py` 构建（输出目录必须是新的）→ `verify.py`
  独立复核 → `tests/` 两个套件 → `gauntlet/gauntlet.py run` 全套电池。
- 输出含更新包、`manifest.json`、`SHA256SUMS.txt` 与 CFG 配置文件；每次从全新的
  官方包构建，不叠加旧产物。
- 版本号 `--version NN.NN`、`--tag`（默认 `p0`）。本分支有意把“必须高于输入号”
  放宽为“≥”（源码内标注 `LOCAL DEVIATION`，依据是真机对低号包的受理观察）；
  这不代表兼容性承诺，同号受理**未实测**；永远不要打 `04.01`。
- 要上机先读 [risks.md](risks.md)：当前稳定线正是造成过开机循环事故的那条线。
  刷机与相机操作全归你自己。
