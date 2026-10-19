/* OpenGate (3:2 full-frame) experimental recording option for the N-RAW / ProRes RAW
 * record path. Controlled by Z8OG.CFG on the card (magic "Z8OGCFGv1"); when the file is
 * absent or invalid every hook falls through to the exact stock values, so the camera
 * behaves byte-for-byte like the unpatched build (fail-safe / fully reversible).
 *
 * Patch surface (see 110_OPENGATE_IMPL.md §A):
 *   og_case_*   : RAW record size switch, eg 0x573120/0x573134/0x573140/0x57314c
 *                 (4 cases: 3840x2160 / 4128x2322 / 5392x3032 / 8256x4644 -> 3:2 twins)
 *   og_pad_*    : encoder-input padded size switch, eg 0xb9af64/0xb9af88/0xb9af9c/0xb9afb0
 *   og_rate_row : bitrate-table row redirect at eg 0x40D1E650 (madd) for type1/type2 rows.
 * Experimental tiers: all of them (60/50/30/25/24p and the 120/100p slots); nothing is
 * silently limited - the sensor readout question is a field test, not a firmware gate.
 * Resume branches use x16 (IP0, AAPCS volatile scratch): the stubs enter with b and the
 * interrupted functions keep their own link register in x30 (saved/restored here).
 */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long u64;

#define LOAD32(a) (*(volatile const u32 *)(u64)(a))

#define OPEN ((int (*)(const char *, u32, u32))0x402daa4cul)
#define CLOSE ((int (*)(int))0x402daaacul)
#define READ ((int (*)(int, void *, u32, u32 *))0x402dab4cul)

#define TYPE1_BASE 0x42ab3b28ul   /* ProRes RAW HQ rate table */
#define TYPE2_BASE 0x42ab3c90ul   /* N-RAW (NEV) rate table, 21 HQ + 21 Normal rows */

static const u8 og_magic[16] = "Z8OGCFGv1";

#include "og_rows.inc"

static void zero(u8 *d, u32 n) { while (n--) *d++ = 0; }
static int equal(const u8 *a, const u8 *b, u32 n) {
    u32 x = 0; while (n--) x |= *a++ ^ *b++; return x == 0;
}
static u32 get32(const u8 *p) {
    return (u32)p[0] | (u32)p[1] << 8 | (u32)p[2] << 16 | (u32)p[3] << 24;
}
static u32 crc32(const u8 *p, u32 n) {          /* bitwise, IEEE; same polynomial as Z8PRE.CFG */
    u32 c = 0xffffffffu;
    while (n--) {
        c ^= *p++;
        for (u32 i = 0; i < 8; i++) c = (c >> 1) ^ (0xedb88320u & (0u - (c & 1u)));
    }
    return c ^ 0xffffffffu;
}

/* Z8OG.CFG: [0..15] "Z8OGCFGv1", [16] flags (bit0 = OpenGate on), [20..59] zero,
 * [60] CRC32 over [0..59]. Absent/invalid file -> 0 (stock behaviour). */
__attribute__((noinline)) static int og_cfg_ok(const u8 *raw) {
    if (!equal(raw, og_magic, 16)) return 0;
    for (u32 i = 0x14; i < 0x3c; i++) if (raw[i]) return 0;
    return get32(raw + 0x3c) == crc32(raw, 60);
}
__attribute__((noinline)) static int og_read_flag(void) {
    for (u32 drive = 0; drive < 2; drive++) {
        char path[16] = "A:\\Z8OG.CFG";
        u8 raw[64] __attribute__((aligned(64)));
        u32 count = 0;
        int fd, rc, cl, on = 0;
        path[0] = (char)('A' + drive);
        fd = OPEN(path, 0, 0x20);
        if (fd < 0) continue;
        zero(raw, 64);
        rc = READ(fd, raw, 64, &count);
        cl = CLOSE(fd);
        if (rc == 0 && cl == 0 && count == 64 && og_cfg_ok(raw)) on = (get32(raw + 0x10) & 1u) != 0;
        if (on) return 1;
    }
    return 0;
}

/* packed (H<<16)|W -> OpenGate 3:2 twin, or the input unchanged when the option is off. */
__attribute__((used)) u32 og_size_pick(u32 stock) {
    u32 og = stock;
    if (!og_read_flag()) return stock;
    switch (stock) {
    case 0x08700f00u: og = 0x0a000f00u; break;  /* 3840x2160  -> 3840x2560 */
    case 0x09121020u: og = 0x0ac01020u; break;  /* 4128x2322  -> 4128x2752 */
    case 0x0bd81510u: og = 0x0e081510u; break;  /* 5392x3032  -> 5392x3592 */
    case 0x12242040u: og = 0x15802040u; break;  /* 8256x4644  -> 8256x5504 */
    case 0x08780f0cu: og = 0x0a080f0cu; break;  /* 3852x2168  -> 3852x2568 (padded) */
    case 0x091a102cu: og = 0x0ac8102cu; break;  /* 4140x2330  -> 4140x2760 (padded) */
    case 0x0be0151cu: og = 0x0e10151cu; break;  /* 5404x3040  -> 5404x3600 (padded) */
    case 0x122c204cu: og = 0x1588204cu; break;  /* 8268x4652  -> 8268x5512 (padded) */
    }
    return og;
}

