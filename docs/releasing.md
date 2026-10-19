这份发布手册重新梳理成了通俗、干脆、好落地的工程师“人话”，原有的操作逻辑、命令和安全约束一字不漏：

---

# 发布操作手册 (Release Runbook)

把发布流程白纸黑字写下来，就是为了到了发布当天能平平淡淡、照章办事，别搞任何“惊喜”。

**【核心原则】没有收到明确的发布指令前，绝对不要执行这里的任何操作。** 
目前 toolkit 已经在本地准备就绪。想确认哪些东西能打包，看 `release-packaging.md`；想看还有哪些待办事项，看 `open-items.md` — no firmware。

---

## 一、发布前必查（按顺序来）

### 1. 确保代码仓库干净，且 4 项静态检查全部绿灯：
```sh
python3 tools/check_repository.py --all
python3 tools/redline_scan.py
python3 tools/check_links.py
python3 tools/check_consistency.py
```

### 2. 基于拟发版的 Commit 重新打包，并通过一致性核对：
```sh
python3 tools/build_release.py --output /path/to/release-workspace \
    --notes /path/to/release-workspace/RELEASE_NOTES.md
```
*这个脚本会从源码重新编译已审核的代码对象、对照预设的哈希值验真、打出确定性（deterministic）的 zip 包、刷新发布说明预检记录，并自动运行发布级扫描。只要退出码是 `0`，就代表打包产物、仓库记录和 Release Notes 完全吻合。*

### 3. 最后再过一遍“红线禁区”，绝对不能带私货：
包里**严禁包含**：固件、运行输出物、输入文件、配置文件、抓包/捕获数据、任何第三方二进制。  
包里**只能包含**：本项目自己的代码对象、源码树、清单文件（manifest）和校验和（sums）。  
**一句话：别把 Release 压缩包当成绕过安全合规检查的后门。**

---

## 二、正式发布（收到明确口令后再执行）

Tag 命名规则严格遵循 `versions.md`：必须是附注标签（annotated tag），**严禁移动，严禁复用**。

```sh
cd /path/to/NijiN
TAG=toolkit-$(date +%Y%m%d)
git tag -a "$TAG" -m "NijiN toolkit $(date +%F): objects fa21fb78…/36e56939… match the pinned recipes; four checks and release reconciliation green"
git push origin "refs/tags/$TAG"

gh release create "$TAG" --verify-tag \
    /path/to/release-workspace/nijin-toolkit-*-prep.zip \
    --title "NijiN toolkit $(date +%F)" \
    --notes-file /path/to/release-workspace/RELEASE_NOTES.md
```

> **特别注意：**
> 1. `--verify-tag` 参数非常关键。不加它的话，如果本地 tag 没推成功，GitHub CLI 会悄悄在默认分支上建一个轻量标签（plain tag），直接导致签名和验证信息丢失。如果想先走一遍预演，可以在后面加上 `--draft` 参数（发草稿，不对外公开）。
> 2. Notes 文件是双语写好的。里面的 `Prep record` 区块是本地记录，正式公开给外界时可以删掉；但**警告说明**和**内容清单表格**必须保留。

---

## 三、发布后收尾验证

1. **从 GitHub 发布页面把刚上传的 zip 包下载回来，做双重校验：**
   ```sh
   # 1. 确认压缩包哈希与发布说明里的一致
   shasum -a 256 nijin-toolkit-*.zip

   # 2. 解压后核对内部所有文件的校验和
   unzip -q nijin-toolkit-*.zip -d verify && cd verify/nijin-toolkit
   shasum -a 256 -c SHA256SUMS.txt
   ```
2. 确认远程 Tag 指向的 commit 与 Notes 里写的一致，且包内 manifest 里的 commit 也是该 Tag 对应的 commit。
3. 把 `open-items.md` 里的第 17 项标记为 `published`，并在账本/记录表中登记该 Tag。

---

## 四、万一翻车了怎么办？

* **绝对不要移动已发布的 Tag，也绝对不要复用同一个 Tag 名。**  
  如果要修复，必须打新 Tag（例如 `toolkit-YYYYMMDD.2`），上传新包。在新版本的 Notes 里明确说明上个版本出了什么问题、取代了哪个版本，并在旧版本的 Release 页面上打上显眼的失效标识。
