# Verification

Verification in this project is split into offline build checks and on-camera hardware tests.

## 1. Offline checks

Offline checks run locally without a camera. They confirm that the output binary matches the patch recipes byte-for-byte. 

| Component | What it checks |
|---|---|
| `verify.py` | Confirms patched regions match the recipe (offset, length, `old_sha256` before and `new_sha256` after), unpatched regions and other modules are untouched, and loader/version edits are correct. |
| Compatibility gate | Validates input file size, module IDs, and hashes before patching. Stops the build on any mismatch. |
| Compiler lock | Compiles injected C code locally and stops the build if the output bytes differ from the reviewed reference. |
| `tests/validate.py`, `tests/validate_features.py` | Regression tests for recipe generation, negative controls, config parsing, and CLI behavior. |
| `tests/test_menuh.py` | Checks structure and recipes for the menu patch (skips if the local EG slice is missing). |
| `gauntlet/gates.py` | Runs 33 checks across 7 areas: byte validation (G1), package integrity (G2), feature combinations and overlaps (G3), configs (G4), test suite (G5), output directory state (G6), and pre-flash checklist generation (G7). |
| `gauntlet/mutations.py` | Tests 34 corrupted packages with valid checksums to ensure content checks catch errors that checksums miss. |
| `gauntlet/combos.py` | Builds and verifies all valid feature combinations, rejects invalid ones, and confirms the default build is byte-reproducible. |
| `gauntlet/structural.py` | Tests decode/encode round-trips, single-byte mutations with repaired checksums, reverse integrity-chain traversal, and cross-tool decoding. |
| Recipe lock | Logs source hashes in `manifest.json`; gate G3.4 re-hashes the sources and fails if recipes changed after the build. |

## 2. Hardware test history

| Feature / Build | Result | Generation |
|---|---|---|
| HE★ pre-capture core | Working. Captured NEFs matched camera-generated references. | Early build (Gen 1) |
| C15 pre-capture | Working. | Early build (Gen 1) |
| No-JPEG mode | Working. | Early build (Gen 1) |
| C30 root-cause test | Identified why the stock C30 window failed. | Early build (Gen 1) |
| V10 build | **Failed.** Caused an unrecoverable boot loop (bricked). | V10 |
| All other features in [features.md](features.md) | **Untested.** | — |

Flashing and hardware operation are entirely your own risk; see [risks.md](risks.md).

## 3. Limitations of offline checks

Offline tools only validate static files against build rules. They cannot verify:
- Whether the firmware will boot or brick the camera.
- How patched code in the boot path behaves at power-on.
- Whether reverse-engineered constants match the camera's internal tables.
- How modified menus render or behave at runtime.
- Whether third-party software (Lightroom, Adobe Camera Raw, NX Studio, recovery tools) will accept the output files.

## 4. Running offline checks

```sh
python tests/validate.py --stock "/path/to/Z_8_0311.bin" --report build/validate.json
python tests/validate_features.py --stock "/path/to/Z_8_0311.bin" --report build/features.json
python gauntlet/gauntlet.py run --kit build/mybuild --stock "/path/to/Z_8_0311.bin" --out build/gauntlet
```

Exit code `0` means all checks passed. Checks missing required local inputs or external tools are marked `SKIPPED` rather than passed. Full results are written to `GAUNTLET_REPORT.md` and `PREFLIGHT_CHECKLIST.md` in the output directory.

## 简体中文

- **离线检查仅核对字节**：通过 `verify.py`、兼容性校验、编译器锁、回归测试及 `gauntlet` 测试集（7 道门 33 个检查点、34 项变异测试、组合穷举与结构测试），确保生成的固件与补丁配方完全一致。
- **真机测试记录**：仅早期版本（第一代）在真机上测试过 HE★ 预拍、C15 预拍、不写 JPEG 及单次 C30 故障排查。**V10 版本首次刷机即导致相机无限重启（变砖且无法恢复）**。其余功能从未上机测试，刷写与上机操作风险自担。
- **离线检查的局限**：无法测试刷机后能否正常开机、开机路径补丁的实际运行情况、逆向推导的常量是否匹配真机内部表、菜单在真机上的实际表现，以及第三方软件（如 Lightroom、NX Studio）能否正常读取生成的文件。
