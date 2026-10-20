/* Host behaviour-harness mocks (143 §5) — compiled only with -DPREC_CAPTURE_HOST_TEST.
 *
 * z8precapture/firmware.c is compiled unchanged for the host; every camera service it calls
 * (absolute-address function pointers) and every absolute-address memory access is redirected
 * here. Address translation (tests/host_gate_harness.c): addresses in the firmware's own
 * absolute ranges (0x40xxxxxx / 0xA0xxxxxx) map into harness-owned scratch, everything else is
 * a native pointer (the record/R/E/M objects the harness allocates). */
#ifndef Z8_PRECAPTURE_HOST_MOCK_H
#define Z8_PRECAPTURE_HOST_MOCK_H

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long u64;
typedef long s64;

u8 host_load8(u64 a);
u16 host_load16(u64 a);
u32 host_load32(u64 a);
u64 host_load64(u64 a);
void host_store8(u64 a, u8 v);
void host_store32(u64 a, u32 v);
void host_store64(u64 a, u64 v);

#define LOAD8(a) host_load8((u64)(a))
#define LOAD16(a) host_load16((u64)(a))
#define LOAD32(a) host_load32((u64)(a))
#define LOAD64(a) host_load64((u64)(a))
#define STORE8(a,v) host_store8((u64)(a),(v))
#define STORE32(a,v) host_store32((u64)(a),(v))
#define STORE64(a,v) host_store64((u64)(a),(v))

u64 host_submit(void *rec, u32 keep);
void host_free_e(u64 e);
u64 host_xlate(u64 a);
int host_open(const char *p, u32 a, u32 b);
int host_create(const char *p, u32 a);
int host_close(int fd);
int host_read(int fd, void *dst, u32 n, u32 *got);
int host_write(int fd, u64 src, u32 n, u32 *put);
int host_exists(const char *p);
int host_rename(const char *a, const char *b);
void *host_alloc(u32 a, u32 b);
void host_free(void *p);
void host_clean(const void *p, u32 n);
void host_clock(void *t);
u64 host_dcf_get(u32 a);
u64 host_dcf_name(u64 a);
void host_dcf_put(u64 a);
u32 host_orig_write(u32 a, u32 b, u64 c);
u32 host_lock(u64 a, u32 b, u32 c);
u32 host_unlock(u64 a);
u32 host_db_add(u64 a, u32 b, const void *c);
void host_db_remain(u32 a);
void host_db_cancel(u32 a);
void host_rc_params(u64 a, u32 b, u32 c, u64 d, u8 *e);
u64 host_y_alloc(u32 a, u64 b);
u32 host_y_size(u64 a, u64 b, u32 c);
u32 host_capacity(u32 a, u32 b, u32 c, u32 d);
u32 host_desc_init(u32 a, u32 b, u64 c, u64 d);
u32 host_main_encode(u64 a);
u32 host_job_word(u64 a);
void host_ch_lock(u32 a, u32 b, u32 c, u32 d);
void host_ch_unlock(u32 a, u32 b, u32 c, u32 d);
void host_engine(u32 a, u64 b);
u32 host_is_jpeg_format(u64 a);
void host_rtc7(void *dst);
void host_rtc_split(const void *rtc, void *d, void *tm, void *z);

#define SUBMIT host_submit
#define FREE_E host_free_e
#define XLATE host_xlate
#define OPEN host_open
#define CREATE host_create
#define CLOSE host_close
#define READ host_read
#define WRITE host_write
#define EXISTS host_exists
#define RENAME host_rename
#define ALLOC host_alloc
#define FREE host_free
#define CLEAN host_clean
#define CLOCK host_clock
#define DCF_GET host_dcf_get
#define DCF_NAME host_dcf_name
#define DCF_PUT host_dcf_put
#define ORIG_WRITE host_orig_write
#define LOCK host_lock
#define UNLOCK host_unlock
#define DB_ADD host_db_add
#define DB_REMAIN host_db_remain
#define DB_CANCEL host_db_cancel
#define RC_PARAMS host_rc_params
#define Y_ALLOC host_y_alloc
#define Y_SIZE host_y_size
#define CAPACITY host_capacity
#define DESC_INIT host_desc_init
#define MAIN_ENCODE host_main_encode
#define JOB_WORD host_job_word
#define CH_LOCK host_ch_lock
#define CH_UNLOCK host_ch_unlock
#define ENGINE host_engine
#define IS_JPEG_FORMAT host_is_jpeg_format
#define RTC7 host_rtc7
#define RTC_SPLIT host_rtc_split
/* data address used through LOAD32; lives with the interface macros on the firmware target */
#define G_PREVIEW_Q 0xa029e9fd0ul

#endif
