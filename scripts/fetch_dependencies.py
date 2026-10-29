"""Fetch pinned upstream dependencies into ignored directories and patch runtime."""
import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

project=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--only',choices=['ps3recomp']);a=p.parse_args()
lock=json.loads((project/'dependencies.lock.json').read_text())
for dep in lock['dependencies']:
    if a.only and dep['name']!=a.only:continue
    dest=project/dep['destination'];marker=dest/'.gt5-dependency.json'
    if marker.exists():
        if json.loads(marker.read_text())['url']!=dep['url']:raise SystemExit('Existing dependency pin differs: '+dep['name'])
        continue
    if dest.exists() and any(dest.iterdir()):raise SystemExit('Existing dependency has no provenance marker; inspect it first: '+str(dest))
    archive=project/'research'/dep['archive'];archive.parent.mkdir(exist_ok=True)
    if not archive.exists():subprocess.run(['node',str(project/'scripts/fetch_asset.cjs'),dep['url'],str(archive),dep.get('sha256','')],check=True)
    if dep.get('sha256') and hashlib.sha256(archive.read_bytes()).hexdigest()!=dep['sha256']:raise SystemExit('Archive SHA-256 mismatch: '+dep['name'])
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            parts=Path(info.filename).parts[1:]
            if not parts or info.is_dir():continue
            target=dest.joinpath(*parts)
            if not target.resolve().is_relative_to(dest.resolve()) or (info.external_attr>>16)&0o170000==0o120000:
                raise SystemExit('Unsafe archive member')
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(info))
    if dep['name']=='ps3recomp':
        expected=json.loads((project/'patches/base-files.sha256.json').read_text())
        for name,digest in expected.items():
            base=dest/name;raw=base.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=digest:raise SystemExit('Pinned runtime base differs: '+name)
            # The upstream snapshot mixes CRLF and LF. Check exact original
            # bytes first, then use the patch's canonical LF text on all OSes.
            base.write_bytes(raw.replace(b'\r\n',b'\n'))
        for option in ('--check',None):
            cmd=['git','apply','--directory='+dep['destination']]
            if option:cmd.append(option)
            subprocess.run([*cmd,str(project/'patches/ps3recomp-gt5.patch')],cwd=project,check=True)
    marker.write_text(json.dumps({'url':dep['url'],'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},indent=2))
    print('Prepared',dep['name'])