/* Bitrate-table row pointer: stock row unless the OpenGate rows apply.
 * v2 (110 §E): dispatch table so the upstream ProRes four-tier tables (type0 copies,
 * addresses only known after the prores build) can register their own OG rows. */
#include "og_dispatch.inc"
__attribute__((used)) const u32 *og_rate_pick(u64 base, u64 row, u64 stride) {
    if (og_read_flag()) {
        for (u32 i = 0; i < (u32)(sizeof og_rate_map / sizeof og_rate_map[0]); i++) {
            if (base == og_rate_map[i].base && row < og_rate_map[i].count)
                return og_rate_map[i].rows + row * 6;
        }
    }
    return (const u32 *)(base + row * stride);
}

/* ---- patch stubs (entered by b; x30 = the interrupted function's link register) ---- */
__asm__(
".global og_case_23x\n"
"og_case_23x:\n"
"   stp x29, x30, [sp, #-16]!\n"
"   mov x29, sp\n"
"   mov w0, #0x0f00\n"
"   movk w0, #0x0870, lsl #16\n"
"   b og_case_common\n"
".global og_case_41k\n"
"og_case_41k:\n"
"   stp x29, x30, [sp, #-16]!\n"
"   mov x29, sp\n"
"   mov w0, #0x1020\n"
"   movk w0, #0x0912, lsl #16\n"
"   b og_case_common\n"
".global og_case_dx\n"
"og_case_dx:\n"
"   stp x29, x30, [sp, #-16]!\n"
"   mov x29, sp\n"
"   mov w0, #0x1510\n"
"   movk w0, #0x0bd8, lsl #16\n"
"   b og_case_common\n"
".global og_case_83k\n"
"og_case_83k:\n"
"   stp x29, x30, [sp, #-16]!\n"
"   mov x29, sp\n"
"   mov w0, #0x2040\n"
"   movk w0, #0x1224, lsl #16\n"
"og_case_common:\n"                 /* w0 = stock packed; resume the setter at 0x406d3154 */
"   bl og_size_pick\n"
"   mov w8, w0\n"                    /* W -> strh [x1,#0x102] */
"   lsr w9, w0, #16\n"               /* H -> strh [x1,#0x104] */
"   ldp x29, x30, [sp], #16\n"
"   movz x16, #0x3154\n   movk x16, #0x406d, lsl #16\n   br x16\n"
".global og_pad_23x\n"
"og_pad_23x:\n"
"   stp x29, x30, [sp, #-16]!\n"
"   mov x29, sp\n"
"   mov w0, #0x0f0c\n"
"   movk w0, #0x0878, lsl #16\n"
"   b og_pad_common\n"
".global og_pad_41k\n"
"og_pad_41k:\n"
"   stp x29, x30, [sp, #-16]!\n"
"   mov x29, sp\n"
"   mov w0, #0x102c\n"
"   movk w0, #0x091a, lsl #16\n"
"   b og_pad_common\n"
".global og_pad_dx\n"
"og_pad_dx:\n"
"   stp x29, x30, [sp, #-16]!\n"
"   mov x29, sp\n"
"   mov w0, #0x151c\n"
"   movk w0, #0x0be0, lsl #16\n"
"   b og_pad_common\n"
".global og_pad_83k\n"
"og_pad_83k:\n"
"   stp x29, x30, [sp, #-16]!\n"
"   mov x29, sp\n"
"   mov w0, #0x204c\n"
"   movk w0, #0x122c, lsl #16\n"
"og_pad_common:\n"                  /* w0 = stock padded; resume the record setup at 0x40cfafc0 */
"   bl og_size_pick\n"
"   lsr w8, w0, #16\n"               /* H */
"   and w9, w0, #0xffff\n"           /* W */
"   mov w10, w0\n"                   /* packed */
"   ldp x29, x30, [sp], #16\n"
"   movz x16, #0xafc0\n   movk x16, #0x40cf, lsl #16\n   br x16\n"
".global og_rate_row\n"
"og_rate_row:\n"                     /* x8 = stride, x9 = row, x10 = table base -> x8 = row ptr */
"   stp x29, x30, [sp, #-16]!\n"
"   mov x29, sp\n"
"   mov x0, x10\n"
"   mov x1, x9\n"
"   mov x2, x8\n"
"   bl og_rate_pick\n"
"   mov x8, x0\n"
"   ldp x29, x30, [sp], #16\n"
"   movz x16, #0xe654\n   movk x16, #0x40d1, lsl #16\n   br x16\n"
);
