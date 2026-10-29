// Native Vulkan RSX consumer, adapted from GT5P's vblank/FIFO scheduling.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdio>
#include <cstdlib>
#include "rsx_vulkan_backend.h"
extern "C" {
void cellGcmTickVBlank(void);
void cellGcmTickFlip(void);
void cellGcm_rsx_process_fifo(void);
int cellGcm_take_flip_pending(void);
}
static CRITICAL_SECTION drain_lock;
static HANDLE ready;
static int backend_ok=0;
static DWORD WINAPI present_thread(LPVOID) {
    backend_ok=rsx_vulkan_backend_init(1280,720,"Gran Turismo 5 - native Vulkan")==0;
    fprintf(stderr,"[GT5-VULKAN] backend=%s; waiting for game commands\n",backend_ok?"ready":"failed");
    SetEvent(ready);
    if(!backend_ok)return 1;
    ULONGLONG next=GetTickCount64();
    unsigned frames=0;bool observed_draw=false;
    for(;;){
        Sleep(4);
        EnterCriticalSection(&drain_lock);
        ULONGLONG now=GetTickCount64();
        if(now>=next){cellGcmTickVBlank();cellGcmTickFlip();next=now+16;}
        cellGcm_rsx_process_fifo();
        if(!observed_draw&&rsx_vulkan_backend_guest_draws()){
            observed_draw=true;
            fprintf(stderr,"[GT5-VULKAN] first guest draw submitted\n");
        }
        if(cellGcm_take_flip_pending()){
            rsx_vulkan_backend_present();
            if(++frames<=3)fprintf(stderr,"[GT5-VULKAN] game flip=%u guest_draws=%u\n",frames,rsx_vulkan_backend_guest_draws());
        }
        LeaveCriticalSection(&drain_lock);
        if(rsx_vulkan_backend_pump_messages()!=0)ExitProcess(0);
    }
}
extern "C" int gt5_start_present(void) {
    InitializeCriticalSection(&drain_lock);
    ready=CreateEventW(nullptr,TRUE,FALSE,nullptr);
    HANDLE worker=CreateThread(nullptr,4*1024*1024,present_thread,nullptr,0,nullptr);
    if(!ready||!worker)return 0;
    if(WaitForSingleObject(ready,15000)!=WAIT_OBJECT_0)return 0;
    CloseHandle(worker);CloseHandle(ready);
    return backend_ok;
}
