"""Bounded AOT generation with the full title's code window and explicit gaps.

Uses ps3recomp's Python API so calls outside this batch remain external native
symbols. Unlike a raw CLI slice, it never treats the batch end as the game's
code end. Undecoded words become explicit gap handlers rather than no-ops.
This is a generation/compilation check, not a linkable or bootable port.
"""
from local_config import tool
import os
import argparse
import hashlib
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

project=Path(__file__).resolve().parents[1]
toolkit=project/'third_party/ps3recomp-master'
sys.path.insert(0,str(toolkit/'tools'))
from ppu_lifter import PPULifter, discover_jump_tables
from ppu_disasm import disassemble_bytes

p=argparse.ArgumentParser()
p.add_argument('--count',type=int,default=256)
a=p.parse_args()
if not 1<=a.count<=512: raise SystemExit('This probe accepts 1..512 seed functions')
data=(project/'private/update-2.17/EBOOT-full.ELF').read_bytes()
functions=json.loads((project/'private/analysis-full-2.17/EBOOT-full.functions.json').read_text())
imports=json.loads((project/'private/analysis-full-2.17/EBOOT-full.imports.json').read_text())
selected=functions[:a.count]
start,end=int(selected[0]['start'],16),int(selected[-1]['end'],16)
out=project/f'private/ppu-aot-{a.count}-r2'
out.mkdir(exist_ok=True)
instructions=disassemble_bytes(data[start-0x10000:end-0x10000],start,True)
gaps=[]

class CheckedLifter(PPULifter):
    def lift_function(self,instructions,first,last):
        if not start<=first<end:
            raise ValueError('Refusing to generate a function outside the supplied batch')
        return super().lift_function(instructions,first,min(last,end))
    def _translate_op(self,insn,func):
        code=super()._translate_op(insn,func)
        if code.startswith('/* TODO') or '-> non-code' in code or 'unsupported SPR' in code:
            gaps.append({'address':hex(insn.addr),'word':hex(insn.raw),'mnemonic':insn.mnemonic,'operands':insn.operands,'function':hex(func.start_addr),'emission':code})
            return f'gt5_codegen_gap(ctx, 0x{insn.addr:X}ULL, 0x{insn.raw:08X}u);'
        return code

def read32(addr):
    # The ELF's two PT_LOADs both use the same VA -> file-offset delta.
    for lo,hi in ((0x10000,0x16ae768),(0x16b0000,0x17cf9d8)):
        if lo<=addr and addr+4<=hi:
            return struct.unpack_from('>I',data,addr-0x10000)[0]
    return None

lifter=CheckedLifter()
lifter.header_name='ppu_recomp.h'
lifter.code_lo=0x10200
lifter.code_hi=0xfa84d0
lifter.toc_base=0x17727e0
lifter.function_entries={int(f['start'],16) for f in functions}
lifter.hle_stub_nids={int(str(i['stub']),0):int(str(i['nid']),0) for i in imports}
lifter.jump_tables=discover_jump_tables(instructions,read32,[0x17727e0],lifter.code_lo,lifter.code_hi,func_starts=sorted(lifter.function_entries))
print(f'PPU AOT: {len(selected)} seeds, {len(instructions)} decoded words, {len(lifter.jump_tables)} jump-table dispatchers',flush=True)
for f in selected:
    lifter.lift_function(instructions,int(f['start'],16),int(f['end'],16))
for _ in range(25):
    # The upstream helper promotes gaps, including addresses outside the given
    # instruction list. Keep those as externs instead of generating empty bodies.
    saved_calls,saved_branches=set(lifter.call_targets),set(lifter.branch_targets)
    lifter.call_targets={x for x in saved_calls if start<=x<end}
    lifter.branch_targets={x for x in saved_branches if start<=x<end}
    added=lifter.generate_mid_function_entries(instructions)
    lifter.call_targets |= saved_calls
    lifter.branch_targets |= saved_branches
    if not added: break
assert all(start<=f.start_addr<f.end_addr<=end for f in lifter.functions)
header=lifter.emit_header()+'\nextern "C" void gt5_codegen_gap(ppu_context*, uint64_t, uint32_t);\n'
(out/'ppu_recomp.h').write_text(header,encoding='utf-8')
paths=lifter.write_source_files(str(out),max_lines=60000)
units=[]
for source in paths:
    source=Path(source)
    obj=source.with_suffix('.o')
    print('PPU AOT: compiling '+source.name,flush=True)
    command=[tool('gxx'),'-std=c++20','-O1','-msse4.1','-c','-fmax-errors=8',f'-I{out}',f'-I{toolkit/"runtime/ppu"}',str(source),'-o',str(obj)]
    with source.with_suffix('.compile.log').open('w',encoding='utf-8') as log:
        result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    units.append({'source':source.name,'compile_returncode':result.returncode,'object_bytes':obj.stat().st_size if obj.exists() else 0})
defined={f.start_addr for f in lifter.functions}
external=sorted((lifter.call_targets|lifter.branch_targets)-defined)
report={'scope':'AOT object generation only, not linked or executed; OPD-based function boundaries still require validation. Calls outside the batch remain explicit external symbols. Unresolved instruction/data words invoke an explicit gap handler if reached.','source_elf_sha256':hashlib.sha256(data).hexdigest(),'seed_functions':len(selected),'generated_functions_and_wrappers':len(defined),'jump_table_dispatchers':len(lifter.jump_tables),'external_native_targets':[hex(x) for x in external],'guarded_gaps':gaps,'translation_units':units,'compile_complete':all(u['compile_returncode']==0 for u in units)}
(out/'summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('guarded_gaps','external_native_targets')},indent=2),flush=True)
print(f'External native targets: {len(external)}; explicit gap sites: {len(gaps)}',flush=True)
