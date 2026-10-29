"""Repair only non-loaded section-name metadata for an analysis copy in Ghidra."""
import os
import hashlib
import json
import struct
from pathlib import Path
p=Path(__file__).resolve().parents[1]
source=p/'private/update-2.17/EBOOT-full.ELF';original=source.read_bytes();data=bytearray(original)
phoff,shoff=struct.unpack_from('>QQ',data,32)
phsize,phnum,shsize,shnum,shstr=struct.unpack_from('>HHHHH',data,54)
assert shsize==64 and shnum and shstr<shnum
names=bytearray(b'\0')
for i in range(shnum):
    h=shoff+i*shsize
    typ,flags,addr=struct.unpack_from('>IQQ',data,h+4)
    if i==0:offset=0
    else:
        name=('.text' if flags&4 else '.bss' if typ==8 else '.opd' if addr==0x171e4b8 else '.ctors' if addr==0x16b0000 else '.shstrtab' if i==shstr else '.section')+'_'+str(i)
        offset=len(names);names+=name.encode()+b'\0'
    struct.pack_into('>I',data,h,offset)
struct.pack_into('>Q',data,shoff+shstr*shsize+24,len(data))
struct.pack_into('>Q',data,shoff+shstr*shsize+32,len(names))
data+=names
for i in range(phnum):
    h=phoff+i*phsize
    if struct.unpack_from('>I',data,h)[0]!=1:continue
    off=struct.unpack_from('>Q',data,h+8)[0];size=struct.unpack_from('>Q',data,h+32)[0]
    assert data[off:off+size]==original[off:off+size],'Analysis metadata must not alter loaded bytes'
folder=p/'private/ghidra';folder.mkdir(exist_ok=True)
dest=folder/'EBOOT-ghidra.ELF';dest.write_bytes(data)
(folder/'analysis-copy.json').write_text(json.dumps({'purpose':'Analysis only. Replaced invalid non-loaded section names. Every PT_LOAD remains byte-identical. Runtime uses the original ELF.','source_sha256':hashlib.sha256(original).hexdigest(),'analysis_sha256':hashlib.sha256(data).hexdigest()},indent=2))
print(dest)
