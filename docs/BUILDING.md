# Building and regenerating private artifacts

This repository publishes the integration source, not the maintainer's generated game code or ready-to-run executable. The original local checkpoint built successfully; **the clean-clone path below has not been validated end to end**. Build reproducibility is a first-class contribution target. Do not interpret successful source CI as a GT5 boot test.

## Requirements

- Windows x86-64, Git, Python 3.11+ and Node.js for dependency downloads.
- MinGW-w64 GCC/G++ with C++20 and SSE4.1 support, CMake 3.20+ and Ninja. The original workspace used GCC 12 through Cygwin.
- A Vulkan-capable GPU and installed driver. Only the maintainer's GTX 1050 Ti startup has been observed.
- Your own **BCUS98114 v2.17** installed update tree, base disc ISO and prepared ELF64 big-endian executable. This repository does not include input extraction/key material or game downloads.
- Optional Ghidra 12.2, its PyGhidra/JPype wheels and a compatible JDK for targeted analysis. REA is optional/evaluated, not a required functioning backend.

The checkpoint ELF SHA-256 is `7181599ce46a7d5bdd404048856c6e9b2d296637c5b515fb10b242aad35ba047`. Scripts contain addresses/layout assumptions for that exact input. Do not apply them to another region, update or GT5 Prologue.

## Public source checks

These do not require the game or download its content:

```powershell
python scripts/check_public_source.py
```

CI also checks that the runtime patch applies to the pinned upstream source. No game execution occurs in CI.

## Fetch dependencies

```powershell
python scripts/fetch_dependencies.py
```

The downloader reads `dependencies.lock.json`, keeps downloads under ignored `research/`, extracts into ignored `third_party/` and `tools/`, verifies pinned patch-base file hashes, and applies `patches/ps3recomp-gt5.patch`. SDL's archive has an explicit SHA-256. Source archives use upstream refs plus base-file verification for the patched runtime. Review upstream licenses; source archives are not tool installers.

## Configure local inputs

Use paths appropriate to your machine. `--update-root` points to the **BCUS98114 directory containing PARAM.SFO and USRDIR**, not the whole RPCS3 installation.

```powershell
python scripts/prepare_private_inputs.py --elf "X:\your-data\EBOOT-full.ELF" --iso "X:\your-data\GT5.iso" --update-root "X:\your-data\BCUS98114" --gcc "C:\your-toolchain\gcc.exe" --gxx "C:\your-toolchain\g++.exe" --cmake "C:\your-tools\cmake.exe" --ninja "C:\your-tools\ninja.exe"
```

This writes ignored `config/local.json`, copies the supplied ELF and PARAM.SFO into `private/`, and generates loader/import metadata. The ISO and update assets remain in their original locations. A disc index is generated without extracting GT.VOL.

`scripts/local_config.py` resolves tools from that file or `GT5_GCC`, `GT5_GXX`, `GT5_CMAKE`, `GT5_NINJA`, `GT5_ISO` and `GT5_UPDATE_ROOT`. Native runs receive the update source via environment. The original working folder is not modified by this public-source setup.

## Regenerate AOT artifacts

```powershell
python scripts/regenerate_native.py
python scripts/build_native.py
python scripts/run_native.py --seconds 10
```

`regenerate_native.py` lifts the small frozen PPU base, recovers from the published address-only seeds, emits the remaining PPU code, and generates/compiles embedded SPU ELF images. Generated code and outputs stay in `private/`.

Raw SPURS images are captured only as startup requests them. The registry is initially empty and missing raw jobs stop with exit code 86. To lift an observed new job or missing PPU target, use:

```powershell
python scripts/advance_boot.py --steps 2
```

It performs a bounded change/build/run sequence and stops on a fault requiring investigation. A missing SPU PC or unsupported instruction is not treated as a raw-job capture. Inspect that failure before rerunning.

The workflow may produce a different initial batch layout from the maintainer's historical incremental batches. Preserve evidence and report the first difference instead of assuming identical execution. Code/data boundary inference and clean regeneration are still under review.

## Ghidra and REA

Set `JAVA_HOME` and optionally `GHIDRA_INSTALL_DIR`, install PyGhidra/JPype into your local Python environment, and keep Ghidra settings/cache/project data under ignored local directories. `prepare_ghidra_elf.py` makes an analysis-only copy; targeted exports use `ghidra_boot_export.py` after a local Ghidra project/import has been prepared. Project import is not automated by the public bootstrap.

REA 6.8.0 was installed/evaluated locally but its PS3/Ghidra integration is not working in the recorded environment. Installing REA is not a substitute for the working direct Ghidra path.

## Current limitations

- This is a Windows-specific integration; Linux/macOS and alternate toolchains are not validated.
- Some analysis scripts still assume existing private stage metadata. Read their preconditions before use.
- No game-generated source, raw SPU images, private compiler objects, firmware or playable release is supplied.
- The clean regeneration path has source/patch checks, not a confirmed fresh full-game rebuild.
- Reports must distinguish missing native code, incomplete HLE behavior, Vulkan readiness, actual draws/flips and gameplay.
