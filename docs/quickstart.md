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

| Message | What it means | Fix |
|---|---|---|
| `Unsupported firmware length` / `Input must be a regular firmware file` | Not the update package | Use the 99,051,117-byte official C 3.11 file |
| `Incompatible region: …` / `Package SHA1 mismatch` | Wrong or damaged input | Re-download and check the SHA-256 in step 1 |
| `Unsupported package length; expected Z8 3.11 layout` | Another model or version | Only official Z8 C 3.11 is supported |
| `Output directory already exists; use a new directory` | The tool never overwrites | Pick a new `--output` directory |
| `AArch64 compilation failed: …` / `Compiler output differs from the reviewed recipe` | No usable Clang, or a compiler that produces different bytes | Build `prores` alone, or use the reviewed Clang |
| `opengate needs precapture: …` | Feature rule | Add `precapture` to `--features` |
| `Selected features contain overlapping patch windows` | A feature was listed twice | List each feature once |
| `Tag must be a lowercase letter and digit` | `--tag` format | Use something like `p0` |
| `Building requires --version and --output; …` | Missing flags | Add `--version NN.NN --output <new dir>` |
| pytest prints `skipped` | Tests that need a local file slice are gated | Normal without `NIJIN_EG_SLICE`; nothing is wrong |

If a message is not in this table: read it literally — every refusal is a
safety check, not a nuisance. There is no force or bypass switch.

## Where to go next

- [build.md](build.md) — the full flow, version numbers, the gauntlet
- [features.md](features.md) — what each feature does and its honest state
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

**出错对照表**（完整表见英文部分）：长度/文件不对 → 用官方 C 3.11 的 99,051,117 字节
文件｜指纹或校验不符 → 重新下载并按第 1 步核 sha256｜包布局不对 → 只支持 Z8 C 3.11｜
输出目录已存在 → 换个新目录｜编译失败或"Compiler output differs" → 只构建 prores 或
换审阅过的 Clang｜`opengate needs precapture` → 功能组合规则，补上 precapture｜
feature 重复/ tag 格式 / 缺 `--version`/`--output` → 按提示改｜pytest 出现 skipped →
没设 `NIJIN_EG_SLICE` 时的正常表现。**表里没有的报错照字面理解：每一次拒绝都是安全检查，
不是刁难；没有强制绕过开关。**

**下一步**：[build.md](build.md) 完整流程｜[features.md](features.md) 功能与真实状态｜
[verification.md](verification.md) 检查能证明什么｜[risks.md](risks.md) 事故、风险与回退。
