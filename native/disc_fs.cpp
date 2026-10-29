// Read-only ISO-backed files and installed-update reads. Original files stay untouched.
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <map>
#include <mutex>
#include <filesystem>
#include "ppu_context.h"
#include "ps3emu/guest_call.h"
#include "disc_index.h"
extern "C" {extern uint8_t* vm_base;void vm_write32(uint64_t,uint32_t);void vm_write64(uint64_t,uint64_t);uint32_t vm_read32(uint64_t);uint64_t vm_read64(uint64_t);}
static constexpr int32_t enoent=int32_t(0x80010006),eio=int32_t(0x8001002b),eperm=int32_t(0x80010009);
static constexpr unsigned fd_base=20000;
struct File {FILE* stream;const DiscEntry* entry;uint64_t size,pos;};
static std::map<unsigned,File> files;
static unsigned next_fd=fd_base;
static std::recursive_mutex fs_lock;
static std::string guest_string(uint32_t a) {std::string s;for(unsigned i=0;i<1024&&vm_base[a+i];++i)s+=char(vm_base[a+i]);return s;}
static const DiscEntry* find_disc(std::string path) {
    if(path=="/dev_bdvd")path="/";
    else if(path.rfind("/dev_bdvd/",0)==0)path=path.substr(9);
    else if(path.rfind("/app_home/",0)==0)path="/PS3_GAME/USRDIR/"+path.substr(10);
    else return nullptr;
    for(const auto& e:disc_entries)if(_stricmp(path.c_str(),e.path)==0)return &e;
    return nullptr;
}
static bool is_disc(const std::string& p){return p=="/dev_bdvd"||p.rfind("/dev_bdvd/",0)==0||p.rfind("/app_home/",0)==0;}
static void result(ppu_context* c,int32_t value){c->gpr[3]=uint64_t(int64_t(value));}
static void stat_out(uint32_t a,uint64_t size,bool dir) {
    if(!a)return;
    memset(vm_base+a,0,52);vm_write32(a,(dir?0x4000u:0x8000u)|0555u);
    vm_write64(a+0x24,size);vm_write64(a+0x2c,2048);
}
static std::filesystem::path update_path(const std::string& guest) {
    const std::string prefix="/dev_hdd0/game/BCUS98114/";
    std::string rel;
    if(guest.rfind(prefix,0)==0)rel=guest.substr(prefix.size());
    else if(guest.rfind("PDIPFS/",0)==0)rel="USRDIR/"+guest;
    else return {};
    if(rel.find("..")!=std::string::npos)return {};
    auto overlay=std::filesystem::path("game-data/dev_hdd0/game/BCUS98114")/rel;
    std::error_code ec;if(std::filesystem::exists(overlay,ec))return overlay;
    const char* root=getenv("GT5_UPDATE_ROOT");
    return std::filesystem::path(root&&*root?root:"game-data/update-source")/rel;
}
extern "C" int gt5_disc_fs_call(ppu_context* c,uint32_t nid) {
    if(nid!=nid_cellFsOpen&&nid!=nid_cellFsRead&&nid!=nid_cellFsClose&&nid!=nid_cellFsLseek&&nid!=nid_cellFsStat&&nid!=nid_cellFsFstat&&nid!=nid_cellFsGetBlockSize&&nid!=nid_cellFsFGetBlockSize&&nid!=nid_cellFsAioRead)return 0;
    std::unique_lock<std::recursive_mutex> guard(fs_lock);
    if(nid==nid_cellFsAioRead){
        uint32_t aio=uint32_t(c->gpr[3]),out_id=uint32_t(c->gpr[4]),callback=uint32_t(c->gpr[5]);
        unsigned fd=vm_read32(aio);auto found=files.find(fd);if(found==files.end())return 0;
        uint64_t offset=vm_read64(aio+8),saved=found->second.pos;
        ppu_context read=*c;read.gpr[3]=fd;read.gpr[4]=vm_read32(aio+16);read.gpr[5]=vm_read64(aio+24);read.gpr[6]=0;
        found->second.pos=offset;gt5_disc_fs_call(&read,nid_cellFsRead);
        uint64_t count=found->second.pos-offset;found->second.pos=saved;
        static uint32_t next_id=1;uint32_t id=next_id++;if(out_id)vm_write32(out_id,id);
        result(c,0);guard.unlock();
        if(callback)ps3_invoke_guest(callback,aio,read.gpr[3],id,count,0,0,0,0);
        return 1;
    }
    unsigned fd=unsigned(c->gpr[3]);auto found=files.find(fd);
    if(nid==nid_cellFsOpen||nid==nid_cellFsStat||nid==nid_cellFsGetBlockSize){
        std::string path=guest_string(uint32_t(c->gpr[3]));
        const DiscEntry* entry=find_disc(path);auto update=update_path(path);
        if(!is_disc(path)&&update.empty())return 0;
        if(nid==nid_cellFsGetBlockSize){vm_write64(c->gpr[4],512);vm_write64(c->gpr[5],2048);result(c,0);return 1;}
        std::error_code ec;bool directory=entry?entry->directory:(!update.empty()&&std::filesystem::is_directory(update,ec));
        uint64_t size=entry?entry->size:(!update.empty()&&!directory?std::filesystem::file_size(update,ec):0);
        if((!entry&&update.empty())||ec){result(c,enoent);return 1;}
        if(nid==nid_cellFsStat){stat_out(c->gpr[4],size,directory);result(c,0);return 1;}
        if(directory){result(c,int32_t(0x80010012));return 1;}
        if(c->gpr[4]!=0){if(!entry)return 0;result(c,eperm);return 1;}
        FILE* stream=entry?_wfopen(disc_source,L"rb"):_wfopen(update.c_str(),L"rb");
        if(!stream){result(c,enoent);return 1;}
        unsigned allocated=next_fd++;
        files.emplace(allocated,File{stream,entry,size,0});vm_write32(c->gpr[5],allocated);result(c,0);
        fprintf(stderr,"[GT5-FS] read-only open %s fd=%u bytes=%llu\n",path.c_str(),allocated,(unsigned long long)size);return 1;
    }
    if(found==files.end())return 0;
    auto& f=found->second;
    if(nid==nid_cellFsClose){fclose(f.stream);files.erase(found);result(c,0);return 1;}
    if(nid==nid_cellFsFstat){stat_out(c->gpr[4],f.size,false);result(c,0);return 1;}
    if(nid==nid_cellFsFGetBlockSize){vm_write64(c->gpr[4],512);vm_write64(c->gpr[5],2048);result(c,0);return 1;}
    if(nid==nid_cellFsLseek){
        int64_t off=int64_t(c->gpr[4]);unsigned wh=unsigned(c->gpr[5]);
        int64_t base=wh==2?int64_t(f.size):wh==1?int64_t(f.pos):0;
        if(wh>2||off < -base){result(c,int32_t(0x80010002));return 1;}
        f.pos=uint64_t(base+off);if(c->gpr[6])vm_write64(c->gpr[6],f.pos);result(c,0);return 1;
    }
    if(nid==nid_cellFsRead){
        const uint64_t initial_pos=f.pos;
        uint64_t wanted=c->gpr[5],done=0;uint32_t dest=uint32_t(c->gpr[4]);
        if(wanted>0x100000000ULL-dest||(!dest&&wanted)){result(c,eio);return 1;}
        uint64_t available=f.pos<f.size?f.size-f.pos:0;if(wanted>available)wanted=available;
        while(done<wanted){
            uint64_t source_offset=f.pos,take=wanted-done;
            if(f.entry){
                uint64_t relative=f.pos;bool located=false;
                for(unsigned i=0;i<f.entry->count;++i){const auto& span=disc_spans[f.entry->first+i];
                    if(relative<span.size){source_offset=span.offset+relative;if(take>span.size-relative)take=span.size-relative;located=true;break;}
                    relative-=span.size;
                }
                if(!located){result(c,eio);return 1;}
            }
            if(_fseeki64(f.stream,int64_t(source_offset),SEEK_SET)){result(c,eio);return 1;}
            size_t count=fread(vm_base+dest+done,1,size_t(take),f.stream);
            done+=count;f.pos+=count;if(count<take)break;
        }
        static unsigned logged=0;
        if(logged++<12)fprintf(stderr,"[GT5-FS] read fd=%u offset=%llu bytes=%llu\n",fd,(unsigned long long)initial_pos,(unsigned long long)done);
        if(c->gpr[6])vm_write64(c->gpr[6],done);result(c,0);return 1;
    }
    return 0;
}
