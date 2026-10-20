/* 143 §5 — gate behaviour harness: executes the real precapture gate code (this repo's
 * z8precapture/firmware.c, or tests/reference/firmware_v111_p1_seam.c for the before-behaviour)
 * against a mocked camera: two cards, the file services, CLOCK, FREE_E and the absolute-address
 * RAM the gates use. Vectors drive precapture_tdec_release() — the actual entry point of the
 * retention decision — through every gate path of 141 §1 and report what the firmware decided.
 *
 * Build:  cc -DPREC_CAPTURE_HOST_TEST -I <merged>/tests -I <merged>/z8precapture
 *             tests/host_gate_harness.c -o harness && ./harness
 * Variant: -DFW_SOURCE='"reference/firmware_v111_p1_seam.c"'  runs the V11.1 base behaviour.
 *
 * Output: one "VEC name keep=<0|1> ..." line per vector, then "HARNESS PASS". The keep
 * observation is derived from state both builds share (R+0x748 kept vs unbind+free); the gate
 * block fields are only meaningful in the 143 build. */
#ifndef FW_SOURCE
#define FW_SOURCE "../z8precapture/firmware.c"
#endif
#include FW_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef GATE_BLOCK                       /* the base source has no 143 observability block: the
                                          * harness still reads the same RAM, which stays zero */
#define GATE_BLOCK 0x40958040ul
#define GO_MAGIC 0x00u
#define GO_LAST 0x04u
#define GO_LATCH 0x06u
#define GO_RETAIN 0x10u
#define GO_NA 0x14u
#define GO_CFGREJ 0x18u
#define GO_DUAL 0x1Cu
#define GO_STP 0x20u
#define GO_OTHER 0x24u
#define GO_STOPW 0x28u
#define GO_DECIDE 0x2Cu
#define GO_RING 0x40u
#endif

/* ---------------------------------------------------------------- mock camera state */

static u64 fake_clock;                     /* µs, monotonic per session */
static struct { u64 base; u32 len; u8 *p; } map[8];
static int nmap;
static struct { char name[24]; u8 data[96]; u32 len; int present; } files[8];
static int nfiles;
static struct { int idx; u32 pos; } fds[8];
static int nfds, n_free_e, n_submit;

static u8 *hptr(u64 a) {
    for (int i = 0; i < nmap; i++)
        if (a >= map[i].base && a < map[i].base + map[i].len) return map[i].p + (a - map[i].base);
    if ((a >> 32) == 0xaul || (a >> 24) == 0x40ul) { fprintf(stderr, "hptr: unmapped firmware address 0x%lx\n", a); abort(); }
    return (u8 *)(size_t)a;
}
static void map_add(u64 base, void *p, u32 len) { map[nmap].base = base; map[nmap].p = p; map[nmap].len = len; nmap++; }

u8 host_load8(u64 a) { return *hptr(a); }
u16 host_load16(u64 a) { u16 v; memcpy(&v, hptr(a), 2); return v; }
u32 host_load32(u64 a) { u32 v; memcpy(&v, hptr(a), 4); return v; }
u64 host_load64(u64 a) { u64 v; memcpy(&v, hptr(a), 8); return v; }
void host_store8(u64 a, u8 v) { *hptr(a) = v; }
void host_store32(u64 a, u32 v) { memcpy(hptr(a), &v, 4); }
void host_store64(u64 a, u64 v) { memcpy(hptr(a), &v, 8); }

