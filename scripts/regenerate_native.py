"""Generate private AOT artifacts from the user's configured, pinned ELF.

This is a new clean-clone orchestration path, not an end-to-end validated boot.
It deliberately does not run the game.
"""
import json
import subprocess
import sys
from pathlib import Path
from local_config import project,tool

def run(*args):subprocess.run([sys.executable,'-X','utf8',*[str(x) for x in args]],cwd=project,check=True)

if (project/'private/bootstrap-extras').exists():raise SystemExit('A bootstrap batch already exists; use incremental recovery instead of overwriting it')
elf=project/'private/update-2.17/EBOOT-full.ELF'
if not elf.exists():raise SystemExit('Run prepare_private_inputs.py first')
seeds=json.loads((project/'config/ppu-entry-seeds.json').read_text())
(project/'private/bootstrap-seeds.json').write_text(json.dumps(seeds['entries'],indent=2))
run(project/'scripts/lift_ppu_batch.py')
run(project/'scripts/recover_bootstrap_closure.py','--limit','2048')
cfg=json.loads((project/'private/bootstrap-cfg.json').read_text())
if cfg['blocked'] or cfg['pending']:raise SystemExit('CFG generation has blocked/pending work; inspect bootstrap-cfg.json before compiling')
run(project/'scripts/lift_bootstrap_extras.py','--cfg','--jobs','3')
stage=project/'private/spu-stage3'
run(project/'third_party/ps3recomp-master/tools/build_spu_workloads.py','--input',elf,
    '--lifted',stage,'--out',stage/'spu_workloads.c','--title','GT5 BCUS98114 2.17',
    '--register-fn','spu_register_all','--constructor','--lifter',project/'scripts/spu_lifter_with_bounds.py')
run(project/'scripts/compile_spu_units.py','--stage','spu-stage3')
report=json.loads((project/'private/spu-stage3-compile-summary.json').read_text())
if report['compiled_units']!=6:raise SystemExit('Expected six compiled embedded images; inspect stage reports')
subprocess.run([tool('gcc'),'-std=c11','-O1','-c','-I'+str(project/'third_party/ps3recomp-master/runtime/spu'),str(stage/'spu_workloads.c'),'-o',str(stage/'spu_workloads.o')],check=True)
run(project/'scripts/lift_spu_captured.py')
print('Private AOT generation finished. Build explicitly with scripts/build_native.py; no boot was run.')