* **触碰红线是“严重安全事故”，不是“手滑笔误”。**  
  一旦发现包里混入了违禁文件，**立刻删除**线上资产！在本地保存证据，复盘并记录到底漏了什么、怎么漏进去的。查清责任和路径后，才能按流程发新 Tag。严禁在旧 Release 页面上悄悄替换文件蒙混过关。
* **如果发现 Notes 吹了仓库里根本没有的东西：**  
  先改仓库、补全代码，再发修正版。绝不能为了圆谎去强行修改历史 commit。
* **包“过期”了怎么办：**  
  如果在打包后、正式发版前，主分支又合入了新代码，**必须彻底重新打包**。核对流程只要发现包里的 commit 与仓库当前状态对不上，就会直接拒绝发布。
* **关于 GitHub 不可变发布（Immutable Releases）：**  
  如果仓库开启了这项设置，上述规则就会变成代码级强制限制（即发出去的 Tag 和产物物理上不可修改、不可删除）。这与我们的发布原则一致，但也意味着：**`--draft`（草稿预览）是你避免翻车的最后一道防线。**
## 简体中文

这份发布文档翻译成通俗、直白的“人话”如下：

---

## 发布操作指南

这是标准发布流程，平时按步骤照做即可。**核心原则：只要没收到明确的“发”指令，绝对不要动**。目前 toolkit 仅在本地打包待命，不要私自发布。

### 1. 发布前（确认三件事）
1. **内部检查全绿**：跑通这四个自查脚本（`check_repository`、`redline_scan`、`check_links`、`check_consistency`），必须全部通过。
2. **重新打包并对账**：用 `tools/build_release.py` 基于目标 commit 重新打包 toolkit，并跑 `--release` 与 `--release-kit` 双重对账。退出码必须是 0（代表打包文件、代码库锁定值、发布文档三者完全一致）。
3. **红线排查（重中之重）**：仔细检查，绝不能混入固件、生成包、用户输入、配置文件、照片或第三方二进制文件。发布包里**只能**有本项目自身的代码、源码、清单和校验哈希。**发布包没有任何免死金牌，红线必须守住。**

### 2. 发布时（收到“发”的指令后，一条命令搞定）
按 [versions.md](versions.md) 打一个附注标签（annotated tag，严禁挪用或复用已有 tag），然后执行：
```bash
git push refs/tags/$TAG
gh release create "$TAG" --verify-tag <zip附件> --notes-file RELEASE_NOTES.md
```
* **`--verify-tag` 绝对不能漏**：如果不加，万一远程没找到这个 tag，`gh` 命令会自动在默认分支建一个轻量标签（非注解 tag），这样我们之前的注解和校验记录就全白费了。
* **想彩排可以加 `--draft`**：加上后会先存为草稿，外界看不到。
* **文档清理**：文案里的 `Prep record` 属于本地台账，正式发布时可以删掉；但**警告说明**和**内容清单**必须保留。

### 3. 发布后（收尾核验）
1. 把刚上传的附件重新下载下来，用公布的哈希值核对一遍文件完整性。
2. 核对 tag 指向的位置与文案一致，确保清单里的 commit 与 tag 对应的 commit 完全相符。
3. 把 [open-items.md](open-items.md) 中的第 17 项改成“已发布”，并记入台账。

### 4. 出现错误怎么补救？
* **标签绝不覆写、绝不复用**：发出去的 tag 错了，千万不要删了重新打。必须打一个新 tag（例如 `toolkit-YYYYMMDD.2`），带上新附件重新发布。新文案要写清修了什么、替代了哪个旧版本；同时在旧版说明里加上“已被新版替代”的提示。
* **踩红线是严重事故，不是小打小闹**：万一把敏感文件传上去了，**必须立即删除违规附件**；在本地保留证据，写清事故报告（混入了什么、怎么混进去的），然后再发修复版本。**严禁偷偷替换已发布的附件！**
* **文案吹过了头怎么办**：如果文案写了仓库里根本不支持的功能，必须先提代码修复仓库，再发新版，严禁靠篡改 Git 历史去硬凑。
* **代码有更新就得重新打包**：只要仓库进了新 commit，之前的备料就作废了，必须重新打包对账（否则校验会自动卡死拦截）。
* **关于 GitHub 的不可变发布（Immutable Releases）**：如果以后仓库开启了这个功能，平台会从技术上彻底锁死已发布的 tag 和附件（不可删改）。所以请记住：**发布前的 `--draft` 草稿，是你最后一次纠错的机会。**