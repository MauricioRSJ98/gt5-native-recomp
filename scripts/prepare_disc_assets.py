"""Generate a small read-only disc index; do not extract the 12 GB volume."""
from local_config import setting
import os
import json
import shutil
from pathlib import Path
from native_inputs import project,write_changed
index=json.loads((project/'private/disc-index.json').read_text())
assert Path(index['source']).stat().st_size==index['iso_size']
entries={'/':{'directory':True,'size':0},**index['entries']}
parts=['#pragma once\nstruct DiscSpan {uint64_t offset,size;};\nstruct DiscEntry {const char* path;uint64_t size;unsigned first,count;bool directory;};\n']
parts.append('static const wchar_t* disc_source=L'+json.dumps(index['source'])+';\n')
spans=[];records=[]
for path,entry in sorted(entries.items()):
    first=len(spans)
    for span in entry.get('extents',[]):
        assert span['offset']+span['size']<=index['iso_size']
        spans.append(span)
    records.append('{'+json.dumps(path)+','+str(entry['size'])+'ULL,'+str(first)+','+str(len(spans)-first)+','+str(entry['directory']).lower()+'},\n')
parts.append('static const DiscSpan disc_spans[]={\n'+''.join('{'+str(s['offset'])+'ULL,'+str(s['size'])+'ULL},\n' for s in spans)+'};\n')
parts.append('static const DiscEntry disc_entries[]={\n'+''.join(records)+'};\n')
names={i.get('name'):i['nid'] for i in json.loads((project/'private/analysis-full-2.17/imports-named.json').read_text())}
for name in ('cellFsOpen','cellFsRead','cellFsClose','cellFsLseek','cellFsStat','cellFsFstat','cellFsGetBlockSize','cellFsFGetBlockSize','cellFsAioRead'):
    parts.append('static constexpr uint32_t nid_'+name+'='+str(names.get(name,'0'))+'u;\n')
write_changed(project/'private/disc_index.h',''.join(parts))
data=project/'private/source-data';data.mkdir(exist_ok=True)
source=Path(setting('update_root'))/'PARAM.SFO'
if not (data/'PARAM.SFO').exists():shutil.copyfile(source,data/'PARAM.SFO')
for folder in ('game-data/dev_hdd0','game-data/dev_hdd1'):(project/folder).mkdir(parents=True,exist_ok=True)
print('Prepared read-only disc index:',len(entries),'entries')
