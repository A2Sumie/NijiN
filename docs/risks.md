# Risks, the incident, and rollback

Read this page before building anything, and again before any thought of
putting a build on a camera.

## The short version

This project modifies the firmware of a working camera. The worst case is a
camera that never boots again. **That worst case has already happened once
during this project's development**, to a test unit, with a build whose
offline checks were all green. The unit was not recoverable by software and
was sent for service.

If you need a working camera, run official firmware. Nothing here is worth
a dead camera.

## Incident record: V10 boot loop (2026-10)

What happened, in full, because it is the most important fact in this
repository:

1. The V10 build of the stable line passed the entire offline battery twice:
   byte-level verification, 33 checkpoints, 34/34 mutations intercepted,
   17/17 combination rows green, structural torture green, rebuild
   reproducible.
2. It was installed on one test camera. The camera powered the display,
   kept the loader alive, and crashed during application initialization,
   then restarted — a boot loop. It never returned to service.
3. Recovery attempts in software (card-file sequences, key sequences,
   service/hidden entry paths, the USB link) did not restore it. The unit
   was sent for service.
4. Offline forensics afterwards narrowed the cause to the V10-specific
   changes:
   - a settings-count immediate value raised from 617 to 618 while its
     backing table stayed at 617 — a one-entry overrun for any walk that
     trusts the count (**proven mechanism**);
   - a write at the boundary between two adjacent tables whose ownership
     could not be closed statically (zero code references to that table);
   - a load-time guard that cannot crash but computes its bound across two
     different regions, so it may silently skip or allow everything;
   - everything else in the delta was either excluded by inspection or
     unchanged from a build generation that had run on hardware before.
   The exact instruction that faults on hardware has **not** been pinned.
5. The V11 line (`bricking-edge`) exists to strip those suspect changes. It
   was built and compared byte for byte as a trial, was deliberately never
   released into a build kit, and is frozen until the cause is settled.

Lessons that are now policy in this project:

- **A green gauntlet is not a boot test.** The battery validates bytes and
  recipes; nothing in it executes on a device.
- **Never start with the newest line on hardware.** Even the older line is
  unproven here.
- **Changes in boot-reachable code need their own evidence**, and "the
  previous version did this too" is not evidence.
- **One variable at a time, with a rollback ready**, and stop at the first
  anomaly.

## Risk classes

| Risk | Reality |
|---|---|
| Camera no longer boots | **Has happened.** Software recovery attempts failed; the unit went to service |
| Data loss (photos on card) | Use a dedicated, empty test card. Assume anything on a card can be lost |
| Card corruption | Configuration files and heavy write patterns are involved; use media you can throw away |
| Silent wrong behaviour | Displayed values, metadata fields and menu states can be wrong without any error |
| Undetected incompatibility | The device model is reconstructed and incomplete; constants were inferred |
| Third-party software rejection | Adobe Camera Raw / Lightroom / NX Studio acceptance of modified files is untested |
| No downgrade path | Recovery is not guaranteed. Keep the official package verified and ready |

## What the tools do to reduce risk

They cannot make the firmware safe. They reduce the chance of *building the
wrong thing*:

- input is checked against SHA-256 fingerprint windows before anything is
  touched; a mismatch stops the build;
- added code must compile to exactly the reviewed bytes;
- the verifier is independent of the builder and checks every byte outside
  the declared windows;
- there is no force or bypass switch anywhere;
- the gauntlet attacks its own output (mutations, structural torture,
  refused combinations) and refuses to call anything green while red items
  remain;
- the output directory must be new, and inputs are never overwritten.

## If something goes wrong

Rollback is the official firmware, full stop:

1. Stop. Do not retry, do not "try one more build", do not keep the camera
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
camera malfunction, a camera that no longer boots, service costs or any
other loss arising from building, installing or using anything produced
from this repository. See [NOTICE.md](../NOTICE.md) and the disclaimer in
[LICENSE](../LICENSE). This project is not affiliated with Nikon.

## 简体中文

- **一句话：改固件的最坏结果是相机永远开不了机，而且这个最坏结果在开发中已经
  真实发生过一次**（V10 构建，离线全绿，测试机开机重启循环，软件救机未果，送修）。
- 事故经过、离线取证结论（618/617 走查越界为已证机理、T4 表尾写归属未闭环、
  guard 跨区比较不会崩但可能全跳过/全放行；真机炸点未定谳）以及由此固化的纪律，
  全部记录在本页英文部分，不省略。
- 风险清单：开不了机、照片丢失、卡损坏、静默错误行为、推断常量不准、第三方软件
  不认、不保证可降级。
- 工具能做的只是“别构建出错的东西”：指纹门、编译器锁、独立复核、无强制开关、
  自我攻击的 gauntlet、输出目录必须全新。
- 出事就回官方固件：先核 sha256 再重刷官方 03.11，删卡上的 `Z8PRE*.CFG` /
  `Z8OG.CFG`；完全不开机则软件手段可能已穷尽。
- 免责见 [NOTICE.md](../NOTICE.md) 与 [LICENSE](../LICENSE)；本项目与 Nikon 无隶属关系。
