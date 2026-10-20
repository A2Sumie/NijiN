# Release Runbook

See [release-packaging.md](release-packaging.md) for package specifications and [open-items.md](open-items.md) for pending tasks.

## Pre-release Checks

1. Ensure the working tree is clean and all repository checks pass:
   ```sh
   python3 tools/check_repository.py --all
   python3 tools/redline_scan.py
   python3 tools/check_links.py
   python3 tools/check_consistency.py
   ```
2. Build the release package from the target commit:
   ```sh
   python3 tools/build_release.py --output /path/to/release-workspace \
       --notes /path/to/release-workspace/RELEASE_NOTES.md
   ```
   This script compiles the code from source, verifies hashes against pinned recipes, builds a deterministic zip archive, updates the release notes, and runs `redline_scan --release` and `check_consistency --release-kit`.
3. Verify the archive contents. It must only contain project code objects, source files, the manifest, and checksums: no firmware, no inputs, no outputs, no settings files, no captures, no third-party binaries.
4. Remove the local "Prep record" block from `RELEASE_NOTES.md` before publishing. Keep the warning lines and content table.

## Publishing

Follow the tag naming conventions in [versions.md](versions.md). Always use annotated tags.

```sh
cd /path/to/NijiN
TAG=toolkit-$(date +%Y%m%d)
git tag -a "$TAG" -m "NijiN toolkit $(date +%F): objects 63d3acd2…/f2cf11c4… match the pinned recipes; four checks and release reconciliation green"
git push origin "refs/tags/$TAG"

gh release create "$TAG" --verify-tag \
    /path/to/release-workspace/nijin-toolkit-*-prep.zip \
    --title "NijiN toolkit $(date +%F)" \
    --notes-file /path/to/release-workspace/RELEASE_NOTES.md
```

* `--verify-tag` is required. Without it, `gh release create` will silently create a lightweight tag on the default branch if the remote tag is missing.
* Add `--draft` to create an unpublished draft release for review.

## Post-release Verification

1. Download the published archive from the release page and verify its checksums:
   ```sh
   shasum -a 256 nijin-toolkit-*.zip      # must match the release notes
   unzip -q nijin-toolkit-*.zip -d verify && cd verify/nijin-toolkit
   shasum -a 256 -c SHA256SUMS.txt
   ```
2. Confirm the tag points to the target commit and matches the commit hash in the manifest.
3. Update item 17 in [open-items.md](open-items.md) to "published" and record the tag.

## Handling Bad Releases

* **Never move or reuse a tag.** To fix an issue, publish a new tag (e.g., `toolkit-YYYYMMDD.2`) with new assets. State what was fixed and which release is superseded in the new release notes, and mark the old release as deprecated.
* **Prohibited file leaks:** If an archive contains restricted files (firmware, captures, etc.), delete the release asset immediately, document the root cause locally, and publish a corrected release under a new tag. Never silently replace files on an existing release.
* **Stale builds:** If new commits land after the package was built, re-run `build_release.py`. The verification scripts will reject packages whose manifest commit does not match `HEAD` and the release notes.

---

## 简体中文

打包规范见 [release-packaging.md](release-packaging.md)，未完事项见 [open-items.md](open-items.md)。

### 发布前检查

1. 确保工作区干净，且四项检查全部通过：
   ```sh
   python3 tools/check_repository.py --all
   python3 tools/redline_scan.py
   python3 tools/check_links.py
   python3 tools/check_consistency.py
   ```
2. 基于目标提交构建发布包：
   ```sh
   python3 tools/build_release.py --output /path/to/release-workspace \
       --notes /path/to/release-workspace/RELEASE_NOTES.md
   ```
   该脚本会从源码编译目标文件、核对哈希值、生成确定性 zip 包、更新发布说明，并执行 `--release` 与 `--release-kit` 校验。
3. 核对产物内容：仅允许包含本项目代码对象、源码树、清单（manifest）和校验和文件。不含固件（no firmware），不含输出包、用户输入、设置文件、抓拍图像或第三方二进制文件。
4. 清理 `RELEASE_NOTES.md`：删掉供本地记录用的“Prep record”段落，保留警示语和内容表。

### 发布

按 [versions.md](versions.md) 规范打附注标签（annotated tag）并创建发布：

```sh
cd /path/to/NijiN
TAG=toolkit-$(date +%Y%m%d)
git tag -a "$TAG" -m "NijiN toolkit $(date +%F): objects 63d3acd2…/f2cf11c4… match the pinned recipes; four checks and release reconciliation green"
git push origin "refs/tags/$TAG"

gh release create "$TAG" --verify-tag \
    /path/to/release-workspace/nijin-toolkit-*-prep.zip \
    --title "NijiN toolkit $(date +%F)" \
    --notes-file /path/to/release-workspace/RELEASE_NOTES.md
```

* **必须加上 `--verify-tag`**：否则当远端缺少该 tag 时，`gh` 会直接基于默认分支静默创建一个普通轻量 tag，绕过附注与验证信息。
* 如需预览，可加 `--draft` 生成草稿。

### 发布后验证

1. 从发布页下载附件并核对校验和：
   ```sh
   shasum -a 256 nijin-toolkit-*.zip      # 必须与发布说明中的值一致
   unzip -q nijin-toolkit-*.zip -d verify && cd verify/nijin-toolkit
   shasum -a 256 -c SHA256SUMS.txt
   ```
2. 确认 tag 指向的提交与发布说明、manifest 中的 commit 一致。
3. 将 [open-items.md](open-items.md) 第 17 项更新为“已发布”，并记录 tag。

### 异常处理

* **禁止移动或复用 tag**：如需修正，必须打新 tag（如 `toolkit-YYYYMMDD.2`）并上传新附件。在新版说明中写明修复内容及替代的旧版本，并在旧版说明中标注“已废弃”。
* **违规文件泄露**：若发布包混入禁传文件，立即删除该附件，在本地记录原因，随后通过新 tag 发布修正版。严禁在原 release 上静默替换文件。
* **构建产物过期**：若打包后又有新提交合入，必须重新运行 `build_release.py`，否则对账脚本会因 commit 不匹配而拒绝通过。
