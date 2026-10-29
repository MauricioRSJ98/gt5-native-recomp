"""Compile only SPU units accepted by static generation; never run/register them."""
from local_config import tool
import os
import json
import argparse
import subprocess
from pathlib import Path

project=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--stage',default='spu-stage2',choices=['spu-stage2','spu-stage3'])
a=p.parse_args()
stage=project/'private'/a.stage
toolkit=project/'third_party/ps3recomp-master'
inventory=json.loads((stage/'inventory.json').read_text())
results=[]
for program in inventory['programs']:
    result={k:program.get(k) for k in ('name','status','reason')}
    result['functions']=len(program.get('diagnostics',{}).get('functions',[]))
    if program['status'] in ('generated','registered') and not program['diagnostics']['unsupported']:
        folder=stage/program['name']
        source=folder/'spu_recomp.c'
        obj=folder/'spu_recomp.o'
        command=[tool('gcc'),'-std=c11','-O1','-msse4.1','-c','-fmax-errors=8',f'-I{folder}',f'-I{toolkit/"runtime/spu"}',str(source),'-o',str(obj)]
        print('SPU: compiling '+program['name'][:20],flush=True)
        with (folder/'compile.log').open('w',encoding='utf-8') as log:
            proc=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=120)
        result.update(compile_returncode=proc.returncode,object_bytes=obj.stat().st_size if obj.exists() else 0)
    results.append(result)
summary={'scope':'Native object compilation of statically accepted SPU units only. No workload registration, linking, execution or semantic validation.','programs':results,'compiled_units':sum(r.get('compile_returncode')==0 for r in results)}
report_path=project/'private'/('spu-compile-summary.json' if a.stage=='spu-stage2' else 'spu-stage3-compile-summary.json')
report_path.write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2),flush=True)
