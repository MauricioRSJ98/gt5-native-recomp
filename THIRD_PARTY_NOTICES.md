# Third-party notices

This repository distributes original integration scripts/native glue and patches, not third-party SDK/tool binaries or game content.

## ps3recomp and GT5 Prologue Recompiled

The integration adapts code and interfaces from Ned Heller / sp00nznet's MIT-licensed projects. Their copyright and permission notices are included in:

- [licenses/ps3recomp-MIT.txt](licenses/ps3recomp-MIT.txt)
- [licenses/GT5P-MIT.txt](licenses/GT5P-MIT.txt)

The runtime patch is against ps3recomp commit `4e8f3ca87a3e1d87bb83b8b7e9348fe2685cd514`. Preserve upstream file notices when applying or redistributing it. The GT5P loader is fetched as a separate dependency, not re-licensed by this project.

## Other references and dependencies

RPCS3 source was consulted as a behavior/file-format reference. Its source is not vendored in this public repository and its CPU execution engine is not linked here. Consult [RPCS3's license](https://github.com/RPCS3/rpcs3/blob/master/LICENSE) for that project's terms. Private extraction utilities, source/key tables and extracted results are excluded from this publication.

Ghidra, REA, SDL2, Vulkan-Headers, glslang, SPIRV-Tools, SPIRV-Headers, GCC/MinGW-w64, CMake, Ninja, Python, Node.js, Java, PyGhidra/JPype, PyCryptodome and GitHub CLI retain their own licenses. See [CREDITS](docs/CREDITS.md) for links and roles. Downloaded dependencies stay outside version control and must retain the license files distributed by their authors.

Gran Turismo, PlayStation and associated names are trademarks of their respective owners. No ownership of the game, firmware, SDK or assets is claimed or licensed by this repository.
