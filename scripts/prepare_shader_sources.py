"""Extract the two dependency commits pinned by glslang's known_good.json."""
import os
import zipfile
from pathlib import Path
p=Path(__file__).resolve().parents[1]
for archive,directory in [('spirv-tools.zip','External/spirv-tools'),('spirv-headers.zip','External/spirv-tools/external/spirv-headers')]:
    dest=p/'third_party/glslang-16.6.0'/directory
    with zipfile.ZipFile(p/'research'/archive) as z:
        for entry in z.infolist():
            parts=Path(entry.filename).parts[1:]
            if not parts or entry.is_dir():continue
            target=dest.joinpath(*parts)
            assert target.resolve().is_relative_to(dest.resolve())
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(z.read(entry))
    print('Prepared',directory,flush=True)
