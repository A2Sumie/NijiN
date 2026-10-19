**WIP. Owner's Z8 bricked! Use at your own risk.**
**施工中。作者的 Z8 已经刷砖！风险自担。**

这里是一份更符合中文日常表达、直白接地气的重写版本，保留了所有关键技术细节、警告和参数：

---

# 快速上手：手把手打一个固件包

一页讲清，零门槛。带你从下载尼康官方固件开始，到在本地编译并完成独立校验。

**⚠️ 极高风险警告：V11.1 版本极不安全！已知存在严重缺陷，千万不要刷进相机！详情见 [risks.md](risks.md)。**   — experimental — never on hardware。
**⚠️ 项目施工中。作者自己的 Z8 已经刷成砖了！执意尝试，风险自负。**  

QQ 群：`1108781835`

刷机是你自己的个人决定；本项目的脚本工具**绝对不会**主动连接相机或向存储卡写入任何数据。在把固件弄进相机前，务必先仔细阅读 [risks.md](risks.md)。

---

## 准备工作

- **环境**：macOS 或 Linux，Python 3.10 或更新版本。需要联网一次（安装 Python 依赖库）。
- **空间**：大约 500 MB 剩余磁盘空间。
- **编译器（可选）**：支持 AArch64 架构目标的 Clang——**只有**在需要 `precapture`（预拍摄）功能时才必须装；如果不装，就只能单独打 `prores` 补丁。
- **官方固件**：请自行下载官方 **Nikon Z8 C 3.11** 固件更新包。

---

## 操作步骤

