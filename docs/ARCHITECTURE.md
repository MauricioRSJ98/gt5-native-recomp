# Integration map

```text
User-local ELF + disc ISO + installed update
                  |
        analysis / address metadata
                  |
       ps3recomp PPU + SPU lifters
                  |
   generated native objects (private/)
                  |
   native/main.cpp + compatibility runtime
       |              |               |
   PS3 services   SPURS + AOT SPU   RSX command stream
       |                              |
   native/disc_fs.cpp             native/present.cpp
   read-only input sources       Vulkan + glslang/SPIR-V
```

`native/main.cpp` loads the prepared ELF, sets up memory/TLS/native registries and invokes the AOT entry. Unknown PPU targets produce structured diagnostics and exit 87. `spu_aot_dispatch.c` provides compiled-only dispatch and exits 86 for a missing SPU target or unsupported instruction.

`disc_fs.cpp` reads ISO extents and installed update sources without extracting GT.VOL. Writes delegated to the compatibility filesystem use project-local `game-data/`. Directory and other filesystem behavior are not complete.

`present.cpp` runs the Vulkan consumer/vblank/FIFO loop. Vulkan initialization is not a game frame. Instrumentation separately records the first guest draw and game flip.

The upstream runtime patch ports the Vulkan loader path to Windows, disables the D3D12 path, adds real lightweight-condition waiting and adjusts strict SPURS completion behavior. Review the patch with the pinned base source; it is part of the implementation, not an opaque binary dependency.

The published metadata lists entry addresses and exact input hashes. Generated native instruction bodies, captured local stores, traces containing game data and compiled artifacts remain private and must be regenerated locally.
