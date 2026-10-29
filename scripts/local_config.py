"""Resolve machine-local configuration without publishing personal paths."""
import json
import os
import shutil
from pathlib import Path

project=Path(__file__).resolve().parents[1]
defaults={'gcc':'x86_64-w64-mingw32-gcc','gxx':'x86_64-w64-mingw32-g++','cmake':'cmake','ninja':'ninja'}

def setting(name):
    path=project/'config/local.json'
    values=json.loads(path.read_text()) if path.exists() else {}
    result=os.environ.get('GT5_'+name.upper()) or values.get(name) or defaults.get(name)
    if not result:raise SystemExit(f'Missing {name}: run prepare_private_inputs.py or set GT5_{name.upper()}')
    return str(result)

def tool(name):
    value=setting(name)
    resolved=shutil.which(value)
    if resolved:return str(Path(resolved).resolve())
    path=Path(value)
    if path.is_file():return str(path.resolve())
    raise SystemExit(f'Tool not found: {name}. Configure GT5_{name.upper()} or config/local.json')
