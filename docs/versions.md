# Release lines and version policy

## The two lines

| Line | Branch | Tag | What it is | Honest state |
|---|---|---|---|---|
| **V10** | `main` | — | The current stable line: `prores` + `precapture` + `opengate` + `menuh`, with the settings save/load fixes of the last iteration | Offline green (all gates, twice). **On hardware: caused a boot loop.** Do not flash |
| **V11 `bricking-edge`** | `bricking-edge` | `bricking-edge` | The hotfix / forensics line: V10 with the three suspect changes stripped and four patch windows reverted to the previous build's bytes | Built and compared byte for byte as a trial. Never released into a build kit. **Frozen** until the boot-loop cause is settled |

In this project, "stable" means **offline stable**: the build is reproducible
and every byte is accounted for. It has never meant "safe on hardware", and
following the incident, this distinction is stated explicitly.

## Why `bricking-edge`

The name is deliberate dark humour. Where convention uses "bleeding edge",
this line exists because a camera was bricked, so it is named directly after
what it actually did. Renaming it to something reassuring would obscure the
one fact a reader most needs to know.

## Branch and tag layout

```text
main          V10 stable line — the default branch
bricking-edge V11 hotfix / forensics line (branch)
bricking-edge tag on that branch — a fixed marker of the trial state
```

Any unreleased work under investigation belongs on `bricking-edge`, not
on `main`. `main` advances only with reviewed, offline-verified changes.
The V11 recipe and status page are carried on `main` too, so the line is
readable and reviewable everywhere; changes to the V11 line itself land on
`bricking-edge`. Unfreezing the line has its own written bar in
[unfreeze-criteria.md](unfreeze-criteria.md) and remains the owner's
decision.

## Tag naming

Tags are annotated, never moved and never reused. A tag name records what
kind of marker it is; the tag message records the commit and what was
verified at the time.

| Pattern | Meaning | State |
|---|---|---|
| `bricking-edge` | Fixed marker of the V11 trial state, on the `bricking-edge` branch | Exists |
| `vN` (for example `v10`) | Stable-line marker: the commit that line is named after, only cut when its full gauntlet run is green | None published yet |
| `toolkit-YYYYMMDD` | A toolkit package release, following [release-packaging.md](release-packaging.md) | None published yet; the first toolkit is prepared locally and **not** published |

Rules: cut a tag from the branch the line lives on; put the verification
state in the message; if a tag turns out wrong, publish a new tag rather
than moving the old one; release assets are governed by
[release-packaging.md](release-packaging.md) and published per
[releasing.md](releasing.md), not by the tag name.

## Package identity and version numbers

| Knob | Rule |
|---|---|
| `--version NN.NN` | The version written into the package. Example used in docs: `03.11` |
| `--tag` | Lowercase letter plus a digit, default `p0`. The stamped identity becomes `NN.NN.xN`. **For the experimental line use `p1`** |
| Identity consistency | Runtime slot, trailer and public version text must agree; the gauntlet fails the build if they do not |
| Forbidden value | `04.01` is a placeholder and is treated as a defect by the test battery |

Policy notes, including deviations from upstream:

- This fork accepts an output version **equal to or higher than** the input
  version, whereas upstream required it to be strictly higher (`LOCAL DEVIATION`
  markers in `features.py` and `verify.py`). Rationale: a real camera was observed
  accepting a lower-numbered package. This is not a compatibility guarantee.
- Tag generations: **`p0` is the historical smoke and incident generation**;
  **`p1` is the V11.1 experimental generation — build anything from V11.1
  content with `--tag p1`, yielding identity `03.11.p1`**. Later generations
  take the next digit. Build records written before this split cite `p0`
  and stay as written; they are history.
- The `03.11.p0` identity deliberately differs from the stock tag so the
  package is not mistaken for stock. Whether a camera accepts an update
  carrying the same version number it already runs remains **untested**; if it
  refuses, rebuild with a higher `--version`.
- A changed version number adds neither functionality nor compatibility.

## Upgrade / downgrade reality

- There is no downgrade path and no recovery guarantee.
- Build every package from a fresh official input, never from a previous
  build output.
- The official C 3.11 package and its checksum are your only rollback:
  `d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96`.

## 简体中文

- 两条分支线：**V10**（`main`，当前稳定线）与 **V11 `bricking-edge`**（分支及同名标签，
  热修／取证线；剥离了三处存疑改动，回退了四个补丁窗口）。
- 本项目中的“稳定”仅指**离线稳定**（构建可复现、所有字节均可归因），并不代表上机安全；
  V10 曾导致真机开机循环，README 与本文对此均不作回避。
- `bricking-edge` 是特意保留的黑色幽默：该分支因刷砖而生，直接以其实际后果命名。
  改成好听的名字，只会掩盖读者最该知道的事实。
- 版本号规则：`--version NN.NN` + `--tag`（默认 `p0`），最终标识形如 `NN.NN.xN`；禁止 `04.01`。
- **V12 = 已发布的试验性世代**——内部构建记录称 V11.2（V11.1 之上的三态门修复）的公开名；发布面一律写 **V12**，史实记录保留原名加注。
- **tag 世代**：`p0` = 历史冒烟/事故代；**`p1` = V11.1 试验品代——凡基于 V11.1 内容构建一律用 `--tag p1`，身份即 `03.11.p1`**；后续世代顺延。本次划分之前写成 `p0` 的构建记录保持原样，属史实。
  本分支将上游“必须高于输入号”放宽为“≥”（源码标注 `LOCAL DEVIATION`），依据是真机
  曾接受过低版本固件，但这**并不是兼容性承诺**；设备是否接受相同版本号尚未实测，若被拒绝，使用更高的 `--version` 重新构建即可。
- 不提供降级路径与恢复保证；每次必须基于全新官方原始包构建，切勿基于此前的构建产物；
  唯一的回退锚点是官方 03.11 及其 sha256。
