"""Inspect unresolved SPU words against the ELF sections and typed symbols."""
import os
import json
import re
import sys
from pathlib import Path

project=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(project/'third_party/ps3recomp-master/tools'))
from find_spu_functions import parse_elf, read_symbols, pick_text
from spu_disasm import disassemble_spu

stage=project/'private/spu-stage2'
inventory=json.loads((stage/'inventory.json').read_text())
results=[]
for program in inventory['programs']:
    folder=stage/program['name']
    blob=(folder/'image.elf').read_bytes()
    elf=parse_elf(blob)
    symbols=read_symbols(blob,elf['shs'])
    source=(folder/'spu_recomp.c').read_text(encoding='utf-8',errors='replace')
    misses=[{'address':int(addr,16),'word':word} for word,addr in re.findall(r'/\* TODO spu: \.word (0x[0-9A-Fa-f]+) \*/ spu_unsupported\((0x[0-9A-Fa-f]+),',source)]
    for m in misses:
        m['sections']=[{k:s[k] for k in ('name','addr','size','flags')} for s in elf['shs'] if s['addr']<=m['address']<s['addr']+s['size']]
        m['typed_function_symbols']=[s for s in symbols if s['addr']<=m['address']<s['addr']+s['size']]
    file_off,base,size=pick_text(elf['phs'])
    insns=disassemble_spu(blob[file_off:file_off+size],base)
    suspect_lines={m['address']&~15 for m in misses}
    load_refs=[]
    for ins in insns:
        if ins.mnemonic in ('lqr','lqa'):
            targets=[int(x,16) for x in re.findall(r'0x[0-9A-Fa-f]+',ins.operands)]
            if any((x&~15) in suspect_lines for x in targets):
                load_refs.append({'instruction':hex(ins.addr),'mnemonic':ins.mnemonic,'operands':ins.operands})
    first=min((m['address'] for m in misses),default=None)
    nearby=[{'address':hex(i.addr),'mnemonic':i.mnemonic,'operands':i.operands} for i in insns if first is not None and first-32<=i.addr<first+32]
    results.append({'name':program['name'],'status':program['status'],'entry':elf['entry'],'sections':[{k:s[k] for k in ('name','addr','off','size','flags','type')} for s in elf['shs']],'typed_function_symbols':len(symbols),'unresolved_words':misses,'loads_referencing_suspect_qwords':load_refs,'instructions_near_first_unresolved':nearby,'interpretation':'Sequential byte masks suggest embedded constant data, but stripped images have no authoritative section boundary. Do not omit these ranges or claim complete SPU coverage without additional validation.' if misses else 'No unresolved words reported by generation; runtime semantics still unvalidated.'})
(project/'private/spu-boundaries.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
for r in results:
    print(json.dumps({'name':r['name'][:16],'symbols':r['typed_function_symbols'],'unresolved':len(r['unresolved_words']),'addresses':[hex(m['address']) for m in r['unresolved_words']],'load_references':len(r['loads_referencing_suspect_qwords'])},ensure_ascii=True))
