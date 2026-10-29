/* Native-only SPU dispatch. Missing compiled code is reported for the next lift. */
#include "spu_interp.h"
#include <stdio.h>
#include <stdlib.h>
uint32_t g_spu_pending_evt[3];
int g_spu_pending_evt_valid;
uint32_t g_spu_interp_last_pc;
uint64_t g_spu_interp_steps;
static void missing(spu_context* ctx,uint32_t pc) {
    fprintf(stderr,"[GT5-AOT-MISS] SPU image=%d pc=0x%05x; compile this target before continuing\n",ctx->image_id,pc);
    fflush(stderr);
    exit(86);
}
void gt5_spu_unsupported(spu_context* ctx,uint32_t pc,const char* mnemonic) {
    fprintf(stderr,"[GT5-SPU-UNSUPPORTED] %s at 0x%05x\n",mnemonic,pc);
    missing(ctx,pc);
}
uint32_t spu_interp_run_until(spu_context* ctx,uint32_t start,uint32_t stop) {
    (void)stop;missing(ctx,start);return 0;
}
uint32_t spu_interp_run(spu_context* ctx,uint32_t start) {missing(ctx,start);return 0;}
void spu_dispatch(spu_context* ctx,uint32_t target) {
    target&=0x3fffc;
    spu_lifted_fn fn=spu_lifted_lookup(ctx,target);
    if(!fn)missing(ctx,target);
    ctx->pc=target;fn(ctx);
}
void spu_trace_call(uint32_t from,uint32_t to) {(void)from;(void)to;}
void spu_trace_dump(uint32_t at) {(void)at;}
