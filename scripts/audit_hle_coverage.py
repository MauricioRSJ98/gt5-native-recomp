"""Compare game imports with runtime definitions, without claiming semantics."""
import os
import json
import sys
from collections import Counter
from pathlib import Path

project=Path(__file__).resolve().parents[1]
toolkit=project/'third_party/ps3recomp-master'
sys.path.insert(0,str(toolkit/'tools'))
from gen_hle_nids import scan, DEF_RE

handlers={}
for category in ('system','filesystem','input','audio','video','network','spurs','sync','codec','font','misc','hardware'):
    for file in sorted((toolkit/'libs'/category).glob('*.c')):
        if not file.name.startswith(('cell','sce','sys')): continue
        text=file.read_text(encoding='latin1')
        locations={m.group(1):text.count('\n',0,m.start())+1 for m in DEF_RE.finditer(text)}
        for nid,name in scan(str(file)):
            handlers.setdefault(nid,[]).append({'name':name,'source':str(file.relative_to(toolkit)),'line':locations.get(name)})
imports=json.loads((project/'private/analysis-full-2.17/imports-named.json').read_text())
rows=[]
for entry in imports:
    nid=int(entry['nid'],0)
    rows.append({**entry,'candidate_handlers':handlers.get(nid,[])})
bylib=Counter(e['lib'] for e in rows)
missing=Counter(e['lib'] for e in rows if not e['candidate_handlers'])
summary={'scope':'Static NID-to-definition comparison only. A matching C definition can still be a stub or semantically incomplete, and an unmatched import need not be used during offline boot.','imports':len(rows),'with_candidate_handler':sum(bool(e['candidate_handlers']) for e in rows),'without_candidate_handler':sum(not e['candidate_handlers'] for e in rows),'per_library':[{'library':lib,'imports':count,'without_candidate_handler':missing[lib]} for lib,count in bylib.most_common()],'entries':rows}
(project/'private/hle-coverage.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='entries'},indent=2))
