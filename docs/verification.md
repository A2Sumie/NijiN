# What verification means here

Two distinct concepts are called "verified" in this project, and conflating them
risks bricking cameras. This page draws the line explicitly.

## 1. Offline verification (what the tools actually prove)

Offline verification proves that **the bytes are what the recipe says they are**.
It runs entirely on your machine, with no camera involved.

| Layer | What it checks |
|---|---|
| `verify.py` | Independent re-verification of a build pair: confirms every declared patch window matches the published recipe (offset, length, `old_sha256` before, `new_sha256` after), every byte outside declared windows is preserved, other modules are untouched, and shared loader edits and version fields are correct |
| Compatibility gate | Pre-edit checks: input size, module identities, per-module hashes, and every fingerprint window's current hash must match. Any mismatch stops the build |
| Compiler lock | Injected code is compiled from the local C sources; if the compiler produces anything other than the reviewed code bytes, the build stops |
| `tests/validate.py`, `tests/validate_features.py` | Offline regression suites: recipe regeneration, negative controls, configuration file semantics, and CLI behaviour |
| `tests/test_menuh.py` | Recipe-lock and structural checks for the menu group patch (requires a local EG slice to run in full; explicitly skips without it) |
| `gauntlet/gates.py` | Seven gates, 33 checkpoints: byte-level validation (G1), package identity and integrity chain (G2), feature-combination rules and window overlaps (G3), configuration files (G4), test stack (G5), output-directory hygiene (G6), and pre-flash checklist generation (G7) |
| `gauntlet/mutations.py` | 34 mutation test cases: structurally valid but corrupted packages, rebuilt with the entire integrity chain repaired by an "attacker" model. Every case must be caught by content gates, not by checksums |
| `gauntlet/combos.py` | Combination matrix: builds and verifies every legal feature combination end-to-end, rejects illegal combinations at build time, and ensures rebuilding the shipping combination reproduces the shipped file byte for byte |
| `gauntlet/structural.py` | Structural stress testing: decode/encode round-trip identity, one-byte mutation with chain repair (structure passes, content must fail), reverse integrity-chain traversal, and cross-tool decode comparisons |
| Recipe lock | The build records source hashes in `manifest.json`; gate G3.4 re-hashes the sources and fails if the recipe drifted after the build |

A passing run proves only that this build is a faithful, reproducible realization of the
published recipes against your exact input. It does **not** mean the camera
will boot, record, or survive flashing.

## 2. On-hardware verification (what actually exists)

Documented hardware evidence for this project's own builds:

| Area | Hardware evidence | Build generation |
|---|---|---|
| HE★ pre-capture core | Actual HE★ NEFs captured and compared against camera-generated references | Early build (first generation) |
| C15 pre-capture | Working pre-capture in C15 mode | Early build |
| No-JPEG behaviour | Verified at code level and tested on hardware | Early build |
| C30 root-cause experiment | One controlled experiment that identified why the stock C30 window failed | Early build |
| Everything else in [features.md](features.md) | **None.** Never tested on a camera | — |
| The current stable line (V10) | **One attempt, one boot loop.** The camera did not recover | V10 |

This is the complete list. No other hardware test records exist for these
builds, and hardware records from upstream projects describe their own
builds, not these.

## 3. What the offline battery cannot prove

- Whether the camera boots the result. A build passing all offline checks
  previously caused a boot loop; test gates cannot detect runtime boot failures.
- How a patch window in a boot-reachable path behaves at power-on. The
  battery verifies build-time invariants, not runtime execution on hardware.
- Whether inferred constants match the device's internal tables. The offline
  model of the device is reverse-engineered and incomplete.
- Whether menu structures on hardware match static binary slices
  (including logo resources, entry behaviour, and item counts).
- Whether third-party software (Adobe Camera Raw, Lightroom, NX Studio, card
  readers, recovery tools) will accept the output.

## 4. How to run it

```sh
python tests/validate.py --stock "/path/to/Z_8_0311.bin" --report build/validate.json
python tests/validate_features.py --stock "/path/to/Z_8_0311.bin" --report build/features.json
python gauntlet/gauntlet.py run --kit build/mybuild --stock "/path/to/Z_8_0311.bin" --out build/gauntlet
```

Exit code 0 indicates all gates passed. `SKIPPED` rows mark checks that require
a local input or an external tool that was not provided (such as legacy build
archives or cross-check tools); these are reported as skipped and never counted
green. The generated `GAUNTLET_REPORT.md` and `PREFLIGHT_CHECKLIST.md` files in
the output directory document the full check history.

## 5. How claims are worded in this project

- "offline verified" refers strictly to the byte-level and test evidence above.
- "on hardware" means a specific build generation was installed on a camera and the stated
  behaviour observed. It is never used for a build that was not installed.
- "not verified" and "not deliverable" are stated explicitly where applicable,
  alongside all other statuses in the tables.

## 简体中文

- **离线验证只证明“字节=配方”**：涵盖独立核验器、兼容性指纹门、编译器锁、测试套件、
  gauntlet 七道门 33 个检查点、34 项变异用例、组合穷举、结构压力测试与配方源码指纹锁。
- **上机证据仅有早期构建的 HE★ 预拍、C15、不写 JPEG、单次 C30 根因实验**；
  其余功能从未上机；当前稳定线 V10 仅上机一次，结果为开机循环事故且未能恢复。
- 离线测试集**证明不了**：相机会不会开机、开机路径补丁在真机上如何执行、推断常量与
  真机表是否一致、第三方软件是否接受产物。
- 措辞纪律：“离线验证”“上机验证”“未验证”“不可交付”严格区分，不互相升级。
