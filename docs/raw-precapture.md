# C15/C30 HE RAW capture / C15/C30 HE RAW 连拍与预拍

> **Provenance note.** This usage guide is derived from the upstream
> NikonFirmwarePatch project (GPL-3.0-only, see [NOTICE.md](../NOTICE.md)).
> Testing statements in it (converter checks, file counts, menu coverage)
> describe **that project's own builds**. They are not hardware records for
> the builds produced with this repository's recipes — see
> [verification.md](verification.md) for what has actually been checked here.

[English](#english) · [简体中文](#简体中文)

## English

**Experimental; use at your own risk.** Read the [risk notice](../README.md#english), back up photos and settings, and assess the risk before installation. Public support is limited to **official Nikon Z8 C 3.11 as the build input**. Successful tests do not rule out data loss or camera damage.

### What controls the files

With the new configuration enabled, C15/C30 follows the camera's **ordinary Image quality menu**. The choice applies to pre-release history, the full-press frame, and subsequent frames. It also applies when pre-release capture is off.

| Ordinary Image quality choice | Every supported C15/C30 frame | Full-size preview embedded in the NEF |
|---|---|---|
| RAW | HE NEF only | **8256×5504** at the camera's NEF-preview quality |
| RAW + JPEG fine★ / fine / normal★ / normal / basic★ | HE NEF + the selected JPEG quality | **8256×5504**, separately encoded at the camera's NEF-preview quality |
| RAW + JPEG basic | HE NEF + basic JPEG | **8256×5504**, reuses the basic JPEG main image, as the stock NEF path does |
| JPEG fine★ / fine / normal★ / normal / basic★ / basic | The selected JPEG quality only | No NEF |

Both RAW and RAW+JPEG now embed full-size previews. The previous reduced-preview limitation of RAW+JPEG is removed for successful captures in this menu-controlled mode. NEFs still contain full-resolution RAW data, a 1620×1080 preview and smaller previews. The JPEG ★ choices mean **Optimal Quality**; unstarred choices mean **Size Priority**. These are JPEG options and do not enable HE★ RAW.

Use **MENU → Photo shooting menu → Image quality settings → Image quality** (labels may differ by language). In supported C15/C30 shooting, **Image quality (HSFC) does not select the output**. The **i menu, f2 button/dial shortcut and shooting display still refer to the HSFC setting**, so they may disagree with what this patch saves. Use the full menu and inspect the resulting files. C60/C120 remain outside the patch's scope.

The ordinary **RAW recording** compression choice does not affect these extra NEFs: they are **HE only**, even if that menu says lossless or HE★. Ordinary single-shot/other release modes retain their original behavior.

### Build and migrate

1. Start from a fresh official C 3.11 package. Choose `--features precapture` for this function or `--features prores precapture` to include ProRes. Keep the input, manifest and checksums, and verify the generated package against the same input. **Do not apply this release on top of an earlier pre-capture output.** Choose an output version higher than the camera's installed version; the script cannot read that version or guarantee downgrade/recovery.
2. Read Nikon's [update instructions and precautions](https://downloadcenter.nikonimglib.com/en/download/fw/606.html). Installation is manual, with adequate battery power and no interruption. The tools do not write a card or operate a camera.
3. Back up a card and leave ample space. Trials used SD; other card timings are not established. Initially use only one recording card. Copy the generated update package to its root, update following Nikon's procedure, and confirm the displayed version.
4. Copy the **new `Z8PRE.CFG`** to that card's root. **This release requires v3; regenerate and replace older v1/v2 files.** Invalid/missing configuration, or valid configuration on both cards, leaves the feature inactive. Reformatting removes the file. It is generated binary data, not editable text.
5. Set photo mode, **FX / full-size L**, and C15 or C30. Select RAW, RAW+JPEG or JPEG in the ordinary menu above. Configure pre-release and post-release durations in **Pre-Release Capture Options**. See Nikon's [release-mode guide](https://onlinemanual.nikonimglib.com/z8/en/release_mode_33.html) and [pre-release settings](https://onlinemanual.nikonimglib.com/z8/en/csmd_pre-release_capture_options_233.html).

```sh
python patch.py "/path/to/Z_8_0311.bin" --features precapture --version 04.03 --output build/capture
python verify.py "/path/to/Z_8_0311.bin" "build/capture/Z_8_0403.bin" --features precapture

# Regenerate the normal menu-controlled configuration locally
python configure.py --output build/config-menu
# Optional diagnostic footer, normally omitted
python configure.py --diagnostic-footer --output build/config-diagnostic
```

The same firmware/configuration supports all three file types; **change them on the camera, without rebuilding, reinstalling or exchanging configuration files**. Previous `--capture-mode`, `--frames` and `--c15-only` configuration options are removed and rejected. The new configuration enables both C15 and C30. Its history ceiling is 30, allowing the camera's normal pre-release windows; **it does not limit an entire burst or the post-release portion to 30 frames**. Do not hand-edit flags.

### Shoot and check

1. Start with a static scene, manual focus, a visible timer, C15, a 0.3 s history window and a short post-release duration. Begin with RAW+JPEG so both files can be checked.
2. Half-press long enough to fill the selected history window, then fully press briefly and release. A full buffer yields 5/15 history frames at C15 with 0.3/1 s, or 9/30 at C30. Shorter half-presses or unavailable buffer space can produce fewer. The full-press and later frames follow the **same menu format**; with pre-release off, all saved frames are current/post-release frames.
3. Wait for card writing to finish before playback, normal power-off or card removal. Do not interrupt writing. Initially finish one burst before starting another.
4. Normal successful NEFs are registered in the stock photo database and can be played back directly. **No restart is needed for playback.** Immediately after capture, the RAW label may omit **L**; a normal restart later restores RAW L. The tested files already record Large and contain the full-size image. This display issue remains unresolved.
5. Check the card files and full RAW decoding. RAW should have only NEF; RAW+JPEG should have both files at every number; JPEG should have only JPEG, for both history and current frames. Check that JPEG grade/★ agrees with the ordinary menu, not the stale shooting display.

Switch between the three formats only after the previous burst is finished. The implementation records the menu selection when each frame is submitted; changing it during a burst or pending write is not a validated workflow.

### Buffer behavior and limits

- **Capture cadence is not card-writing speed.** Limited RAW+JPEG trials showed roughly 0.45–0.69 s between frame writes; RAW-only showed 0.24–0.32 s. A 14-trigger RAW+JPEG stress sequence saved 308 pairs and took about 155 s to finish writing. These are scene/card-specific observations, not limits or guarantees of sustained 30-fps RAW.
- The pre-capture **“!”** indicator appeared during accumulated writes. One stress trigger had **zero historical frames and three current frames**. Waiting until the normal indication returns is necessary before expecting a full history window, and filling that window still takes time. The exact buffer threshold has not been established; no guarantee of unlimited retriggering or a particular Max-duration burst is made.
- Keeping RAW frames until written and allocating an additional preview region for most RAW+JPEG grades increases memory use. A 30-frame compressed history alone uses about 519 MB. Scene complexity, card throughput and other settings can change the available depth and waiting time.
- RAW is **HE, FX L only**. No lossless, HE★, DX or C60/C120 RAW. HLG/HEIF, unsupported special processing modes, dual-card backup and split RAW/JPEG recording are not handled; they fall back to stock behavior. Use one card for the supported workflow.
- In RAW+JPEG normal/basic grades, the NEF's smaller FHD/VGA previews inherit the JPEG path's grade. Factory NEFs can instead carry fine-quality small previews. Full-size NEF previews use the intended NEF-preview quality.
- Optional factory metadata is still missing, including lens-correction blocks, a grayscale subimage and some XMP correction data. Adobe DNG Converter 18.1.1 has been tested; NX Studio, Lightroom, full lens-correction equivalence and every converter have not. In-camera deletion/protection/transfer, near-full cards, AF tracking and automatic capture have not been fully validated. Remaining-shot/buffer estimates and shortcut displays are still stock HSFC estimates.

### Failures and disabling

Registration failure can fall back to a JPEG plus a separately written NEF, temporarily named `.NE_`; that NEF may require a later database rescan. Other failures may produce JPEG-only output, a reduced 1620×1080 NEF preview, missing/partial files, or **`Z8PRESTP.BIN`**. A RAW-only fallback JPEG can have the lower NEF-preview quality while its metadata still says FINE. Check the file set, not just the absence of an error message.

The stop file prevents additional NEF saving and survives restart; **JPEG menu quality may still be applied**. To disable this feature fully, remove `Z8PRE.CFG` while the camera is off and the card is safely accessible. C15/C30 then uses original HSFC behavior. This does not uninstall firmware, remove an included ProRes feature or guarantee rollback.

The per-NEF budget is 1.5 s, checked after a stock write returns or between fallback I/O calls. It cannot interrupt a blocked call or guarantee against freezes. On errors, missing files, `.NE_`, a stop file, resets or freezes, stop testing and preserve evidence. After writing has ended, back up the card and disable the feature; investigate before deleting a stop file or retrying.

Read the [validation scope](validation.md) for hardware coverage, frame-correspondence review and model limits. New public packages are not individually hardware-certified.

## 简体中文

**测试版本，风险自负。** 安装前阅读[风险说明](../README.md#简体中文)，备份照片和设置，自行衡量上机风险。公开支持的构建输入仅限**官方 Nikon Z8 C 3.11**；测试通过不排除数据丢失或相机损坏。

### 哪个菜单决定文件

启用本版配置后，C15／C30 按普通**“画质”菜单**保存文件。预拍历史帧、全按那一帧和之后的正式拍摄帧都采用同一选择；关闭预拍时也生效。

| 普通“画质”选择 | 每张受支持的 C15／C30 帧 | NEF 的全尺寸内嵌预览 |
|---|---|---|
| RAW | 仅 HE NEF | **8256×5504**，相机 NEF 预览画质 |
| RAW＋JPEG fine★／fine／normal★／normal／basic★ | HE NEF＋所选画质 JPEG | **8256×5504**，另行编码为相机 NEF 预览画质 |
| RAW＋JPEG basic | HE NEF＋basic JPEG | **8256×5504**，像原厂一样复用 basic JPEG 主图 |
| JPEG fine★／fine／normal★／normal／basic★／basic | 仅所选画质 JPEG | 无 NEF |

RAW 和 RAW+JPEG 现在都带全尺寸内嵌预览；本版菜单控制模式正常成功拍摄时，上一版 RAW+JPEG 只有缩小内嵌图的限制已解除。NEF 仍含完整分辨率 RAW、1620×1080 及更小预览。JPEG 的 ★ 表示 **Optimal Quality（最佳品质）**，不带 ★ 表示 **Size Priority（文件大小优先）**；这不等于启用 HE★ RAW。

请在 **MENU → 照片拍摄菜单 → 画质设置 → 画质** 中选择（不同语言名称可能略有差异）。在受支持的 C15／C30 下，**“画质（HSFC）”不决定实际输出**。但 **i 菜单、f2 按钮加拨盘和取景画面上的显示仍对应 HSFC 设置**，可能与实际文件不同；请使用完整菜单，并核对拍出的文件。C60／C120 不在补丁范围内。

普通 **“RAW 记录”** 的压缩设置对这些 NEF 无效：即便选了无损或 HE★，本功能也只生成 **HE**。普通单张及其他释放模式保持原有行为。

### 构建与升级

1. 从全新的官方 C 3.11 包构建，选择 `--features precapture`，或用 `--features prores precapture` 同时加入 ProRes。保留输入、manifest 和校验值，用同一原始输入核验输出。**不要叠加到上一版预拍补丁输出上。** 输出版本须高于机身已安装版本；脚本不读取机身版本，不保证降级或恢复。
2. 阅读 Nikon 的[更新步骤与注意事项](https://downloadcenter.nikonimglib.com/en/download/fw/606.html)，手动决定和执行安装，保证电量充足，不中断更新。工具不会写卡或操作相机。
3. 备份存储卡并留足空间。实测使用 SD，其他卡的耗时未验证。初次只插入一张记录卡，将生成的更新包放到卡根目录，按官方流程更新并核对版本。
4. 将新生成的 **`Z8PRE.CFG`** 放到卡根目录。**本版要求 v3，旧 v1／v2 文件必须重新生成并替换。** 缺少／无效配置或两张卡都有有效配置时，功能不启用；格式化会删除配置。它是二进制文件，不能用文本编辑器修改。
5. 设置照片模式、**FX／全尺寸 L**、C15 或 C30，在上述普通菜单中选择 RAW、RAW+JPEG 或 JPEG。通过**预拍摄选项**设置预拍／后拍时长。官方说明：[释放模式](https://onlinemanual.nikonimglib.com/z8/en/release_mode_33.html)、[预拍摄选项](https://onlinemanual.nikonimglib.com/z8/en/csmd_pre-release_capture_options_233.html)。

```sh
python patch.py "/path/to/Z_8_0311.bin" --features precapture --version 04.03 --output build/capture
python verify.py "/path/to/Z_8_0311.bin" "build/capture/Z_8_0403.bin" --features precapture

# 本地重新生成普通菜单控制配置
python configure.py --output build/config-menu
# 可选诊断尾标，默认不添加
python configure.py --diagnostic-footer --output build/config-diagnostic
```

同一固件和配置支持三种文件类型，**之后直接在机内切换，无需重建、重装或换配置**。旧的 `--capture-mode`、`--frames`、`--c15-only` 配置参数已移除并会被拒绝。新配置同时启用 C15／C30，30 是历史帧容量上限，允许使用机内各档预拍时长；**不代表整组拍摄或后拍部分最多 30 张**。不要手工修改配置位。

### 拍摄与核对

1. 初次使用静态场景、手动对焦和可见计时器，从 C15、0.3 秒预拍、较短后拍开始。可先用 RAW+JPEG，便于核对两种文件。
2. 半按覆盖所选历史时长，再短暂全按并松开。缓存填满时，C15 预拍 0.3／1 秒为 5／15 张，C30 为 9／30 张；半按不足或缓冲不可用时可能更少。全按当帧和之后的帧采用**相同菜单格式**；关预拍时则全部是当前／后拍帧。
3. 等写卡完成再回放、正常关机或取卡，不在写卡中断电／拔卡。初次让一组完全写完再开始下一组。
4. 正常 NEF 会进入原厂照片库，写完可直接回放，**不需要重启才能看图**。刚拍完的 RAW 标签可能暂不显示 **L**，之后正常关开机才显示 RAW L；实测文件已写 Large 且尺寸完整。这个显示问题尚未修复。
5. 在电脑检查文件集合并完整解码 RAW。RAW 每号应只有 NEF；RAW+JPEG 每号应成对；JPEG 应只有 JPG；历史帧和正式帧都适用。JPEG 档位／★ 应与普通菜单一致，不以尚未更新的取景显示为准。

请等上一组结束后再切换三种格式。实现按每帧提交时的菜单值记录；拍摄或积压写入中途改格式不是已验证的使用流程。

### 缓冲与限制

- **拍摄帧率不等于写卡速度。** 有限实测中，RAW+JPEG 每帧写入间隔约 0.45–0.69 秒，RAW-only 约 0.24–0.32 秒；一次连续触发 14 次的压力试验保存 308 对文件，约 155 秒写完。这些是特定场景和卡的测量，不保证持续每秒写入 30 张 RAW。
- 写入积压时预拍图标曾出现 **“!”**。压力试验中一次触发**没有历史帧，仅有三张正式帧**。期待完整预拍窗口前需等正常标志恢复，之后还需时间填满历史缓存；确切阈值尚未确认，不保证无限连续触发或某个 Max 后拍长度。
- RAW 缓冲留到写完才释放，大多数 RAW+JPEG 档还需额外预览空间，内存占用增加。仅 30 帧压缩历史分配约 519 MB；场景、卡速和设置都会影响可用深度和等待。
- RAW 仅 **HE、FX L**；不支持无损、HE★、DX 或 C60／C120 RAW。HLG／HEIF、未支持的特殊处理模式、双卡备份和 RAW／JPEG 分卡不接管，回到原厂行为；支持流程请使用一张卡。
- RAW+JPEG 的 normal／basic 档，NEF 的小型 FHD／VGA 预览继承 JPEG 路径的画质；原厂 NEF 可能另编为 fine。全尺寸 NEF 预览仍采用预期的 NEF 预览画质。
- 仍缺少镜头校正块、灰度子图和部分 XMP 校正等可选原厂元数据。已测试 Adobe DNG Converter 18.1.1；NX Studio、Lightroom、完整镜头校正等效性及全部软件尚未验证。机内删除／保护／传输、近满卡、自动对焦跟踪、自动捕获尚未充分测试。可拍张数／缓冲估计和快捷设置显示仍沿用原厂 HSFC 估计。

### 异常与停用

登记失败时可能回退为 JPEG＋另写 NEF，先用 `.NE_` 再改名；该 NEF 可能要之后重新扫描照片库。其他失败可能产生 JPEG-only、缩小的 1620×1080 NEF 预览、缺失／不完整文件或 **`Z8PRESTP.BIN`**。RAW-only 回退 JPEG 可能使用较低的 NEF 预览画质而元数据仍写 FINE。不能只看是否报错，也要核对文件集合。

停止文件会阻止额外 NEF 保存，关开机不清除它；**JPEG 仍可能应用普通菜单中的画质**。要完全停用本功能，关机并安全取卡后移除 `Z8PRE.CFG`，C15／C30 回到原有 HSFC 行为。这不卸载固件、不移除已包含的 ProRes 功能，也不保证固件可回退。

每张 NEF 预算 1.5 秒，只能在原厂写入返回后或回退 I/O 调用之间检查，不能打断已阻塞的调用，也不保证不会冻结。报错、缺片、出现 `.NE_`／停止文件、重启或冻结时停止测试并保留证据；待写入结束后备份、停用，排查后再考虑删除停止文件或重试。

请阅读[验证范围](validation.md)，了解上机覆盖、画面对应复核和模型边界。公开脚本新生成的包没有逐个上机认证。
