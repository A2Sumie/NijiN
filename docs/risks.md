# Risks, the incident, and rollback

Read this page before building anything, and again before any thought of
putting a build on a camera.

## The short version

This project modifies the firmware of a working camera. The worst case is a
camera that never boots again. **That worst case has already happened once
during this project's development**, on a test unit, with a build whose
offline checks were all green. The unit was not recoverable by software and
was sent for service.

If you need a working camera, run official firmware. Nothing here is worth
a dead camera.

## Incident record: V10 boot loop (2026-10)

What happened, in full, because it is the most important fact in this
repository:

1. The V10 build of the stable line passed the entire offline battery twice:
   byte-level verification, 33 checkpoints, 34/34 mutations intercepted,
   17/17 combination rows green, structural torture green, and reproducible
   rebuild.
2. It was installed on one test camera. The camera powered the display,
   kept the loader alive, crashed during application initialization, and then
   restarted into a boot loop. It never returned to service.
3. Software recovery attempts (card-file sequences, key sequences,
   service/hidden entry paths, and the USB link) failed to restore it. The
   unit was sent for service.
4. Offline forensics afterwards narrowed the cause down to V10-specific
   changes:
   - a settings-count immediate value raised from 617 to 618 while its
     backing table stayed at 617 — a one-entry overrun for any traversal
     that relies on the count (**proven mechanism**);
   - a write at the boundary between two adjacent tables whose ownership
     could not be closed statically (zero code references to that table);
   - a load-time guard that cannot crash directly but computes its bounds
     across two different regions, so it may silently skip or allow
     everything;
   - everything else in the delta was either excluded by inspection or
     unchanged from a build generation that had previously run on hardware.
   The exact instruction that faults on hardware has **not** been pinned.
5. The V11 line (`bricking-edge`) exists to strip those suspect changes. It
   was built and compared byte for byte as a trial, was deliberately never
   released into a build kit, and remains frozen until the cause is settled.

