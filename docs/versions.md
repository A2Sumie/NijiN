# Release lines and version policy

## Release lines

| Line | Branch | Tag | Description | Status |
|---|---|---|---|---|
| **V10** | `main` | — | `prores` + `precapture` + `opengate` + `menuh`, plus settings save/load fixes. | Passes offline checks. **Bricked** a test camera (boot loop on hardware). Do not flash. |
| **V11** | `bricking-edge` | `bricking-edge` | Hotfix/forensics build. V10 with three suspect changes removed and four patch windows reverted. | Byte-verified trial build. **Frozen** until the V10 boot loop is resolved. |

*Note: "Stable" in this project means the build is reproducible and passes all offline verification checks. It does not mean it is safe to flash on hardware.*

## Branch and tag layout

```text
main          V10 line (default branch)
bricking-edge V11 hotfix/forensics branch and fixed trial tag
```

* `main` only accepts reviewed, offline-verified changes. It also hosts the V11 recipe and status docs for visibility.
* `bricking-edge` holds all experimental and investigative work for V11. See [unfreeze-criteria.md](unfreeze-criteria.md) for the requirements to unfreeze this branch.

## Tag naming

Tags are annotated and immutable. If a tag is wrong, cut a new one rather than moving the old one.

| Pattern | Meaning | Status |
|---|---|---|
| `bricking-edge` | Fixed marker for the V11 trial state on the `bricking-edge` branch. | Active |
| `vN` (e.g., `v10`) | Stable-line release, cut only when all offline verification checks pass. | None |
| `toolkit-YYYYMMDD` | Toolkit package release. | None |

Release packaging and publishing are governed by [release-packaging.md](release-packaging.md) and [releasing.md](releasing.md).

## Package identity and version numbers

| Rule / Flag | Description |
|---|---|
| `--version NN.NN` | Target version written to the package (e.g., `03.11`). |
| `--tag` | Format: lowercase letter + digit (default `p0`), producing `NN.NN.xN`. **Use `p1` for V11.1 experimental builds.** |
| Consistency check | Runtime slot, trailer, and public version text must match, or the build will fail verification. |
| `04.01` | Forbidden placeholder value; rejected by the test suite. |

### Versioning notes

* **Version comparison:** Unlike upstream (which requires the output version to be strictly higher than the input), this fork allows output versions **equal to or higher than** (`>=`) the input (marked as `LOCAL DEVIATION` in `features.py` and `verify.py`). 
* **Same-version flashing:** Flashing a package with the same version number currently running on the camera is untested. If the camera rejects the update, rebuild with a higher `--version`.
* **Tag generations:** 
  * `p0`: Legacy builds (V10 and earlier).
  * `p1`: V11.1 experimental builds (produces `03.11.p1`).
  * Subsequent generations increment the digit.

## Building and rollback

* Always build from a fresh official firmware image, never from a previously modified build.
* Downgrading is not supported.
* Official C 3.11 firmware (for base builds and rollback):
  `SHA256: d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96`

## 简体中文

* **分支结构**：
  * **V10 (`main`)**：主分支。通过全部离线校验，但**真机刷入会把相机刷砖（开机循环），请勿刷入**。
  * **V11 (`bricking-edge`)**：热修与排查分支（含同名 Tag）。基于 V10 剥离了三处存疑改动并回退了四个补丁窗口。目前处于**冻结状态**，待查明开机循环原因后解冻。
  * *注：本项目中的“稳定”仅代表“离线构建可复现且所有字节校验通过”，不代表真机安全。*
* **版本号规则**：
  * 格式为 `--version NN.NN` 加上 `--tag`（默认 `p0`），最终标识如 `03.11.p0`。测试套件禁止使用占位符 `04.01`。
  * **V12**：内部记录中 V11.2（基于 V11.1 的三态门修复版）的公开构建名称。
  * **Tag 世代**：`p0` 用于旧版构建；**基于 V11.1 的试验构建必须使用 `--tag p1`（生成 `03.11.p1`）**；后续版本数字顺延。
  * **版本校验放宽**：上游强制要求输出版本号高于输入版本，本分支放宽为“大于等于（`>=`）”（源码中标有 `LOCAL DEVIATION`）。真机是否允许平刷相同版本号尚未实测；若相机拒绝更新，请调高 `--version` 重新构建。
* **构建与回退**：
  * 每次构建必须使用全新的官方原版固件作为输入，切勿基于已修改的固件二次构建。
  * 无降级方案。官方 03.11 原版固件 SHA256 校验值：
    `d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96`
