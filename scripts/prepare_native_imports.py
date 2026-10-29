"""Generate import/missing-target wrappers and register every compiled batch."""
import os
import json
import re
from native_inputs import project,batches,write_changed
base=project/'private/ppu-aot-256-r2'
info=json.loads((base/'summary.json').read_text())
defined=set()
for cpp in base.glob('ppu_recomp_*.cpp'):
    defined|={int(x,16) for x in re.findall(r'^void func_([0-9A-F]+)\(ppu_context\* ctx\) \{',cpp.read_text(),re.M)}
targets={int(x,0) for x in info['external_native_targets']}
extra=batches()
for folder,batch in extra:
    defined|={int(x,0) for x in batch['defined']}
    targets|={int(x,0) for x in batch['external_native_targets']}
imports={int(i['stub'],0):i for i in json.loads((project/'private/analysis-full-2.17/imports-named.json').read_text())}
parts=['#include "ppu_recomp.h"\n[[noreturn]] void gt5_missing_native(ppu_context*,uint64_t);\nvoid gt5_import_call(ppu_context*,uint32_t);\n']
for address in sorted((targets-defined)|set(imports)):
    body=f'gt5_import_call(c,{imports[address]["nid"]}u);' if address in imports else f'gt5_missing_native(c,0x{address:X}ULL);'
    parts.append(f'void func_{address:08X}(ppu_context* c) {{ {body} }}\n')
parts.append('extern "C" const func_entry gt5_import_functions[] = {\n')
for address,entry in sorted(imports.items()):parts.append(f'{{0x{address:X}ULL,func_{address:08X},"{entry.get("name",entry["lib"])}"}},\n')
parts.append('};\nextern "C" const uint64_t gt5_import_function_count = '+str(len(imports))+';\n')
write_changed(project/'private/native-boot-probe/unlifted_targets.cpp',''.join(parts))
reg=['#include "ppu_recomp.h"\nextern "C" void ppu_register_function(uint64_t,void (*)(ppu_context*));\n']
for folder,batch in extra:
    reg.append('extern "C" { extern const func_entry '+batch['table_symbol']+'[]; extern const uint64_t '+batch['count_symbol']+'; }\n')
reg.append('extern "C" const uint64_t gt5_extra_entry_count = '+str(sum(len(b['defined']) for _,b in extra))+';\n')
reg.append('extern "C" void gt5_register_extra_batches(void) {\n')
for folder,batch in extra:
    table=batch['table_symbol'];count=batch['count_symbol']
    reg.append(f'for(uint64_t i=0;i<{count};++i)ppu_register_function({table}[i].addr,{table}[i].func);\n')
reg.append('}\n')
write_changed(project/'private/native-batch-registry.cpp',''.join(reg))
print('Prepared',len(extra),'native batches and',len(imports),'imports')