static int find_file(const char *p) {
    for (int i = 0; i < nfiles; i++) if (files[i].present && strcmp(files[i].name, p) == 0) return i;
    return -1;
}
int host_exists(const char *p) { return find_file(p); }
int host_open(const char *p, u32 a, u32 b) {
    (void)a; (void)b;
    int i = find_file(p);
    if (i < 0) return -1;
    fds[nfds].idx = i; fds[nfds].pos = 0;
    return nfds++;
}
int host_create(const char *p, u32 a) {
    (void)a;
    if (find_file(p) >= 0 || nfiles >= 8) return -1;
    files[nfiles].present = 1; files[nfiles].len = 0;
    snprintf(files[nfiles].name, sizeof files[nfiles].name, "%s", p);
    fds[nfds].idx = nfiles; fds[nfds].pos = 0;
    nfiles++;
    return nfds++;
}
int host_close(int fd) { (void)fd; return 0; }
int host_read(int fd, void *dst, u32 n, u32 *got) {
    if (fd < 0 || fd >= nfds) return -1;
    int i = fds[fd].idx;
    u32 avail = files[i].len - fds[fd].pos;
    u32 take = n < avail ? n : avail;
    memcpy(dst, files[i].data + fds[fd].pos, take);
    fds[fd].pos += take;
    if (got) *got = take;
    return 0;
}
int host_write(int fd, u64 src, u32 n, u32 *put) {
    if (fd < 0 || fd >= nfds) return -1;
    int i = fds[fd].idx;
    if (files[i].len + n > sizeof files[i].data) return -1;
    memcpy(files[i].data + files[i].len, (const void *)(size_t)src, n);
    files[i].len += n;
    if (put) *put = n;
    return 0;
}
int host_rename(const char *a, const char *b) { (void)a; (void)b; return -1; }
void *host_alloc(u32 a, u32 b) { (void)a; (void)b; return malloc(4096); }
void host_free(void *p) { free(p); }
void host_clean(const void *p, u32 n) { (void)p; (void)n; }
void host_clock(void *t) { memcpy(t, &fake_clock, 8); }
u64 host_submit(void *rec, u32 keep) { (void)rec; (void)keep; n_submit++; return 0; }
void host_free_e(u64 e) { (void)e; n_free_e++; }
u64 host_xlate(u64 a) { return a; }
u64 host_dcf_get(u32 a) { (void)a; return 0; }
u64 host_dcf_name(u64 a) { return a; }
void host_dcf_put(u64 a) { (void)a; }
u32 host_orig_write(u32 a, u32 b, u64 c) { (void)a; (void)b; (void)c; return 0; }
u32 host_lock(u64 a, u32 b, u32 c) { (void)a; (void)b; (void)c; return 0; }
u32 host_unlock(u64 a) { (void)a; return 0; }
u32 host_db_add(u64 a, u32 b, const void *c) { (void)a; (void)b; (void)c; return 0; }
void host_db_remain(u32 a) { (void)a; }
void host_db_cancel(u32 a) { (void)a; }
void host_rc_params(u64 a, u32 b, u32 c, u64 d, u8 *e) { (void)a; (void)b; (void)c; (void)d; (void)e; }
u64 host_y_alloc(u32 a, u64 b) { (void)a; (void)b; return 0; }
u32 host_y_size(u64 a, u64 b, u32 c) { (void)a; (void)b; (void)c; return 0; }
u32 host_capacity(u32 a, u32 b, u32 c, u32 d) { (void)a; (void)b; (void)c; (void)d; return 0; }
u32 host_desc_init(u32 a, u32 b, u64 c, u64 d) { (void)a; (void)b; (void)c; (void)d; return 0; }
u32 host_main_encode(u64 a) { (void)a; return 0; }
u32 host_job_word(u64 a) { (void)a; return 0; }
void host_ch_lock(u32 a, u32 b, u32 c, u32 d) { (void)a; (void)b; (void)c; (void)d; }
void host_ch_unlock(u32 a, u32 b, u32 c, u32 d) { (void)a; (void)b; (void)c; (void)d; }
void host_engine(u32 a, u64 b) { (void)a; (void)b; }
u32 host_is_jpeg_format(u64 a) { (void)a; return 0; }
void host_rtc7(void *dst) { static const u8 rtc[7] = {0x20, 0x26, 0x0a, 0x13, 0x0c, 0x00, 0x00}; memcpy(dst, rtc, 7); }
void host_rtc_split(const void *rtc, void *d, void *tm, void *z) { (void)rtc; (void)d; (void)tm; (void)z; }

/* ---------------------------------------------------------------- camera objects */

