"""Title-specific checked adapter for ps3recomp's SPU lifter.

Only infers code bounds for exact, pinned image hashes. Keeps the full image
unchanged. Rejects any direct executable branch crossing the proposed boundary.
The static inference is not a proof about dynamic branch targets.
"""
import os
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

project=Path(__file__).resolve().parents[1]
toolkit=project/'third_party/ps3recomp-master'
sys.path.insert(0,str(toolkit/'tools'))
from find_spu_functions import parse_elf,pick_text
from spu_disasm import disassemble_spu

args=sys.argv[1:]
raw=Path(args[0])
image=raw.parent/'image.elf'
if not image.is_file():raise SystemExit('Adapter requires pipeline-owned image.elf')
blob=image.read_bytes()
digest=hashlib.sha256(blob).hexdigest()
config=json.loads((project/'config/spu-code-ranges.json').read_text())['images']
if digest in config:
    end=int(config[digest]['code_end'],0)
    info=parse_elf(blob)
    off,base,size=pick_text(info['phs'])
    if not base<info['entry']<end<=base+size:raise SystemExit('Invalid code boundary or entry')
    insns=disassemble_spu(blob[off:off+size],base)
    terminal=next(i for i in insns if i.addr==end-4)
    if terminal.mnemonic!='bi' or terminal.operands!='$r0':raise SystemExit('Expected final bi r0 at reviewed boundary')
    branches={'brsl','brasl','br','bra','brz','brnz','brhz','brhnz'}
    crossing=[]
    undecoded=[]
    for ins in insns:
        if ins.addr>=end:break
        if ins.mnemonic=='.word':undecoded.append(hex(ins.addr))
        if ins.mnemonic in branches:
            targets=[int(x,16) for x in re.findall(r'0x[0-9A-Fa-f]+',ins.operands)]
            crossing += [{'source':hex(ins.addr),'target':hex(t)} for t in targets if end<=t<base+size]
    audit={'image_sha256':digest,'code_end':hex(end),'last_instruction':str(terminal),'direct_branches_into_excluded_tail':crossing,'undecoded_words_below_boundary':undecoded,'static_evidence':config[digest]['evidence'],'limitation':'Indirect targets and execution semantics remain unvalidated; all image bytes are preserved.'}
    (raw.parent/'code-boundary-audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    if crossing or undecoded:raise SystemExit('Boundary rejected: direct branches into tail or undecoded code words')
    args += ['--code-end',hex(end)]
result=subprocess.run([sys.executable,'-X','utf8',str(toolkit/'tools/spu_lifter.py'),*args])
raise SystemExit(result.returncode)
