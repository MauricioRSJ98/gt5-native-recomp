# Status — 2026-10-29

The latest maintainer-local executable reached audio and controller initialization with Vulkan ready. It has **not produced an observed guest draw, game flip, menu or playable race**.

## Evidence boundary

- 43,525 PPU entry addresses were generated/compiled, including internal CFG entries. This is not a count of independently verified functions.
- Six embedded ELF SPU images were generated. Another 16 raw images, captured as the game requested them, were compiled/registered with 6,723 generated entries. Native jobs ran, but the entire image set has not been semantically validated.
- Vulkan initialized on a GTX 1050 Ti with glslang/SPIR-V translation enabled. The game configured display buffers at 2048×1080/pitch 8192; the current host offscreen target is 1280×720. These are different objects, not proof of correct presentation.
- The native filesystem reads the original ISO's extents and the installed 2.17 update tree. It does not extract the 12 GB GT.VOL onto the system drive.
- Audio initialization, an audio port/thread, XInput initialization and force-feedback worker creation were observed. Audio playback and working gameplay input are not claimed.

## Current stop

Latest bounded run returned **87** for missing PPU code, without a native access-violation report:

| Thread | Missing target | Guest LR |
| --- | --- | --- |
| 22–25, force-feedback workers | `0x00AE2118` | `0x00AE4CBC` |
| 1, main | `0x00A92DD8` | `0x00A931E0` |

USB imports still unresolved include `cellUsbdSetThreadPriority2` (`0x5C832BD7`), `cellUsbdRegisterExtraLdd2` (`0xBD554BCB`), `0xCA9A60BF` and `0x7FE92C54`. Generic fallback returns are not validated implementations.

The local generated batches end at `bootstrap-delta-065`. Those bodies, binaries and private logs are intentionally not published. `config/ppu-entry-seeds.json` publishes addresses only, tied to the exact ELF hash.

The private input-preparation work verified loaded program sections, but did not authenticate the SELF signature. A stored whole-ELF digest and non-loaded section metadata had discrepancies; the Ghidra analysis copy repairs names only and preserves loaded bytes. The recorded SHA-256 pins the actual local research input, not a claim of independently authenticated original software.

## Important fixes and remaining uncertainty

A runtime lightweight-condition wait previously returned after sleeping instead of correctly waiting for notification. Its replacement allowed startup threads to progress.

Comparison with RPCS3's `SPUThread.cpp` at `93dbdead24e1474a94c59fffc1f6cfb25abe488b` showed that user events carry a port-specific payload to the bound queue. The integration runtime additionally broadcast synthetic job completions to every SPURS queue. Disabling that extra broadcast in `GT5_AOT_ONLY=1` allowed GT5 past its previous `ACD7E4` event-handler null access and into new startup work. This observation supports the fix; it does not prove complete scheduler equivalence.

An unknown raw SPURS job is now captured and stops with **86**, before any synthetic completion. Unlifted SPU PCs and unsupported instruction guards also stop with 86 and require inspection. PPU code-generation gaps are explicitly reported. There is no interpreter fallback in the integrated CPU path.

The clean public-clone regeneration process, portability of every dependency and eventual RSX drawing remain work in progress. No ETA or percentage-to-gameplay is supported by the current evidence.
