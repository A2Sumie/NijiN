# Release runbook

This is the publish procedure, written down so it is boring on the day.
**Nothing here is executed without an explicit instruction to publish.** The
toolkit currently sits prepared locally; see
[release-packaging.md](release-packaging.md) for what may go into it and
[open-items.md](open-items.md) for what is still unfinished.

## Before anything is published

1. The repository is clean and its four checks pass:
   ```sh
   python3 tools/check_repository.py --all
   python3 tools/redline_scan.py
   python3 tools/check_links.py
   python3 tools/check_consistency.py
   ```
2. The toolkit is rebuilt from the commit you intend to tag, and the
   release reconciliation passes:
   ```sh
   python3 tools/build_release.py --output /path/to/release-workspace \
       --notes /path/to/release-workspace/RELEASE_NOTES.md
   ```
   This compiles the reviewed code objects from source, verifies them
   against the pinned recipe hashes, assembles the kit and a deterministic
   zip, refreshes the notes prep record, and runs `redline_scan --release`
   plus `check_consistency --release-kit`. Exit code 0 means the prepared
   material matches the repository pins and the notes.
3. Read the red lines once more: no firmware, no outputs, no inputs, no
   settings files, no captures, no third-party binaries — only this
   project's own code objects, the source tree, the manifest and the sums.
   A release asset is not a loophole.

## Publishing (one command, after the word)

Tag naming follows [versions.md](versions.md): annotated tag, never moved,
never reused.

```sh
cd /path/to/NijiN
TAG=toolkit-$(date +%Y%m%d)
git tag -a "$TAG" -m "NijiN toolkit $(date +%F): objects 8fb68da6…/36e56939… match the pinned recipes; four checks and release reconciliation green"
git push origin "refs/tags/$TAG"

gh release create "$TAG" --verify-tag \
    /path/to/release-workspace/nijin-toolkit-*-prep.zip \
    --title "NijiN toolkit $(date +%F)" \
    --notes-file /path/to/release-workspace/RELEASE_NOTES.md
```

`--verify-tag` matters: without it, `gh release create` silently creates a
plain tag from the default branch when the tag is missing, which would skip
the annotated tag and its verification record. Add `--draft` for a
dress rehearsal that is still unpublished.

The notes file is the prepared bilingual text; its "Prep record" block is
local bookkeeping and can be deleted from the published copy, the warning
lines and content table stay.

## After publishing

1. Download the asset back from the release page and verify it against the
   published sums:
   ```sh
   shasum -a 256 nijin-toolkit-*.zip      # must equal the value in the notes
   unzip -q nijin-toolkit-*.zip -d verify && cd verify/nijin-toolkit
   shasum -a 256 -c SHA256SUMS.txt
   ```
2. Confirm the tag points where the notes say, and that the manifest commit
   is the tagged commit.
3. Update [open-items.md](open-items.md) item 17 to "published" and record
   the tag in the ledger.

## If something is wrong afterwards

- **Never move or reuse a tag.** Corrections get a new tag
  (`toolkit-YYYYMMDD.2`) and a new asset, and the new release notes say what
  was wrong and which release it supersedes. Mark the old release clearly in
  its notes.
- **A red-line violation is an incident, not a typo.** Delete the offending
  asset immediately, keep the evidence local, write down what was in it and
  how it got there, and only then prepare a corrected tag. Do not silently
  replace files on an existing release.
- If the published notes turn out to claim something the repository does not
  support, fix the repository first, then publish a corrected release; do
  not edit history to match.
- If a prepared kit goes stale (new commits landed), rebuild it; the
  reconciliation refuses a kit whose manifest commit is not what the notes
  and the pinning expect.
- If the repository ever enables GitHub's immutable releases, the rules
  above become physically enforced: published tags and assets cannot be
  changed or deleted at all. That matches the posture here, but it also
  means a draft is the last chance to catch a mistake.

## 简体中文

这是发布流程，提前写好，到日子照做。**没有明确的"发"字，一律不执行**；toolkit
目前只在本地备好待命。

**发布前**：① 仓内四查全绿（check_repository / redline_scan / check_links /
check_consistency）② 用 `tools/build_release.py` 从要打标签的提交重建 toolkit，
并跑 `--release` 与 `--release-kit` 双对账（退出码 0 = 备料与仓内钉死值、文案三方
一致）③ 再读一遍红线：不带固件、输出包、用户输入、设置文件、照片、第三方二进制——
只有本项目自己的代码对象、源码树、清单和校验和；**发布物不是豁免口**。

**发布（用户说"发"之后一条命令）**：按 [versions.md](versions.md) 打 annotated
tag（不移不复用）→ `git push refs/tags/$TAG` → `gh release create "$TAG" --verify-tag
<zip> --notes-file RELEASE_NOTES.md`。**`--verify-tag` 不能省**：不加它，tag 缺失时
`gh` 会从默认分支自动补一个非注解 tag，跳过我们的注解与验证记录。想彩排就加
`--draft`（仍是未发布状态）。文案里的 Prep record 块是本地台账，发布副本可删；
警示语与内容表必须保留。

**发布后**：把附件下回来按公布校验和核一遍；确认 tag 指向与文案一致、manifest
commit 与 tag 提交一致；把 [open-items.md](open-items.md) 第 17 项改成"已发布"并
记台账。

**出错怎么更正**：**永远不挪不复用 tag**——错了就发新 tag（`toolkit-YYYYMMDD.2`）
和新附件，新文案写清错在哪、替代哪个旧版，旧版在自己的说明里标注被替代。**踩红线
是事故不是笔误**：立刻删掉违规附件、证据留本地、写清里面有什么、怎么进去的，然后才
准备更正 tag；绝不静默替换已发布附件。文案若宣称了仓里不支持的东西，先修仓再发
更正版，不要改历史去凑。备料过期（来了新提交）就重建；对账会拒绝 commit 对不上的包。
若将来开启 GitHub 的 immutable releases，上述规则会被平台强制执行：已发布的 tag
与附件一律不可改不可删——这与本仓姿态一致，但也意味着 draft 是最后一个能发现错误的
机会。