#define DATA_BYTES 0x01b68000u          /* the HE* slot (g_alloc(G_HES)) */
static u8 *data_buf, *block_buf;
static u8 r_obj[0x800], e_obj[0x80], m_obj[0x2600];
static u8 gate_ram[0x200];
static u8 mode_ram[32], qual_ram[16], drained_ram[8], alloc_ram[16];

static u32 rec_off(void) { return (DATA_BYTES - REC_BYTES + 63) & ~63u; }

static void reset_session(void) {
    fake_clock = 1000;
    nfiles = nfds = n_free_e = n_submit = 0;
    memset(files, 0, sizeof files);
    memset(fds, 0, sizeof fds);
    memset(gate_ram, 0, sizeof gate_ram);     /* loader re-ran: cave RAM back to image zeros */
    memset(r_obj, 0, sizeof r_obj);
    memset(e_obj, 0, sizeof e_obj);
    memset(m_obj, 0, sizeof m_obj);
    memset(qual_ram, 0, sizeof qual_ram);
    memset(drained_ram, 0, sizeof drained_ram);
    memset(alloc_ram, 0, sizeof alloc_ram);
    memset(data_buf, 0, DATA_BYTES);
    host_store32(G_MODE, 6);                   /* C15 */
    host_store32(G_LIMIT, 8);
    host_store32(G_DRAINED, 8);
    host_store32(G_QTYPE, 0); host_store32(G_QGRADE, 0); host_store32(G_QSTAR, 0);
    /* E: descriptor + data block + a full HE* slot (only the record tail is touched) */
    host_store64((u64)(size_t)(e_obj + 8), (u64)(size_t)block_buf);
    host_store64((u64)(size_t)block_buf, (u64)(size_t)data_buf);
    host_store32((u64)(size_t)(block_buf + 8), DATA_BYTES);
    host_store32((u64)(size_t)(e_obj + 0x30), 3);
    host_store32((u64)(size_t)(e_obj + 0x34), 5);
    host_store32((u64)(size_t)(e_obj + 0x38), FX_DIMS);
    host_store64((u64)(size_t)(e_obj + 0x40), ((u64)(size_t)data_buf + 511) & ~511ul);
    /* M: kind 3 + HE* (+0x2ac = 4), the stock HSFC frame shape */
    host_store32((u64)(size_t)m_obj, 3);
    host_store32((u64)(size_t)(m_obj + 0x2ac), 4);
    host_store32((u64)(size_t)(m_obj + 0x294), 3);
    host_store32((u64)(size_t)(m_obj + 0x290), 1);
    host_store32((u64)(size_t)(m_obj + 0x120), 1);        /* seq */
    host_store64((u64)(size_t)(r_obj + 0x748), (u64)(size_t)e_obj);
    host_store64((u64)(size_t)(r_obj + 0x790), (u64)(size_t)m_obj);
}

static void put_file(const char *name, const u8 *data, u32 len) {
    snprintf(files[nfiles].name, sizeof files[nfiles].name, "%s", name);
    memcpy(files[nfiles].data, data, len);
    files[nfiles].len = len;
    files[nfiles].present = 1;
    nfiles++;
}

/* 64B Z8PRE.CFG: kind 0 = none, 1 = valid, 2 = present but refused (CRC broken = ③) */
static void put_cfg(char drive, int kind, u32 flags, u32 pre) {
    u8 cfg[64];
    char name[24];
    if (!kind) return;
    snprintf(name, sizeof name, "%c:\\Z8PRE.CFG", drive);
    memset(cfg, 0, sizeof cfg);
    copy(cfg, cfg_magic, 16);
    set32(cfg + 0x10, flags);
    set32(cfg + 0x14, pre);
    set32(cfg + 0x18, 0);
    set32(cfg + 0x1c, (u32)G_HES << 8);
    set32(cfg + 0x3c, crc32(cfg, 60));
    if (kind == 2) cfg[0x3c] ^= 0xff;
    put_file(name, cfg, 64);
}

