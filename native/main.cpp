// GT5 BCUS98114 2.17 AOT bring-up with Vulkan command consumption/presentation.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "ps3emu/module.h"
#include "ps3emu/guest_call.h"
#include "ppu_context.h"
#include "vm.h"
#include "elf_loader.h"
#include "lv2_syscall_table.h"
uint8_t* vm_base=nullptr;
ps3_module_registry g_ps3_module_registry={};
extern "C" {
int gt5_start_present(void);
int gt5_disc_fs_call(ppu_context*,uint32_t);
void gt5_register_extra_batches(void);
extern const uint64_t gt5_extra_entry_count;
extern uint32_t g_ppu_main_stack_addr,g_ppu_main_stack_size;
extern ppu_context* volatile g_ppu_main_ctx;
uint64_t ppu_guest_call(uint32_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t);
const unsigned char* g_spu_coh_bits=nullptr;
typedef struct {uint64_t addr;void (*func)(ppu_context*);const char* name;} func_entry;
extern const func_entry function_table[],gt5_extra_functions[],gt5_import_functions[];
extern const uint64_t function_table_count,gt5_extra_function_count,gt5_import_function_count;
extern uint32_t ppu_hle_inject_base;
extern PPU_THREAD_LOCAL void (*g_trampoline_fn)(void*);
extern PPU_THREAD_LOCAL ppu_context* g_active_ctx;
void ppu_register_function(uint64_t,void (*)(ppu_context*));
void ppu_install_thread_trampoline(void);
void ppu_hle_register_all(void);
void ppu_sysprx_register(void);
void cellfs_set_root_path(const char*);
void cellfs_add_path_mapping(const char*,const char*);
void cellGame_init_from_paramsfo(const char*);
uint64_t ppu_thread_register_main(void);
void ps3_hle_call(uint32_t,ppu_context*);
void vm_write64(uint64_t,uint64_t);
void vm_write32(uint64_t,uint32_t);
void spu_register_all(void);
void gt5_register_captured_spu(void);
}
[[noreturn]] void gt5_missing_native(ppu_context* c,uint64_t target) {
    static volatile LONG stopping=0;
    static SRWLOCK lock=SRWLOCK_INIT;
    const bool first=InterlockedCompareExchange(&stopping,1,0)==0;
    char record[256];int length=snprintf(record,sizeof(record),"{\"target\":\"0x%llx\",\"lr\":\"0x%llx\",\"thread\":%llu,\"stack\":\"0x%llx\"}\n",(unsigned long long)target,(unsigned long long)c->lr,(unsigned long long)c->thread_id,(unsigned long long)c->gpr[1]);
    AcquireSRWLockExclusive(&lock);
    HANDLE all=CreateFileW(L"private/native-stops.jsonl",FILE_APPEND_DATA,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(all!=INVALID_HANDLE_VALUE){DWORD written;WriteFile(all,record,DWORD(length),&written,nullptr);CloseHandle(all);}
    if(first){
        HANDLE file=CreateFileW(L"private/native-stop.json",GENERIC_WRITE,FILE_SHARE_READ,nullptr,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
        if(file!=INVALID_HANDLE_VALUE){DWORD written;WriteFile(file,record,DWORD(length),&written,nullptr);CloseHandle(file);}
    }
    ReleaseSRWLockExclusive(&lock);
    fprintf(stderr,"[GT5-AOT-MISS] PPU target=0x%08llx lr=0x%08llx sp=0x%08llx\n",
        (unsigned long long)target,(unsigned long long)c->lr,(unsigned long long)c->gpr[1]);
    fflush(stderr);
    if(first){Sleep(20);ExitProcess(87);}
    Sleep(INFINITE);ExitProcess(87);
}
extern "C" void gt5_codegen_gap(ppu_context* c,uint64_t pc,uint32_t word) {
    fprintf(stderr,"[GT5-CODEGEN] pc=0x%08llx instruction=0x%08x\n",(unsigned long long)pc,word);
    gt5_missing_native(c,pc);
}
void gt5_import_call(ppu_context* c,uint32_t nid) {
    const auto toc=c->gpr[2],sp=c->gpr[1];
    if(gt5_disc_fs_call(c,nid)){c->gpr[2]=toc;vm_write64(sp+0x28,toc);}
    else ps3_hle_call(nid,c);
}
static void guest_callback(uint32_t opd,uint64_t a,uint64_t b,uint64_t c,uint64_t d,uint64_t e,uint64_t f,uint64_t g,uint64_t h) {
    ppu_guest_call(opd,a,b,c,d,e,f,g,h);
}
static LONG WINAPI report_fault(EXCEPTION_POINTERS* p) {
    char data[1800];int n=snprintf(data,sizeof(data),"{\"exception\":\"0x%lx\",\"host_rva\":\"0x%llx\",\"address\":\"0x%llx\",\"access\":%llu,\"lr\":\"0x%llx\",\"thread\":%llu,\"gpr\":[",p->ExceptionRecord->ExceptionCode,(unsigned long long)((uintptr_t)p->ExceptionRecord->ExceptionAddress-(uintptr_t)GetModuleHandleW(nullptr)),(unsigned long long)(p->ExceptionRecord->NumberParameters>1?p->ExceptionRecord->ExceptionInformation[1]:0),(unsigned long long)(p->ExceptionRecord->NumberParameters?p->ExceptionRecord->ExceptionInformation[0]:0),(unsigned long long)(g_active_ctx?g_active_ctx->lr:0),(unsigned long long)(g_active_ctx?g_active_ctx->thread_id:0));
    for(int i=0;i<32;++i)n+=snprintf(data+n,sizeof(data)-n,"%s\"0x%llx\"",i?",":"",(unsigned long long)(g_active_ctx?g_active_ctx->gpr[i]:0));
    n+=snprintf(data+n,sizeof(data)-n,"]}\n");
    HANDLE file=CreateFileW(L"private/native-fault.json",GENERIC_WRITE,FILE_SHARE_READ,nullptr,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(file!=INVALID_HANDLE_VALUE){DWORD written;WriteFile(file,data,DWORD(n),&written,nullptr);CloseHandle(file);}
    fprintf(stderr,"[GT5-NATIVE-FAULT] exception=0x%08lx host_rva=0x%llx guest_lr=0x%llx\n",
        p->ExceptionRecord->ExceptionCode,
        (unsigned long long)((uintptr_t)p->ExceptionRecord->ExceptionAddress-(uintptr_t)GetModuleHandleW(nullptr)),
        (unsigned long long)(g_active_ctx?g_active_ctx->lr:0));
    return EXCEPTION_EXECUTE_HANDLER;
}
int main(int argc,char** argv) {
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX|SEM_NOOPENFILEERRORBOX);
    SetUnhandledExceptionFilter(report_fault);
    setvbuf(stdout,nullptr,_IONBF,0);setvbuf(stderr,nullptr,_IONBF,0);
    if(argc!=2){fprintf(stderr,"Usage: gt5-native.exe EBOOT-full.ELF\n");return 64;}
    // This runtime uses CPU AOT only. Unknown SPU targets stop for recompilation.
    _putenv_s("PS3_HEADLESS","1");_putenv_s("PS3_VERBOSE","0");
    _putenv_s("PS3_HDD0_ROOT","game-data/dev_hdd0");_putenv_s("PS3_HDD1_ROOT","game-data/dev_hdd1");
    ppu_hle_inject_base=0x03000000;
    if(vm_init())return 65;
    vm_commit(0x03000000,0x10000);vm_commit(0xc0000000,0x10000000);
    lv2_register_all_syscalls(&g_lv2_syscalls);
    ElfLoadResult elf=load_elf_into_vm(argv[1]);if(!elf.success)return 66;
    ppu_hle_register_all();ppu_sysprx_register();
    cellGame_init_from_paramsfo("private/source-data/PARAM.SFO");
    cellfs_set_root_path(".");
    cellfs_add_path_mapping("/dev_hdd0/","game-data/dev_hdd0/");
    cellfs_add_path_mapping("/dev_bdvd/","disc/");
    cellfs_add_path_mapping("/app_home/","disc/PS3_GAME/USRDIR/");
    auto reg=[](const func_entry* table,uint64_t count){for(uint64_t i=0;i<count;++i)ppu_register_function(table[i].addr,table[i].func);};
    fprintf(stderr,"[GT5-INIT] registering PPU entries\n");
    reg(function_table,function_table_count);gt5_register_extra_batches();
    reg(gt5_import_functions,gt5_import_function_count);ppu_install_thread_trampoline();
    fprintf(stderr,"[GT5-INIT] registering captured SPU entries\n");
    gt5_register_captured_spu();
    fprintf(stderr,"[GT5-INIT] native registries ready\n");
    ppu_context ctx{};ctx.thread_id=ppu_thread_register_main();
    ctx.gpr[1]=0x0dfff000;ctx.gpr[2]=elf.toc;
    ctx.gpr[3]=1;ctx.gpr[4]=0x0dfe0000;ctx.gpr[5]=0x0dfe0010;
    ctx.gpr[7]=ctx.thread_id;ctx.gpr[8]=elf.tls_vaddr;ctx.gpr[9]=elf.tls_filesz;ctx.gpr[10]=elf.tls_memsz;ctx.gpr[12]=0x100000;
    const char name[]="/dev_bdvd/PS3_GAME/USRDIR/EBOOT.BIN";
    memcpy(vm_base+0x0dfe0100,name,sizeof(name));vm_write64(0x0dfe0000,0x0dfe0100);
    vm_write64(ctx.gpr[1],0);ctx.cia=elf.func_addr;g_active_ctx=&ctx;
    g_ppu_main_ctx=&ctx;g_ppu_main_stack_addr=0x0df00000;g_ppu_main_stack_size=0x100000;
    g_ps3_guest_caller=guest_callback;
#ifdef GT5_VULKAN
    if(!gt5_start_present()){fprintf(stderr,"[GT5] Vulkan initialization failed\n");return 68;}
#endif
    fprintf(stderr,"[GT5] Native boot entry=0x%08llx PPU=%llu SPU=embedded + captured\n",
        (unsigned long long)elf.func_addr,(unsigned long long)(function_table_count+gt5_extra_entry_count));
    for(uint64_t i=0;i<function_table_count;++i)if(function_table[i].addr==elf.func_addr){
        function_table[i].func(&ctx);
        while(g_trampoline_fn){auto next=g_trampoline_fn;g_trampoline_fn=nullptr;next(&ctx);}
        fprintf(stderr,"[GT5] Entry returned r3=0x%llx\n",(unsigned long long)ctx.gpr[3]);return 0;
    }
    return 67;
}
