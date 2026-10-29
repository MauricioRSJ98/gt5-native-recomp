"""AOT-compile the actual SPURS policy/job images captured from this GT5 build."""
from local_config import tool
import os
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from native_inputs import project,write_changed
tools=project/'third_party/ps3recomp-master/tools'
sys.path.insert(0,str(tools))
from build_spu_workloads import fnv1a64
root=project/'private/spu-captured';root.mkdir(exist_ok=True)
(root/'summary.json').write_text(json.dumps({'compile_complete':False,'generation_in_progress':True}))
registry=['#include "spu_workload.h"\nextern void spu_begin_image(int);\n']
registrations=[];units=[]
for index,blob in enumerate(sorted((project/'private/spu-misses').glob('spujob_*.bin'))):
    match=re.fullmatch(r'spujob_([0-9A-Fa-f]{16})_(\d+)\.bin',blob.name)
    if not match:continue
    raw=blob.read_bytes();fp=int(match[1],16)
    assert len(raw)==int(match[2]) and fnv1a64(raw)==fp
    base=0xa00 if fp==0x75bfe68ae96d7577 else 0
    prefix='gt5_spu_'+match[1].lower();folder=root/prefix;folder.mkdir(exist_ok=True)
    bounds=folder/'functions.json';report=folder/'generation.json'
    generation_hash=hashlib.sha256(raw+str(base).encode()+Path(__file__).read_bytes())
    for dependency in sorted(tools.glob('*.py')):generation_hash.update(dependency.read_bytes())
    generation_signature=generation_hash.hexdigest();stamp=folder/'compile-cache.json'
    prior=json.loads(stamp.read_text()) if stamp.exists() else {}
    generated=prior.get('generation_signature')==generation_signature and all(x.exists() for x in (bounds,report,folder/'spu_recomp.c',folder/'spu_recomp.h'))
    if not generated:
        with (folder/'generation.log').open('w',encoding='utf-8') as log:
            subprocess.run([sys.executable,'-X','utf8',str(tools/'find_spu_functions.py'),str(blob),'--raw','--base',hex(base),'--out',str(bounds)],stdout=log,stderr=subprocess.STDOUT,check=True)
            subprocess.run([sys.executable,'-X','utf8',str(tools/'spu_lifter.py'),str(blob),'--base',hex(base),'--functions',str(bounds),'--symbol-prefix',prefix,'--output',str(folder),'--source-name','spu_recomp.c','--report',str(report)],stdout=log,stderr=subprocess.STDOUT,check=True)
    diagnostics=json.loads(report.read_text())
    unsupported=diagnostics.get('unsupported',[])
    for name in (() if generated else ('spu_recomp.h','spu_recomp.c')):
        path=folder/name;text=path.read_text(encoding='utf-8')
        text=re.sub(r'"(?:\.\./)+(?:runtime/spu/)?(spu_[^"/]+\.h)"',r'"\1"',text)
        if name.endswith('.c'):
            text=text.replace('spu_unsupported(', 'gt5_spu_unsupported(ctx, ')
            text=text.replace('#include "spu_recomp.h"','#include "spu_recomp.h"\nextern void gt5_spu_unsupported(spu_context*,uint32_t,const char*);')
        path.write_text(text,encoding='utf-8')
    source=folder/'spu_recomp.c';obj=folder/'spu_recomp.o'
    cmd=[tool('gcc'),'-std=c11','-O1','-msse4.1','-c',f'-I{folder}',f'-I{tools.parent/"runtime/spu"}',str(source),'-o',str(obj)]
    # Reuse only a successfully compiled object with identical generated code,
    # compiler options and runtime headers. New jobs do not rebuild old jobs.
    fingerprint=hashlib.sha256(json.dumps(cmd).encode())
    for dependency in [source,folder/'spu_recomp.h',*sorted((tools.parent/'runtime/spu').glob('*.h'))]:
        fingerprint.update(dependency.read_bytes())
    signature=fingerprint.hexdigest()
    cached=obj.exists() and stamp.exists() and json.loads(stamp.read_text()).get('signature')==signature
    if not cached:
        if stamp.exists():stamp.unlink()
        with (folder/'compile.log').open('w',encoding='utf-8') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    stamp.write_text(json.dumps({'signature':signature,'generation_signature':generation_signature}))
    image_id=1000+index
    entry=f'{prefix}_spu_func_{base:08X}'
    assert entry in (folder/'spu_recomp.h').read_text()
    registry.append(f'extern void {entry}(spu_context*);\nextern void {prefix}_spu_recomp_register(void);\n')
    registrations.append(f'spu_begin_image({image_id});{prefix}_spu_recomp_register();spu_workload_register_img(0x{fp:016X}ULL,{entry},{image_id},"{prefix}");\n')
    units.append({'object':str(obj.relative_to(project)),'fingerprint':hex(fp),'sha256':hashlib.sha256(raw).hexdigest(),'base':hex(base),'functions':len(json.loads(bounds.read_text())),'guarded_unsupported':unsupported})
    print('Cached SPU' if cached else 'Compiled SPU',blob.name,'functions',units[-1]['functions'],flush=True)
registry.append('void gt5_register_captured_spu(void) {\n'+''.join(registrations)+'spu_begin_image(0);\n}\n')
source=root/'registry.c';write_changed(source,''.join(registry));obj=source.with_suffix('.o')
subprocess.run([tool('gcc'),'-std=c11','-O1','-c',f'-I{tools.parent/"runtime/spu"}',str(source),'-o',str(obj)],check=True)
units.append({'object':str(obj.relative_to(project))})
(root/'summary.json').write_text(json.dumps({'compile_complete':True,'units':units},indent=2))
