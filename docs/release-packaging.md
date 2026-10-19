# Release Packaging (Precompiled Code Objects)

Building this project from source compiles the injected C code and verifies the output byte-for-byte against pinned hashes. This requires Clang with an AArch64 target (specifically `Apple clang 21.0.0 (clang-2100.3.34.2)`). 

Release archives provide precompiled code objects from this repository so users without Clang can still build the project. When using a release archive, the build system verifies the shipped objects against the same hash locks in `resources/*.json` instead of compiling locally.

## Release contents

A release asset contains only the following items:

| Item | Description |
|---|---|
| Precompiled code objects | Flat AArch64 code blobs compiled from `z8precapture/firmware.c`, `z8opengate/firmware.c`, and the emitters. |
| Manifest | A metadata file listing every object's filename, size, SHA-256, matching `code_sha256` in `resources/`, and source file hashes. |
| `SHA256SUMS.txt` | SHA-256 checksums covering the entire release asset. |
| Commit hash | The exact Git commit the objects were built from. |

## Packaging and verification workflow

1. **Build**: Compile the objects from a clean checkout of the tagged commit.
2. **Verify hashes**: Check every object's SHA-256 against `code_sha256` and `source_sha256` in `resources/*.json`. Abort if the compiler output differs from the pinned hashes.
3. **Reproduce**: Rebuild the objects on a second clean machine and verify that the outputs are identical.
4. **Scan**: Run the release scanner on the staging directory:
   ```sh
   python3 tools/redline_scan.py --release build/release-staging
   ```
   The scanner verifies that every file is listed in the manifest, all hashes match both the manifest and `resources/`, and no extraneous binaries, firmware data, local paths, or credentials are present. An exit code of `0` indicates the directory is ready to publish.
5. **Publish**: Upload the archive with the manifest and checksums, and link [NOTICE.md](../NOTICE.md) in the release notes.

## Drill record (2026-10-19)

The flow above was rehearsed end to end without publishing anything. With the reviewed compiler (`Apple clang 21.0.0 (clang-2100.3.34.2)`) both code objects compiled from the sources in this repository matched the recipe pins byte for byte (then-current objects: `precapture` 35,053 bytes `fb53a549…`, `opengate` 4,040 bytes `36e56939…`; object history: V11.1 brought 35,229 bytes `8fb68da6…`, **V12 brings 36,189 bytes `fa21fb78…`** — the current pin in `resources/`). `tools/redline_scan.py --release` passed the staging directory and refused, as it must, a one-byte tampering of an object, a smuggled `.bin`, and a manifest with the source hashes stripped. No release has been published.

Flashing anything built from these objects is at your own risk: read [risks.md](risks.md) first.

---

## 简体中文

本项目默认从 C 源码编译注入代码，并强制校验编译产物的字节哈希。这要求本地安装支持 AArch64 目标的 Clang（基准版本为 `Apple clang 21.0.0 (clang-2100.3.34.2)`）。

Release 发布包用于提供预编译好的代码目标文件，方便没有 Clang 环境的用户直接构建。使用预编译包时，构建脚本会直接对照 `resources/*.json` 中的哈希锁校验随附的目标文件。

### 发布包内容

- **预编译代码对象**：由 `z8precapture/firmware.c`、`z8opengate/firmware.c` 及生成器编译出的 AArch64 纯二进制代码片段。
- **清单文件（Manifest）**：记录每个目标文件的文件名、大小、SHA-256、`resources/` 中对应的 `code_sha256` 以及源码哈希。
- **`SHA256SUMS.txt`**：覆盖整个发布包的校验和文件。
- **Commit 哈希**：构建该批目标文件所用的 Git 提交哈希。

### 打包与校验流程

1. **构建**：从打好标签的 commit 检出干净的工作区，编译目标文件。
2. **核对哈希**：对照 `resources/*.json` 中的 `code_sha256` 和 `source_sha256` 校验每个产物的 SHA-256。若编译产物不一致则直接中止，不得修改清单去迁就编译产物。
3. **复现构建**：在另一台干净环境中重新构建，确认产物逐字节一致。
4. **安全扫描**：对暂存目录运行发布扫描脚本：
   ```sh
   python3 tools/redline_scan.py --release build/release-staging
   ```
   脚本会拒绝任何未列入清单的文件、哈希与清单或 `resources/` 不符的文件，以及固件数据、个人路径或第三方二进制文件等违规内容。返回码为 `0` 表示校验通过。
5. **发布**：上传发布包、清单与校验和文件，并在 Release 说明中附上 [NOTICE.md](../NOTICE.md) 的链接。

### 演练记录（2026-10-19）

整套流程已完整演练过（未发布任何 release）。用审定过的编译器（`Apple clang 21.0.0 (clang-2100.3.34.2)`）从本仓源码编译出的两个代码对象与配方钉死值逐字节一致（当时对象：`precapture` 35,053 字节 `fb53a549…`、`opengate` 4,040 字节 `36e56939…`；对象沿革：V11.1 换 35,229 字节 `8fb68da6…`，**V12 换 36,189 字节 `fa21fb78…`**（现钉死在 `resources/`））。`tools/redline_scan.py --release` 通过了暂存目录，并如预期拒绝了单字节篡改、夹带 `.bin`、以及抹掉源码哈希的清单。

刷写这些对象构建出的固件风险自担：先读 [risks.md](risks.md)。
