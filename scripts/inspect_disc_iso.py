"""Index ISO9660 file extents; read the disc without extracting GT.VOL."""
from local_config import setting
import os
import json
import struct
from pathlib import Path
p=Path(__file__).resolve().parents[1]
source=Path(setting('iso'))
total=source.stat().st_size;sector=2048
def both32(data,off):
    a=struct.unpack_from('<I',data,off)[0];b=struct.unpack_from('>I',data,off+4)[0]
    if a!=b:raise ValueError('ISO endian copies differ')
    return a
def record(data):
    extent=both32(data,2)*sector;size=both32(data,10);flags=data[25]
    assert extent+size<=total
    return extent,size,flags,data[33:33+data[32]]
entries={};visited=set()
with source.open('rb') as f:
    pvd=None
    for sec in range(16,256):
        f.seek(sec*sector);block=f.read(sector)
        if block[1:6]==b'CD001' and block[0]==1:pvd=block;break
    if pvd is None:raise ValueError('ISO9660 primary volume not found')
    root=record(pvd[156:190])
    def walk(prefix,entry):
        start,size,flags,_=entry
        if start in visited:return
        visited.add(start);assert size<16*1024*1024
        f.seek(start);data=f.read(size);at=0
        while at<len(data):
            length=data[at]
            if not length:at=(at//sector+1)*sector;continue
            e=record(data[at:at+length]);at+=length
            if e[3] in (b'\0',b'\1'):continue
            path=prefix+'/'+e[3].decode('ascii').split(';')[0]
            if e[2]&2:
                entries[path]={'directory':True,'size':e[1]};walk(path,e)
            else:
                item=entries.setdefault(path,{'directory':False,'size':0,'extents':[]})
                item['extents'].append({'offset':e[0],'size':e[1]});item['size']+=e[1]
    walk('',root)
report={'source':str(source),'iso_size':total,'format':'ISO9660','entries':entries}
(p/'private/disc-index.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('Disc files/directories:',len(entries))
print('GT.VOL:',json.dumps(entries.get('/PS3_GAME/USRDIR/GT.VOL')))
