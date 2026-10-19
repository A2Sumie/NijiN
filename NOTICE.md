# Research and rights notice

NijiN is an independent research and learning project. Nikon has not
sponsored, endorsed or supplied it. Nikon and Z8 identify the
interoperability target; their owners retain their rights.

## Bring your own firmware

We respect Nikon's rights and do not publish its private material. This
repository distributes original and derived tool source together with the
applicable open-source license notices. **No Nikon firmware, decrypted
proprietary code, boot ROM, flash dump, key, font, icon bitmap, extracted
string table, calibration data, photograph or camera UI screenshot is
included.** The tools do not download Nikon firmware and contain no updater,
flashing utility, USB device access or recovery service. Users provide their
own compatible local update package; output is generated locally on their
machine.

A source license here does not grant rights to Nikon firmware or any other
third-party material. Firmware-derived local files — including runtime
folders, extracted segments, settings files and build outputs — are excluded
from publication and must stay local.

The compatibility profiles in `resources/` contain **hashes, offsets and
layout parameters, not firmware contents**. Patch instructions are generated
from the sources in this repository. Menu structures and text are read from
the user's own input at build time and are never redistributed.

The model of the device is incomplete and inferred. Nothing in this
repository is a hardware specification, a factory dataset or a statement
about physical timing.

## Experimental use and responsibility

Everything produced from this repository is experimental firmware for
research and learning. Building, installing or using it can cause data loss,
card corruption, camera malfunction, a camera that no longer boots, or
permanent damage. **During development, one test build was installed on a
test camera and the camera entered a boot loop and was sent for repair.**
Users must assess these risks and decide for themselves whether to install
anything. Do not use it for irreplaceable work. To the extent permitted by
applicable law, the authors and contributors provide no warranty and accept
no liability for data loss, camera damage or other losses arising from this
project or its outputs. These limitations supplement the warranty and
liability provisions in LICENSE; they do not alter third-party rights.

刷机与相机操作一律由使用者自行决定和承担。构建、安装或使用可能造成照片
丢失、存储卡损坏、相机故障乃至永久损坏；开发期间确有一次测试构建刷入测试机
后出现开机重启循环并送修。在适用法律允许的范围内，作者及贡献者不提供担保，
不对由此造成的数据损失、相机损失或其他损失承担责任。以上说明补充 LICENSE
中的无担保与责任限制条款，不改变第三方权利。

## License scope

Original tool source in this repository is licensed under **GPL-3.0-only**;
see [LICENSE](LICENSE). This license does not grant rights to user-supplied
Nikon firmware. Output licensing depends on its contents, including any
generated code; the complete output firmware is not represented as a
GPL-licensed distribution. See
[GNU's explanation of program output](https://www.gnu.org/licenses/gpl-faq.en.html#WhatCaseIsOutputGPL).

## Derivation and attribution

This project is derived from and builds on public work by others. Their
licenses and notices remain applicable to their code.

- [NikonFirmwarePatch](https://github.com/XinmiaoZhao/NikonFirmwarePatch) (GPL-3.0-only): the tool
  architecture this repository extends — package reader/writer, feature
  module layout, verifier, validation suites, repository checks and the
  ProRes and pre-capture patch recipes. Files unchanged from that project
  keep their original form; modified and added files remain GPL-3.0-only.
  Its hardware validation records belong to that project's own builds and
  are **not** claims about the builds produced here.
- [WonderLantern/z9-qemu](https://github.com/WonderLantern/z9-qemu)
  (GPL-2.0-or-later): the documentation posture of this repository —
  bring-your-own-firmware, source-only publication, local runtime artifacts —
  follows its published practice. No code or binaries from it are
  redistributed here.
- [WonderLantern/z7-qemu](https://github.com/WonderLantern/z7-qemu):
  emulator and protocol references consulted during development.
- [RdWing/z8-qemu](https://github.com/RdWing/z8-qemu): Z8 emulation work
  that made offline development possible. Its code and binaries are not
  distributed here.
- [QEMU](https://www.qemu.org/)
  ([source](https://gitlab.com/qemu-project/qemu)): the emulation
  infrastructure used for offline work. Not bundled.
- [Nikon Hacker's Package.cs](https://github.com/simeonpilgrim/nikon-firmware-tools/blob/main/Nikon-Patch/LocalUI/Package.cs)
  (via NikonFirmwarePatch): the package XOR indexing format was studied with
  reference to it. Neither that C# source nor its lookup tables are
  included; the implementation recovers equivalent parameters from the
  user-supplied package.
- [Capstone](https://github.com/capstone-engine/capstone) 5.0.7: used
  separately to inspect generated instructions. Its code and runtime are not
  bundled; see its [LICENSE.TXT](https://github.com/capstone-engine/capstone/blob/5.0.7/LICENSE.TXT).
  Declared in `requirements.txt`.
- Clang/LLVM: an external build dependency for the C sources. No compiler or
  runtime is bundled.

These are external development tools and references. This repository does
not redistribute their source or binaries, claim authorship of their work,
or imply that their maintainers endorse this project.

## Brand assets

The NijiN wordmark and icon in `assets/` were created for this project and
are part of this project's own work. They are distributed under
**CC BY-SA 4.0**; see [assets/ASSETS.md](assets/ASSETS.md). They contain no
third-party artwork, no font outlines and no device imagery.
