# C15/C30 HE RAW Capture / C15/C30 HE RAW 连拍与预拍

[English](#english) · [简体中文](#简体中文)

## English

Requires official Nikon Z8 firmware **C 3.11** as the base input.

**Experimental; use at your own risk.** Read the [risk notice](../README.md#english), back up photos and settings, and assess the risk before installation. Derived from the NikonFirmwarePatch project (GPL-3.0-only, see [NOTICE.md](../NOTICE.md)); see [verification.md](verification.md) for what has actually been checked here. Public support is limited to **official Nikon Z8 C 3.11 as the build input**. Successful tests do not rule out data loss or camera damage.

### File Formats and Menu Control

With this patch enabled, C15 and C30 modes follow the standard **Image quality** menu (`MENU → Photo shooting menu → Image quality settings → Image quality`). Your selection applies to pre-release history frames, the full-press frame, and subsequent burst frames (even when pre-release capture is turned off).

| Image Quality Setting | Output per C15/C30 Frame | Embedded NEF Full-Size Preview |
|---|---|---|
| RAW | HE NEF only | **8256×5504** (standard NEF preview quality) |
| RAW + JPEG fine★ / fine / normal★ / normal / basic★ | HE NEF + selected JPEG | **8256×5504** (separately encoded at NEF preview quality) |
| RAW + JPEG basic | HE NEF + basic JPEG | **8256×5504** (reuses the basic JPEG main image, matching stock behavior) |
| JPEG fine★ / fine / normal★ / normal / basic★ / basic | Selected JPEG only | None (No NEF) |

* **Previews:** Both RAW and RAW+JPEG embed full-size (8256×5504) previews alongside the standard 1620×1080 and smaller thumbnails.
* **JPEG ★ Options:** Starred (★) options set JPEG compression to *Optimal Quality* rather than *Size Priority*. They do not enable HE★ RAW.
* **Fixed RAW Format:** Extra NEFs generated in C15/C30 are always **HE compression** and **FX (L)** size, regardless of what is selected in the *RAW recording* compression menu.
* **UI Displays:** In C15/C30, the **Image quality (HSFC)** setting is bypassed. However, the `i` menu, `f2` button+dial shortcut, and shooting display still read from the HSFC setting and will not reflect your actual output format. Always configure formats via the main menu.
* **Unchanged Modes:** C60, C120, and standard single-shot/continuous release modes retain their stock behavior.

### Build and Installation

```sh
# 1. Patch official Z8 3.11 firmware (or use --features prores precapture for both)
python patch.py "/path/to/Z_8_0311.bin" --features precapture --version 04.03 --output build/capture
python verify.py "/path/to/Z_8_0311.bin" "build/capture/Z_8_0403.bin" --features precapture

# 2. Generate the v3 configuration file
python configure.py --output build/config-menu

# Optional: Generate config with diagnostic footer
python configure.py --diagnostic-footer --output build/config-diagnostic
```

1. **Build the firmware:** Start from a clean official C 3.11 `.bin` file. Do not patch over an already-patched file. Set `--version` higher than the firmware currently installed on your camera.
2. **Generate `Z8PRE.CFG`:** This release requires a **v3** configuration file; regenerate and replace any older v1/v2 files. All three output formats (RAW, RAW+JPEG, JPEG) are now toggled via the camera menu using this single configuration file. Legacy flags (`--capture-mode`, `--frames`, `--c15-only`) have been removed.
3. **Update and activate:** 
   * Read Nikon's [update instructions and precautions](https://downloadcenter.nikonimglib.com/en/download/fw/606.html) first. Insert a **single** memory card, copy the patched `.bin` to its root directory, and run the standard firmware update from the camera menu with adequate battery power and no interruption. The tools do not write a card or operate a camera.
   * Copy the generated `Z8PRE.CFG` binary file to the root directory of that same card. 
   * The patch remains inactive if `Z8PRE.CFG` is missing, invalid, or present on two cards simultaneously. Formatting the card deletes `Z8PRE.CFG`.
4. **Camera settings:** Set the camera to Photo mode, **FX (L)** image area, and **C15** or **C30** release mode. Configure your desired pre-release and post-release durations in [Pre-Release Capture Options](https://onlinemanual.nikonimglib.com/z8/en/csmd_pre-release_capture_options_233.html). See also Nikon's [release-mode guide](https://onlinemanual.nikonimglib.com/z8/en/release_mode_33.html).

### Usage and Limitations

* **Single Card Only:** Dual-card backup and split RAW/JPEG recording are not supported and will fall back to stock behavior. Use a single memory card.
* **Supported Formats:** Only **HE RAW** at **FX (L)** size is supported. DX crop, Lossless/HE★ RAW, C60/C120, HLG/HEIF, and special processing modes fall back to stock behavior.
* **Switching Formats:** Wait for all pending card writes to finish before changing the Image Quality menu or powering off the camera.
* **In-Camera Playback:** Recorded NEFs are registered directly in the camera's playback database—no restart is needed to view them. Immediately after capture, playback info may display `RAW` instead of `RAW L` (though the file itself is full-size); restarting the camera restores the `L` label.
* **Buffer and Memory:** Holding RAW data in memory until written to the card (plus allocating extra preview buffers for RAW+JPEG) increases RAM usage. A 30-frame compressed history window uses ~519 MB. Note that the 30-frame cap applies only to the pre-release history buffer (allowing up to 1s at C30 or 15 frames at C15), not the total burst or post-release length.
* **Write Speeds:** On SD cards, frame write intervals average ~0.24–0.32 s for RAW-only and ~0.45–0.69 s for RAW+JPEG (e.g., 308 RAW+JPEG pairs took ~155 s to clear). If accumulated writes saturate the buffer, the pre-capture `!` warning icon will appear and pre-release history frames may be dropped until writes finish and you half-press again to refill the buffer.
* **Metadata & Small Previews:** Generated NEFs omit some optional factory metadata, including lens-correction blocks, the grayscale subimage, and certain XMP correction tags. In RAW+JPEG Normal/Basic modes, the smaller FHD/VGA previews inside the NEF inherit the Normal/Basic JPEG quality rather than Fine.

### Error Handling and Disabling

* **Write Timeouts & Fallbacks:** Each NEF has a 1.5-second write budget (checked between I/O calls). If database registration fails, the camera may write a fallback JPEG alongside an unregistered `.NE_` file. Other errors may result in JPEG-only output or a reduced (1620×1080) NEF preview. In RAW-only mode, a fallback JPEG uses lower NEF-preview compression even though its EXIF header reports `FINE`.
* **Stop File (`Z8PRESTP.BIN`):** If a write error occurs, the firmware writes `Z8PRESTP.BIN` to the card and halts NEF saving for the remainder of the current power session (JPEG quality settings may still apply). 
  * Restarting the camera clears the session lock, though `Z8PRESTP.BIN` stays on the card as a diagnostic log.
  * If `Z8PRESTP.BIN` was not generated by this firmware (e.g., an empty or manually placed file), it acts as a permanent kill-switch and blocks NEF saving even across restarts.
* **Diagnostics:** Frame retention and rejection reasons are written to a fixed-address status block in memory for diagnostic tools (no on-screen alerts are shown).
* **Disabling the Patch:** Power off the camera, remove the card, and delete `Z8PRE.CFG`. C15 and C30 will revert to stock HSFC behavior.

---

## 简体中文

仅支持基于官方 Nikon Z8 **C 3.11** 固件构建。

**测试版本（试验性功能），风险自负。** 安装前阅读[风险说明](../README.md#简体中文)，备份照片和设置，自行衡量上机风险。本工作派生自 NikonFirmwarePatch 项目（GPL-3.0-only，见 [NOTICE.md](../NOTICE.md)）；已核验范围见 [verification.md](verification.md)。公开支持的构建输入仅限**官方 Nikon Z8 C 3.11**；测试通过不排除数据丢失或相机损坏。

### 文件格式与菜单控制

启用本补丁后，C15 和 C30 模式直接遵循机内的普通**“画质”菜单**（`MENU → 照片拍摄菜单 → 画质设置 → 画质`）。所选格式同时作用于预拍历史帧、全按快门当帧及后续连拍帧（关闭预拍功能时同样生效）。

| 普通“画质”菜单选项 | C15／C30 每帧实际输出 | NEF 内嵌全尺寸预览图 |
|---|---|---|
| RAW | 仅 HE NEF | **8256×5504**（相机标准 NEF 预览画质） |
| RAW＋JPEG fine★／fine／normal★／normal／basic★ | HE NEF＋所选画质 JPEG | **8256×5504**（另行编码为相机 NEF 预览画质） |
| RAW＋JPEG basic | HE NEF＋basic JPEG | **8256×5504**（与原厂一致，直接复用 basic JPEG 主图） |
| JPEG fine★／fine／normal★／normal／basic★／basic | 仅所选画质 JPEG | 无 NEF |

* **内嵌预览：** RAW 和 RAW+JPEG 均内嵌全尺寸（8256×5504）预览图，同时保留 1620×1080 及更小尺寸的缩略图。
* **JPEG ★ 选项：** 带 ★ 选项代表 JPEG 采用“最佳品质（Optimal Quality）”，不带 ★ 代表“文件大小优先（Size Priority）”。该选项仅针对 JPEG，不会开启 HE★ RAW。
* **固定 RAW 规格：** C15／C30 生成的 NEF 固定为 **HE 压缩**、**FX（L）全尺寸**，不受“RAW 记录”菜单中无损压缩或 HE★ 选项的影响。
* **界面显示差异：** 在 C15／C30 下，**“画质（HSFC）”**菜单不决定实际输出。但 `i` 菜单、`f2` 快捷键及取景器拍摄界面仍会读取并显示 HSFC 的设置，与实际保存的文件格式可能不一致。请始终通过主菜单设置画质。
* **不受影响的模式：** C60、C120 以及普通单张/其他连拍模式保持原厂行为。

### 构建与安装

```sh
# 1. 基于官方 Z8 3.11 固件打补丁（如需同时启用 ProRes 可用 --features prores precapture）
python patch.py "/path/to/Z_8_0311.bin" --features precapture --version 04.03 --output build/capture
python verify.py "/path/to/Z_8_0311.bin" "build/capture/Z_8_0403.bin" --features precapture

# 2. 生成 v3 版配置文件
python configure.py --output build/config-menu

# 可选：生成带诊断尾标的配置文件
python configure.py --diagnostic-footer --output build/config-diagnostic
```

1. **构建固件：** 必须使用干净的官方 C 3.11 `.bin` 文件，切勿在已打过补丁的固件上二次叠加。`--version` 参数设定的版本号必须高于机身当前已安装的版本。
2. **生成 `Z8PRE.CFG`：** 本版本要求 **v3** 配置文件，旧版 v1／v2 文件必须重新生成并替换。同一份固件和配置文件已支持全部三种输出格式（直接机内切换），旧版 `--capture-mode`、`--frames`、`--c15-only` 参数已废弃。
3. **升级与激活：**
   * 先阅读 Nikon 的[更新步骤与注意事项](https://downloadcenter.nikonimglib.com/en/download/fw/606.html)。机身内**仅插入一张**存储卡，将生成的固件包复制到卡根目录，按官方流程完成固件升级（保证电量充足、不中断）。工具不会写卡、不操作相机。
   * 将生成的二进制配置文件 `Z8PRE.CFG` 复制到该卡根目录。
   * 若缺少 `Z8PRE.CFG`、文件无效、或两张卡同时存在配置文件，补丁均不会激活。格式化存储卡会清除此文件。
4. **机身设置：** 设为照片模式、**FX（L）** 画幅、释放模式选 **C15** 或 **C30**。在[预拍摄选项](https://onlinemanual.nikonimglib.com/z8/zh-cn/csmd_pre-release_capture_options_233.html)中设置预拍和后拍时长（另见 Nikon 的[释放模式说明](https://onlinemanual.nikonimglib.com/z8/zh-cn/release_mode_33.html)）。

### 使用与限制

* **仅限单卡：** 不支持双卡备份或 RAW/JPEG 分卡记录（插双卡或开启相关设置将回退至原厂逻辑）。请仅使用单张存储卡。
* **格式限制：** 仅支持 **HE RAW** 与 **FX（L）** 画幅。DX 裁切、无损/HE★ RAW、C60/C120、HLG/HEIF 及特殊处理模式均不接管，按原厂逻辑运行。
* **切换画质：** 请等待存储卡写入完全结束后，再进入菜单切换画质或关机。
* **机内回放：** 正常生成的 NEF 会直接注册到机内照片库，写卡完成后即可直接回放，**无需重启相机**。刚拍完回放时，左上角可能仅显示 `RAW` 而缺少 `L` 标记（文件实际为完整大尺寸），重启相机后即恢复显示 `RAW L`。
* **缓存与内存：** RAW 数据需等到写卡完成才释放内存（RAW+JPEG 还需额外分配预览图空间），内存占用显著增加。仅 30 帧预拍历史缓存即占用约 519 MB。注：配置文件中的 30 帧上限仅代表“预拍历史窗口”的最大容量（如 C30 预拍 1 秒为 30 张，C15 预拍 1 秒为 15 张），**不限制整组连拍的总张数或后拍张数**。
* **写卡速度：** 以 SD 卡为例，纯 RAW 写入间隔约 0.24–0.32 秒/张，RAW+JPEG 约 0.45–0.69 秒/张（实测连续保存 308 对 RAW+JPEG 耗时约 155 秒）。当写入积压导致缓存耗尽时，取景器预拍图标会出现 `!` 警告，此时按下快门可能会丢失预拍历史帧；需等待写入完成、警告消失后再半按快门重新填满历史缓存。
* **元数据与小预览图：** 生成的 NEF 缺少部分可选的原厂元数据（镜头校正数据块、灰度子图及部分 XMP 校正信息）。在 RAW+JPEG 的 Normal／Basic 档位下，NEF 内部的小尺寸（FHD/VGA）预览图会继承 JPEG 的 Normal／Basic 画质，而非原厂的 Fine 画质。

### 异常处理与停用

* **超时与回退机制：** 单张 NEF 写入预算为 1.5 秒（在底层 I/O 调用间隙检查）。若数据库注册失败，可能回退为生成一张 JPEG 外加一个未注册的 `.NE_` 临时文件（需后续重新扫描照片库）；其他异常可能导致仅输出 JPEG 或 NEF 预览图缩小为 1620×1080。纯 RAW 模式下若触发回退生成 JPEG，其实际画质为较低的 NEF 预览画质，但 EXIF 仍会标记为 `FINE`。
* **停机保护文件 (`Z8PRESTP.BIN`)：** 发生严重写入故障时，固件会在卡上写入 `Z8PRESTP.BIN`，并在**本次开机期间**停止保存后续 NEF（JPEG 画质设置仍可能生效）。
  * 重启相机后，由本固件生成的 `Z8PRESTP.BIN` 不再阻止保存 NEF（文件保留在卡上供排查，固件不会自动删除）。
  * 若卡上的 `Z8PRESTP.BIN` 非本固件生成（如手工放置的空文件或截断文件），则会作为永久停机开关生效，重启后依然阻止保存 NEF。
* **诊断状态：** 每帧是否成功保留及具体的拒写原因均记录在固定内存地址的状态块中，供诊断工具读取（机身屏幕无报错弹窗）。
* **完全停用：** 关机并安全取卡，删除卡根目录下的 `Z8PRE.CFG`，C15／C30 即恢复原厂 HSFC 行为。
