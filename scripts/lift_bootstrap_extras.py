"""Lift reviewed bootstrap ranges as native code, with a separate entry table."""
from local_config import tool
import os
import json
import hashlib
import argparse
import subprocess
import sys
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

project=Path(__file__).resolve().parents[1]
toolkit=project/'third_party/ps3recomp-master'
sys.path.insert(0,str(toolkit/'tools'))
from ppu_lifter import PPULifter
from ppu_disasm import disassemble_bytes,decode

p=argparse.ArgumentParser()
p.add_argument('--cfg',action='store_true')
p.add_argument('--jobs',type=int,default=3)
p.add_argument('--delta',help='Write only new functions into this new private batch directory')
args=p.parse_args()
assert 1<=args.jobs<=4
config=json.loads((project/('private/bootstrap-cfg.json' if args.cfg else 'config/bootstrap-extra-functions.json')).read_text())
data=(project/'private/update-2.17/EBOOT-full.ELF').read_bytes()
out=project/'private/bootstrap-extras'
table='gt5_extra_functions';count='gt5_extra_function_count'
all_entries={int(f['start'],0) for f in config['functions']}
if args.delta:
    assert re.fullmatch(r'bootstrap-delta-[0-9]+',args.delta)
    covered=set()
    for folder in [project/'private/bootstrap-extras',*sorted((project/'private').glob('bootstrap-delta-*'))]:
        meta=folder/'summary.json'
        if meta.exists() and folder.name!=args.delta:
            previous=json.loads(meta.read_text())
            if previous.get('compile_complete'):covered|={int(x,0) for x in previous['defined']}
    config['functions']=[f for f in config['functions'] if int(f['start'],0) not in covered]
    out=project/'private'/args.delta
    suffix=args.delta.rsplit('-',1)[1]
    table='gt5_delta_'+suffix+'_functions';count='gt5_delta_'+suffix+'_count'
out.mkdir(exist_ok=True)
(out/'summary.json').write_text(json.dumps({'compile_complete':False,'generation_in_progress':True}),encoding='utf-8')
gaps=[]
class GuardedLifter(PPULifter):
    def _translate_op(self,insn,func):
        code=super()._translate_op(insn,func)
        if code.startswith('/* TODO') or '-> non-code' in code or 'unsupported SPR' in code:
            gaps.append({'site':hex(insn.addr),'instruction':str(insn),'emission':code})
            return f'gt5_codegen_gap(ctx,0x{insn.addr:X}ULL,0x{insn.raw:08X}u); return;'
        return code
lifter=GuardedLifter()
lifter.header_name='ppu_extra.h'
lifter.code_lo=0x10200;lifter.code_hi=0xfa84d0
lifter.toc_base=0x17727e0
lifter.function_entries={int(f['start'],0) for f in config['functions']}
lifter.function_entries|=all_entries
if args.cfg:
    lifter.function_entries|={int(t,0) for f in config['functions'] for t in f['tail_targets']}
for f in config['functions']:
    start,end=int(f['start'],0),int(f['end'],0)
    assert 0x10200<=start<end<=0xfa84d0 and (end-start)<0x10000
    if args.cfg:
        ins=[decode(int.from_bytes(data[int(pc,0)-0x10000:int(pc,0)-0x10000+4],'big'),int(pc,0)) for pc in f['instruction_addresses']]
    else:
        ins=disassemble_bytes(data[start-0x10000:end-0x10000],start,True)
        assert ins[-1].mnemonic=='blr'
    lifted=lifter.lift_function(ins,start,end)
    for i,line in enumerate(lifted.body_lines):
        if 'branch into undecoded region' in line:
            import re
            addr=int(re.search(r'loc_([0-9A-F]+)',line).group(1),16)
            lifted.body_lines[i]=f'loc_{addr:08X}: gt5_codegen_gap(ctx,0x{addr:X}ULL,0); return;'
            gaps.append({'site':hex(addr),'kind':'unseen branch target'})
    if args.cfg:lifted.fallthrough_to=None
(out/'ppu_extra.h').write_text(lifter.emit_header()+'\nextern "C" void gt5_codegen_gap(ppu_context*,uint64_t,uint32_t);\nextern "C" { extern const func_entry gt5_extra_functions[]; extern const uint64_t gt5_extra_function_count; }\n',encoding='utf-8')
paths=lifter.write_source_files(str(out),base='ppu_extra',max_lines=60000)
abi_header=re.sub(r'^void func_[0-9A-F]+\(ppu_context\* ctx\);[^\n]*\n','',(out/'ppu_extra.h').read_text(encoding='utf-8'),flags=re.M)
helper_headers=b''.join(h.read_bytes() for h in sorted((toolkit/'runtime/ppu').glob('*.h')))
def compile_unit(p):
    p=Path(p);text=p.read_text(encoding='utf-8')
    if '/* TODO' in text or '-> non-code' in text:raise SystemExit('Reviewed bootstrap function has unresolved emission')
    text=text.replace('const func_entry function_table[] =','extern "C" const func_entry '+table+'[] =').replace('const uint64_t function_table_count =','extern "C" const uint64_t '+count+' =')
    p.write_text(text,encoding='utf-8')
    obj=p.with_suffix('.o')
    cmd=[tool('gxx'),'-std=c++20','-O1','-msse4.1','-c',f'-I{out}',f'-I{toolkit/"runtime/ppu"}',str(p),'-o',str(obj)]
    # New forward declarations alone do not change an existing object's ABI.
    signature=hashlib.sha256(text.encode('utf-8')+abi_header.encode('utf-8')+helper_headers+repr(cmd).encode()).hexdigest()
    stamp=p.with_suffix('.compile-stamp')
    cached=obj.exists() and stamp.exists() and stamp.read_text()==signature
    rc=0
    if not cached:
        with p.with_suffix('.compile.log').open('w',encoding='utf-8') as log:
            result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=120)
        rc=result.returncode
        if rc==0:stamp.write_text(signature)
    print(('Reused ' if cached else 'Compiled ')+p.name+' rc='+str(rc),flush=True)
    return {'source':p.name,'object':obj.name,'compile_returncode':rc,'cached':cached}
with ThreadPoolExecutor(max_workers=args.jobs) as pool:
    units=list(pool.map(compile_unit,paths))
defined={f.start_addr for f in lifter.functions}
report={'scope':config['scope'],'source_elf_sha256':hashlib.sha256(data).hexdigest(),'cfg_recovery':args.cfg,'guarded_gaps':gaps,'defined':[hex(a) for a in sorted(defined)],'external_native_targets':[hex(a) for a in sorted((lifter.call_targets|lifter.branch_targets)-defined)],'translation_units':units,'compile_complete':all(x['compile_returncode']==0 for x in units)}
report.update(table_symbol=table,count_symbol=count)
(out/'summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
