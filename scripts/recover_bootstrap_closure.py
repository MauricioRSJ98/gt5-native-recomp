"""Recover a bounded static call-graph closure for native bootstrap work.

Only follows reachable direct control flow. Calls are separate AOT functions;
indirect dispatch remains explicit. No instructions are interpreted at runtime.
Exception/unwind-only entries and indirect targets require further discovery.
"""
import os
import argparse
from collections import deque
import json
import hashlib
import struct
import sys
from pathlib import Path

project=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(project/'third_party/ps3recomp-master/tools'))
from ppu_disasm import decode,sign_extend

p=argparse.ArgumentParser()
p.add_argument('--limit',type=int,default=192)
p.add_argument('--from-stop',action='store_true',help='Add the reached native stop target to persistent bootstrap seeds')
p.add_argument('--from-native-log',action='store_true',help='Add the most recent target in the full-runtime log')
p.add_argument('--all-opd',action='store_true',help='Seed every address-taken entry in the title executable')
p.add_argument('--reached-only',action='store_true',help='Follow only the reached stop and stop at already compiled functions')
a=p.parse_args()
assert 1<=a.limit<=2048
data=(project/'private/update-2.17/EBOOT-full.ELF').read_bytes()
source_digest=hashlib.sha256(data).hexdigest()
imports={int(x['stub'],0) for x in json.loads((project/'private/analysis-full-2.17/imports-named.json').read_text())}
base=project/'private/ppu-aot-256-r2'
defined=set()
for cpp in base.glob('ppu_recomp_*.cpp'):
    import re
    defined|={int(x,16) for x in re.findall(r'^void func_([0-9A-F]+)\(ppu_context\* ctx\) \{',cpp.read_text(),re.M)}
opd={int(f['start'],0) for f in json.loads((project/'private/analysis-full-2.17/EBOOT-full.functions.json').read_text())}
known=opd|defined
cache_file=project/'private/bootstrap-cfg-cache.json'
cached={}
if cache_file.exists():
    old_cache=json.loads(cache_file.read_text())
    if old_cache['source_elf_sha256']!=source_digest:raise SystemExit('CFG cache belongs to another executable')
    cached={int(f['start'],0):f for f in old_cache['functions']}
previous_cfg=project/'private/bootstrap-cfg.json'
if previous_cfg.exists():
    cached.update({int(f['start'],0):f for f in json.loads(previous_cfg.read_text())['functions']})
known|=set(cached)
compiled=set(defined)
for folder in [project/'private/bootstrap-extras',*sorted((project/'private').glob('bootstrap-delta-*'))]:
    meta=folder/'summary.json'
    if meta.exists():
        info=json.loads(meta.read_text())
        if info.get('compile_complete'):compiled|={int(x,0) for x in info['defined']}

def word(pc):
    if pc%4 or not 0x10200<=pc<0xfa84d0: raise ValueError(f'code address out of range: {pc:#x}')
    return struct.unpack_from('>I',data,pc-0x10000)[0]

def prologue(pc):
    try:words=[word(pc+i*4) for i in range(5)]
    except ValueError:return False
    # stdu r1,-N(r1), optionally after setup/mflr.
    return any((w>>26)==62 and ((w>>21)&31)==1 and ((w>>16)&31)==1 and w&3==1 and w&0x8000 for w in words)

def recover(start):
    todo=[start];seen={};calls=set();tails=set();indirect=[];call_sites={}
    while todo:
        pc=todo.pop()
        if pc in seen:continue
        if not start<=pc<start+0x10000:tails.add(pc);continue
        if len(seen)>=8192:raise ValueError('function exceeds bounded CFG instruction count')
        w=word(pc);ins=decode(w,pc);seen[pc]=ins
        op=w>>26;lk=w&1
        if op in (18,16):
            mask=0x3fffffc if op==18 else 0xfffc
            disp=sign_extend(w&mask,26 if op==18 else 16)
            target=(disp if w&2 else pc+disp)&0xffffffff
            if lk:
                if target!=pc+4:calls.add(target);call_sites[pc]=target
                todo.append(pc+4)
                continue
            separate=(target!=start and (target in imports or target in known or (abs(target-pc)>32 and prologue(target))))
            if separate or target<start or target>=start+0x10000:tails.add(target)
            else:todo.append(target)
            if op==16 and ((w>>21)&31)!=20:todo.append(pc+4)
            continue
        if op==19 and ((w>>1)&1023) in (16,528):
            xo=(w>>1)&1023;bo=(w>>21)&31
            if xo==528 or lk:indirect.append({'site':hex(pc),'instruction':str(ins),'link':bool(lk)})
            if lk or bo!=20:todo.append(pc+4)
            continue
        if ins.mnemonic.startswith('.'):
            raise ValueError(f'reachable undecoded word at {pc:#x}: {w:#x}')
        todo.append(pc+4)
    return {'start':hex(start),'end':hex(max(seen)+4),'instruction_addresses':[hex(x) for x in sorted(seen)],'direct_calls':[hex(x) for x in sorted(calls)],'ordered_calls':[hex(call_sites[pc]) for pc in sorted(call_sites)],'tail_targets':[hex(x) for x in sorted(tails)],'indirect_sites':indirect,'evidence':'Reachable direct CFG from a reached bootstrap/native call target; exception-only and indirect edges remain outside this static discovery.'}

seed_file=project/'private/bootstrap-seeds.json'
seeds={0x10230,0xac109c,0xabfed8}
required_previous=set(cached)
# Recover coverage from the retained successful diagnostic build logs as well.
# This migrates pre-cache runs without discarding their accepted native entries.
for name in ('mapper-bootstrap-run.log','closure192-run.log'):
    log=project/'private'/name
    if log.exists():
        text=log.read_text(encoding='utf-8')
        try:record=json.loads(text[text.index('{'):])
        except (ValueError,json.JSONDecodeError):continue
        required_previous|={int(x,0) for x in record.get('extra_native_functions',[])}
