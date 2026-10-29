"""Check the public source surface without loading or executing game data."""
import argparse
import ast
import json
import re
import subprocess
from pathlib import Path

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--git-index',action='store_true');a=p.parse_args()
excluded={'.git','private','game','game-data','tools','third_party','research','build','__pycache__'}
if a.git_index:
    paths=[root/x for x in subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0') if x]
else:paths=[x for x in root.rglob('*') if x.is_file() and not any(part in excluded for part in x.relative_to(root).parts)]
if not paths:raise SystemExit('No public files found')
bad=[];python_count=0
for path in paths:
    rel=path.relative_to(root);data=path.read_bytes()
    if any(part in excluded for part in rel.parts):bad.append(str(rel)+': excluded directory')
    if path.suffix.lower() in {'.elf','.self','.iso','.pkg','.bin','.vol','.sfo','.exe','.dll','.o','.obj','.a','.lib','.dmp','.zip','.7z','.log','.pem','.key'}:
        bad.append(str(rel)+': non-public artifact type')
    if len(data)>2*1024*1024 or b'\0' in data or data.startswith((b'\x7fELF',b'MZ',b'SCE\0')):bad.append(str(rel)+': binary/large artifact')
    for pattern in (rb'gh[pousr]_[A-Za-z0-9]{30,}',rb'github_pat_[A-Za-z0-9_]{40,}',rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'):
        if re.search(pattern,data):bad.append(str(rel)+': potential credential material')
    if re.search(rb'[A-Za-z]:[\\/]+Users[\\/]+(?:Administrator|ADMINI~1)',data,re.I):bad.append(str(rel)+': maintainer-local user path')
    if path.suffix=='.py':ast.parse(data,filename=str(rel));python_count+=1
    if path.suffix=='.json':json.loads(data)
for required in ('README.md','LICENSE','CONTRIBUTING.md','THIRD_PARTY_NOTICES.md','docs/BUILDING.md','docs/STATUS.md','docs/CREDITS.md'):
    if not (root/required).is_file():bad.append('Missing '+required)
if bad:raise SystemExit('\n'.join(bad))
print(f'Public source checks passed: {len(paths)} files; {python_count} Python sources; no game execution.')
