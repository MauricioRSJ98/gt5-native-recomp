"""Use Ghidra's CPython API for targeted boot analysis, without a full scan."""
import json
import os
import sys
import argparse
from pathlib import Path
p=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('addresses',nargs='*');parser.add_argument('--out',default='boot-decompile.txt');args=parser.parse_args()
assert Path(args.out).name==args.out
os.environ['JAVA_HOME_OVERRIDE']=os.environ.get('JAVA_HOME_OVERRIDE',os.environ.get('JAVA_HOME',''))
os.environ.setdefault('GHIDRA_INSTALL_DIR',str(p/'tools/ghidra_12.2_PUBLIC'))
sys.path=[x for x in sys.path if Path(x).resolve()!=Path(__file__).resolve().parent]
import pyghidra
from pyghidra.launcher import HeadlessPyGhidraLauncher
launcher=HeadlessPyGhidraLauncher(install_dir=Path(os.environ['GHIDRA_INSTALL_DIR']))
launcher.vm_args+=['-Xmx2G','-Dapplication.settingsdir='+str(p/'tools/ghidra-settings'),'-Dapplication.cachedir='+str(p/'tools/ghidra-cache'),'-Djava.io.tmpdir='+str(p/'tools/ghidra-temp')]
launcher.start()
from ghidra.program.flatapi import FlatProgramAPI
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import TaskMonitor
from java.math import BigInteger
from ghidra.program.model.symbol import SourceType
from ghidra.program.model.address import AddressSet
targets=[int(x,16) for x in args.addresses] if args.addresses else [0x10230,0xbd8164,0xbf1fa4,0x3729f0,0xf6a374]
with pyghidra.open_project(p/'private/ghidra','GT5_BCUS98114_217') as project:
    with pyghidra.program_context(project,'/EBOOT-ghidra.ELF') as program:
        api=FlatProgramAPI(program);tx=program.startTransaction('GT5 targeted boot functions')
        try:
            r2=program.getRegister('r2')
            program.getProgramContext().setValue(r2,api.toAddr(0x10200),api.toAddr(0xfa84cf),BigInteger.valueOf(0x17727e0))
            for address in targets:
                start=api.toAddr(address)
                if not api.getFunctionAt(start):
                    api.disassemble(start)
                    api.createFunction(start,'gt5_'+hex(address)[2:])
        finally:program.endTransaction(tx,True)
        decompiler=DecompInterface();decompiler.openProgram(program)
        with (p/'private/ghidra'/args.out).open('w',encoding='utf-8') as out:
            out.write('Ghidra '+str(program.getLanguageID())+'\n')
            for address in targets:
                f=api.getFunctionAt(api.toAddr(address))
                out.write('\n/* '+hex(address)+' */\n')
                if f is None:out.write('Function unavailable\n');continue
                result=decompiler.decompileFunction(f,20,TaskMonitor.DUMMY)
                out.write(str(result.getDecompiledFunction().getC()) if result.decompileCompleted() else str(result.getErrorMessage()))
                out.flush()
        decompiler.dispose()
print('Ghidra decompilation:',p/'private/ghidra'/args.out,flush=True)
