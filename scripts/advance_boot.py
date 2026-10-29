"""Advance only missing compiled-code blockers, with one run per changed batch."""
import os
import argparse
import json
import re
import shutil
import subprocess
import sys
import msvcrt
from pathlib import Path
from native_inputs import project,batches
p=argparse.ArgumentParser();p.add_argument('--steps',type=int,default=4);p.add_argument('--companion-on-fault',action='store_true');a=p.parse_args()
lock=(project/'private/advance-boot.lock').open('a+b')
if lock.tell()==0:lock.write(b'0');lock.flush()
lock.seek(0)
try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
except OSError:raise SystemExit('Another native boot advance is running; wait for it to finish')
scripts=project/'scripts';archive=project/'private/boot-steps';archive.mkdir(exist_ok=True)
def run(script,*args):
    subprocess.run([sys.executable,'-X','utf8',str(scripts/script),*args],check=True)
seen=set()
for step in range(a.steps):
    state=json.loads((project/'private/native-run.json').read_text())
    log=(project/'private/native-run.log').read_text(encoding='utf-8',errors='replace')
    capture=re.search(r'\[GT5-AOT-MISS\] captured SPURS job fp=(0x[0-9A-Fa-f]+) size=(\d+)',log)
    if state.get('returncode')==86 and capture:
        fp=int(capture[1],0);size=int(capture[2]);key=('spu',fp)
        blob=project/f'private/spu-misses/spujob_{fp:016X}_{size}.bin'
        if key in seen or not blob.is_file():raise SystemExit('Repeated or missing captured SPU; inspect dispatch')
        meta=project/'private/spu-captured/summary.json'
        if meta.exists():
            prior=json.loads(meta.read_text())
            if prior.get('compile_complete') and any(int(u.get('fingerprint','0'),0)==fp for u in prior['units']):
                raise SystemExit('SPU already compiled: inspect registry or fingerprint')
        seen.add(key)
        print('Reached SPU',hex(fp),'size',size,flush=True)
        run('lift_spu_captured.py');run('build_native.py');run('run_native.py')
        continue
    if state.get('returncode')!=87 and not (a.companion_on_fault and step==0 and state.get('native_stop')):
        print('Stopped at a non-missing-code blocker:',state,flush=True);break
    targets=re.findall(r'PPU target=(0x[0-9a-fA-F]+)',log)
    structured=project/'private/native-stop.json'
    if structured.exists():targets=[json.loads(structured.read_text())['target']]
    if not targets or '[GT5-CODEGEN]' in log:print('Stopped at a blocker requiring inspection',flush=True);break
    target=int(targets[-1],0)
    if target in seen:raise SystemExit('Repeated native target; inspect dispatch rather than rerunning')
    seen.add(target)
    if any(hex(target) in info['defined'] for _,info in batches()):raise SystemExit('Target already compiled: inspect registry')
    next_id=max([int(folder.name.rsplit('-',1)[1]) for folder in (project/'private').glob('bootstrap-delta-*')]+[0])+1
    name=f'bootstrap-delta-{next_id:03d}'
    print('Reached',hex(target),'->',name,flush=True)
    run('recover_bootstrap_closure.py','--from-native-log','--reached-only','--limit','2048')
    cfg=json.loads((project/'private/bootstrap-cfg.json').read_text())
    if cfg['blocked']:raise SystemExit('CFG recovery requires inspection: '+str(cfg['blocked']))
    run('lift_bootstrap_extras.py','--cfg','--delta',name,'--jobs','3')
    run('build_native.py')
    run('run_native.py')
    shutil.copyfile(project/'private/native-run.log',archive/(name+'.log'))
    if structured.exists():shutil.copyfile(structured,archive/(name+'.stop.json'))
    all_stops=project/'private/native-stops.jsonl'
    if all_stops.exists():shutil.copyfile(all_stops,archive/(name+'.stops.jsonl'))
