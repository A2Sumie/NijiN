# Quickstart — build one package

One page, no background assumed. It gets you from the official Nikon
download to a locally built, independently verified package.

**WIP. Owner's Z8 bricked! Use at your own risk.**
**施工中。作者的 Z8 已经刷砖！风险自担。**

QQ group / QQ 群: `1108781835`

Flashing anything onto a camera is your own decision; the tools never touch
a camera or a card. Read [risks.md](risks.md) before you go near one.

## What you need

- macOS or Linux, Python 3.10 or newer, internet once (for Python packages)
- About 500 MB of free disk
- Optional: Clang with an AArch64 target — only for the `precapture`
  feature. Without it, build `prores` alone
- The official **Nikon Z8 C 3.11** update package, downloaded by you

## The path

**1. Get the firmware and check it.** From
[Nikon's download center](https://downloadcenter.nikonimglib.com/en/download/fw/606.html),
under Nikon's terms. The file must be exactly this:

```sh
shasum -a 256 /path/to/Z_8_0311.bin
# 99,051,117 bytes, and the hash must print:
# d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96
```

**2. Get the tools.**

```sh
git clone https://github.com/A2Sumie/NijiN.git
cd NijiN
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

**3. Read-only compatibility check.** This reads your file and stops:

```sh
python patch.py "/path/to/Z_8_0311.bin" --features prores precapture --check
```

A JSON report means your input is the supported one.

**4. Build.** Pick features (`prores`, `precapture`, `opengate`, `menuh`),
pick any version number, and use a directory that does not exist yet:

```sh
python patch.py "/path/to/Z_8_0311.bin" --features prores precapture \
    --version 03.11 --tag p0 --output build/first
```

**5. Verify.** This is a second tool that re-checks the result without
trusting the builder:

```sh
python verify.py "/path/to/Z_8_0311.bin" "build/first/Z_8_0311.bin" \
    --features prores precapture
```

**6. Test.** Optional but cheap:

```sh
python tests/validate.py --stock "/path/to/Z_8_0311.bin" --report build/validate.json
```

You now have `build/first/Z_8_0311.bin`, plus `manifest.json`,
`SHA256SUMS.txt` and any `Z8PRE*.CFG` / `Z8OG.CFG` for the features you
picked. **That is the end of the safe part.** What the file does on a
camera is a different question entirely — see [risks.md](risks.md) and the
status table in [features.md](features.md).

## When something fails

Every refusal below was produced by actually running the tool into that
situation; the last two rows are quoted from the source instead and marked.
There is no force or bypass switch.

| Message | What it means | Fix |
|---|---|---|
| `Input must be a regular firmware file` | Path wrong, or not a plain file | Check the path you passed |
| `Unsupported firmware length` | Not the update package | Use the 99,051,117-byte official C 3.11 file |
| `Unsupported outer package context` | Right size, wrong content | It is not an update package at all; re-download |
| `Package body CRC mismatch` / `Package SHA1 mismatch` | The file was altered or damaged | Re-download and check the SHA-256 in step 1 |
| `Incompatible region: …` *(quoted from source)* | Right package family, but a fingerprint window differs | Only official Z8 C 3.11 is supported |
| `Output directory already exists; use a new directory` | The tool never overwrites | Pick a new `--output` directory |
| `AArch64 compilation failed: …` | No working Clang | Build `prores` alone, or install Clang with an AArch64 target |
| `Compiler output differs from the reviewed recipe` *(quoted from source)* | A compiler produced different bytes than the reviewed ones | Use the reviewed Clang; the build will not "accept close enough" |
| `opengate needs precapture: only the precapture loader window (0x40970000) maps the hook code` | Feature rule | Add `precapture` to `--features` |
| `Select prores, precapture, opengate, or any combination, without duplicates` | A feature was listed twice, or an unknown name was used | List each feature once; the valid names are `prores`, `precapture`, `opengate`, `menuh` |
| `Tag must be a lowercase letter and digit` | `--tag` format | Use something like `p0` |
| `Version must be two digits, a dot and two digits, e.g. 04.01` | Version format. The example is only a format example — never actually stamp `04.01`, see [build.md](build.md) | Use e.g. `03.11` |
| `Building requires --version and --output; use --check for read-only inspection` | Missing flags | Add `--version NN.NN --output <new dir>` |
| `--check cannot be combined with output options` | Mixed the two modes | Use either `--check` or a build |
| pytest prints `skipped` | Tests that need a local file slice are gated | Normal without `NIJIN_EG_SLICE`; nothing is wrong |

If a message is not in this table, read it literally: every refusal is a
safety check, not a nuisance.

## Where to go next

- [build.md](build.md) — the full flow, version numbers, the gauntlet
- [features.md](features.md) — what each feature does and its honest state
- [raw-precapture.md](raw-precapture.md) — the shooting guide for RAW
  pre-capture: preparation, steps and limitations
- [verification.md](verification.md) — what the checks prove and what they
  cannot
- [risks.md](risks.md) — the incident, the risks, the rollback

## 简体中文

**WIP. Owner's Z8 bricked! Use at your own risk.**
**施工中。作者的 Z8 已经刷砖！风险自担。**

QQ 群：`1108781835`

刷不刷机由你自己决定，工具不碰相机不写卡；靠近相机之前先读
[risks.md](risks.md)。

**你需要**：macOS 或 Linux、Python 3.10+、约 500 MB 磁盘、（可选，仅 `precapture`
需要）支持 AArch64 的 Clang；以及**你自己下载**的官方 **Nikon Z8 C 3.11** 更新包。

**最短路径**（命令照抄，把路径换掉）：

1. **核固件**：`shasum -a 256 /path/to/Z_8_0311.bin` 必须是
   `d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96`，大小 99,051,117 字节。
2. **装工具**：`git clone` → `python3 -m venv .venv` → `source .venv/bin/activate` →
   `python -m pip install -r requirements.txt`。
3. **只读检查**：`python patch.py "/path/to/Z_8_0311.bin" --features prores precapture --check`
   ——输出 JSON 报告=输入被支持。
4. **构建**：`python patch.py "/path/to/Z_8_0311.bin" --features prores precapture
   --version 03.11 --tag p0 --output build/first`（输出目录必须是新的）。
5. **独立核验**：`python verify.py "/path/to/Z_8_0311.bin"
   "build/first/Z_8_0311.bin" --features prores precapture`。
6. **测试**（可选）：`python tests/validate.py --stock "/path/to/Z_8_0311.bin"
   --report build/validate.json`。

到手的东西：`Z_8_0311.bin` + `manifest.json` + `SHA256SUMS.txt` + 相应的
`Z8PRE*.CFG`／`Z8OG.CFG`。**安全的部分到此为止**——文件上机会怎样完全是另一个问题，
见 [risks.md](risks.md) 与 [features.md](features.md) 的状态表。

**出错对照表**（完整表见英文部分，每条都实测触发过，仅两条标注"源码引文"）：
文件不存在 → 检查路径｜`Unsupported firmware length` → 用官方 C 3.11 的 99,051,117 字节
文件｜`Unsupported outer package context` → 大小对但内容根本不是更新包，重新下载｜
`Package body CRC mismatch`/`Package SHA1 mismatch` → 文件被改动或损坏，重下并核 sha256｜
`Incompatible region`（源码引文）→ 只支持官方 Z8 C 3.11｜输出目录已存在 → 换个新目录｜
`AArch64 compilation failed` → 只构建 prores 或装带 AArch64 的 Clang｜
`Compiler output differs from the reviewed recipe`（源码引文）→ 换审阅过的 Clang，
"差不多"不收｜`opengate needs precapture` → 补上 precapture｜`Select prores, precapture,
opengate, or any combination, without duplicates` → feature 别重复、别写错名｜
`Tag must be a lowercase letter and digit` → tag 用 `p0` 这类｜
`Version must be two digits, a dot and two digits, e.g. 04.01` → 注意：**04.01 只是格式
示例，绝不要真的打 04.01**（见 [build.md](build.md)）｜缺 `--version`/`--output` → 补上｜
`--check cannot be combined with output options` → 两种模式二选一｜pytest 出现 skipped →
没设 `NIJIN_EG_SLICE` 时的正常表现。**表里没有的报错照字面理解：每一次拒绝都是安全检查，
不是刁难；没有强制绕过开关。**

**下一步**：[build.md](build.md) 完整流程｜[features.md](features.md) 功能与真实状态｜
[raw-precapture.md](raw-precapture.md) RAW 预拍拍摄指南（准备、步骤与限制）｜
[verification.md](verification.md) 检查能证明什么｜[risks.md](risks.md) 事故、风险与回退。
