"""Inventory the frozen base and incremental native PPU batches."""
import os
import json
from pathlib import Path
project=Path(__file__).resolve().parents[1]
def batches():
    result=[]
    for folder in [project/'private/bootstrap-extras',*sorted((project/'private').glob('bootstrap-delta-*'))]:
        if not folder.is_dir():continue
        info=json.loads((folder/'summary.json').read_text())
        if not info.get('compile_complete'):raise RuntimeError('Batch not ready: '+str(folder))
        info.setdefault('table_symbol','gt5_extra_functions')
        info.setdefault('count_symbol','gt5_extra_function_count')
        result.append((folder,info))
    return result
def write_changed(path,text):
    if not path.exists() or path.read_text(encoding='utf-8')!=text:path.write_text(text,encoding='utf-8')