/* Z8PRESTP.BIN: kind 1 = our 32B record, 2 = 0B foreign, 3 = foreign garbage */
static void put_stop(char drive, int kind) {
    u8 raw[32];
    char name[24];
    snprintf(name, sizeof name, "%c:\\Z8PRESTP.BIN", drive);
    if (kind == 1) {
        memset(raw, 0, sizeof raw);
        copy(raw, (const u8 *)"Z8PRESTOP", 9);
        set32(raw + 16, S_WRITE_FAIL);
        set32(raw + 20, 7);
        set64(raw + 24, 500);
        put_file(name, raw, 32);
    } else if (kind == 2) {
        put_file(name, raw, 0);
    } else {
        put_file(name, (const u8 *)"NOTOURS!", 8);
    }
}

/* ---------------------------------------------------------------- vectors */

typedef struct {
    const char *name;
    int cfgA, cfgB;          /* 0 absent / 1 valid / 2 refused */
    int stopA, stopB;        /* 0 none / 1 ours / 2 empty foreign / 3 garbage foreign */
    int error_this_session;  /* run stop_file() first (sets the session latch in 143) */
    int delete_stop_after;   /* remove the stop file again (the latch keeps holding in 143) */
    int menu;                /* F_MENU configuration (menu path) */
    int current_frame;       /* 1: the record is a K_CURRENT frame (not a history frame) */
    int stale;               /* record older than FRESH_US */
    int bad_shape;           /* break the stock HSFC frame shape (menu path) */
    int jpeg_value;          /* menu value resolves to T_JPEG (nothing to keep) */
    int outside_window;      /* pre=1: not one of the last pre frames */
    int no_c30;              /* mode 3 + config without F_C30: fixed path shape gate */
    const char *note;
} vec_t;

static void run_vec(const vec_t *v, int *keep_out) {
    u32 flags = F_ENABLE | F_C30 | F_DCF;
    u32 pre = 8;
    reset_session();
    if (v->menu) flags |= F_MENU;
    if (v->no_c30) flags &= ~(u32)F_C30;
    if (v->outside_window) pre = 1;
    if (v->jpeg_value) { host_store32(G_QTYPE, 3); host_store32(G_QGRADE, 1); host_store32(G_QSTAR, 1); }
    put_cfg('A', v->cfgA, flags, pre);
    put_cfg('B', v->cfgB, flags, pre);
    if (v->stopA) put_stop('A', v->stopA);
    if (v->stopB) put_stop('B', v->stopB);
    if (v->error_this_session) stop_file('A', S_WRITE_FAIL, 7);
    if (v->delete_stop_after) { int i = find_file("A:\\Z8PRESTP.BIN"); if (i >= 0) files[i].present = 0; }
    if (v->bad_shape) host_store32((u64)(size_t)(m_obj + 0x294), 2);
    if (v->no_c30) host_store32(G_MODE, 3);
    precapture_history_entry(r_obj, 1);                    /* mark the frame (P1) */
    if (v->current_frame) {
        u8 *q = data_buf + rec_off();
        set32(q + A_KIND, K_CURRENT);                      /* mark() stamps K_HISTORY */
        set32(q + A_CRC, crc32(q + 0x80, 0x7c));
    }
    if (v->stale) fake_clock += FRESH_US + 1000;
    fake_clock += 10;
    precapture_tdec_release((u64)(size_t)r_obj);
    *keep_out = host_load64((u64)(size_t)(r_obj + 0x748)) != 0;
}

