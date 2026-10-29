# GT5 Native Recomp

[![Source checks](https://github.com/MauricioRSJ98/gt5-native-recomp/actions/workflows/source-checks.yml/badge.svg)](https://github.com/MauricioRSJ98/gt5-native-recomp/actions/workflows/source-checks.yml)

Experimental native recompilation research for **Gran Turismo 5, PS3, BCUS98114 v2.17**, targeting **Windows x86-64 and Vulkan**.

**Pre-alpha / boot bring-up. The game does not render a frame yet and is not playable.** This repository publishes the integration code, runtime patches, generation tools and address-only analysis metadata so other developers can help.

[Português brasileiro](README.pt-BR.md) · [Roadmap](https://github.com/MauricioRSJ98/gt5-native-recomp/issues/1) · [Build and regeneration](docs/BUILDING.md) · [Current status](docs/STATUS.md) · [Contributing](CONTRIBUTING.md) · [Credits and tools](docs/CREDITS.md)

## What this project does

The intended execution path recompiles PPU and SPU instructions ahead of time into native code. A native compatibility runtime implements the necessary PS3 services and consumes RSX commands through Vulkan. Missing CPU code stops execution for investigation and another AOT generation pass. The integrated executable excludes the SPU instruction interpreter; DirectX 12 is disabled.

The immediate goal is to reach the first real game frame, then a menu and eventually a drivable race, even at very low performance. These are separate milestones; no gameplay or performance claim is made.

## Latest local checkpoint — 29 October 2026

| Area | Observed result |
| --- | --- |
| PPU | 43,525 generated native entry addresses, including internal CFG entries |
| SPU | Six embedded ELF images plus 16 captured raw images compiled/registered; raw images contain 6,723 generated entries |
| Vulkan | GTX 1050 Ti initialization; guest shader translation through glslang/SPIR-V enabled |
| Files | Reads from the original disc ISO and installed update files |
| Startup | Display buffers configured; audio initialization/port/thread and XInput controller initialization reached |
| Graphics | **No observed guest draw or game flip/frame** |
| Current blockers | Uncompiled PPU targets and incomplete USB HLE services |

Compilation counts are **not completion percentages or proofs of correctness**. Some entries are basic-block wrappers; SPU code/data boundaries and indirect transfers still need review. See [the checkpoint and its limitations](docs/STATUS.md).

## Help wanted

Useful contributions include:

- PPU/SPU lifting, control-flow recovery and ABI review.
- SPURS scheduling, synchronization and correctly routed SPU-to-PPU events.
- RSX command consumption, shader translation and Vulkan rendering.
- USB/controller compatibility services and clean Windows builds.
- Reproducing a documented blocker using your own local game data.

Start with the [pinned roadmap](https://github.com/MauricioRSJ98/gt5-native-recomp/issues/1), [CONTRIBUTING.md](CONTRIBUTING.md) and [issues labeled `help wanted`](https://github.com/MauricioRSJ98/gt5-native-recomp/issues?q=is%3Aissue%20is%3Aopen%20label%3A%22help%20wanted%22). Small, evidenced changes are especially helpful. Report what changed and the next observed blocker; avoid repeated unchanged boot runs. Use [Discussions](https://github.com/MauricioRSJ98/gt5-native-recomp/discussions) for questions and planning.

## Source and local data

The repository contains **no game executable, disc image, update package, captured SPU binary, generated game instruction bodies, firmware, SDK, keys, or playable download**. Contributors must supply their own local inputs. `private/`, `game/`, `game-data/`, `tools/` and `third_party/` are excluded from Git.

The local checkpoint was built with private generated artifacts. A clean public clone must regenerate them; the clean-clone workflow is not yet validated end to end. The public repository is a research starting point, not a one-click game release. [Build details](docs/BUILDING.md) distinguish established local results from remaining reproduction work.

## Foundations and disclosure

- [ps3recomp](https://github.com/sp00nznet/ps3recomp): main PPU/SPU lifting and compatibility-runtime foundation.
- [GT5 Prologue Recompiled](https://github.com/sp00nznet/GT5P): loader and startup/presentation integration reference. Prologue addresses are not treated as GT5 addresses.
- [RPCS3](https://github.com/RPCS3/rpcs3): behavior and file-format reference, including SPURS/user-event routing; its CPU emulation engine is not incorporated into this executable.
- [ShadowOfTheColossus-PC](https://github.com/Oussama268/ShadowOfTheColossus-PC/releases/tag/v0.60.6-opt11): architectural inspiration. Its different console/CPU/GPU path is not a drop-in GT5 implementation.
- [Ghidra](https://github.com/NationalSecurityAgency/ghidra): targeted static analysis via PyGhidra.
- [REA](https://github.com/morluto/rea): installed/evaluated analysis tooling; its Ghidra/PS3 integration is **not operational in this workflow**. Analysis that worked used Ghidra directly.

Development is AI-assisted with **OpenAI Codex, GPT-6.1 Sol, medium reasoning**, as specified by the maintainer. AI assistance covers code, analysis and documentation; it does not replace review or execution evidence. This is an independent community project, without endorsement from OpenAI, Sony, Polyphony Digital or the projects referenced above.

Full versions, roles, licenses and limitations: [CREDITS](docs/CREDITS.md) and [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES.md).

## License

Original integration code and documentation are provided under the [MIT license](LICENSE). Patches and adapted portions retain their upstream notices. This license does not grant rights to game content, trademarks, firmware or third-party software.