### 1. 下载并校验官方固件
前往[尼康官网下载中心](https://downloadcenter.nikonimglib.com/en/download/fw/606.html)下载（需同意尼康用户协议）。下载后必须校验，文件必须一字节不差：

```sh
shasum -a 256 /path/to/Z_8_0311.bin
# 文件大小必须正好是 99,051,117 字节，且终端输出的哈希值必须完全一致：
# d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96
```

### 2. 获取代码并配置环境

```sh
git clone https://github.com/A2Sumie/NijiN.git
cd NijiN
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 3. 只读兼容性测试
这一步只读取文件做检查，不会修改任何东西：

```sh
python patch.py "/path/to/Z_8_0311.bin" --features prores precapture --check
```
如果终端打印出了一段 JSON 格式的报告，就说明你的固件文件受支持，可以继续。

### 4. 开始构建（打补丁）
挑选你需要的功能（可选 `prores`、`precapture`、`opengate`、`menuh`），指定版本号，并输出到一个**尚不存在**的新目录：

```sh
python patch.py "/path/to/Z_8_0311.bin" --features prores precapture \
    --version 03.11 --tag p1 --output build/first
```

### 5. 独立二次校验
用另一个独立的校验脚本复查刚才打好的包（不盲信编译脚本自己的输出）：

```sh
python verify.py "/path/to/Z_8_0311.bin" "build/first/Z_8_0311.bin" \
    --features prores precapture
```

### 6. 跑单元测试（可选，跑一下很快）

```sh
python tests/validate.py --stock "/path/to/Z_8_0311.bin" --report build/validate.json
```

---

现在你手里应该有了打好补丁的固件 `build/first/Z_8_0311.bin`，外加 `manifest.json`、`SHA256SUMS.txt` 以及对应功能的配置文件（如 `Z8PRE*.CFG` / `Z8OG.CFG`）。

**⚠️ 到这一步为止，安全阶段就结束了！**  
生成文件是安全的，但**这个文件刷进相机后会发生什么，完全是另一回事**——请务必阅读 [risks.md](risks.md) 以及 [features.md](features.md) 中的功能可用性表格。  
上面这套流程编译出的固件属于 **V11.1** 分支（`03.11.p1` 这一代），已被明确标记为 **⛔ 不安全（已知存在严重缺陷）**，缺陷详情见 [risks.md](risks.md#known-unsafe-v111-2026-10-19)。  
**强烈建议：在 V12 版本被完全确认可用之前，不要把任何生成的文件刷入实体相机！** V12（即原 V11.2 构建）虽然修复了变砖相关的缺陷家族（详见 [bricking-edge.md](bricking-edge.md)），但目前依然处于高度实验阶段，**严禁上机测试**。

---

## 常见报错与排错

下面列出的每一条报错，都是脚本在遇到异常时主动抛出、用于防止意外的拦截机制（最后两项摘自源码）。**脚本没有任何 `--force` 强制跳过开关。**

| 报错信息 | 意思是什么 | 怎么解决 |
|---|---|---|
| `Input must be a regular firmware file` | 路径填错了，或者该路径不是普通文件 | 检查你输入的固件文件路径 |
| `Unsupported firmware length` | 文件大小不对，不是官方对应的更新包 | 必须使用大小正好为 99,051,117 字节的官方 C 3.11 固件 |
| `Unsupported outer package context` | 文件大小虽然对，但内容全错（根本不是固件） | 文件损坏或不是固件包，重新下载 |
| `Package body CRC mismatch` / `Package SHA1 mismatch` | 固件文件被改动过，或者下载损坏了 | 重新下载，并用步骤 1 核对 SHA-256 哈希值 |
| `Incompatible region: …` *(源码抛出)* | 是该系列固件，但特征指纹与受支持版本对不上 | 目前仅支持官方发布的 Z8 C 3.11 固件 |
| `Output directory already exists; use a new directory` | 输出目录已经存在（脚本为了安全绝不覆盖旧文件） | 在 `--output` 参数里换一个不存在的新目录 |
| `AArch64 compilation failed: …` | 系统里没有能用的 Clang 编译器 | 要么编译时不加 `precapture`（只留 `prores`），要么安装支持 AArch64 编译目标的 Clang |
| `Compiler output differs from the reviewed recipe` *(源码抛出)* | 你的编译器生成的二进制机器码与经过审核的代码不一致 | 必须使用经审核的 Clang 版本；脚本绝不接受“看着差不多”的编译产物 |
| `opengate needs precapture: only the precapture loader window (0x40970000) maps the hook code` | 功能依赖限制：`opengate` 必须依赖 `precapture` 的加载窗口来映射钩子代码 | 在 `--features` 参数里加上 `precapture` |
| `Select prores, precapture, opengate, or any combination, without duplicates` | 功能参数里有重复项，或者名字打错了 | 检查功能列表，不能重复填；目前合法的功能名称只有：`prores`、`precapture`、`opengate`、`menuh` |
| `Tag must be a lowercase letter and digit` | `--tag` 格式不合规 | 请填 `p1`（代表实验分支的代数，见 [versions.md](versions.md)） |
| `Version must be two digits, a dot and two digits, e.g. 04.01` | 版本号格式不对（注：示例里的 `04.01` 纯粹只是格式演示，千万别真填 `04.01`，见 [build.md](build.md)） | 请填写类似 `03.11` 的格式 |
| `Building requires --version and --output; use --check for read-only inspection` | 构建时缺少必填参数 | 补充 `--version NN.NN --output <新目录>` 参数 |
| `--check cannot be combined with output options` | 检查模式和输出模式冲突了 | 要么只用 `--check` 纯看，要么指定输出目录去构建，不能混用 |
| pytest 提示 `skipped` | 某些测试需要特定的本地切片文件，脚本自动跳过了 | 没设置环境变量 `NIJIN_EG_SLICE` 时这是正常现象，不用管 |

如果你遇到了表格之外的报错，请直接按报错英文的字面意思去理解：**脚本抛出的每一个拒绝提示都是一道安全防护，不是在刁难你。**

---

## 接下来该看什么

- [build.md](build.md) —— 完整构建流程、版本号命名逻辑与严格检验机制
- [features.md](features.md) —— 各功能的具体作用及当前真实的稳定性状态
- [raw-precapture.md](raw-precapture.md) —— RAW 预拍摄使用指南：前期准备、操作流程与局限性
- [verification.md](verification.md) —— 校验机制能证明什么、以及它证明不了什么
- [risks.md](risks.md) —— 翻车变砖事件复盘、已知风险与救砖回滚说明
## 简体中文

以下是转换为**通俗易懂、排版清晰**的“人话”版本。所有命令、校验值与安全警告均完整保留：

---

# 尼康 Z8 固件修改工具

> **⚠️ 极度危险，千万别刷！**
> **作者自己的 Z8 已经刷成砖头了！**
> 当前 **V11.1** 版本存在严重已知缺陷，**绝对不要刷入相机**！详情请看 [risks.md](risks.md) — 从未上机。
> 项目仍在施工中，一切风险请自行承担。

* **交流 QQ 群**：`1108781835`
* **特别说明**：本工具只在电脑上生成文件，**不会**直接连接相机，也**不会**往存储卡里写东西。刷不刷机全凭你自己决定；但在你把文件放进相机之前，**务必先阅读 [risks.md](risks.md)**。

---

### 准备工作

在开始前，你需要准备：
1. **电脑系统**：macOS 或 Linux。
2. **运行环境**：Python 3.10 或更高版本。
3. **硬盘空间**：至少 500 MB 剩余空间。
4. **编译器（可选）**：如果打算开启 `precapture`（预拍）功能，需要安装支持 AArch64 架构的 Clang。
5. **官方原厂固件**：请自行下载官方 **Nikon Z8 C 3.11** 固件文件。

---

### 快速上手（命令照抄，替换固件路径即可）

#### 1. 核对原厂固件
确保你下载的官方固件完全正确。终端运行：
```bash
shasum -a 256 /固件路径/Z_8_0311.bin
```
* **必须匹配**哈希值：`d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96`
* 文件大小必须精确为：`99,051,117` 字节。

#### 2. 安装工具与环境
```bash
git clone <本仓库地址>
cd <仓库目录>
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

#### 3. 兼容性只读检查（不会修改任何文件）
```bash
python patch.py "/固件路径/Z_8_0311.bin" --features prores precapture --check
```
* 如果终端输出了 JSON 格式的报告，说明该固件支持修改。

#### 4. 生成改版固件
```bash
python patch.py "/固件路径/Z_8_0311.bin" --features prores precapture --version 03.11 --tag p1 --output build/first
```
* **注意**：`--output` 指定的目录（如 `build/first`）**必须是一个全新的不存在目录**。

#### 5. 校验生成的文件
```bash
python verify.py "/固件路径/Z_8_0311.bin" "build/first/Z_8_0311.bin" --features prores precapture
```

#### 6. 自动化测试（可选）
```bash
python tests/validate.py --stock "/固件路径/Z_8_0311.bin" --report build/validate.json
```

---

### 关于生成的文件与当前状态

构建完成后，你会得到：`Z_8_0311.bin`、`manifest.json`、`SHA256SUMS.txt` 以及对应的 `Z8PRE*.CFG` / `Z8OG.CFG` 配置文件。

**请牢记：到这一步为止是安全的，但一旦把文件放进相机，风险完全由你承担！**
* 上面步骤编译出来的是 **V11.1** 分支（`03.11.p1` 试验版），目前状态是 **⛔ 不安全（存在已知缺陷，极易成砖）**。
* **强烈建议：先别着急刷，等 V12 验收之后再用！** 虽然 V12 修复了这批变砖缺陷（详见 [bricking-edge.md](bricking-edge.md)），但目前依然处于完全没有在真实相机上测试过的试验阶段。
* 已知缺陷清单见：[risks.md (已知不安全问题)](risks.md#known-unsafe-v111-2026-10-19)。

---

### 常见报错与排查指南

> **核心原则**：这里没有“强制跳过/绕过”开关。程序只要报错拒绝执行，就是在**保护你的相机不变成砖头**。看清报错，按规矩来：

| 报错信息 / 现象 | 产生原因及解决方法 |
| :--- | :--- |
| **文件不存在 (File not found)** | 检查你输入的固件路径对不对。 |
| **Unsupported firmware length** | 固件大小不对。请务必使用官方 C 3.11（精确为 99,051,117 字节）的文件。 |
| **Unsupported outer package context** | 文件虽然大小对，但内容不对（不是原厂升级包）。请重新下载原版固件。 |
| **Package body CRC mismatch**<br>**Package SHA1 mismatch** | 文件被改动过或已损坏。重新下载官方固件并校验 SHA-256。 |
| **Incompatible region** | 当前只支持官方原版 Z8 C 3.11 固件。 |
| **输出目录已存在** | `--output` 参数指定的文件夹已经存在了，换个新路径名。 |
| **AArch64 compilation failed** | 缺少 ARM 交叉编译器。要么只开 `prores` 功能，要么电脑上装好支持 AArch64 的 Clang。 |
| **Compiler output differs from the reviewed recipe** | 编译结果与审核过的指令不一致。必须换用经过验证的官方指定版本 Clang，“差不多”可不行。 |
| **opengate needs precapture** | 依赖缺失。启用了 `opengate` 就必须同时加上 `precapture`。 |
| **Select prores, precapture, opengate...** | 功能参数写错了：只能选这三个，不能拼错，也不能重复添加。 |
| **Tag must be a lowercase letter and digit** | `--tag` 格式必须是小写字母+数字，例如填 `p1`（代表试验版世代，详见 [versions.md](versions.md)）。 |
| **Version must be two digits, a dot...** | 版本号格式必须是两位数字.两位数字（例如 `03.11`）。<br>⚠️ **特别警告：文档里的 `04.01` 只是格式举例，千万不要真的照抄打成 04.01**（见 [build.md](build.md)）！ |
| **缺少 `--version` 或 `--output`** | 命令漏写了必要参数，补齐后再跑。 |
| **--check cannot be combined with output options** | `--check`（检查模式）和输出文件模式冲突，二选一。 |
| **pytest 运行时显示 skipped** | 正常现象（因为你没配置 `NIJIN_EG_SLICE` 环境变量）。 |

---

### 进一步阅读

* [完整构建流程与文档 (build.md)](build.md)
* [功能列表与实际可用状态 (features.md)](features.md)
* [RAW 格式预拍使用指南（准备、步骤与限制）(raw-precapture.md)](raw-precapture.md)
* [独立校验工具的原理与意义 (verification.md)](verification.md)
* [事故记录、变砖风险与恢复指南 (risks.md)](risks.md)