int main(void) {
    static const vec_t vecs[] = {
        {.name = "v01_retain_fixed", .cfgA = 1, .note = "valid config, history frame -> keep"},
        {.name = "v02_dual_both_valid", .cfgA = 1, .cfgB = 1, .note = "gate (1) both cards configured -> drop"},
        {.name = "v03_dual_none", .note = "gate (1) neither card configured -> drop"},
        {.name = "v04_cfg_refused", .cfgA = 2, .note = "gate (3) A refused + B absent -> drop"},
        {.name = "v05_cfg_refused_other_valid", .cfgA = 2, .cfgB = 1, .note = "gate (3) B refused, A valid -> keep"},
        {.name = "v06_stop_session_error", .cfgA = 1, .error_this_session = 1, .note = "gate (2) error this session -> drop"},
        {.name = "v07_stop_leftover_record", .cfgA = 1, .stopA = 1, .note = "gate (2) earlier session record -> 143 self-heals"},
        {.name = "v08_stop_foreign_empty", .cfgA = 1, .stopA = 2, .note = "gate (2) foreign 0B file -> drop"},
        {.name = "v09_stop_foreign_garbage", .cfgA = 1, .stopA = 3, .note = "gate (2) foreign garbage file -> drop"},
        {.name = "v10_stop_latch_file_gone", .cfgA = 1, .error_this_session = 1, .delete_stop_after = 1,
         .note = "gate (2) error this session, file removed -> 143 still stops"},
        {.name = "v11_stale_record", .cfgA = 1, .stale = 1, .note = "record older than FRESH_US -> drop"},
        {.name = "v12_bad_shape_menu", .cfgA = 1, .menu = 1, .bad_shape = 1, .note = "menu path shape gate -> drop"},
        {.name = "v13_current_frame_fixed", .cfgA = 1, .current_frame = 1, .note = "current frame in a fixed config -> n/a"},
        {.name = "v14_menu_retain", .cfgA = 1, .menu = 1, .note = "F_MENU, menu value ours -> keep"},
        {.name = "v15_menu_jpeg_only", .cfgA = 1, .menu = 1, .jpeg_value = 1, .note = "F_MENU, JPEG only -> n/a"},
        {.name = "v16_menu_stop_hold", .cfgA = 1, .menu = 1, .stopA = 1, .note = "F_MENU + leftover record -> 143 self-heals"},
        {.name = "v17_outside_window", .cfgA = 1, .outside_window = 1, .note = "seq+pre<=total -> n/a"},
        {.name = "v18_stop_on_other_card", .cfgA = 1, .stopB = 1, .note = "stop record on the non-config card -> irrelevant"},
        {.name = "v19_mode_gate_fixed", .cfgA = 1, .no_c30 = 1, .note = "fixed path mode gate -> drop"},
    };
    if (posix_memalign((void **)&data_buf, 512, DATA_BYTES) || posix_memalign((void **)&block_buf, 64, 64))
        return 2;
    memset(block_buf, 0, 64);
    map_add(GATE_BLOCK & ~0x1fful, gate_ram, sizeof gate_ram);
    map_add(0xa03bc6bacul, mode_ram, sizeof mode_ram);     /* G_LIMIT 0xa03bc6bac .. G_MODE 0xa03bc6bc8 */
    map_add(G_DRAINED, drained_ram, sizeof drained_ram);
    map_add(G_QTYPE, qual_ram, sizeof qual_ram);           /* type/grade/star in one block */
    map_add(0xa04d2ffc0ul, alloc_ram, 4);
    map_add(0xa04d2ffccul, alloc_ram + 4, 4);
    for (unsigned i = 0; i < sizeof vecs / sizeof vecs[0]; i++) {
        int keep = 0;
        run_vec(&vecs[i], &keep);
        u8 code = host_load8(GATE_BLOCK + GO_LAST), latch = host_load8(GATE_BLOCK + GO_LATCH);
        u8 why = host_load8(GATE_BLOCK + GO_RING + 2);
        u32 magic = host_load32(GATE_BLOCK + GO_MAGIC);
        u32 retain = host_load32(GATE_BLOCK + GO_RETAIN), na = host_load32(GATE_BLOCK + GO_NA);
        u32 cfgr = host_load32(GATE_BLOCK + GO_CFGREJ), dual = host_load32(GATE_BLOCK + GO_DUAL);
        u32 stp = host_load32(GATE_BLOCK + GO_STP), other = host_load32(GATE_BLOCK + GO_OTHER);
        u32 decide = host_load32(GATE_BLOCK + GO_DECIDE), stopw = host_load32(GATE_BLOCK + GO_STOPW);
        printf("VEC %-26s keep=%d magic=%08x code=%u latch=%u why=%u counts=%u/%u/%u/%u/%u/%u dec=%u stopw=%u\n",
               vecs[i].name, keep, magic, code, latch, why, retain, na, cfgr, dual, stp, other, decide, stopw);
    }
    printf("HARNESS PASS\n");
    return 0;
}
