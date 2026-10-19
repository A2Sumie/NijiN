# Release lines and version policy

## The two lines

| Line | Branch | Tag | What it is | Honest state |
|---|---|---|---|---|
| **V10** | `main` | — | The current stable line: `prores` + `precapture` + `opengate` + `menuh`, with the settings save/load fixes of the last iteration | Offline green (all gates, twice). **On hardware: caused a boot loop.** Do not flash |
| **V11 `bricking-edge`** | `bricking-edge` | `bricking-edge` | The hotfix / forensics line: V10 with the three suspect changes stripped and four patch windows reverted to the previous build's bytes | Built and compared byte for byte as a trial. Never released into a build kit. **Frozen** until the boot-loop cause is settled |

"Stable" in this project means **offline stable**: the build is reproducible
and every byte is accounted for. It has never meant "safe on hardware", and
after the incident it is stated explicitly that it does not.

## Why `bricking-edge`

The name is dark humour kept on purpose. The usual term is "bleeding edge";
this line exists because a camera was bricked, so it is named after what it
actually did. Renaming it to something reassuring would hide the one fact a
reader most needs to know.

## Branch and tag layout

```text
main          V10 stable line — the default branch
bricking-edge V11 hotfix / forensics line (branch)
bricking-edge tag on that branch — a fixed marker of the trial state
```

Anything unreleased and under investigation belongs on `bricking-edge`, not
on `main`. `main` moves only with reviewed, offline-verified work.

## Package identity and version numbers

| Knob | Rule |
|---|---|
| `--version NN.NN` | The version written into the package. Example used in docs: `03.11` |
| `--tag` | Lowercase letter plus a digit, default `p0`. The stamped identity becomes `NN.NN.xN`, for example `03.11.p0` |
| Identity consistency | Runtime slot, trailer and public version text must agree; the gauntlet fails the build if they do not |
| Forbidden value | `04.01` is a placeholder and is treated as a defect by the test battery |

Policy notes, including deviations from upstream:

- This fork accepts an output version **equal to or higher than** the input
  version where upstream required strictly higher (`LOCAL DEVIATION` markers
  in `features.py` and `verify.py`). Basis: a real-camera observation that a
  lower-numbered package was accepted. It is not a compatibility guarantee.
- The `03.11.p0` identity deliberately differs from the stock tag so the
  package is not mistaken for stock. Whether a camera accepts an update
  carrying the same version number it already runs is **untested**; if it
  refuses, rebuild with a higher `--version`.
- A changed version number adds no function and no compatibility.

## Upgrade / downgrade reality

- There is no downgrade path and no recovery guarantee.
- Build every package from a fresh official input, never from a previous
  output.
- The official C 3.11 package and its checksum are your only rollback:
  `d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96`.

## 简体中文

- 两条线：**V10**（`main`，当前稳定线）与 **V11 `bricking-edge`**（分支+同名标签，
  热修／取证线，剥掉三处嫌疑改动、四窗回退）。
- “稳定”在这里只指**离线稳定**（可复现、字节全归因），不指上机安全；V10 上机
  造成过开机循环，README 与本文都不回避。
- `bricking-edge` 是故意保留的黑色幽默：这条线因刷砖而生，改成好听的名字会把
  最该知道的事实藏起来。
- 版本号：`--version NN.NN` + `--tag`（默认 `p0`），身份如 `03.11.p0`；禁止 `04.01`。
  本分支把“必须高于输入号”放宽为“≥”（源码标注 `LOCAL DEVIATION`），依据是真机
  受理观察，**不是兼容性承诺**；同号受理未实测，被拒就用更高号重建。
- 没有降级与恢复保证；每次从全新官方包构建；唯一回退锚是官方 03.11 及其 sha256。
