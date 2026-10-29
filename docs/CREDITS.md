# Credits, foundations and tools

Maintained by [MauricioRSJ98](https://github.com/MauricioRSJ98), with community contributions welcome. The following projects are credited for their actual role; reference is not a claim of endorsement or interchangeable game support.

## Core projects

| Project | Version/reference | Role |
| --- | --- | --- |
| [ps3recomp](https://github.com/sp00nznet/ps3recomp) | v0.18.0 snapshot, `4e8f3ca87a3e1d87bb83b8b7e9348fe2685cd514` | Main PPU/SPU lifters, loader/HLE/LV2 interfaces, SPURS runtime and RSX/Vulkan foundation. Local Windows/Vulkan, synchronization and strict-stop changes are supplied as a patch. MIT notice retained. |
| [GT5 Prologue Recompiled](https://github.com/sp00nznet/GT5P) | `65c75d61ade58efb4f6af5f099c3b78b64c0a8e6` | Loader and startup/presentation integration reference. The reference project documents a D3D12 path; this project targets Vulkan. Its game addresses are not applied to GT5. MIT notice retained. |
| [RPCS3](https://github.com/RPCS3/rpcs3) | Local reference 0.0.39-18763, `93dbdead24e1474a94c59fffc1f6cfb25abe488b` | File-format/service behavior and SPURS/event routing reference. The RPCS3 CPU execution engine is not linked into the native executable. Reference source and private extraction/key material are excluded. |
| [ShadowOfTheColossus-PC](https://github.com/Oussama268/ShadowOfTheColossus-PC/releases/tag/v0.60.6-opt11) | User-selected release v0.60.6-opt11 | Architectural inspiration for native loading/runtime/Vulkan work. Its console, CPU and GPU path differs and cannot be transplanted as a PS3 GT5 port. |

Special thanks to **Ned Heller / sp00nznet** for the MIT-licensed foundations. This repository is an independent downstream experiment, not an official release from any upstream author.

## Analysis and development tools

| Tool | Local version | Actual use / limitation |
| --- | --- | --- |
| [Ghidra](https://github.com/NationalSecurityAgency/ghidra) | 12.2 PUBLIC | Targeted PowerPC boot analysis and decompilation. Analysis-copy metadata repairs preserve loaded bytes. No claim of complete game analysis. |
| [REA / rea-agents](https://github.com/morluto/rea) | 6.8.0 | Installed/evaluated. Its Ghidra integration accepted 12.1.x rather than the installed 12.2, with additional Windows/PS3 ELF and sandbox limitations. It is not operational for this analysis pipeline; Ghidra was used directly. |
| PyGhidra / JPype | PyGhidra 3.2.0; JPype 1.5.2 | CPython-to-Ghidra bridge for targeted exports. |
| Java | Existing JDK 25 installation | Runs Ghidra; configure your own compatible JDK. |
| Python | Local CPython runtime | Analysis, metadata generation, lifting orchestration, builds and bounded runs. |
| [PyCryptodome](https://www.pycryptodome.org/) | Private preparation environment | Used in a local input-preparation utility. That utility and its extraction/key inputs are not distributed here. |
| [Node.js](https://nodejs.org/) | 24.22.1 portable | HTTPS dependency/tool downloads. |
| MinGW-w64 GCC/G++ | GCC 12 via Cygwin in the original workspace | Windows x86-64 native compilation. |
| [CMake](https://cmake.org/) / [Ninja](https://ninja-build.org/) | Existing local build tools | Native dependency compilation/linking. |
| Git / [GitHub CLI](https://cli.github.com/) | Publication tooling | Version control, repository publication and collaboration setup. Credentials are never part of the source repository. |

## Graphics dependencies

| Dependency | Pin |
| --- | --- |
| [SDL2](https://github.com/libsdl-org/SDL) | 2.32.10, MinGW development package |
| [Vulkan-Headers](https://github.com/KhronosGroup/Vulkan-Headers) | vulkan-sdk-1.4.363.0 |
| [glslang](https://github.com/KhronosGroup/glslang) | 16.6.0 |
| [SPIRV-Tools](https://github.com/KhronosGroup/SPIRV-Tools) | `ef96ed763b43b59b33b31b362f09a02b729fa1c9`, from glslang known_good |
| [SPIRV-Headers](https://github.com/KhronosGroup/SPIRV-Headers) | `496543121ce6419f23d6fa5d7194ba66c36212d2`, from glslang known_good |

Downloaded source/binaries retain their upstream license files and are kept outside Git. No Vulkan driver is redistributed.

## AI assistance

The maintainer specifies **OpenAI Codex with GPT-6.1 Sol at medium reasoning** as the AI-assisted development setup. AI has assisted with analysis, integration code, tooling, documentation and publication preparation. This disclosure records the maintainer's stated configuration; it is not a claim of independent verification of model internals or of correctness of generated code.

Human and AI-assisted contributions need the same review, attribution and meaningful validation. OpenAI is not a project sponsor or endorser.
