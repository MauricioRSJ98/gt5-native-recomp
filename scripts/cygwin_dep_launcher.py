"""Translate Cygwin GCC dependency paths for native Windows Ninja caching."""
import os
import re
import subprocess
import sys
from pathlib import Path
args=sys.argv[1:]
result=subprocess.run(args)
if result.returncode==0 and '-MF' in args:
    dep=Path(args[args.index('-MF')+1])
    if dep.exists():
        text=dep.read_text()
        text=re.sub(r'/cygdrive/([a-z])/',lambda m:m[1].upper()+':/',text)
        text=text.replace('/usr/lib/','C:/cygwin/lib/').replace('/usr/','C:/cygwin/usr/')
        dep.write_text(text)
sys.exit(result.returncode)
