"""Configure user-supplied inputs and generate private loader/import metadata."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

project=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
for name in ('elf','iso','update-root'):p.add_argument('--'+name,required=True,type=Path)
for name in ('gcc','gxx','cmake','ninja'):p.add_argument('--'+name)
a=p.parse_args()
expected=json.loads((project/'config/ppu-entry-seeds.json').read_text())['source_elf_sha256']
if hashlib.sha256(a.elf.read_bytes()).hexdigest()!=expected:raise SystemExit('ELF hash differs: this address configuration is only for the pinned BCUS98114 2.17 input')
if not a.iso.is_file() or not (a.update_root/'PARAM.SFO').is_file() or not (a.update_root/'USRDIR').is_dir():
    raise SystemExit('Supply an ISO and update root containing PARAM.SFO and USRDIR')
values={'iso':str(a.iso.resolve()),'update_root':str(a.update_root.resolve())}
values.update({k:getattr(a,k) for k in ('gcc','gxx','cmake','ninja') if getattr(a,k)})
(project/'config/local.json').write_text(json.dumps(values,indent=2))
for relative in ('private/update-2.17','private/source-data','private/analysis-full-2.17','private/spu-misses','research'):
    (project/relative).mkdir(parents=True,exist_ok=True)
elf=project/'private/update-2.17/EBOOT-full.ELF'
if elf.exists() and hashlib.sha256(elf.read_bytes()).hexdigest()!=expected:raise SystemExit('Existing private ELF differs; inspect it before replacing anything')
if a.elf.resolve()!=elf.resolve():shutil.copyfile(a.elf,elf)
shutil.copyfile(a.update_root/'PARAM.SFO',project/'private/source-data/PARAM.SFO')
tools=project/'third_party/ps3recomp-master/tools'
if not tools.is_dir():raise SystemExit('Fetch dependencies first: python scripts/fetch_dependencies.py')
subprocess.run([sys.executable,str(tools/'ppu_loader.py'),str(elf),'-o',str(project/'private/analysis-full-2.17')],check=True)
subprocess.run([sys.executable,str(tools/'gen_imports.py'),str(elf),'-o',str(project/'private/analysis-full-2.17/imports-named.json')],check=True)
subprocess.run([sys.executable,str(project/'scripts/inspect_disc_iso.py')],cwd=project,check=True)
print('Private inputs configured; no game data was added to Git.')
