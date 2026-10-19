# Release packaging plan (precompiled code objects)

This is a plan, not a promise. No release has been published from this
repository yet, and the warnings in [risks.md](risks.md) apply to anything
that ever is published.

## Why a release would exist at all

The build compiles the added code from the C sources in this repository and
rejects any compiler whose output differs from the reviewed bytes. That lock
is the safety property, but it requires Clang with an AArch64 target. A release
could carry **this project's own generated code objects** so that users
without Clang can still build — while the same byte lock still applies,
checked against the shipped objects instead of a local compile.

That is the only thing a release may add. Everything else in a release is
what Git already carries.

## What may go into a release asset

| Item | Rule |
|---|---|
| Code objects for the injected code (flat AArch64 code blobs produced from `z8precapture/firmware.c`, `z8opengate/firmware.c` and the emitters) | Allowed. They are this project's own generated code, licensed like the source |
| A manifest listing every object: file name, size, SHA-256, the `code_sha256` it must match in `resources/`, and the source hashes that produced it | Required. A release without it is rejected |
| `SHA256SUMS.txt` over the whole asset | Required |
| The commit hash the objects were built from | Required |

## What must never go into a release asset

- any user-supplied input package, in whole or in part;
- any generated output package, even one built for testing;
- extracted segments, dumps, or anything decoded out of a device file;
- settings files, card contents, captures, screenshots, photographs;
- third-party binaries (compiler, emulator, converters);
- anything the scanners in `tools/` would reject in the repository tree.

A release asset is not a loophole: it is published content and the same red
lines apply to it as to the Git tree.

## Verification recipe

1. Build the objects from a clean checkout of the tagged commit.
2. Check every object's SHA-256 against `resources/*.json` (`code_sha256`,
   `source_sha256`). If a compiler produces anything else, stop — do not
   "fix" the manifest to match the object.
3. Rebuild the objects a second time on a clean machine and compare.
4. Run the release scan (below) over the staging directory.
5. Publish the asset together with the manifest and sums, and link
   [NOTICE.md](../NOTICE.md) in the release notes.

## Release scan

`tools/redline_scan.py --release DIR` scans a staging directory under
stricter rules than the repository scan:

```sh
python3 tools/redline_scan.py --release build/release-staging
```

It rejects any file that is not listed in the staging manifest, any file
whose SHA-256 does not match the manifest, any file that does not match a
declared `code_sha256` in `resources/`, and all the usual red-line content
(firmware-shaped files, personal data, local paths, credentials, blobs that
are not in the manifest). Exit code 0 means the staging directory is safe
to attach to a release.

## Drill record (2026-10-19)

The flow above was rehearsed end to end without publishing anything. With
the reviewed compiler (`Apple clang 21.0.0 (clang-2100.3.34.2)`) both code
objects compiled from the sources in this repository matched the recipe
pins byte for byte (then-current objects: `precapture` 35,053 bytes
`fb53a549…`, `opengate` 4,040 bytes `36e56939…`; V11.1 later replaced the
pre-capture object with 35,229 bytes `8fb68da6…`, pinned in `resources/`),
the manifest and sums were generated from
`resources/`, and `tools/redline_scan.py --release` passed the staging
directory. It refused, as it must, a one-byte tampering of an object, a
smuggled `.bin`, and a manifest with the source hashes stripped. No release
has been published.

## 简体中文

- 这是**预案**，不是承诺：本仓目前没有发布过任何 Release，[risks.md](risks.md)
  中的警告对任何未来产物同样成立。
- 发布物存在的唯一理由：让没有 Clang 的人也能构建——Release 里可以带**本项目
  自己生成的注入代码目标文件**，字节锁改为对照随附对象校验，锁本身不变。
- 允许进入发布物：自研代码对象 + 清单（文件名/大小/sha256/对应 `resources/`
  的 `code_sha256`/产生它的源码哈希）+ `SHA256SUMS.txt` + 构建用 commit。
- **绝不允许**：任何用户输入包或其片段、任何生成的输出包、提取段/解密产物、
  设置文件/卡内容/照片截图、第三方二进制、仓库扫描器会拒绝的一切。发布物不是
  红线豁免口。
- 校验流程：从打标签的干净检出构建 → 逐对象核对 `resources/` 的哈希（编译产物
  不一致就停，禁止修改清单去迁就对象）→ 在干净机器上二次重建比对 → 运行
  `tools/redline_scan.py --release DIR` → 连同清单与校验和一起发布，并在 Release 说明
  里给出 [NOTICE.md](../NOTICE.md) 链接。
- **演练记录（2026-10-19）**：全流程已彩排，未发布任何东西。用审阅编译器
  （`Apple clang 21.0.0 (clang-2100.3.34.2)`）从本仓源码编译的两个代码对象与配方
  钉死值逐字节一致（当时对象：precapture 35,053 字节 `fb53a549…`、opengate 4,040 字节
  `36e56939…`；V11.1 后预拍对象换为 35,229 字节 `8fb68da6…`，现钉死在 `resources/`）；清单与校验和由 `resources/` 生成；`--release` 扫描放行，并对
  单字节篡改、夹带 `.bin`、剥掉源码哈希的清单三种情况全部拒绝。
