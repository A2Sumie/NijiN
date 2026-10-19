# What verification means here

Two different things get called "verified" in this project, and mixing them
is how cameras get bricked. This page draws the line explicitly.

## 1. Offline verification (what the tools actually prove)

Offline verification proves **the bytes are what the recipe says they are**.
It runs entirely on your machine, with no camera involved.

| Layer | What it checks |
|---|---|
| `verify.py` | Independent re-verification of a build pair: every declared patch window matches the published recipe (offset, length, `old_sha256` before, `new_sha256` after), every byte outside the declared windows is preserved, the other modules are untouched, the shared loader edit and version fields are right |
| Compatibility gate | Before editing: input size, module identities, per-module hashes, and every fingerprint window's current hash must match. A mismatch stops the build |
| Compiler lock | Added code is compiled from the C sources here; if the compiler produces anything other than the reviewed code bytes, the build stops |
| `tests/validate.py`, `tests/validate_features.py` | Offline regression suites: recipe regeneration, negative controls, configuration file semantics, CLI behaviour |
| `tests/test_menuh.py` | Recipe-lock and structural checks for the menu group patch (needs a local EG slice to run in full; skips loudly without it) |
| `gauntlet/gates.py` | Seven gates, 33 checkpoints: byte-level (G1), package identity and integrity chain (G2), feature-combination rules and window overlaps (G3), configuration files (G4), the test stack (G5), output-directory hygiene (G6), pre-flash checklist generation (G7) |
| `gauntlet/mutations.py` | 34 mutation cases: structurally valid but wrong packages, rebuilt with the whole integrity chain repaired by an "attacker" model. Every one must be caught by content gates, not by checksums |
| `gauntlet/combos.py` | Combination matrix: each legal feature combination built and verified end to end, illegal combinations must be refused at build time, and rebuilding the shipping combination must reproduce the shipped file byte for byte |
| `gauntlet/structural.py` | Structural torture: decode/encode round-trip identity, one-byte mutation with chain repair (structure green, content must go red), reverse integrity-chain walk, cross-tool decode comparison |
| Recipe lock | The build records source hashes in `manifest.json`; gate G3.4 re-hashes the sources and fails if the recipe drifted after the build |

A green run means: this build is a faithful, reproducible realization of the
published recipes against your exact input. It does **not** mean the camera
will boot, record, or survive it.

## 2. On-hardware verification (what actually exists)

Honest inventory of hardware evidence for this project's own builds:

| Area | Hardware evidence | Build generation |
|---|---|---|
| HE★ pre-capture core | Real HE★ NEFs captured and compared against camera-made references | Early build (first generation) |
| C15 pre-capture | Working pre-capture in C15 | Early build |
| No-JPEG behaviour | Verified at code level and probed on hardware | Early build |
| C30 root-cause experiment | One controlled experiment that established why the stock C30 window failed | Early build |
| Everything else in [features.md](features.md) | **None.** Not tried on a camera | — |
| The current stable line (V10) | **One attempt, one boot loop.** The camera did not come back into service | V10 |

That is the complete list. There is no other hardware record for these
builds, and the upstream projects' hardware records describe their own
builds, not these.

## 3. What the offline battery cannot prove

- That the camera boots the result. A build with a fully green battery
  caused a boot loop; the gates did not and could not see it.
- That a patch window in a boot-reachable path behaves at power-on. The
  battery exercises build-time invariants, not device execution.
- That inferred constants match the device's own tables. The model of the
  device is reconstructed and incomplete.
- That a menu structure exists on hardware the way it reads in a static
  slice (logo resources, entry behaviour, item counts).
- That third-party software (Adobe Camera Raw, Lightroom, NX Studio, card
  readers, recovery tools) accepts the output.

## 4. How to run it

```sh
python tests/validate.py --stock "/path/to/Z_8_0311.bin" --report build/validate.json
python tests/validate_features.py --stock "/path/to/Z_8_0311.bin" --report build/features.json
python gauntlet/gauntlet.py run --kit build/mybuild --stock "/path/to/Z_8_0311.bin" --out build/gauntlet
```

Exit code 0 = all gates passed. `SKIPPED` rows are checks that need a local
input or an external tool you did not provide (legacy build archive,
cross-check tools); they are reported as skipped and never counted green.
The generated `GAUNTLET_REPORT.md` and `PREFLIGHT_CHECKLIST.md` in the output
directory are the record of what was checked.

## 5. How claims are worded in this project

- "offline verified" = the byte-level and test evidence above.
- "on hardware" = a named build generation was installed and the stated
  behaviour observed. It is never used for a build that was not installed.
- "not verified" and "not deliverable" are stated as such, in the same
  tables as everything else.

## 简体中文

- **离线验证只证明“字节=配方”**：独立核验器、兼容性指纹门、编译器锁、测试套件、
  gauntlet 七道门 33 检查点、34 项变异电池、组合穷举、结构酷刑、配方源码指纹锁。
- **上机证据只有早期构建的 HE★ 预拍、C15、不写 JPEG、一次 C30 根因实验**；
  其余功能从未上机；当前稳定线 V10 上机一次 = 开机循环事故。
- 离线电池**证明不了**：相机会不会开机、开机路径补丁在真机上怎么走、推断常量与
  真机表是否一致、第三方软件是否接受产物。
- 措辞纪律：“离线验证”“上机验证”“未验证”“不可交付”分开写，不互相升级。
