"""One bounded boot attempt, preserving output even on a timeout."""
from local_config import setting
import argparse
import json
import os
import subprocess
import shutil
from datetime import datetime,timezone
from pathlib import Path
project=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--seconds',type=int,default=10);p.add_argument('--window',action='store_true');a=p.parse_args()

# Keep the preceding evidence before a changed native build replaces it.
archive=project/'private/boot-runs';archive.mkdir(exist_ok=True)
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
for name in ('native-run.log','native-run.json','native-stop.json','native-stops.jsonl','native-fault.json'):
    source=project/'private'/name
    if source.exists():shutil.copyfile(source,archive/(stamp+'-'+name))
env=os.environ.copy();env['PS3_VERBOSE']='0';env['PS3_HEADLESS']='1'
env['PS3RECOMP_VK_DUMP']=str(project/'private/native-frame.ppm')
env['PS3RECOMP_VK_GUEST_PROGRAMS']='1'
(project/'private/spu-misses').mkdir(exist_ok=True)
env['SPU_DUMP_MISS']=str(project/'private/spu-misses')
env['GT5_AOT_ONLY']='1'
env['GT5_UPDATE_ROOT']=setting('update_root')
if a.window:env['PS3RECOMP_VK_WINDOW']='1'
report={'seconds':a.seconds,'window_requested':a.window}
stop_file=project/'private/native-stop.json'
if stop_file.exists():stop_file.unlink()
all_stops=project/'private/native-stops.jsonl'
if all_stops.exists():all_stops.unlink()
fault_file=project/'private/native-fault.json'
if fault_file.exists():fault_file.unlink()
with (project/'private/native-run.log').open('wb') as log:
    try:
        result=subprocess.run([str(project/'private/native-build/gt5-native.exe'),str(project/'private/update-2.17/EBOOT-full.ELF')],cwd=project,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=a.seconds)
        report['returncode']=result.returncode
    except subprocess.TimeoutExpired:
        report['timeout']=True
(project/'private/native-run.json').write_text(json.dumps(report,indent=2))
text=(project/'private/native-run.log').read_text(encoding='utf-8',errors='replace')
report['vulkan_ready']='[GT5-VULKAN] backend=ready' in text
report['observed_game_flip']='[GT5-VULKAN] game flip=' in text
report['observed_game_draw']='[GT5-VULKAN] first guest draw submitted' in text
if stop_file.exists():report['native_stop']=json.loads(stop_file.read_text())
if all_stops.exists():report['native_stops']=[json.loads(x) for x in all_stops.read_text().splitlines() if x.strip()]
if fault_file.exists():report['native_fault']=json.loads(fault_file.read_text())
(project/'private/native-run.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
print('\n'.join(text.splitlines()[-25:]))
