"""Build the GT5 AOT executable using the existing runtime; no automatic run."""
from local_config import tool
import os
import json
import hashlib
import subprocess
import sys
from pathlib import Path
from native_inputs import batches,write_changed
project=Path(__file__).resolve().parents[1]
objects=[]
digest=hashlib.sha256((project/'private/update-2.17/EBOOT-full.ELF').read_bytes()).hexdigest()
base=project/'private/ppu-aot-256-r2'
inputs=[(base,json.loads((base/'summary.json').read_text())),*batches()]
for folder,info in inputs:
    assert info['source_elf_sha256']==digest
    assert info['compile_complete']
    for unit in info['translation_units']:
        obj=folder/(unit.get('object') or Path(unit['source']).with_suffix('.o').name)
        assert obj.exists(),obj
        objects.append(obj)
spu_objects=sorted((project/'private/spu-stage3').rglob('*.o'))
assert len(spu_objects)==7,len(spu_objects)
objects+=spu_objects
captured=project/'private/spu-captured/summary.json'
if captured.exists():
    report=json.loads(captured.read_text());assert report['compile_complete']
    objects += [str(project/u['object']) for u in report['units']]
objects=[Path(x) for x in objects]
subprocess.run([sys.executable,'-X','utf8',str(project/'scripts/prepare_disc_assets.py')],check=True)
subprocess.run([sys.executable,'-X','utf8',str(project/'scripts/prepare_native_imports.py')],check=True)
write_changed(project/'private/native-sources.cmake','set(GT5_NATIVE_OBJECTS\n'+''.join('  "'+p.as_posix()+'"\n' for p in objects)+')\n')
subprocess.run([sys.executable,'-X','utf8',str(project/'third_party/ps3recomp-master/tools/gen_hle_nids.py'),'--all','--out',str(project/'private/ppu_hle_nids.cpp')],check=True)
cmake=tool('cmake')
cmd=[cmake,'-S',str(project/'native'),'-B',str(project/'private/native-build'),'-G','Ninja',
     '-DCMAKE_MAKE_PROGRAM='+tool('ninja'),
     '-DCMAKE_C_COMPILER='+tool('gcc'),
     '-DCMAKE_CXX_COMPILER='+tool('gxx'),
     '-DCMAKE_C_COMPILER_LAUNCHER='+sys.executable+';'+str(project/'scripts/cygwin_dep_launcher.py'),
     '-DCMAKE_CXX_COMPILER_LAUNCHER='+sys.executable+';'+str(project/'scripts/cygwin_dep_launcher.py'),
     '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_C_FLAGS_RELEASE=-O1','-DCMAKE_CXX_FLAGS_RELEASE=-O1']
with (project/'private/native-configure.log').open('w',encoding='utf-8') as log:
    subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
with (project/'private/native-build.log').open('w',encoding='utf-8') as log:
    result=subprocess.run([cmake,'--build',str(project/'private/native-build'),'--target','gt5-native','-j','3'],stdout=log,stderr=subprocess.STDOUT)
print('Native build return code:',result.returncode,flush=True)
if result.returncode:
    print('\n'.join((project/'private/native-build.log').read_text(encoding='utf-8',errors='replace').splitlines()[-35:]))
sys.exit(result.returncode)