if seed_file.exists():seeds|={int(x,0) for x in json.loads(seed_file.read_text())}
known|=seeds
if a.all_opd:seeds|={x for x in opd if 0x10200<=x<0xfa84d0 and x not in imports}
current_target=None
current_lr=None
thread_stops=[]
if a.from_native_log:
    import re
    log=(project/'private/native-run.log').read_text(encoding='utf-8',errors='replace')
    targets=re.findall(r'(?:PPU target=|unresolved indirect call -> )(0x[0-9A-Fa-f]+)',log)
    structured=project/'private/native-stop.json'
    if structured.exists():
        stop=json.loads(structured.read_text());targets=[stop['target']];current_lr=int(stop['lr'],0)
    all_stops=project/'private/native-stops.jsonl'
    if all_stops.exists():thread_stops=[json.loads(x) for x in all_stops.read_text().splitlines() if x.strip()]
    if not targets:raise SystemExit('No missing native target in current runtime log')
    current_target=int(targets[-1],0);seeds.add(current_target)
if a.from_stop:
    event=json.loads((project/'private/native-boot-probe/summary.json').read_text())['events'][-1]
    if event['kind'] not in ('unlifted_native_target','unlifted_indirect_target'):raise SystemExit('Latest stop is not an unlifted native target')
    current_target=int(event['address'],0);seeds.add(current_target)
seed_file.write_text(json.dumps([hex(x) for x in sorted(seeds)],indent=2))
for address in sorted(required_previous-set(cached)):
    cached[address]=recover(address)
root_order=([current_target] if current_target else [])+sorted(seeds-({current_target} if current_target else set()))
if a.reached_only:
    if current_target is None:raise SystemExit('--reached-only requires a reached target')
    root_order=[current_target]
    root_order+=sorted({int(s['target'],0) for s in thread_stops}-compiled-imports-{current_target})
    # Include the next direct calls in the reached caller, avoiding one build
    # for each consecutive call in a single initialization routine.
    if current_lr:
        site=hex(current_lr-4)
        callers=[f for address,f in cached.items() if address in compiled and site in f['instruction_addresses']]
        if not callers:
            possible=[address for address in compiled if address<=current_lr-4]
            if possible:
                try:
                    candidate=recover(max(possible))
                    if site in candidate['instruction_addresses']:callers=[candidate]
                except ValueError:pass
        if callers:
            caller=max(callers,key=lambda f:int(f['start'],0))
            # The bootstrap CFG splits some initialization routines into many
            # tail-connected blocks. Follow their already compiled tails too,
            # so consecutive calls do not each require a separate boot/build.
            siblings=set();follow=deque([caller]);visited=set()
            while follow and len(visited)<128:
                block=follow.popleft();address=int(block['start'],0)
                if address in visited:continue
                visited.add(address)
                siblings.update(int(x,0) for x in block['ordered_calls']+block['tail_targets'])
                for tail in block['tail_targets']:
                    target=int(tail,0)
                    if target in compiled and target in cached and abs(target-current_lr)<0x10000:
                        follow.append(cached[target])
            root_order+=sorted(siblings-compiled-imports-{current_target})
queue=deque();queued=set(root_order) if a.reached_only else set(seeds);results=[];blocked=[];analyzed_base=[];instruction_total=0
# Process every reached root before extending any one root's dependency tree.
for address in root_order:
    try:r=cached.get(address) or recover(address)
    except ValueError as error:blocked.append({'address':hex(address),'reason':str(error)});continue
    if address not in defined:cached[address]=r
    for target in r['ordered_calls']+r['tail_targets']:
        target=int(target,0)
        if 0x10200<=target<0xfa84d0 and target not in imports|queued:
            queued.add(target);queue.append(target)
while queue and len(results)<a.limit and instruction_total<250000:
    address=queue.popleft()
    if address in imports:continue
    if a.reached_only and address in compiled:continue
    try:r=cached.get(address) or recover(address)
    except ValueError as error:
        blocked.append({'address':hex(address),'reason':str(error)});continue
    if address in defined:analyzed_base.append(hex(address))
    else:
        if address not in cached:results.append(r);instruction_total+=len(r['instruction_addresses'])
        cached[address]=r
    known.add(address)
    for target in reversed(r['ordered_calls']+r['tail_targets']):
        target=int(target,0)
        if 0x10200<=target<0xfa84d0 and target not in imports|queued:
            queued.add(target);queue.appendleft(target)
assert required_previous<=set(cached),'Prior native coverage must not shrink'
cache_temp=cache_file.with_suffix('.tmp')
cache_temp.write_text(json.dumps({'source_elf_sha256':source_digest,'functions':[cached[x] for x in sorted(cached)]},indent=2),encoding='utf-8');cache_temp.replace(cache_file)
out=project/'private/bootstrap-cfg.json'
report={'scope':__doc__,'source_elf_sha256':source_digest,'functions':[cached[x] for x in sorted(cached)],'blocked':blocked,'pending':[hex(x) for x in queue],'base_definitions':len(defined),'analyzed_base_entries':analyzed_base,'import_stubs':len(imports),'prior_coverage_preserved':required_previous<=set(cached)}
temporary=out.with_suffix('.tmp')
temporary.write_text(json.dumps(report,indent=2),encoding='utf-8');temporary.replace(out)
print(json.dumps({'total_recovered':len(cached),'new_recovered':len(results),'reachable_instruction_instances':sum(len(x['instruction_addresses']) for x in cached.values()),'blocked':blocked,'pending':len(queue),'prior_coverage_preserved':True},indent=2))