A comparable post-flash failure was reported independently on another Z8
modification project (upstream Issue #3). The symptom comparison, what our
forensics suggest checking there, and what must not be blurred between the
two cases are in [upstream-issue-3.md](upstream-issue-3.md).

A comparable post-flash failure was reported independently on another Z8
modification project (upstream Issue #3). The symptom comparison, what our
forensics suggest checking there, and what must not be blurred between the
two cases are in [upstream-issue-3.md](upstream-issue-3.md).

Lessons that are now project policy:
- **A green gauntlet is not a boot test.** The battery validates bytes and
  recipes; nothing in it executes on a device.
- **Never start with the newest line on hardware.** Even the older line is
  unproven here.
- **Changes in boot-reachable code need their own evidence**, and "the
  previous version did this too" is not evidence.
- **One variable at a time, with a rollback ready**, and stop at the first
  anomaly.

## C1 evidence slot

Status: **filled 2026-10-19 from the crash verdict record.**

Status log:

- 2026-10-19 — the verdict record has been located in the crash-forensics
  workstream (`136_CRASH_VERDICT.md`, evidence chain
  `126_BOOTLOOP_FORENSICS.md` → `132_Z9QEMU_PORT.md` → `134_EXPLOIT_TESTBED.md`
  → verdict). Its §0 verdict section is still unfilled. Nothing below is
  filled, and C1 remains **unmet** until the verdict text exists and is
  copied in verbatim.
- 2026-10-19, later — **§0 written; the slot above is now filled**
  mechanically by `tools/fill_c1.py`. Verdict: the fault is the S3 slot
  count 618/617 overrun in the settings-load walk — a **layout-related
  out-of-bounds UB**. Warning carried from the verdict for any release
  note: **the same V10 build may silently corrupt instead of crashing
  under a different memory layout — never treat "one machine that did not
  crash" as V10 being safe**, and builds before V11 must not be flashed
  again. Dynamic re-reproduction (poisoned layout) is still in flight,
  see the "What stays unproven" field.

Criterion C1 of [unfreeze-criteria.md](unfreeze-criteria.md) counts as met
only when every field below is filled. An empty or partial slot means C1 is
unmet, whatever else is written around it. The verdict is expected from the
crash-forensics workstream (`136_CRASH_VERDICT.md` there) and is to be
copied here **verbatim, with its anchors**.

| Field | Required content | Value |
|---|---|---|
| Verdict | One sentence naming the faulting instruction or path | **是它。** v10 真机 boot loop 的炸点 = **S3 槽计数 618/617 越界**：v10 的两个计数立即数把注册计数改成 618，而背衬表/ROM 变体表仍是 617 ⇒ 设置装载走查环多走 1 项，越界读写紧邻对象。 ⏎ **炸点函数 = 设置装载走查环**（装载器 `0x410DF358` 内 `0x410DFD98..0x410DFE4C`）；**第一口越界 = `0x410DFDF8`**（`ldrb w11,[x10,#5]`，元素 `0xA029B1BB8+5`），紧随 `0x410DFE10`（`ldr w1,[x9,x29]`，x29=`0x1348`=617×8），下游 apply `0x410E1790`。 ⏎ **形态 = 布局相关的越界 UB**（越界项落在什么对象上取决于堆/内存布局）⇒ 真机炸、模拟器默认布局不炸，**不矛盾**；v11 撤掉两个计数即根除（运行态已验：617 与表一致）。 ⏎ **置信度**：机理 A 级（字节+运行态 RAM 直接观测）；受害者 PC 指令级 A 级（结构+唯一消费者），动态复现见 §2（布局毒化）。 |
| Evidence grade | A (bytes / disassembly measured), B (static inference), C (unresolved) | A |
| Record anchor | The verdict record's file, section, and its SHA-256 | 136_CRASH_VERDICT.md §0 终审判词, sha256 465a8885bbfc2bea7eea3375be7021e37e14fe09e66fc33d3a34813839ca9f2e |
| Code anchors | Every offset / symbol cited, with the address mapping used | 0x410DF358; 0x410DFD98; 0x410DFE4C; 0x410DFDF8; 0xA029B1BB8; 0x410DFE10; 0x1348; 0x410E1790; 0x410DFE1C; 0x410DFE24; 0xF7F9D4; 0xF803D4; 0xF80F68; 0x4CBC9B9; 0x4CBC9BD; 0xA04812848; 0xA04812850; 0xA029B0670; 0x44182FE0; 0x410E0F38; 0xA047E6B3C; 0x40874284; 0x40001000; 0xA04842160; 0x40FFFFFF; 0x4086871C; 0x410DF3F8; 0x410DF4F4 |
| Delta exhaustion | Statement that every other candidate in the V9↔V10 delta is excluded, naming the method for each | present in §3 (8 lines); method named: yes |
| Hardware reproduction | Yes / no; if no, why the evidence stands without it | **判**：越界的**动态复现**在模拟器里卡在"文件读入"一步（合成卡 + 顶开的门 ≠ 真机的文件服务上下文）； |
| What stays unproven | Spelled out, not left implicit | 剩余工作 = 让 FS 读真的拿到98 B 设置体（约 0.5–1 人日：补 FS_open 调用点/文件对象上下文，或用 `--skipcall` 顶开 fd 获取），随后 `--poison-at` 毒化列表尾即可看到越界显形。 |
| Filled by / date | Who copied it here, and when | 2026-10-19 (copied verbatim by tools/fill_c1.py on 2026-10-19) |

Rules for filling this slot:

- Copy the verdict; do not paraphrase it into something stronger. The
  mechanical filler `tools/fill_c1.py` copies it verbatim and refuses while
  any field is missing — run it against the finished record first.
- A verdict graded B or C is recorded here, but does **not** meet C1.
- Anchors must be checkable from this repository plus the local evidence; a
  hash without a source is not an anchor.
- The delta-exhaustion line is mandatory. A verdict that leaves another
  delta window unexcluded is a hypothesis, and hypotheses live in
  [upstream-issue-3.md](upstream-issue-3.md), not here.

## Risk classes

| Risk | Reality |
|---|---|
| Camera no longer boots | **Has happened.** Software recovery attempts failed; the unit was sent for service |
| Data loss (photos on card) | Use a dedicated, empty test card. Assume anything on the card can be lost |
| Card corruption | Configuration files and heavy write patterns are involved; use media you can afford to discard |
| Silent wrong behaviour | Displayed values, metadata fields, and menu states can be wrong without triggering an error |
| Undetected incompatibility | The device model is reconstructed and incomplete; constants were inferred |
| Third-party software rejection | Adobe Camera Raw / Lightroom / NX Studio acceptance of modified files is untested |
| No downgrade path | Recovery is not guaranteed. Keep the official package verified and ready |

## What the tools do to reduce risk

They cannot make the firmware safe. They only reduce the chance of *building the
wrong thing*:

- input is checked against SHA-256 fingerprint windows before anything is
  touched; any mismatch halts the build;
- added code must compile to the exact reviewed bytes;
- the verifier is independent of the builder and checks every byte outside
  the declared windows;
- there is no force or bypass switch anywhere in the pipeline;
- the gauntlet attacks its own output (mutations, structural torture,
  refused combinations) and refuses to report green while red items remain;
- the output directory must be new, and inputs are never overwritten.

## If something goes wrong

Rollback is the official firmware, full stop:

1. Stop. Do not retry, do not "try one more build", and do not keep the camera
   running in a broken state.
2. Reflash the official Nikon C 3.11 package and verify its checksum first:
   `shasum -a 256 <your-path>/Z_8_0311.bin` must print
   `d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96`.
3. Remove the project's configuration files from the card
   (`Z8PRE*.CFG`, `Z8OG.CFG`) — deleting them switches off the added
   behaviours that depend on them.
4. If the camera does not boot at all, software options may be exhausted;
   the V10 incident ended at a service centre.

## Not a warranty

To the extent permitted by applicable law, the authors and contributors
provide no warranty and accept no liability for data loss, card corruption,
camera malfunction, a camera that no longer boots, service costs, or any
other loss arising from building, installing, or using anything produced
from this repository. See [NOTICE.md](../NOTICE.md) and the disclaimer in
[LICENSE](../LICENSE). This project is not affiliated with Nikon.

## 简体中文

- **一句话：改固件的最坏结果是相机永远开不了机，且该最坏情况在开发中已经
  真实发生过一次**（V10 构建，离线全绿，测试机陷入开机循环，软件救机无效，送修）。
- 事故经过、离线取证结论（618/617 遍历越界为已证机理；T4 表尾写归属未闭环；
  guard 跨区比较虽不致崩溃但可能导致全跳过或全放行；实机炸点已于 2026-10-19 定谳=S3 槽计数 618/617 越界、布局相关 UB）以及由此固化的纪律，
  全部详实记录在本页英文部分，不作省略。**C1 证据槽已备好留空**（[risks.md#c1-evidence-slot](risks.md#c1-evidence-slot)）：
  判词、证据分级、记录与代码锚点、delta 穷举声明、复现状态、仍未证明项逐格待填——**八格已于定谳当日由 `tools/fill_c1.py` 逐字填满。**警示随判词带出：同一份 v10 在不同内存布局下可能静默写坏而非立即崩——"某台机器没炸"不等于 v10 安全，V11 之前的构建一律不回灌。**
- 风险清单：开不了机、照片丢失、存储卡损坏、静默异常行为、推断常量不准、第三方软件
  不兼容、不保证可降级恢复。
- 工具能做的只是“避免构建出错误的产物”：指纹门禁校验、编译器锁定、独立校验器复核、无任何强制开关、
  执行自攻击测试套件（gauntlet）、输出目录必须全新且绝不覆盖输入。
- 出事就回退官方固件：先校验 sha256 再重刷官方 03.11，删除卡上的 `Z8PRE*.CFG` 与
  `Z8OG.CFG`（移除即可停用依赖它们的注入逻辑）；若完全无法开机，则软件恢复手段可能已全部穷尽。
- 免责声明参见 [NOTICE.md](../NOTICE.md) 与 [LICENSE](../LICENSE)；本项目与 Nikon 无任何隶属关系。
