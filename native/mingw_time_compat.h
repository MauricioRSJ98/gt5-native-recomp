#pragma once
#include <time.h>
#include <sys/time.h>
#ifndef TIME_UTC
#define TIME_UTC 1
static inline int gt5_timespec_get(struct timespec* ts,int base) {
    struct timeval tv;
    if(base!=TIME_UTC || gettimeofday(&tv,0))return 0;
    ts->tv_sec=tv.tv_sec;ts->tv_nsec=tv.tv_usec*1000L;return base;
}
#define timespec_get gt5_timespec_get
#endif
