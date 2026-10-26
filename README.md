# A7C II Camera Tools（fork: burst boost button）

[简体中文](README.zh-CN.md)

Research and reproducible firmware tools for the Sony ILCE-7CM2. The installer builds a version 2.00 package from a user-supplied, unmodified official 2.01 DAT; the normal official 2.01 update path remains available afterward.

**This fork adds exactly one patch stage on top of upstream: `burst boost button`** (Sony's
`Cnt Shoot Speed Boost` / 連写速度ブースト) — a custom-key function that raises the continuous
shooting speed while the assigned button is held or toggled. It runs as an overlay on an
already-built 2.00 package and does not touch any upstream patch byte or pinned hash.
The stage is currently `status: "unresolved"`: **the gate bytes are not located yet, so the
stage refuses to build.** Evidence and the on-device plan:
[windows/runtime/release/SPOTBOOST.zh-CN.md](windows/runtime/release/SPOTBOOST.zh-CN.md).

## References / 参考项目（read this first）

This work is a fork of, and stands on, the following public research. **None of the upstream
authors endorse this fork's conclusions or its patches.**

| Project | What this repository uses | License |
| --- | --- | --- |
| **[YuuLuo/a7c2-camera-tools](https://github.com/YuuLuo/a7c2-camera-tools)** | **the entire upstream toolchain this repository is forked from** (DAT builder, p1 gate, BK4 commit, CP color/sound patches, Windows/macOS installers). The `burst boost button` stage is the only addition. | GPL-3.0-only |
| [YuuLuo/a7c2-service-preload](https://github.com/YuuLuo/a7c2-service-preload) | the service-mode authentication and on-camera execution chain that the runtime probes build on | as published upstream |
| [ma1co/Sony-PMCA-RE](https://github.com/ma1co/Sony-PMCA-RE) | USB enumeration, Senser two-stage authentication and the `SonySenserCamera` API (`windows/runtime/core/pmca/`, and the vendored copy used by the libJit runtime route) | MIT |
| [ma1co/fwtool.py](https://github.com/ma1co/fwtool.py) | reference for unpacking official update packages | MIT |
| [QAQLeonard/a7c2-fl23-research](https://github.com/QAQLeonard/a7c2-fl23-research) · [lzh2016zzz/a7cr-fl23-research](https://github.com/lzh2016zzz/a7cr-fl23-research) | the libJit `dlopen` execution entry and the FL2/FL3 enablement methodology this repository independently re-verified | as published upstream |

Everything under [docs/research/](docs/research/) is this fork's own analysis
(spot-boost gate hunting plus a runtime session log). It contains addresses and hashes only —
**no Sony firmware, original or modified**, and `.gitignore` enforces that.

## Features

| Selection | Firmware changes | Post-update work |
| --- | --- | --- |
| FL2/FL3 | Enables the two Creative Look modes, playback icons and photo metadata | Writes the live CP color table and checks both BK4 copies |
| Electronic shutter sound | Enables the capture sound path and two sound menu choices | Uses the camera's built-in sound or user audio; leaves FL2/FL3 color properties unchanged |
| Both | Combines both sets of changes in one DAT | Performs the FL2/FL3 color steps and checks the sound |
| **Burst boost button (fork only)** | Overlays the byte spans declared in `patches_spotboost.json` on the built 2.00 package | Cold-start check that `Cnt Sht Spd Bst Hold/Toggle` appears in the custom-key list |

Sound can use the camera's original sample at its original level without an uploaded file. Custom sound accepts an MP3/WAV of up to 2 seconds and a **1–100%** level.

## How it works

1. The camera connects in USB Mass Storage mode (`054C:0E8A`). The host authenticates and switches it to service mode (`054C:0336`), where Jiritsu file commands are available.
2. A bounded AArch64 worker is staged in the camera's Work area. Service commands set a preload entry and trigger a child process. The host checks the versioned, checksummed result, removes the preload entry and verifies the return to normal USB mode. See the [service probes](windows/runtime/core/sony-service-research/).
3. Read-only captures of p1 and both BK4 copies establish the camera baseline. The selected 2.00 DAT is fully decrypted for verification, copied to the photo card and read back by full hash. A temporary p1 patch opens the update version gate; the original p1 is restored after the camera update.
4. FL2/FL3 connects mode paths already present in the camera and supplies four color-property rows converted from FX2-format functional parameters. The sound patch connects the camera's existing KindID 3 shutter sample. Custom mode also extends `SYSSOUND.BIN` and updates sound registration in the main application and boot overlay.

A7C II 2.01 already contains FL2/FL3 menu resources and shared processing code. This project enables the missing routing and supplies color parameters; it does not transplant the full FX2 imaging program.

## Run

| Platform | Entry |
| --- | --- |
| Windows 10/11 | [windows/run.bat](windows/run.bat) · [setup](windows/README.md) |
| macOS | [macos/run.command](macos/run.command) |

Place your own official 2.01 DAT beside the launcher. Both platforms use a fixed-screen Chinese/English interface and save per-camera resume records. The workflow has run on Windows 10, Windows 11 and macOS with mainland China and Japanese-market bodies.

The repository contains project code, patch descriptions and driver files, but no Sony firmware, camera captures, generated DAT, user audio or run logs. Original project code is [GPL-3.0-only](LICENSE); see [licenses and provenance](THIRD_PARTY_NOTICES.md) for other components.

Compatibility testing passed on nearly ten A7C II cameras without boot problems. Unofficial firmware can still affect warranty or prevent a camera from booting. **Do not use this tool if you are unwilling to accept those risks.** Keep your camera-specific backups and use a charged battery. Do not alter firmware offsets, hashes, memory access or write steps without independent validation and recovery capability.
