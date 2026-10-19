/* Experimental C15/C30 HE RAW capture, controlled by the ordinary Image quality
 * menu. Both pre-release history and current/full-press frames use the selected
 * RAW, RAW+JPEG or JPEG format and JPEG grade. NEFs use stock photo registration,
 * the stock writer and full-size previews at the camera's NEF-preview quality.
 * RAW+JPEG allocates and encodes a separate preview except when basic JPEG can
 * be reused. See docs/raw-precapture.md for setup, exclusions and failure paths.
 */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long u64;
typedef long s64;

#define LOAD8(a) (*(volatile const u8 *)(u64)(a))
#define LOAD16(a) (*(volatile const u16 *)(u64)(a))
#define LOAD32(a) (*(volatile const u32 *)(u64)(a))
#define LOAD64(a) (*(volatile const u64 *)(u64)(a))
#define STORE8(a,v) (*(volatile u8 *)(u64)(a)=(v))
#define STORE32(a,v) (*(volatile u32 *)(u64)(a)=(v))
#define STORE64(a,v) (*(volatile u64 *)(u64)(a)=(v))
#define STORE8(a,v) (*(volatile u8 *)(u64)(a)=(v))

/* Original firmware interfaces (byte-audited by the build). */
#define SUBMIT ((u64 (*)(void *,u32))0x40f93098ul)
#define FREE_E ((void (*)(u64))0x4104df5cul)
#define XLATE ((u64 (*)(u64))0x41186718ul)
#define OPEN ((int (*)(const char *,u32,u32))0x402daa4cul)
#define CREATE ((int (*)(const char *,u32))0x402dad04ul)
#define CLOSE ((int (*)(int))0x402daaacul)
#define READ ((int (*)(int,void *,u32,u32 *))0x402dab4cul)
#define WRITE ((int (*)(int,u64,u32,u32 *))0x402dabb8ul)
#define EXISTS ((int (*)(const char *))0x402db1acul)
#define RENAME ((int (*)(const char *,const char *))0x402dad58ul)
#define ALLOC ((void *(*)(u32,u32))0x40d2c408ul)
#define FREE ((void (*)(void *))0x40d2c448ul)
#define CLEAN ((void (*)(const void *,u32))0x40d2b8b8ul)
#define CLOCK ((void (*)(void *))0x40c7c778ul)
#define DCF_GET ((u64 (*)(u32))0x4085a8e0ul)
#define DCF_NAME ((u64 (*)(u64))0x4085bfe0ul)
#define DCF_PUT ((void (*)(u64))0x4085aa7cul)
/* patch: the stock still-image writer and the stock DCF database interfaces. */
#define ORIG_WRITE ((u32 (*)(u32,u32,u64))0x406cc134ul)             /* (0, mode, J) -> status */
#define LOCK ((u32 (*)(u64,u32,u32))0x40875834ul)                   /* (lock, ticks, tries) */
#define UNLOCK ((u32 (*)(u64))0x408758b4ul)
#define DB_ADD ((u32 (*)(u64,u32,const void *))0x408602ccul)        /* (db, first id, entry) */
#define DB_REMAIN ((void (*)(u32))0x408648a8ul)
#define DB_CANCEL ((void (*)(u32))0x4085ac54ul)                     /* (file id), no result */
/* patch: the stock rate-control parameter builder of the JPEG encodes. */
#define RC_PARAMS ((void (*)(u64,u32,u32,u64,u8 *))0x40eaecb4ul)   /* (R, mode, kind 0 main / 1 NEF preview / 2, template copy, rc) */
#define G_PREVIEW_Q 0xa029e9fd0ul  /* the (quality index, table half) pair the stock NEF preview encode puts at rc+0x14/+0x18 */
/* patch: output resource Y, the JPEG engine and its channel locks, as used by 0x41048d78 and 0x40eaf398. */
#define Y_ALLOC ((u64 (*)(u32,u64))0x41048d78ul)                     /* (kind word of the step, M) -> Y */
#define Y_SIZE ((u32 (*)(u64,u64,u32))0x4104886cul)                  /* (M, M+0x26c, M+0x2570==0x1d) -> bytes */
#define CAPACITY ((u32 (*)(u32,u32,u32,u32))0x410457ccul)            /* table 0xa02a2460c[a][b][c][d] */
#define DESC_INIT ((u32 (*)(u32,u32,u64,u64))0x41060780ul)           /* (1, 0, M, descriptor): the RAW-preview descriptor */
#define MAIN_ENCODE ((u32 (*)(u64))0x40eaea0cul)                       /* main JPEG encode of one step context */
#define JOB_WORD ((u32 (*)(u64))0x40eaec6cul)                        /* first word of the engine parameter block */
#define CH_LOCK ((void (*)(u32,u32,u32,u32))0x40eb8854ul)
#define CH_UNLOCK ((void (*)(u32,u32,u32,u32))0x40eb88a4ul)
#define ENGINE ((void (*)(u32,u64))0x40e82090ul)                     /* (engine 0/1, parameter block) */
#define IS_JPEG_FORMAT ((u32 (*)(u64))0x4105903cul)                 /* (M+0x26c): format 0/3 and not HEIF; QEMU probe only */
/* Original globals, only read. */
#define G_MODE 0xa03bc6bc8ul       /* HSFC release mode: 6 = C15, 3 = C30 */
#define G_LIMIT 0xa03bc6bacul      /* pre-capture count of the menu setting */
#define G_DRAINED 0xa03bc5638ul    /* history frames drained at this full press (stale when the history is empty) */
#define G_WRITER_JOB 0xa03b891b8ul /* job of the primary writer 0x40ea340c */
#define G_CREATE_LOCK 0xa048229f0ul /* creation lock of 0x40866260 */
#define G_DB 0xa04822af8ul         /* per-card DCF database pointers: slot 0, then slot 1 at +8 */
#define G_QTYPE 0xa03d482c8ul      /* DS 0x06000604 Image quality file type: 0 RAW + JPEG, 1 RAW, 3 JPEG (group 6 RAM 0xa03d482b4 + 0x14) */
#define G_QGRADE 0xa03d482ccul     /* DS 0x06000605 JPEG grade: 0 fine, 1 normal, 2 basic (+0x18; a RAW setting leaves it) */
#define G_QSTAR 0xa03d482d0ul      /* DS 0x06000606 star: 1 optimal quality, 0 size priority (+0x1c) */
#define G_JPEG_STATS 0xa03b88c18ul /* per-engine statistics, 0x240 each; the preview job's template is entry +0x20 */
#define G_JPEG_FLAGS 0xa03b85920ul /* bit 3: single engine */

#define PAYLOAD 0x01b3e000u /* merged: HE* strip (fixed 28,565,504) */
#define OLD_ALLOCATION 0x01b67e00u /* merged: record base = PAYLOAD + 0x29E00 */
#define NEW_ALLOCATION 0x01b68000u /* merged: base + 0x200 record slack */
/* v9 (90 §0.5 / 100 §1.5): per-grade dispatch. marker 3=Lossless, 13=HE, 14=HE*.
 * caps (user ruling): LL 8 / HE 30 / HE* 20. alloc: LL 0x03A00000 (57.7MB max strip + slack),
 * HE 0x01082400 (stock mode 3/6 request = the upstream 30x17.3MB anchor), HE* 0x01B68000 (v3).
 * PAYLOAD_g = alloc_g - 0x2A000 (record slack 0x200 + header 0x29E00). */
#define G_LL 3u
#define G_HE 13u
#define G_HES 14u
static u32 g_alloc(u32 g) { return g==G_LL?0x03a00000u:(g==G_HE?0x01082400u:0x01b68000u); }
static u32 g_payload(u32 g) { return g_alloc(g)-0x2a000u; }
static u32 g_cap(u32 g) { return g==G_LL?8u:(g==G_HE?30u:20u); }
/* 0x0051 leaf (eg 0x406EA0C8-0x406EA164): kind M+0 = 1 -> marker 3 (Lossless); kind 3 -> M+0x2ac
 * =2 -> 13 (HE), =4 -> 14 (HE*). Other kinds carry no RAW marker (fail safe). */
static u32 marker_of(u64 m) { u32 k=LOAD32(m); if(k==1) return G_LL; if(k!=3) return 0;
    return LOAD32(m+0x2ac)==2?G_HE:G_HES; }
#define FX_DIMS 0x15902058u        /* 5520 << 16 | 8280 */
#define RAW_W 8280u
#define RAW_H 5520u
#define WORK_BYTES 0x40000u        /* one heap block per NEF, freed before return */
#define HDR_MAX 0x30000u           /* NEF header block */
#define TAB 0x30000u               /* entry table, ENT_MAX * 32 bytes */
#define NI 0x36000u                /* NEFInfo block, 1 KiB */
#define FOOT 0x38000u              /* 512-byte footer */
#define ZEROS 0x39000u             /* 4 KiB of zero for RAW alignment */
#define JP 0x3a000u                /* parameter block J' for the stock writer, 0x290 bytes */
#define JA 0x3a300u                /* descriptor pointer array, 4 x u64 */
#define JD 0x3a340u                /* descriptor 0: width/height pair, 16 bytes */
#define JT 0x3a360u                /* descriptor 3: thumbnail size, 32 bytes */
#define PLAN 0x3a400u              /* plan_t */
#define ENT_MAX 160u
#define SEG_MAX 27u                /* capacity of the J+0x68.. segment table */
#define CHUNK 0x100000u
#define DEFAULT_BUDGET 1500000u    /* per-NEF write budget in microseconds */
#define FRESH_US 120000000ul
#define RING_CAP 20u /* merged: HE* ring ceiling (109: N<=21 guaranteed zone; 20*29MB + 1 in-flight = 581MB < 640MB pool floor) */
#define F_ENABLE 1u
#define F_C30 2u
#define F_FULL 4u
#define F_FOOTER 8u
#define F_DCF 0x10u                /* register the NEF in the stock database and use the stock writer */
#define F_RAWONLY 0x20u            /* RAW-only (needs F_DCF) */
#define F_PVQ 0x100u                /* RAW-only: main JPEG at the stock NEF-preview quality, embedded (needs F_RAWONLY and F_FULL) */
#define F_MENU 0x200u               /* patch: every C15/C30 frame follows Image quality (needs 1|2|0x10, 30 frames; 4/0x20/0x40 not in the file) */
#define F_KNOWN 0x7ffu /* merged v4: bit4 DCF/5 RAWONLY/6 NOTHUMB/7 MINITHUMB/8 PVQ/9 MENU/10 PVFIX */
#define F_PVFIX 0x400u  /* merged: preview fixed-length placeholder (no behaviour yet) */
#define BIT_DEPTH 14u   /* merged: NEF bit-depth tag; follow-the-menu anchor pending */
#define F_PREV 0x8000u  /* merged: internal effective flag (never in a file) */
#define F_NOTHUMB 0x40u  /* merged: drop the 1620x1080 stream, JFR->thumbnail, fixed raw_at (104 line) */
#define F_MINITHUMB 0x80u /* merged: keep the 160x120 thumbnail (else none) (104 line) */              /* patch, effective flags only (never in a file): RAW + JPEG with a second, preview-quality encode */
#define PVQ_MARK 0x31515650u       /* "PVQ1": record +0x7c, written by P7 after the parameters were replaced */
#define PVJ_MARK 0x314a5650u       /* "PVJ1": aux +0xb8, written by hook J after the preview encode */
#define AUX_MAGIC 0x41455250u      /* "PREA" */
#define Q_MARKED 1u
#define Q_RETAINED 2u
#define K_HISTORY 1u
#define K_CURRENT 2u
#define T_JPEG 1u
#define T_RAWJPEG 2u
#define T_RAW 3u
#define S_DONE 1u
#define S_BUDGET 3u
#define S_WRITE_FAIL 4u
#define S_RENAME_FAIL 5u
#define S_MISSING 6u               /* the stock writer reported success but the NEF is not on the card */
#define DB_OK 0x4320080u           /* stock success code of the database interfaces */
#define RC_NO_DB 0xfff00001u       /* patch internal result codes, never produced by stock code */
#define RC_LOCK 0xfff00002u
#define RC_INTERNAL 0xfff00003u
/* aux block of the frame record (record +0x80..+0xff, own CRC at +0xfc over +0x80..+0xfb) */
#define A_MAGIC 0x80u
#define A_KIND 0x84u               /* K_HISTORY / K_CURRENT */
#define A_VALUE 0x88u              /* at submit: page value (bits 0..7, V_NONE if not one the menu gives), then file type,
                                      grade and star items (bits 8..15, 16..23, 24..31, each clamped to 0xff) */
#define V_NONE 0xffu
#define A_M290 0x8cu               /* M+0x290 / M+0x2a0 as the stock HSFC path set them */
#define A_M2A0 0x90u
#define A_QUAL 0x94u               /* applied by P2 (F_MENU): quality index, table half, file type */
#define A_HALF 0x98u
#define A_TYPE 0x9cu
#define A_YOFF 0xa0u               /* hook B: stock request bytes; preview capacity */
#define A_YCAP 0xa4u
#define A_Y 0xa8u                  /* hook A: Y and the preview region address */
#define A_YADDR 0xb0u
#define A_PMARK 0xb8u              /* hook J: PVJ_MARK, encoded bytes, engine, source offset in R */
#define A_PBYTES 0xbcu
#define A_PT0 0xc0u
#define A_PT1 0xc8u
#define A_ENGINE 0xd0u
#define A_SRC 0xd4u
#define A_YSTATE 0xd8u             /* 1 enlarged by B, 2 laid out by A */
#define A_RTC 0xdcu               /* v6: 7B RTC wall clock captured at P2 (117; q+0x58 is monotonic) */
#define A_CRC 0xfcu
#define REC_BYTES 256u

static const u8 qual_magic[16] = "Z8PREQUALv3";
static const u8 cfg_magic[16] = "Z8PRECFGv4"; /* merged: v3 and older rejected */
static const u8 foot_magic[16] = "Z8PREFOOTv3";
static const u8 identity[8] = {'P','R','E','C','A','P','0','3'};
/* MakerNote 0x0051 for HE (internal compression 4, budget 2): the original leaf 0x406ea044
 * writes this from M+0x2ac=2; identical in every camera HE NEF examined. */
static const u8 he51[24] = {0x30,0x31,0x30,0x32,0x30,0x35,0x30,0x31,0,0,14,0,0,0,0,0,6,0,0,0,0,0,0,0};
static const u8 rat300[8] = {44,1,0,0,1,0,0,0};
static const u8 refbw[48] = {0,0,0,0,1,0,0,0, 255,0,0,0,1,0,0,0, 0,0,0,0,1,0,0,0,
                             255,0,0,0,1,0,0,0, 0,0,0,0,1,0,0,0, 255,0,0,0,1,0,0,0};
static const u8 tiffep[4] = {1,0,0,0};
static const u8 one8[1] = {1};
/* v8/118 D5: compatibility placeholders (114-P1). ContrastCurve is an empty block on real NEFs. */
static const u8 tpl_008c_empty[578] = { 'I','0' };
static const u8 tpl_00a4[4] = { '0','5','0','1' };
static const u8 tpl_0046[4] = { 0,0,0,0 };
static const u8 cfa_dim[4] = {2,0,2,0};
static const u8 cfa_rggb[4] = {0,1,1,2};
static const u8 quality_raw[8] = {'R','A','W',' ',' ',' ',' ',0};
static const u8 xmp_ns[29] = "http://ns.adobe.com/xap/1.0/";
static const u8 nikon2[18] = {'N','i','k','o','n',0,2,0x11,0,0,'I','I',0x2a,0,8,0,0,0};
static const u8 nikon_ni[18] = {'N','i','k','o','n',0,1,3,0,0,'I','I',0x2a,0,8,0,0,0};
static const u8 type_size[13] = {0,1,1,2,4,8,1,1,2,4,8,4,8};
static const u16 skip0[] = {0x00fe,0x0103,0x014a,0x0201,0x0202,0x0214,0x02bc,0x8769,0x8825,0x9003,0x9216};
static const u16 skipx[] = {0x9000,0x9101,0x9102,0xa000,0xa001,0xa002,0xa003,0xa005,0x927c};
static const u16 skipm[] = {0x0004,0x0011,0x0016,0x0035,0x003d,0x0045,0x0046,0x0051,0x0058,0x008c,0x00a2,0x00a4};
/* v7/117 D3-MAX: 4x4 capacity table in the injected constants (rows = G_MODE-3 case,
 * cols = 0.3s/0.5s/1s/MAX; case bases are patched to these rows). */
__attribute__((used)) const u32 d3max_table[16] = {9,15,20,20, 36,60,120,20, 18,30,60,20, 5,8,15,20};
static const u32 crc_table[256] = {
#include "crc32_table.inc"
};

static void copy(u8 *d,const u8 *s,u32 n) { while(n--) *d++=*s++; }
static void zero(u8 *d,u32 n) { while(n--) *d++=0; }
static int equal(const u8 *a,const u8 *b,u32 n) { u32 x=0; while(n--) x|=*a++^*b++; return x==0; }
static u32 get16(const u8 *p) { return (u32)p[0]|(u32)p[1]<<8; }
static u32 get32(const u8 *p) { return (u32)p[0]|(u32)p[1]<<8|(u32)p[2]<<16|(u32)p[3]<<24; }
static u64 get64(const u8 *p) { return (u64)get32(p)|(u64)get32(p+4)<<32; }
static void set16(u8 *p,u32 v) { p[0]=(u8)v; p[1]=(u8)(v>>8); }
static void set32(u8 *p,u32 v) { for(u32 i=0;i<4;i++){p[i]=(u8)v;v>>=8;} }
static void set64(u8 *p,u64 v) { for(u32 i=0;i<8;i++){p[i]=(u8)v;v>>=8;} }
__attribute__((noinline)) static u32 crc32(const u8 *p,u32 n) {
    u32 c=0xffffffffu; while(n--) c=(c>>8)^crc_table[(c^*p++)&255]; return c^0xffffffffu;
}
static u32 crc16(const u8 *p,u32 n) {              /* CCITT-FALSE, as in NEFInfo blocks */
    u32 c=0xffff;
    while(n--){ c^=(u32)*p++<<8; for(u32 i=0;i<8;i++) c=(c&0x8000)?((c<<1)^0x1021)&0xffff:(c<<1)&0xffff; }
    return c;
}
static u64 now(void) { u64 t; CLOCK(&t); return t; }

/* ---------------- frame record in the E allocation tail ---------------- */
/* E is a resource descriptor: E+8 -> {data_base, data_bytes}; E+0x30 type/format/dims,
 * E+0x40 payload. The 512 bytes past OLD_ALLOCATION exist only because the build enlarges
 * the mode 3/6 request; no original code addresses them. Record: +0x00..+0x7f with CRC at
 * +0x78 over +0x00..+0x77, P7 mark at +0x7c; +0x80..+0xff the patch aux block. */
static u8 *record(u64 e,u32 alloc) {
    u64 block=LOAD64(e+8); if(!block) return 0;
    u64 base=LOAD64(block),bytes=LOAD32(block+8);
    if(!base || bytes!=alloc || base+bytes<base) return 0;  /* v9: the slot must match the grade */
    u64 q=(base+bytes-REC_BYTES+63)&~63ul;                  /* v9: record at the slot tail */
    if(q<base || q+REC_BYTES>base+bytes) return 0;
    return (u8 *)q;
}
static int e_shape(u64 e,u32 pay) {
    if(!e || LOAD32(e+0x30)!=3 || LOAD32(e+0x34)!=5 || LOAD32(e+0x38)!=FX_DIMS) return 0;
    u64 d=LOAD64(e+0x40); return d && !(d&511) && d+pay>d;
}
static void seal(u8 *q) { set32(q+0x78,crc32(q,0x78)); CLEAN(q,128); }
static void aux_seal(u8 *q) { set32(q+A_CRC,crc32(q+0x80,0x7c)); CLEAN(q+0x80,128); }
static int aux_ok(const u8 *q) { return get32(q+A_MAGIC)==AUX_MAGIC && get32(q+A_CRC)==crc32(q+0x80,0x7c); }
static void unbind(u8 *q) { zero(q,16); CLEAN(q,128); }
/* Valid record of this exact HSFC R/E/M in the given state, with a valid aux block. */
static u8 *bound(u64 r,u64 e,u32 state) {
    u64 m=LOAD64(r+0x790); u8 *q; u32 g;
    if(!m || !(g=marker_of(m)) || !e_shape(e,g_payload(g)) || !(q=record(e,g_alloc(g)))) return 0;
    if(!equal(q,qual_magic,16) || get32(q+0x10)!=1 || get32(q+0x14)!=state) return 0;
    if(get64(q+0x28)!=r || get64(q+0x30)!=e || get64(q+0x38)!=m || get64(q+0x40)!=LOAD64(e+0x40)) return 0;
    if(get32(q+0x78)!=crc32(q,0x78) || !aux_ok(q)) return 0;
    return q;
}
/* The retained frame of R whose M is still the frame the record was made for. */
__attribute__((unused)) static u8 *retained(u64 r) {
    u64 e; u8 *q;
    if(!r || !(e=LOAD64(r+0x748)) || !(q=bound(r,e,Q_RETAINED))) return 0;
    if(get32(q+0x70)!=LOAD32(LOAD64(r+0x790)+0x2508)) return 0;
    return q;
}

/* RAM only, inside the original release task. kind: K_HISTORY from P1, K_CURRENT from P8. */
/* The Image quality page value as the stock page composer 0x405dadd4 forms it from file type t (item 0x0604),
 * grade g (0x0605) and star c (0x0606): RAW + JPEG 2g + 1 - c, JPEG 2g + 7 - c, RAW 13. The composer also maps
 * t = 2 to 12 and invalid items to 8, 9 or 14 (fallback rows); none of those is a menu choice, so V_NONE (the
 * frame stays stock). */
static u32 menu_value(u32 t,u32 g,u32 c) {
    if(c>1) return V_NONE;
    if(t==1) return 13;
    if((t!=0 && t!=3) || g>2) return V_NONE;
    return (t==3?6u:0u)+2*g+1-c;
}
static u32 clamp8(u32 v) { return v>0xffu?0xffu:v; }
static u32 menu_word(void) {
    u32 t=LOAD32(G_QTYPE),g=LOAD32(G_QGRADE),c=LOAD32(G_QSTAR),v=menu_value(t,g,c);
#ifdef NEG_GRADE_ONLY                 /* negative-control builds only: patch's read (the grade item taken as the value) */
    v=g;
#endif
    return v | clamp8(t)<<8 | clamp8(g)<<16 | clamp8(c)<<24;
}
__attribute__((noinline)) static void mark(void *rec,u32 kind) {
    u64 r=(u64)rec,m,e; u8 *q; u32 mode,seq,total,g;
    if(!r) return;
    m=LOAD64(r+0x790); e=LOAD64(r+0x748);
    if(!m || !e || !(g=marker_of(m))) return;   /* v9: kind 1 (Lossless) or 3 (HE family) */
    mode=LOAD32(G_MODE); if(mode!=6 && mode!=3) return;
    seq=LOAD32(m+0x120);
    if(kind==K_HISTORY) { total=LOAD32(G_DRAINED); if(!seq || seq>total || total>g_cap(g)) return; }
    else total=0;                    /* G_DRAINED is stale for frames after the full press */
    if(!e_shape(e,g_payload(g)) || !(q=record(e,g_alloc(g)))) return;
    zero(q,REC_BYTES); copy(q,qual_magic,16); set32(q+0x10,1); set32(q+0x14,Q_MARKED);
    set32(q+0x18,seq); set32(q+0x1c,total); set32(q+0x20,mode); set32(q+0x24,LOAD32(G_LIMIT));
    set64(q+0x28,r); set64(q+0x30,e); set64(q+0x38,m); set64(q+0x40,LOAD64(e+0x40));
    set32(q+0x48,LOAD32(e)); set32(q+0x4c,g_alloc(g)); CLOCK(q+0x50);
    set32(q+A_MAGIC,AUX_MAGIC); set32(q+A_KIND,kind); set32(q+A_VALUE,menu_word());
    set32(q+A_M290,LOAD32(m+0x290)); set32(q+A_M2A0,LOAD32(m+0x2a0));
    seal(q); aux_seal(q);
}
__attribute__((used,section(".text.entry"))) u64 precapture_history_entry(void *rec,u32 keep) {
    mark(rec,K_HISTORY);             /* inside the original drain lock */
    return SUBMIT(rec,keep);
}
/* P8. Original: mov x0,x20; mov w1,w21 (set by the original code); bl 0x40f93098. */
__attribute__((used)) u64 precapture_current_entry(void *rec,u32 keep) {
    mark(rec,K_CURRENT);
    return SUBMIT(rec,keep);
}

/* ---------------- card configuration and sticky stop ---------------- */
/* v9: per-grade dispatch at config time — the E allocation request (eg 0x4D2FFC0/CC) and the
 * D3-MAX col4 (= the grade cap, 117 §2). Runs on every drain, so a grade change self-corrects;
 * frames captured before the first run keep the previous slot and are gated out (fail-safe). */
static void grade_dispatch(u32 grade) {
    u32 a=g_alloc(grade),c=g_cap(grade);
    STORE32(0xa04d2ffc0ul,a); STORE32(0xa04d2ffccul,a);
    ((u32 *)d3max_table)[3]=c; ((u32 *)d3max_table)[7]=c;
    ((u32 *)d3max_table)[11]=c; ((u32 *)d3max_table)[15]=c;
}
static int read_cfg(char drive,u8 *out) {
    char path[16]="A:\\Z8PRE.CFG"; u32 count=0; int fd,rc,cl;
    path[0]=drive;
    fd=OPEN(path,0,0x20); if(fd<0) return 0;
    rc=READ(fd,out,65,&count); cl=CLOSE(fd);
    if(rc!=0 || cl!=0 || count!=64 || !equal(out,cfg_magic,16)) return 0;
    u32 flags=get32(out+0x10),pre=get32(out+0x14),budget=get32(out+0x18);
    u32 grade=(get32(out+0x1c)>>8)&0xffu;                 /* v9: 0=auto(HE*) / 3 Lossless / 13 HE / 14 HE* */
    if(!grade) grade=G_HES;
    if(grade!=G_LL && grade!=G_HE && grade!=G_HES) return 0;
    if((flags&~F_KNOWN) || !(flags&F_ENABLE) || pre<1) return 0;
    if(flags&F_PREV) return 0;   /* merged: internal flag must never come from a file */
    if((flags&F_RAWONLY) && !(flags&F_DCF)) return 0;         /* RAW-only needs the stock writer */
    if((flags&F_PVQ) && (flags&(F_RAWONLY|F_FULL))!=(F_RAWONLY|F_FULL)) return 0;   /* the JPEG file must not be kept */
    if((flags&F_MENU) && ((flags&(F_ENABLE|F_C30|F_DCF))!=(F_ENABLE|F_C30|F_DCF) || (flags&(F_FULL|F_RAWONLY|F_PVQ)))) return 0;
    if(budget && (budget<200000 || budget>5000000)) return 0;
    for(u32 i=0x20;i<0x3c;i++) if(out[i]) return 0;
    if(get32(out+0x3c)!=crc32(out,60)) return 0;
    if(pre>g_cap(grade)) { pre=g_cap(grade); set32(out+0x14,pre); }   /* v9: clamp inside the grade cap */
    grade_dispatch(grade);
    return 1;
}
static int stopped(char drive) { char p[20]="A:\\Z8PRESTP.BIN"; p[0]=drive; return EXISTS(p)>=0; }
__attribute__((noinline)) static void stop_file(char drive,u32 status,u32 shot) {
    char p[20]="A:\\Z8PRESTP.BIN"; u8 raw[64] __attribute__((aligned(64))); u32 n; int fd;
    p[0]=drive; if(EXISTS(p)>=0) return;
    zero(raw,64); copy(raw,(const u8 *)"Z8PRESTOP",9); set32(raw+16,status); set32(raw+20,shot);
    set64(raw+24,now()); CLEAN(raw,64);
    fd=CREATE(p,0x20); if(fd<0) return;
    WRITE(fd,(u64)raw,32,&n); CLOSE(fd);        /* never retried or deleted */
}

/* Image quality value -> file type, quality index (M+0x290: 0 fine, 1 normal, 2 basic) and table half
 * (M+0x2a0: 1 = "*", optimal quality). 0 = not a value patch takes over (V_NONE included). */
static u32 plan_of(u32 v,u32 *qi,u32 *half) {
    if(v<=11) { u32 k=v%6; *qi=k>>1; *half=(k&1)?0u:1u; return v<6?T_RAWJPEG:T_JPEG; }
    if(v==13) { *qi=0; *half=0; return T_RAW; }          /* fine FHD/VGA, as in a camera RAW-only NEF; P7 sets the main */
    return 0;
}
/* The frame is an ordinary stock HSFC C15/C30 JPEG frame, as the five real frames: JPEG only, not HEIF,
 * no special size, no second JPEG, FX L, and the HSFC item's own values (fine/normal, half 0). */
static int stock_hsfc_m(u64 m) {
    return LOAD32(m)==3 && LOAD32(m+0x294)==3 && LOAD32(m+0x2fc)==0 && LOAD32(m+0x2570)==0 && LOAD8(m+0x2ce)==0 &&
           LOAD32(m+0x26c)==0 && LOAD32(m+0x290)<=1 && LOAD32(m+0x2a0)==0;
}

/* P2. Original: ldr x0,[x23,#0x748]; bl 0x4104df5c; str xzr,[x23,#0x748]. */
__attribute__((used)) void precapture_tdec_release(u64 r) {
    u64 e=LOAD64(r+0x748); u8 *q=e?bound(r,e,Q_MARKED):0;
    if(q) {
        u8 ca[65] __attribute__((aligned(8))),cb[65] __attribute__((aligned(8)));
        u64 t=now(),m=LOAD64(r+0x790);
        int a=read_cfg('A',ca),b=read_cfg('B',cb);
        if(a!=b && t-get64(q+0x50)<FRESH_US) {
            char drive=a?'A':'B'; const u8 *c=a?ca:cb;
            u32 flags=get32(c+0x10),pre=get32(c+0x14),budget=get32(c+0x18);
            u32 seq=get32(q+0x18),total=get32(q+0x1c),mode=get32(q+0x20),keep=0;
            if(!budget) budget=DEFAULT_BUDGET;
            if(flags&F_MENU) {
                u32 qi,half,type=plan_of(get32(q+A_VALUE)&0xffu,&qi,&half);
#ifdef NEG_MENU_IGNORED               /* negative-control builds only */
                type=0;
#endif
                if(type && (mode==6 || mode==3) && stock_hsfc_m(m) && get32(q+A_M290)==LOAD32(m+0x290) && get32(q+A_M2A0)==LOAD32(m+0x2a0)) {
                    STORE32(m+0x290,qi); STORE32(m+0x2a0,half);
                    set32(q+A_QUAL,qi); set32(q+A_HALF,half); set32(q+A_TYPE,type); aux_seal(q);
                    if(type!=T_JPEG && !stopped(drive)) {
                        flags|=F_FULL;
                        if(type==T_RAW) flags|=F_RAWONLY|F_PVQ;
                        else if(qi!=2 || half!=0) flags|=F_PREV;          /* basic (no *): the main JPEG is the preview */
                        keep=1;
                    }
                }
            } else {                                                      /* fixed-output configurations: history frames only */
                u32 hist=get32(q+A_KIND)==K_HISTORY;
#ifdef NEG_CURRENT_ANY_CONFIG         /* negative-control builds only */
                hist=1;
#endif
                keep=hist && (mode==6 || (mode==3 && (flags&F_C30))) && seq+pre>total && !stopped(drive);
            }
            if(keep) {
                set32(q+0x14,Q_RETAINED); set64(q+0x58,t); set32(q+0x60,flags); set32(q+0x64,pre);
                ((void(*)(void*))0x402DD334ul)(q+A_RTC);   /* v6: capture wall clock (117 §3 ①) */
                STORE8(0x4095803Cul,(u8)(!(flags&F_ENABLE)?0:((flags&F_DCF)?2:1))); /* v7/111: counter scale */
                set32(q+0x68,budget); set32(q+0x6c,(u32)drive); set32(q+0x70,LOAD32(m+0x2508));
                set32(q+0x74,get32(c+0x1c));
                seal(q);
                return;                      /* R+0x748 kept for P3' or the R cleanup */
            }
        }
        unbind(q);
    }
    FREE_E(e);
    STORE64(r+0x748,0);
}

/* ---------------- patch: the preview region in Y ---------------- */
#ifndef PRE_CAPTURE_PROBE
/* A retained frame of R that needs the second encode; M must be R's. */
static u8 *needs_preview(u64 r,u64 m) {
    u8 *q=retained(r);
    if(!q || LOAD64(r+0x790)!=m || !(get32(q+0x60)&F_PREV) || get32(q+A_TYPE)!=T_RAWJPEG) return 0;
    return q;
}
/* B. Original: bl 0x4104886c(x0, x1, w2) inside 0x41048d78; the entry stub passes x23 = R. */
__attribute__((used)) u32 precapture_y_size(u64 m,u64 m26c,u32 flag,u64 r) {
    u32 size=Y_SIZE(m,m26c,flag),cap,base,need; u8 *q;
    if(!r || m26c!=m+0x26c || !(q=needs_preview(r,m))) return size;      /* m26c != M+0x26c: the stock stack-copy path */
    cap=CAPACITY(LOAD32(m+0x26c),0,LOAD32(m+0x29c),2);
    base=(size+511u)&~511u; need=base+((cap+511u)&~511u)+512u;          /* +512: the block base need not be 512-aligned */
    if(!cap || cap>0x2000000u || base<size || need<base) return size;
    set32(q+A_YOFF,size); set32(q+A_YCAP,cap); set32(q+A_YSTATE,1); aux_seal(q);
    return need;
}
__attribute__((unused)) static int ends_by(u64 y,u32 addr_off,u32 cap_off,u64 limit) {          /* a stock region [addr, addr+cap) ends at or before limit */
    u64 a=LOAD64(y+addr_off); u32 c=LOAD32(y+cap_off);
    return !a || (a+c>=a && a+c<=limit);
}
/* A. Original: bl 0x41048d78(w0, x1=M) in 0x40ea9f3c; the entry stub passes x23 = R. */
__attribute__((used)) u64 precapture_y_alloc(u32 kind,u64 m,u64 r) {
    u64 y=Y_ALLOC(kind,m),blk,base,addr; u32 bytes,cap; u8 *q;
    if(!y || !r || !(q=needs_preview(r,m)) || get32(q+A_YSTATE)!=1) return y;
    blk=LOAD64(y+8); if(!blk) return y;
    base=LOAD64(blk); bytes=LOAD32(blk+8); cap=get32(q+A_YCAP);
    addr=(base+get32(q+A_YOFF)+511u)&~511ul;
    if(!base || addr<base || addr+cap<addr || addr+cap>base+bytes) return y;
#ifndef NEG_Y_OVERLAP
    /* every region of the stock JPEG-only layout (main, VGA, FHD, thumbnail) ends before the new one */
    if(!ends_by(y,0x40,0x30,addr) || !ends_by(y,0xa8,0x98,addr) || !ends_by(y,0xc8,0xb8,addr) || !ends_by(y,0xe8,0xd8,addr)) return y;
#else                                 /* negative-control builds only: the preview region on top of the main JPEG's */
    addr=LOAD64(y+0x40);
#endif
    if(LOAD64(y+0x108) || LOAD32(y+0xf8) || DESC_INIT(1,0,m,y+0x100)!=1) return y;
    STORE32(y+0xf8,cap); STORE64(y+0x108,addr);
    set64(q+A_Y,y); set64(q+A_YADDR,addr); set32(q+A_YSTATE,2); aux_seal(q);
    return y;
}
#else
/* QEMU probe only (never packaged). The emulator shoots RAW stills (the stock RAW-only NEF, M+0x294 = 1), whose
 * stock Y layout already has a preview region at Y+0x100. B enlarges that Y by the same preview capacity, A moves
 * the preview region to the end of Y, J runs preview_job there right after the (gated-off) main step; the stock
 * preview step then sees Y+0x1e set and skips. With A, B and J correct the NEF's JpgFromRaw equals the control's.
 * No record: A and J recompute the stock request size with the stock function. */
static int probe_frame(u64 r,u64 m) {
    return r && m && LOAD64(r+0x790)==m && LOAD32(m)!=3 && LOAD32(m+0x294)==1 && LOAD32(m+0x2fc)!=1 && LOAD32(m+0x2570)==0;
}
static u32 probe_cap(u64 m) { return CAPACITY(LOAD32(m+0x26c),0,LOAD32(m+0x29c),2); }
static u64 probe_addr(u64 y,u64 m) {
    u64 blk=LOAD64(y+8); if(!blk) return 0;
    return (LOAD64(blk)+Y_SIZE(m,m+0x26c,0)+511u)&~511ul;
}
__attribute__((used)) u32 precapture_y_size(u64 m,u64 m26c,u32 flag,u64 r) {
    u32 size=Y_SIZE(m,m26c,flag);
    if(m26c!=m+0x26c || !probe_frame(r,m)) return size;
    return ((size+511u)&~511u)+((probe_cap(m)+511u)&~511u)+512u;
}
__attribute__((used)) u64 precapture_y_alloc(u32 kind,u64 m,u64 r) {
    u64 y=Y_ALLOC(kind,m),blk,addr; u32 cap;
    if(!y || !probe_frame(r,m) || !(blk=LOAD64(y+8))) return y;
    addr=probe_addr(y,m); cap=probe_cap(m);
    if(!addr || addr+cap>LOAD64(blk)+LOAD32(blk+8) || DESC_INIT(1,0,m,y+0x100)!=1) return y;
    STORE32(y+0xf8,cap); STORE64(y+0x108,addr);
    return y;
}
#endif
/* v9 (90 §2 路线 B): the kind->+0x2ac mapping site (eg 0xD52564; stock mov w8,#2 = HE, v8 patched
 * it to mov w8,#4 = HE*). Per-grade: w8 follows the E allocation request (2 = HE slot, else 4).
 * The Lossless (kind 1) path never reaches this site (mapping writes +0x2ac only for grades 3/4). */
__asm__(".pushsection .text.precapture_stub,\"ax\",%progbits\n"
        ".global precapture_grade_entry\n.type precapture_grade_entry,%function\n"
        "precapture_grade_entry:\n\t"
        "movz x17, #0xffc0\n\tmovk x17, #0x04d2, lsl #16\n\tmovk x17, #0x000a, lsl #32\n\t"
        "ldr w16, [x17]\n\t"
        "movz w17, #0x2400\n\tmovk w17, #0x0108, lsl #16\n\t"
        "cmp w16, w17\n\tmov w8, #2\n\tmov w17, #4\n\tcsel w8, w8, w17, eq\n\t"
        "movz x16, #0x2570\n\tmovk x16, #0x40eb, lsl #16\n\tbr x16\n"  /* x16/x17: IP scratch, dead at 0x40EB257C's call */
        ".popsection\n");
/* v10 (122 §4 硬前置 1): NCSET012 load guard. The walk's item count comes from firmware-side
 * structures while old files carry fewer slots (position-encoded format, no per-item id) — an
 * unguarded walk reads past the segment. Site: eg 0xF7F9D4 (bl 0x410E1AA8 = the per-item apply).
 * The stub applies the item only when [buf, buf+size) lies inside the file (x25 = header, +0x10 =
 * total length); otherwise it returns 0 and the item keeps its default. Registers touched:
 * w9/x9/x10 (redefined at 0x410df9e8/0x410df9a0) and x16 (IP scratch, dies at the apply call). */
__asm__(".pushsection .text.precapture_stub,\"ax\",%progbits\n"
        ".global precapture_ncset_guard\n.type precapture_ncset_guard,%function\n"
        "precapture_ncset_guard:\n\t"
        "ldr w9, [x25, #0x10]\n\t"
        "add x9, x25, x9\n\t"
        "add x10, x3, x2\n\t"
        "cmp x10, x9\n\t"
        "b.hi 1f\n\t"
        "movz x16, #0x1aa8\n\tmovk x16, #0x410e, lsl #16\n\tbr x16\n"
        "1:\n\tmov w0, wzr\n\t"
        "movz x16, #0xf9d8\n\tmovk x16, #0x410d, lsl #16\n\tbr x16\n"
        ".popsection\n");
__asm__(".pushsection .text.precapture_stub,\"ax\",%progbits\n"
        ".global precapture_y_size_entry\n.type precapture_y_size_entry,%function\n"
        "precapture_y_size_entry:\n\tmov x3, x23\n\tb precapture_y_size\n"
        ".global precapture_y_alloc_entry\n.type precapture_y_alloc_entry,%function\n"
        "precapture_y_alloc_entry:\n\tmov x2, x23\n\tb precapture_y_alloc\n"
        ".popsection\n");

/* The encode job of the stock NEF-preview step 0x40eaf398 (0x40eaf46c..0x40eaf570), on the same step
 * context, R, Y and source: engine, parameter block {job word, source+0x30, Y+0x100, capacity, rc
 * kind 1, scratch}, template from the engine's statistics entry, channel lock 0x23+engine. */
__attribute__((noinline)) static u32 preview_job(u64 ctx,u64 r,u64 y,u64 src,u32 *engine) {
    u8 blk[0x50] __attribute__((aligned(16))),sc[0x60] __attribute__((aligned(16))),tm[0x20] __attribute__((aligned(16)));
    u64 m=LOAD64(r+0x790); u32 eng=0,ch;
    if(LOAD32(m+0x2570)==0 && !(LOAD8(G_JPEG_FLAGS)&8)) eng=(~LOAD32(ctx))&1u;
    zero(blk,0x50); zero(sc,0x60); zero(tm,0x20);
    set32(blk,JOB_WORD(ctx));
    set64(blk+8,src+0x30); set64(blk+0x10,y+0x100); set32(blk+0x18,LOAD32(y+0xf8)); set64(blk+0x48,(u64)sc);
    for(u32 i=0;i<0x20;i++) tm[i]=LOAD8(G_JPEG_STATS+0x240ul*eng+0x20+i);
#ifndef NEG_PREVIEW_KIND0             /* negative-control builds only */
    RC_PARAMS(r,0,1,(u64)tm,blk+0x20);
#else
    RC_PARAMS(r,0,0,(u64)tm,blk+0x20);
#endif
    ch=0x23u+eng;
    CH_LOCK(ch,0,0,0);
    ENGINE(eng,(u64)blk);
    CH_UNLOCK(ch,0,0,0);
    STORE8(y+0x1e,1);
#if defined(PRE_CAPTURE_PROBE) && defined(PROBE_STATS)
    /* QEMU probe only: also the statistics writes of the stock preview step (0x40eaf574..0x40eaf618), which patch leaves out
     * (in a stock RAW + JPEG frame the main encode writes them and the preview step does not). */
    { u64 st=G_JPEG_STATS+0x240ul*eng,x23=LOAD64(m+0x2950);
      STORE32(st+0x38,LOAD32(m+0x180)); STORE32(st+0x3c,LOAD32(m+0x184)); STORE8(st+0x20,blk[0x24]);
      STORE32(st+0x30,LOAD32(m+0x2544)); STORE32(st+0x34,LOAD32(m+0x2548));
      STORE32(st+0x24,get32(blk+0x28)); STORE32(st+0x28,get32(sc+4)); STORE32(st+0x2c,get32(sc+8));
      STORE32(m+0x1970,get32(sc+0xc));
      if(x23 && !IS_JPEG_FORMAT(m+0x26c)) {
          for(u32 k=0;k<5;k++) {
              STORE32(x23+4*k,get32(sc+0x10+8*k)); STORE32(x23+0x14+4*k,get32(sc+0x14+8*k)); STORE64(x23+0x28+8*k,(u64)get32(blk+0x28));
          }
          STORE32(x23+0x8c,0); STORE32(m+0x2948,0x90);
      }
    }
#endif
    *engine=eng;
    return LOAD32(y+0x110);
}
#ifndef PRE_CAPTURE_PROBE
/* J. Original: bl 0x40eaea0c(ctx) in the main-JPEG step wrappers 0x40eaeed8 and 0x40eaeefc (result ignored). */
__attribute__((used)) u32 precapture_main_step(u64 ctx) {
    u32 st=MAIN_ENCODE(ctx),eng,bytes; u64 r,y,src,t0; u8 *q;
    r=LOAD64(ctx+0x18);
    if(!(q=needs_preview(r,LOAD64(r+0x790))) || get32(q+A_YSTATE)!=2) return st;
    y=LOAD64(r+0x6a8);
    if(!y || get64(q+A_Y)!=y || LOAD64(y+0x108)!=get64(q+A_YADDR) || LOAD32(y+0xf8)!=get32(q+A_YCAP)) return st;
    if(LOAD8(y+0x18)!=1 || LOAD8(y+0x1e)!=0) return st;                  /* main encoded, preview not yet */
    src=LOAD64(r+0x690); set32(q+A_SRC,0x690);
    if(!src) { src=LOAD64(r+0x688); set32(q+A_SRC,0x688); }               /* the stock preview's choice */
    if(!src) return st;
    t0=now(); bytes=preview_job(ctx,r,y,src,&eng);
    set64(q+A_PT0,t0); set64(q+A_PT1,now()); set32(q+A_ENGINE,eng); set32(q+A_PBYTES,bytes);
    if(bytes>=4 && bytes<=get32(q+A_YCAP)) set32(q+A_PMARK,PVJ_MARK);
    aux_seal(q);
    return st;
}
#else
__attribute__((used)) u32 precapture_main_step(u64 ctx) {
    u32 st=MAIN_ENCODE(ctx),eng; u64 r=LOAD64(ctx+0x18),m,y,src;
    if(!r || !(m=LOAD64(r+0x790)) || !probe_frame(r,m) || !(y=LOAD64(r+0x6a8))) return st;
    if(LOAD8(y+0x1e) || LOAD64(y+0x108)!=probe_addr(y,m) || LOAD32(y+0xf8)!=probe_cap(m)) return st;
    src=LOAD64(r+0x690); if(!src) src=LOAD64(r+0x688);
    if(src) preview_job(ctx,r,y,src,&eng);
    return st;
}
#endif

/* P7. Original: bl 0x40eaecb4 in 0x40eaea0c (x0=R, w1=mode, w2=0 main, x3=template copy, x4=rc), so the
 * stock parameters are always built first. rc layout (u32): +0 mode, byte +4 size-target flag, +8 target,
 * +0xc size class, +0x10 image size, +0x14 quality index, +0x18 table half, +0x1c, u64 +0x20 template.
 * The JPEG driver's rate control 0x40eb7318 takes the scale from the table at 0xa029d1378 by
 * (+0x18, size class, +0x10, +0x14) and, with the flag, may raise it from the template's statistics. */
#ifndef PRE_CAPTURE_PROBE
static void preview_quality(u8 *rc) {
    set32(rc+0x14,LOAD32(G_PREVIEW_Q)); set32(rc+0x18,LOAD32(G_PREVIEW_Q+4));
    rc[4]=0; set64(rc+0x20,0);       /* the table value exactly; the template written after this encode stays unusable */
}
__attribute__((used)) void precapture_main_rc(u64 r,u32 mode,u32 kind,u64 tmpl,u8 *rc) {
    u8 *q;
    RC_PARAMS(r,mode,kind,tmpl,rc);
#ifdef NEG_PVQ_ANY_FRAME              /* negative-control builds only: every main JPEG */
    if(kind==0) preview_quality(rc);
#endif
    if(kind!=0 || !(q=retained(r))) return;
    if((get32(q+0x60)&(F_PVQ|F_RAWONLY|F_FULL))!=(F_PVQ|F_RAWONLY|F_FULL)) return;
    preview_quality(rc);
#ifndef NEG_PVQ_NO_MARK               /* negative-control builds only */
    set32(q+0x7c,PVQ_MARK); CLEAN(q,128);   /* outside the record CRC (0..0x77); P1/P8 clear it for the next frame */
#endif
}
#else
/* QEMU probe only (never packaged): P7 passes through; B, A and J act on the emulator's RAW still (the stock
 * RAW-only NEF, M+0x294 = 1), whose stock layout already has a preview region: B enlarges Y, A moves the
 * preview region to the end of Y, J encodes the preview there before the stock preview step (which then sees
 * Y+0x1e set and skips). The NEF's JpgFromRaw must equal the control's. */
__attribute__((used)) void precapture_main_rc(u64 r,u32 mode,u32 kind,u64 tmpl,u8 *rc) { RC_PARAMS(r,mode,kind,tmpl,rc); }
#endif

/* ---------------- TIFF reading and writing ---------------- */
typedef struct { const u8 *b; u32 n; } src_t;      /* little-endian TIFF, offsets from b */
typedef struct {
    u16 tag,type; u32 count;
    const u8 *data; u32 bytes;
    u8 slot,dslot,eslot,pad;   /* record value / data / entry position into patch[] */
} ent_t;
typedef struct { u8 *o; u32 pos,cap,bad; u32 patch[16]; } out_t;
enum { P_SUB=1,P_THUMB,P_EXIF,P_GPS,P_JFR,P_OTHER,P_STRIP,P_MNENT,P_MNPV,P_PVSTART };

/* generated by work/make_v7.py from tmp_thumb/lensdb/lensdb.json (118 §4; ref blocks = majority
 * values, CRC16 recomputed by nb()). Matching key = LensID 0x0084 min/max focal x10 (D1). */
typedef struct { u16 fl_min10, fl_max10; u8 dist[84]; u8 vign[116]; } lens_tpl_t;
static const lens_tpl_t LENSDB[7] = {
    {400, 400,
     {144,1,0,0,10,0,0,0,144,1,0,0},
     {144,1,0,0,10,0,0,0,144,1,0,0}},
    {500, 6000,
     {220,5,0,0,10,0,0,0,112,23,0,0},
     {220,5,0,0,10,0,0,0,112,23,0,0}},
    {500, 6000,
     {244,1,0,0,10,0,0,0,244,1,0,0},
     {244,1,0,0,10,0,0,0,244,1,0,0}},
    {850, 850,
     {82,3,0,0,10,0,0,0,82,3,0,0},
     {82,3,0,0,10,0,0,0,82,3,0,0}},
    {1000, 3000,
     {232,3,0,0,10,0,0,0,184,11,0,0},
     {232,3,0,0,10,0,0,0,184,11,0,0}},
    {1050, 1050,
     {26,4,0,0,10,0,0,0,26,4,0,0},
     {26,4,0,0,10,0,0,0,26,4,0,0}},
    {1200, 1200,
     {176,4,0,0,10,0,0,0,184,11,0,0},
     {176,4,0,0,10,0,0,0,184,11,0,0}},
};
static const lens_tpl_t *lensdb_pick(const u8 *lid,u32 fl10) {
    u32 i,lo,hi; if(!lid) return 0;
    lo=(u32)LOAD8(lid+2)|(u32)LOAD8(lid+3)<<8; hi=(u32)LOAD8(lid+10)|(u32)LOAD8(lid+11)<<8;
    for(i=0;i<sizeof LENSDB/sizeof LENSDB[0];i++) {
        if(LENSDB[i].fl_min10==lo && LENSDB[i].fl_max10==hi) return &LENSDB[i];
    }
    (void)fl10; return 0;   /* D4: no template -> write nothing */
}

static u32 ifd_count(const src_t *s,u32 off) {
    if(off<8 || off>s->n-2) return 0;
    u32 n=get16(s->b+off);
    if(!n || n>200 || 2+12*n+4>s->n-off) return 0;
    return n;
}
static const u8 *ent_data(const src_t *s,u32 off,u32 i,u32 *bytes) {
    const u8 *e=s->b+off+2+12*i; u32 t=get16(e+2),c=get32(e+4),sz;
    if(t==0 || t>12 || c>0x100000) return 0;
    sz=type_size[t]*c; *bytes=sz;
    if(sz<=4) return e+8;
    u32 v=get32(e+8); if(v>s->n || sz>s->n-v) return 0;
    return s->b+v;
}
static const u8 *find(const src_t *s,u32 off,u32 tag,u32 type,u32 count) {
    u32 n=ifd_count(s,off),bytes;
    for(u32 i=0;i<n;i++) {
        const u8 *e=s->b+off+2+12*i;
        if(get16(e)!=tag) continue;
        if(get16(e+2)!=type || get32(e+4)!=count) return 0;
        return ent_data(s,off,i,&bytes);
    }
    return 0;
}
static void put(out_t *w,const u8 *p,u32 n) {
    if(w->bad || n>w->cap-w->pos) { w->bad=1; return; }
    if(p) copy(w->o+w->pos,p,n); else zero(w->o+w->pos,n);
    w->pos+=n;
}
static void pad2(out_t *w) { if(w->pos&1) put(w,0,1); }
static ent_t *add(ent_t *t,u32 *n,u32 tag,u32 type,u32 count,const u8 *data) {
    if(*n>=ENT_MAX) return 0;
    ent_t *e=t+(*n)++; zero((u8 *)e,sizeof(*e));
    e->tag=(u16)tag; e->type=(u16)type; e->count=count; e->data=data; e->bytes=type_size[type]*count;
    return e;
}
static int skipped(u32 tag,const u16 *skip,u32 ns) { for(u32 j=0;j<ns;j++) if(skip[j]==tag) return 1; return 0; }
static int copy_entries(const src_t *s,u32 off,ent_t *t,u32 *n,const u16 *skip,u32 ns) {
    u32 k=ifd_count(s,off),bytes; if(!k) return 0;
    for(u32 i=0;i<k;i++) {
        const u8 *e=s->b+off+2+12*i; u32 tag=get16(e);
        if(skipped(tag,skip,ns)) continue;
        const u8 *d=ent_data(s,off,i,&bytes); if(!d) return 0;
        if(!add(t,n,tag,get16(e+2),get32(e+4),d)) return 0;
    }
    return 1;
}
static void sort(ent_t *t,u32 n) {
    for(u32 i=1;i<n;i++) for(u32 j=i;j>0 && t[j-1].tag>t[j].tag;j--) {
        ent_t x; copy((u8 *)&x,(u8 *)&t[j],sizeof(x)); copy((u8 *)&t[j],(u8 *)&t[j-1],sizeof(x));
        copy((u8 *)&t[j-1],(u8 *)&x,sizeof(x));
    }
}
/* IFD then its out-of-line data; stored offsets are (position - rel). Returns position. */
static u32 emit(out_t *w,ent_t *t,u32 n,u32 rel) {
    sort(t,n);
    for(u32 i=1;i<n;i++) if(t[i].tag==t[i-1].tag) w->bad=1;
    pad2(w); if(w->bad) return 0;
    u32 at=w->pos; u8 b[2]; set16(b,n); put(w,b,2);
    u32 vals=w->pos; put(w,0,12*n+4);
    if(w->bad) return 0;
    for(u32 i=0;i<n;i++) {
        u8 *e=w->o+vals+12*i;
        set16(e,t[i].tag); set16(e+2,t[i].type); set32(e+4,t[i].count);
        if(t[i].eslot) w->patch[t[i].eslot]=vals+12*i;
        if(t[i].slot) w->patch[t[i].slot]=vals+12*i+8;
        if(t[i].bytes<=4) { if(t[i].data) copy(e+8,t[i].data,t[i].bytes); continue; }
        pad2(w); if(w->bad) return 0;
        set32(w->o+vals+12*i+8,w->pos-rel);
        if(t[i].dslot) w->patch[t[i].dslot]=w->pos;
        put(w,t[i].data,t[i].bytes);
    }
    return w->bad?0:at;
}
static void patch32(out_t *w,u32 slot,u32 v) { if(!w->patch[slot]) { w->bad=1; return; } set32(w->o+w->patch[slot],v); }

typedef struct { u64 addr; u32 size; } stream_t;
static int stream(u64 d,stream_t *s) {
    if(!d) return 0;
    s->addr=LOAD64(d+8); s->size=LOAD32(d+0x10);
    return s->addr && s->size>=4 && s->size<0x2000000 && s->addr+s->size>s->addr;
}
typedef struct {
    u32 hdr_end,vga_at,fhd_at,main_at,raw_at,end_at,mn_at,thumb_bytes;   /* main_at: where the embedded full-size JPEG goes */
    stream_t main,vga,fhd,jfr;           /* jfr: the embedded full-size JPEG (the main JPEG, or patch's preview in Y) */
} lay_t;
static u8 *nb(u8 *p,const char *v,const u8 *body,u32 n,u32 zeros) {   /* "0100"+body[+0000]+CRC16 */
    copy(p,(const u8 *)v,4); copy(p+4,body,n); zero(p+4+n,zeros);
    set16(p+4+n+zeros,crc16(p,4+n+zeros)); return p;
}

/* Header block: TIFF, IFD0, SubIFDs, GPS, Exif, thumbnail, MakerNote (+PreviewIFD); the
 * VGA preview stream follows directly as the MakerNote's last bytes.
 * h is the CPU view of the stock JPEG header buffer: SOI, APP1 Exif, APP1 XMP, APP2 MPF. */
/* v9 (100 §1.5): strip length per grade. HE family: the ff12 record's BE size field (marker ff12
 * at payload+0x2A, size at +0x2E — A-level, 3 real samples); without that header the per-grade slot
 * is used (the v8 behaviour for HE*). Lossless: marker-less stream — the used span before the zero
 * padding of the slot (B-level); an implausible span fails safe (0 => no NEF for that frame). */
static u32 strip_len(const u8 *pay,u32 cap,u32 g) {
    u32 n;
    if(!pay || !cap) return 0;
    if(g==G_LL) {
        n=cap; while(n && !pay[n-1]) n--;
        return (n>=0x01000000u && n<=cap)?n:0;
    }
    if(pay[0x2a]==0xff && pay[0x2b]==0x12) {
        n=((u32)pay[0x2e]<<24)|((u32)pay[0x2f]<<16)|((u32)pay[0x30]<<8)|pay[0x31];
        if(n && n<=cap) return n;
    }
    return cap;
}
static int build(out_t *w,const u8 *h,u32 hl,const u32 *hlen,u64 m,lay_t *L,u32 flags,u8 *wk,u32 strip) {
    ent_t *t=(ent_t *)(wk+TAB); u32 n;
    u32 g=marker_of(m),kind=LOAD32(m),khz=0; u8 h51[24];      /* v9: marker-3 variant of he51 */
    copy(h51,he51,24); h51[10]=(u8)g; (void)khz;
    if(hl<0x400 || get32(h)!=0xe1ffd8ffu || LOAD32(m+0x2bc)!=0) return 0;   /* M+0x2bc=0: RGGB */
    u32 l1=(u32)h[4]<<8|h[5];
    if(l1<16 || 4+l1>hl || !equal(h+6,(const u8 *)"Exif\0\0",6)) return 0;
    src_t T={h+12,l1-8};
    if(get32(T.b)!=0x002a4949u) return 0;
    const u8 *xmp=0; u32 xmpn=0,at=4+l1,mpf=0;
    while(at+4<=hl && h[at]==0xff && (h[at+1]==0xe1 || h[at+1]==0xe2)) {
        u32 len=(u32)h[at+2]<<8|h[at+3]; if(len<2 || len>hl-at-2) return 0;
        if(h[at+1]==0xe1 && len>2+29 && equal(h+at+4,xmp_ns,29)) { xmp=h+at+4+29; xmpn=len-2-29; }
        if(h[at+1]==0xe2 && len>16 && equal(h+at+4,(const u8 *)"MPF\0",4)) mpf=at+8;
        at+=2+len;
    }
    if(!mpf || at!=hl) return 0;
    /* MPF index must describe exactly this header plus the three descriptor streams. */
    { src_t P={h+mpf,hl-mpf};
      if(get32(P.b)!=0x002a4949u) return 0;
      const u8 *mp=find(&P,get32(P.b+4),0xb002,7,48);
      if(!mp) return 0;
      if(get32(mp+4)!=hlen[0]+L->main.size-2 || get32(mp+20)!=hlen[1]+L->vga.size-2 ||
         get32(mp+36)!=hlen[2]+L->fhd.size-2) return 0; }
    u32 i0=get32(T.b+4),n0=ifd_count(&T,i0); if(!n0) return 0;
    u32 i1=get32(T.b+i0+2+12*n0);
    const u8 *x0=find(&T,i0,0x8769,4,1); if(!x0) return 0;
    u32 ix=get32(x0); if(!ifd_count(&T,ix)) return 0;
    const u8 *g0=find(&T,i0,0x8825,4,1); u32 ig=g0?get32(g0):0;
    if(g0 && !ifd_count(&T,ig)) return 0;
    const u8 *tho=find(&T,i1,0x0201,4,1),*thl=find(&T,i1,0x0202,4,1);
    if(!tho || !thl) return 0;
    u32 thumb=get32(tho),thn=get32(thl);
    if(thn<4 || thumb>T.n || thn>T.n-thumb || get16(T.b+thumb)!=0xd8ff || get16(T.b+thumb+thn-2)!=0xd9ff) return 0;
    const u8 *dto=find(&T,ix,0x9003,2,20);
    /* MakerNote */
    u32 mnc=0,mnoff=0,nx=ifd_count(&T,ix);
    for(u32 i=0;i<nx;i++) if(get16(T.b+ix+2+12*i)==0x927c) { mnc=get32(T.b+ix+2+12*i+4); mnoff=get32(T.b+ix+2+12*i+8); }
    if(mnc<64 || mnoff>T.n || mnc>T.n-mnoff || !equal(T.b+mnoff,nikon2,14)) return 0;
    src_t MN={T.b+mnoff+10,mnc-10}; u32 im=get32(MN.b+4); if(!ifd_count(&MN,im)) return 0;
    const u8 *wb=find(&MN,im,0x000c,5,4),*v54=find(&MN,im,0x0054,7,20),*bnd=find(&MN,im,0x0016,3,4);
    if(!wb || !v54 || !bnd) return 0;
    u32 bx=get16(bnd),by=get16(bnd+2),iw=get16(bnd+4)-bx,ih=get16(bnd+6)-by;
    if(get16(bnd+4)<=bx || get16(bnd+6)<=by || iw>RAW_W || ih>RAW_H || (RAW_W-iw)&1 || (RAW_H-ih)&1) return 0;
    u8 *v=wk+NI;                    /* small computed values */
    for(u32 k=0;k<4;k++) set16(v+k*2,LOAD16(m+0x2b4+2*k));                 /* black   v+0  */
    set16(v+8,(RAW_W-iw)/2); set16(v+10,(RAW_H-ih)/2); set16(v+12,iw); set16(v+14,ih); /* crop v+8 */
    copy(v+16,(const u8 *)"0100",4);                                    /* 0x0058  v+16 */
    if(kind==1) { set32(v+20,0); set32(v+24,0); }                        /* v9/114: real LL = "0100"+0+0 */
    else { set32(v+20,strip); set32(v+24,1); }
    if(flags&F_NOTHUMB) { L->vga.size=0; L->fhd.size=0; L->jfr.size=0; if(!(flags&F_MINITHUMB)) thn=0; }
    u32 jfr=(flags&F_NOTHUMB)?thn:((flags&F_FULL)?L->jfr.size:L->fhd.size);
    set32(v+28,RAW_W); set32(v+32,RAW_H); set32(v+36,strip); set32(v+40,jfr);
    set32(v+44,thn); set32(v+48,L->fhd.size); set32(v+52,(flags&F_NOTHUMB)?thn:L->vga.size);
    if(!get16(v+56)) set16(v+56,BIT_DEPTH);   /* v6: caller may preset the NEF bit depth */ set16(v+58,34713);
    set16(v+60,32803); set16(v+62,1); set16(v+64,2); set16(v+66,6); set32(v+68,1); set32(v+72,0);
    /* NEFInfo (RAW IFD 0xc7d5): blocks 8,9,a,b,d,f; CRC16 per block. Adobe needs 9 and d. */
    u8 *nb5=v+400,*nb6=v+488,*b5=0,*b6=0;   /* v7/118: lens-correction blocks */
    { const u8 *lid=find(&MN,im,0x0084,7,12); const u8 *flr=find(&T,ix,0x920a,5,1);
      u32 fl10=flr?((u32)((int)((const int*)flr)[0])*10/(u32)((const u32*)flr)[1]):0;
      const lens_tpl_t *lt=lensdb_pick(lid,fl10);
      if(lt) { b5=nb(nb5,"0100",lt->dist+4,78,0); b6=nb(nb6,"0100",lt->vign+4,112,0); } }
    u8 *nib=v+128; u8 *b8=nb(nib,"0100",v54+4,16,2),*b9=nib+32,*ba=nib+80,*bb=nib+96,*bd=nib+112,*bf=nib+128;
    copy(b9,wb,32); zero(b9+32,2); set16(b9+34,crc16(b9,34));
    nb(ba,"0100",v,8,0); nb(bb,"0100",v+8,8,0); nb(bd,"0100",(const u8 *)"\x0d\0",2,0); nb(bf,"0100",v+20,8,0);
    out_t ni; zero((u8 *)&ni,sizeof(ni)); ni.o=v+640; ni.cap=512; put(&ni,nikon_ni,18); n=0;  /* v7: +2 blocks */
    if(b5) add(t,&n,0x5,7,84,b5);
    if(b6) add(t,&n,0x6,7,116,b6);
    add(t,&n,0x8,7,24,b8); add(t,&n,0x9,7,36,b9); add(t,&n,0xa,7,14,ba);
    add(t,&n,0xb,7,14,bb); add(t,&n,0xd,7,8,bd); add(t,&n,0xf,7,14,bf);
    if(emit(&ni,t,n,10)!=18 || ni.bad) return 0;
    const u8 *nefinfo=v+512; u32 nin=ni.pos;
    /* ---- emission ---- */
    u8 hd[8]={'I','I',0x2a,0,8,0,0,0}; put(w,hd,8);
    n=0; if(!copy_entries(&T,i0,t,&n,skip0,sizeof(skip0)/2)) return 0;
    add(t,&n,0x00fe,4,1,v+68); add(t,&n,0x0103,3,1,v+66);
    ent_t *e=add(t,&n,0x014a,4,(flags&F_FULL)?3:2,0); if(!e) return 0; e->dslot=P_SUB;
    e=add(t,&n,0x0201,4,1,0); if(!e) return 0; e->slot=P_THUMB;
    add(t,&n,0x0202,4,1,v+44); add(t,&n,0x0214,5,6,refbw);
    if(xmp) add(t,&n,0x02bc,1,xmpn,xmp);
    e=add(t,&n,0x8769,4,1,0); if(!e) return 0; e->slot=P_EXIF;
    if(g0) { e=add(t,&n,0x8825,4,1,0); if(!e) return 0; e->slot=P_GPS; }
    if(dto) add(t,&n,0x9003,2,20,dto);
    if(!add(t,&n,0x9216,1,4,tiffep)) return 0;
    if(emit(w,t,n,0)!=8) return 0;
    u32 sub[3];
    n=0; add(t,&n,0x00fe,4,1,v+68); add(t,&n,0x0103,3,1,v+66); add(t,&n,0x011a,5,1,rat300);
    add(t,&n,0x011b,5,1,rat300); add(t,&n,0x0128,3,1,v+64);
    e=add(t,&n,0x0201,4,1,0); e->slot=P_JFR; add(t,&n,0x0202,4,1,v+40); add(t,&n,0x0213,3,1,v+64);
    sub[0]=emit(w,t,n,0);
    n=0; add(t,&n,0x00fe,4,1,v+72); add(t,&n,0x0100,4,1,v+28); add(t,&n,0x0101,4,1,v+32);
    add(t,&n,0x0102,3,1,v+56); add(t,&n,0x0103,3,1,v+58); add(t,&n,0x0106,3,1,v+60);
    e=add(t,&n,0x0111,4,1,0); e->slot=P_STRIP; add(t,&n,0x0115,3,1,v+62); add(t,&n,0x0116,4,1,v+32);
    add(t,&n,0x0117,4,1,v+36); add(t,&n,0x011a,5,1,rat300); add(t,&n,0x011b,5,1,rat300);
    add(t,&n,0x011c,3,1,v+62); add(t,&n,0x0128,3,1,v+64); add(t,&n,0x828d,3,2,cfa_dim);
    add(t,&n,0x828e,1,4,cfa_rggb); add(t,&n,0x9217,3,1,v+64); add(t,&n,0xc7d5,7,nin,nefinfo);
    add(t,&n,0xc7d6,1,1,one8);
    sub[1]=emit(w,t,n,0);
    if(flags&F_FULL) {
        n=0; add(t,&n,0x00fe,4,1,v+68); add(t,&n,0x0103,3,1,v+66); add(t,&n,0x011a,5,1,rat300);
        add(t,&n,0x011b,5,1,rat300); add(t,&n,0x0128,3,1,v+64);
        e=add(t,&n,0x0201,4,1,0); e->slot=P_OTHER; add(t,&n,0x0202,4,1,v+48); add(t,&n,0x0213,3,1,v+64);
        sub[2]=emit(w,t,n,0);
    }
    u32 gat=0;
    if(g0) { n=0; if(!copy_entries(&T,ig,t,&n,0,0)) return 0; gat=emit(w,t,n,0); }
    n=0; if(!copy_entries(&T,ix,t,&n,skipx,sizeof(skipx)/2)) return 0;
    e=add(t,&n,0x927c,7,4,0); if(!e) return 0; e->eslot=P_MNENT;
    u32 xat=emit(w,t,n,0);
    pad2(w); u32 tat=w->pos; put(w,T.b+thumb,thn);
    /* MakerNote rebuilt with its IFD at offset 8; every value relocated into it. */
    pad2(w); L->mn_at=w->pos; u32 mb=w->pos+10; put(w,nikon2,18);
    n=0; if(!copy_entries(&MN,im,t,&n,skipm,sizeof(skipm)/2)) return 0;
    add(t,&n,0x0004,2,8,quality_raw);
    e=add(t,&n,0x0011,4,1,0); if(!e) return 0; e->slot=P_MNPV;
    add(t,&n,0x003d,3,4,v); add(t,&n,0x0045,3,4,v+8); add(t,&n,0x0046,3,2,tpl_0046);
    add(t,&n,0x0051,7,24,h51);
    if(!add(t,&n,0x0058,7,12,v+16)) return 0;
    add(t,&n,0x008c,7,578,tpl_008c_empty); add(t,&n,0x00a4,7,4,tpl_00a4);   /* v8/118 D5 */
    if(emit(w,t,n,mb)!=mb+8) return 0;
    n=0; add(t,&n,0x0103,3,1,v+66); add(t,&n,0x011a,5,1,rat300); add(t,&n,0x011b,5,1,rat300);
    add(t,&n,0x0128,3,1,v+64); e=add(t,&n,0x0201,4,1,0); e->slot=P_PVSTART;
    add(t,&n,0x0202,4,1,v+52); add(t,&n,0x0213,3,1,v+64);
    u32 pat=emit(w,t,n,mb);
    pad2(w); if(w->bad || !sub[0] || !sub[1] || !xat || !pat) return 0;
    /* ---- layout of the streams after the header block ---- */
    L->hdr_end=w->pos; L->vga_at=w->pos; L->fhd_at=L->vga_at+L->vga.size;
    L->main_at=L->fhd_at+L->fhd.size;
    u32 end=L->main_at+((flags&F_FULL)?L->jfr.size:0);
    L->raw_at=(flags&F_NOTHUMB)?((flags&F_MINITHUMB)?0x12000u:0x10000u):((end+4095)&~4095u);  /* v6/104: exact fixed sizes */
    if((flags&F_NOTHUMB) && end>L->raw_at) return 0;
    L->end_at=L->raw_at+strip; L->thumb_bytes=thn;
    set32(w->o+w->patch[P_SUB],sub[0]); set32(w->o+w->patch[P_SUB]+4,sub[1]);
    if(flags&F_FULL) { set32(w->o+w->patch[P_SUB]+8,sub[2]); patch32(w,P_OTHER,L->fhd_at); }
    patch32(w,P_THUMB,tat); patch32(w,P_EXIF,xat); if(g0) patch32(w,P_GPS,gat);
    patch32(w,P_JFR,(flags&F_NOTHUMB)?tat:((flags&F_FULL)?L->main_at:L->fhd_at)); patch32(w,P_STRIP,L->raw_at);
    patch32(w,P_MNPV,(flags&F_NOTHUMB)?(tat-mb):(pat-mb));
    patch32(w,P_PVSTART,(flags&F_NOTHUMB)?(tat-mb):(L->vga_at-mb));
    if(!w->patch[P_MNENT]) return 0;
    set32(w->o+w->patch[P_MNENT]+4,L->vga_at+L->vga.size-L->mn_at);
    set32(w->o+w->patch[P_MNENT]+8,L->mn_at);
    return !w->bad;
}


/* ---------------- P3' file write ---------------- */
static int write_all(int fd,u64 p,u32 n) { u32 c=0; return WRITE(fd,p,n,&c)==0 && c==n; }
static int jpg_name(u32 id,char *fin,char *tmp) {
    u64 fo=DCF_GET(id); if(!fo) return 0;
    u64 nm=DCF_NAME(fo); u32 len=nm?LOAD32(nm+0x20):0; int ok=0;
    if(nm && len>=12 && len<60) {
        for(u32 i=0;i<len;i++) fin[i]=(char)LOAD8(nm+i);
        fin[len]=0; ok=1;
        for(u32 i=0;i<len;i++) if(!fin[i]) ok=0;
        char *x=fin+len-4;
        if(x[0]!='.' || (x[1]|32)!='j' || (x[2]|32)!='p' || (x[3]|32)!='g') ok=0;
        if(ok) { x[1]='N'; x[2]='E'; x[3]='F'; copy((u8 *)tmp,(const u8 *)fin,len+1); tmp[len-1]='_'; }
    }
    DCF_PUT(fo);
    return ok;
}

/* What the writer task's call identifies: the retained frame, its record and the card config. */
typedef struct {
    u64 r,m,e,J,t_enter;
    u8 *q;
    u32 flags,budget,shot,jid;
    char drive;
} job_t;
/* Everything one NEF needs; lives in the work block so the task stack stays shallow. */
typedef struct {
    u64 r,m,e,J,data;
    u64 t_enter,t_header,t_reg0,t_reg1,t_jpeg0,t_jpeg1,t_nef0,t_raw0,t_raw1,t_raw2;
    u8 *q,*raw,*wk;
    u32 flags,budget,shot,jid,nid,hl,hlen[3],hdr_bytes,total,nsegs,chunks,raw_status,reg_rc,st_jpeg,st_nef,cancel_ok,payload_bytes;
    u32 mtype,stock_mode;                /* registered member type (NEF = 2) and the stock file's writer mode (JPEG = 0) */
    u64 dims_src;                        /* the stock JPEG's descriptor 0 (width/height words), 0 if none */
    char drive,fin[64],tmp[64];
    lay_t L;
} plan_t;

/* The file the writer task is about to write is the JPEG of a retained frame. */
__attribute__((unused)) static int eligible(u64 J,u32 mode,job_t *jb) {
    u64 job,r,m,e,fe; u32 idx,flags; u8 *q;
    if(mode!=0) return 0;
    job=LOAD64(G_WRITER_JOB); if(!job || LOAD8(job+4)) return 0;
    r=LOAD64(job+0x18); idx=LOAD32(job+0xbc)-1;
    if(!r || idx>=4) return 0;
    m=LOAD64(r+0x790); e=LOAD64(r+0x748);
    if(!m || !e || LOAD32(m)!=3) return 0;
    fe=job+0xc0+(u64)idx*0x2d8;
    if(J!=fe+0x48) return 0;
    q=bound(r,e,Q_RETAINED);
    if(!q || LOAD64(J+8)!=m || (LOAD32(J)&15)!=0 || get32(q+0x70)!=LOAD32(m+0x2508)) return 0;
    flags=get32(q+0x60);
    /* patch: without P7's mark the main JPEG has the menu quality; keep the NEF FHD-only */
    if((flags&F_PVQ) && get32(q+0x7c)!=PVQ_MARK) flags&=~F_FULL;
    /* patch: without hook J's mark there is no preview; the NEF is FHD-only, never the main JPEG */
    if((flags&F_PREV) && get32(q+A_PMARK)!=PVJ_MARK) flags&=~F_FULL;
    /* the stock database path handles exactly one group of one file on the primary list */
    if((flags&F_DCF) && !(LOAD32(r+0x14)==1 && LOAD32(r+0x18)==1 && LOAD32(r+0x1c)==LOAD32(J) && LOAD32(r+0x38)==0)) return 0;
    jb->r=r; jb->m=m; jb->e=e; jb->J=J; jb->q=q; jb->flags=flags; jb->budget=get32(q+0x68);
    jb->shot=get32(q+0x70); jb->jid=LOAD32(J); jb->drive=(char)get32(q+0x6c); jb->t_enter=now();
    return 1;
}

/* patch: the preview hook J encoded into this frame's own Y: the record's Y, the stock JPEG's descriptors are that
 * Y's (descriptor 0 = Y+0x38), Y+0x1e set, the region and byte count hook J recorded, within the capacity. */
static int preview_stream(plan_t *p,u64 d0) {
    u64 y=LOAD64(p->r+0x6a8); const u8 *q=p->q;
    if(!y || get64(q+A_Y)!=y || d0!=y+0x38 || LOAD8(y+0x1e)!=1 || LOAD32(y+0x100)!=1) return 0;
    if(!stream(y+0x100,&p->L.jfr) || p->L.jfr.addr!=get64(q+A_YADDR) || p->L.jfr.size!=get32(q+A_PBYTES) ||
       p->L.jfr.size>LOAD32(y+0xf8) || LOAD32(y+0xf8)!=get32(q+A_YCAP)) return 0;
    return 1;
}

/* Parse the JPEG's own buffers, check the names and build the NEF header block. CPU only:
 * no card, database or lock is touched. Returns 0 (work block freed) when no NEF can be made. */
__attribute__((noinline)) static plan_t *prepare(const job_t *jb) {
    u64 J=jb->J,lp=LOAD64(J+0x18),da=LOAD64(J+0x10),hp; u32 hcap,hl;
    u8 *raw,*wk; plan_t *p; out_t w;
    if(!lp || !da) return 0;
    hp=LOAD64(lp); hcap=LOAD32(lp+8); hl=LOAD32(lp+0xc);
    if(!hp || hl<0x400 || hl>hcap || hl>0x40000) return 0;
    raw=(u8 *)ALLOC(WORK_BYTES+63,0); if(!raw) return 0;
    wk=(u8 *)(((u64)raw+63)&~63ul);
    zero(wk+TAB,WORK_BYTES-TAB);
    p=(plan_t *)(wk+PLAN);
    p->raw=raw; p->wk=wk; p->r=jb->r; p->m=jb->m; p->e=jb->e; p->J=J; p->q=jb->q; p->flags=jb->flags;
    p->budget=jb->budget; p->shot=jb->shot; p->jid=jb->jid; p->drive=jb->drive; p->t_enter=jb->t_enter;
    p->nid=(jb->jid&~15u)|2u; p->data=LOAD64(jb->e+0x40);
    p->hl=hl; p->hlen[0]=hl; p->hlen[1]=LOAD32(lp+0x1c); p->hlen[2]=LOAD32(lp+0x2c);
    p->reg_rc=0; p->st_jpeg=0xffffffffu; p->st_nef=0xffffffffu; p->cancel_ok=0xffffffffu;
    { u32 gg=marker_of(p->m); p->payload_bytes=strip_len((const u8 *)p->data,gg?g_payload(gg):0,gg); }
    if(!p->payload_bytes) goto bad;
    p->mtype=2; p->stock_mode=0; p->dims_src=LOAD64(da);
    if(!stream(LOAD64(da),&p->L.main) || !stream(LOAD64(da+8),&p->L.vga) || !stream(LOAD64(da+16),&p->L.fhd)) goto bad;
    if(p->flags&F_FULL) {
        if(!(p->flags&F_PREV)) p->L.jfr=p->L.main;
        else if(!preview_stream(p,LOAD64(da))) p->flags&=~F_FULL;    /* no valid preview: FHD-only, as without hook J's mark */
    }
    if(!jpg_name(p->jid,p->fin,p->tmp) || EXISTS(p->fin)>=0 || EXISTS(p->tmp)>=0) goto bad;
    zero((u8 *)&w,sizeof(w)); w.o=wk; w.cap=HDR_MAX;
    set16(wk+NI+56,(u16)(get32(p->q+0x74)?get32(p->q+0x74):BIT_DEPTH));  /* v6/114: bit depth follows the CFG/menu */
    if(!build(&w,(const u8 *)XLATE(hp),hl,p->hlen,p->m,&p->L,p->flags,wk,p->payload_bytes) || p->L.end_at<p->L.raw_at) goto bad;
    p->hdr_bytes=w.pos; p->total=p->L.end_at+((p->flags&F_FOOTER)?512u:0u); p->t_header=now();
    return p;
bad:
    FREE(raw);
    return 0;
}

static void build_footer(plan_t *p,u32 route) {
    u8 *f=p->wk+FOOT;
    zero(f,512); copy(f,foot_magic,16);
    set32(f+0x10,3); set32(f+0x14,route); set32(f+0x18,(p->flags&F_RAWONLY)?1u:0u); set32(f+0x1c,p->flags);
    set64(f+0x20,p->t_enter); set64(f+0x28,p->t_header); set64(f+0x30,p->t_reg0); set64(f+0x38,p->t_reg1);
    set64(f+0x40,p->t_jpeg0); set64(f+0x48,p->t_jpeg1); set64(f+0x50,p->t_nef0);
    set32(f+0x58,p->reg_rc); set32(f+0x5c,p->st_jpeg);
    set32(f+0x60,p->hdr_bytes); set32(f+0x64,p->L.vga.size); set32(f+0x68,p->L.fhd.size);
    set32(f+0x6c,(p->flags&F_FULL)?p->L.jfr.size:0u); set32(f+0x70,p->L.raw_at); set32(f+0x74,p->L.end_at);
    set32(f+0x78,p->shot); set32(f+0x7c,get32(p->q+0x18));
    set32(f+0x80,p->jid); set32(f+0x84,p->nid); set32(f+0x88,p->hl); set32(f+0x8c,p->nsegs);
    set64(f+0x90,p->r); set64(f+0x98,p->e); set64(f+0xa0,p->m); set64(f+0xa8,p->data); set64(f+0xb0,p->J);
    set64(f+0xb8,(u64)(p->wk+JP));
    set64(f+0xc0,p->L.vga.addr); set64(f+0xc8,p->L.fhd.addr); set64(f+0xd0,(p->flags&F_FULL)?p->L.jfr.addr:0ul);
    set64(f+0xd8,p->t_raw0); set64(f+0xe0,p->t_raw1); set64(f+0xe8,p->t_raw2);
    set32(f+0xf0,p->chunks); set32(f+0xf4,p->raw_status); set64(f+0xf8,p->L.main.addr);
    copy(f+0x108,identity,8); copy(f+0x110,(const u8 *)p->fin,48);
    copy(f+0x140,p->q,128);
    copy(f+0x1c0,p->q+A_KIND,0x3c);              /* aux +0x84..+0xbf: kind, value, M before, applied, Y, preview */
    set32(f+0x1fc,crc32(f,0x1fc));
}

/* patch route: raw file calls under a temporary name, then rename. Used without the DCF flag and
 * as the fallback when registration fails. The NEF pairs with its JPEG after the next scan. */
/* v6 (117 §3 ②③): FAT/exFAT timestamps from the RTC 7B at q+A_RTC. */
static void set_file_time(const char *path,const u8 *rtc7) {
    u16 d=0,tm=0; u8 st[3][4]; u32 id; u32 i;
    ((void(*)(const void*,void*,void*,void*))0x408be2e8ul)(rtc7,&d,&tm,0);
    for(i=0;i<3;i++) { st[i][0]=(u8)d; st[i][1]=(u8)(d>>8); st[i][2]=0; st[i][3]=0; }
    st[0][2]=(u8)tm; st[0][3]=(u8)(tm>>8); st[2][2]=(u8)tm; st[2][3]=(u8)(tm>>8);
    id=(u32)OPEN(path,0,0x20); if((int)id<0) return;
    ((void(*)(u64))0x40d2bfb4ul)(0xa02e81dd8ul);
    ((u32(*)(u32,void*,void*,void*))0x408b9ea4ul)(id,st[0],st[1],st[2]);
    ((void(*)(u64))0x40d2bf60ul)(0xa02e81dd8ul);
    CLOSE(id);
}
/* v6 (112 §P1): card settings path packs the grade shadow byte with 0x120B. */
typedef u32 (*ds_get_fn)(u64,u32,u32*); typedef u32 (*ds_set_fn)(u64,u32,u32,u64);
__attribute__((used)) u32 precapture_bank_get(u64 a0,u32 id,u32 *out) {
    if(id==0x120B) { *out=(u32)(LOAD8(0xa03d5c029ul)<<8)|LOAD8(0xa03d5c028ul); return 1; }
    return ((ds_get_fn)0x410156d0ul)(a0,id,out);
}
__attribute__((used)) u32 precapture_bank_set(u64 a0,u32 id,u32 value,u64 a3) {
    if(id==0x120B) {
        STORE8(0xa03d5c028ul,(u8)value);
        STORE8(0xa03d5c029ul,(u8)((value>>8)&0xff));  /* high byte 0 -> grade default */
        return 1;
    }
    return ((ds_set_fn)0x41015860ul)(a0,id,value,a3);
}
__attribute__((noinline)) static void raw_route(plan_t *p) {
    u8 *wk=p->wk; const lay_t *L=&p->L;
    u32 flags=p->flags,budget=p->budget,status=S_DONE,written=0,chunks=0,payload=p->payload_bytes;
    u32 mainsz=(flags&F_FULL)?L->jfr.size:0u,pad=L->raw_at-L->main_at-mainsz;
    u64 t0=now(),after; int fd;
#ifndef NEG_NO_CLEAN                 /* negative-control builds only */
    CLEAN(wk,p->hdr_bytes);
#endif
    CLEAN(wk+ZEROS,4096);
    fd=CREATE(p->tmp,0x20);
    if(fd<0) { stop_file(p->drive,S_WRITE_FAIL,p->shot); return; }
    p->t_raw0=now();
    if(!write_all(fd,(u64)wk,p->hdr_bytes) || !write_all(fd,L->vga.addr,L->vga.size) || !write_all(fd,L->fhd.addr,L->fhd.size) ||
       (mainsz && !write_all(fd,L->jfr.addr,mainsz)) || (pad && !write_all(fd,(u64)(wk+ZEROS),pad)))
        status=S_WRITE_FAIL;
    p->t_raw1=now();
    if(status==S_DONE && p->t_raw1-t0>=budget) status=S_BUDGET;
#ifdef NEG_READ_PAYLOAD               /* negative-control builds only */
    if(LOAD32(p->data+0x1000)==0x12345678u) status=S_WRITE_FAIL;
#endif
    while(status==S_DONE && written<payload) {
        u32 part=payload-written,c=0; int rc;
        if(part>CHUNK) part=CHUNK;
        rc=WRITE(fd,p->data+written,part,&c);
        written+=c<=part?c:0u; chunks++;
        after=now();
        if(rc!=0 || c!=part) status=S_WRITE_FAIL;
        else if(after-t0>=budget && written<payload) status=S_BUDGET;
    }
    p->t_raw2=now(); p->chunks=chunks; p->raw_status=status;
    if(flags&F_FOOTER) {
        build_footer(p,2); CLEAN(wk+FOOT,512);
        if(!write_all(fd,(u64)(wk+FOOT),512) && status==S_DONE) status=S_WRITE_FAIL;
    }
    if(CLOSE(fd)!=0 && status==S_DONE) status=S_WRITE_FAIL;
    if(status==S_DONE && RENAME(p->tmp,p->fin)!=0) status=S_RENAME_FAIL;
    if(status==S_DONE) set_file_time(p->fin,p->q+A_RTC);   /* v6: mtime = capture wall clock */
    if(status!=S_DONE) stop_file(p->drive,status,p->shot);
}

/* Add a member of the given DCF type (NEF = 2) to the group keyed by the first file id, exactly as the
 * stock creation does for a RAW+JPEG shot: creation lock held around the member add and the
 * remaining-shots update. */
__attribute__((noinline)) static u32 register_member(const plan_t *p,u32 type) {
    u32 drive=p->jid>>29,rc; u64 db; u8 ent[16] __attribute__((aligned(8)));
    if(drive>1) return RC_NO_DB;
    db=LOAD64(G_DB+8ul*drive); if(!db) return RC_NO_DB;
    zero(ent,16); set32(ent,type); set64(ent+8,p->total);       /* {type, 0, exact file bytes} */
    if(LOCK(G_CREATE_LOCK,0xc8,10)!=DB_OK) return RC_LOCK;
    rc=DB_ADD(db,p->jid,ent);
#ifndef NEG_NO_REMAIN                 /* negative-control builds only */
    if(rc==DB_OK) DB_REMAIN(1);
#endif
#ifndef NEG_NO_UNLOCK                 /* negative-control builds only */
    UNLOCK(G_CREATE_LOCK);
#endif
    return rc;
}

static int seg(u8 *jp,u32 *n,u64 addr,u32 size,u64 *sum) {
    if(!size) return 1;                                         /* empty segments never enter the table */
    if(*n>=SEG_MAX || !addr) return 0;
    set64(jp+0x68+16*(*n),addr); set32(jp+0x70+16*(*n),size); (*n)++; *sum+=size;
    return 1;
}
/* Write the registered NEF with the stock writer in its explicit-segment mode 3. */
__attribute__((noinline)) static u32 stock_nef(plan_t *p,u32 raw_only) {
    u8 *wk=p->wk,*jp=wk+JP,*a=wk+JA,*d=wk+JD,*t=wk+JT;
    const lay_t *L=&p->L;
    u32 n=0,mainsz=(p->flags&F_FULL)?L->jfr.size:0u,pad=L->raw_at-L->main_at-mainsz,nst;
    u64 sum=0,c0,c1;
    zero(jp,0x290); zero(a,32); zero(d,16); zero(t,32);
    set32(jp,p->nid); set64(jp+8,p->m); set64(jp+0x10,(u64)a);
    /* descriptor 0: the stock attribute step stores these two words as the object's width and
     * height; they are the JPEG's own, so a sibling write leaves the values unchanged */
#ifndef NEG_DIMS_ZERO                 /* negative-control builds only */
    if(p->dims_src) { set16(d+8,LOAD16(p->dims_src+4)); set16(d+10,LOAD16(p->dims_src+6)); }
#endif
    set64(a,(u64)d);
    if(raw_only && L->thumb_bytes && L->thumb_bytes<0x10000u) { set32(t+0x10,L->thumb_bytes); set64(a+0x18,(u64)t); }
    if(pad>4096 || !seg(jp,&n,(u64)wk,p->hdr_bytes,&sum) || !seg(jp,&n,L->vga.addr,L->vga.size,&sum) ||
       !seg(jp,&n,L->fhd.addr,L->fhd.size,&sum) || !seg(jp,&n,L->jfr.addr,mainsz,&sum) ||
       !seg(jp,&n,(u64)(wk+ZEROS),pad,&sum) || !seg(jp,&n,p->data,p->payload_bytes,&sum)) goto bad;
    p->t_nef0=now();
    if(p->flags&F_FOOTER) {
        p->nsegs=n+1;
        build_footer(p,1); CLEAN(wk+FOOT,512);
        if(!seg(jp,&n,(u64)(wk+FOOT),512,&sum)) goto bad;
    } else p->nsegs=n;
    if(sum!=p->total) goto bad;
#ifdef NEG_BAD_TOTAL                  /* negative-control builds only */
    sum+=1;
#endif
    set64(jp+0x30,sum); set16(jp+0x218,n);
#ifndef NEG_NO_CLEAN                  /* negative-control builds only */
    CLEAN(wk,p->hdr_bytes);
#endif
    CLEAN(wk+ZEROS,4096);
#ifdef NEG_READ_PAYLOAD               /* negative-control builds only */
    if(LOAD32(p->data+0x1000)==0x12345678u) goto bad;
#endif
#ifdef TEST_FORCE_BAD                 /* test builds only: take the internal-failure exit after registration */
    goto bad;
#endif
    c0=now(); nst=ORIG_WRITE(0,3,(u64)jp); c1=now();
    if(nst!=0) stop_file(p->drive,S_WRITE_FAIL,p->shot);        /* the stock writer cancelled the member itself */
    else if(EXISTS(p->fin)<0) stop_file(p->drive,S_MISSING,p->shot);
    else if(c1-c0>=p->budget) stop_file(p->drive,S_BUDGET,p->shot);
    if(nst==0 && EXISTS(p->fin)>=0) set_file_time(p->fin,p->q+A_RTC);   /* v6: mtime = capture wall clock */
    return nst;
bad:
#ifndef NEG_NO_CANCEL                 /* negative-control builds only */
    DB_CANCEL(p->nid);                                          /* never leave a reservation nobody writes */
#endif
    stop_file(p->drive,S_WRITE_FAIL,p->shot);
    return RC_INTERNAL;
}

/* RAW-only: the JPEG reservation is cancelled after the NEF is on the card. The cancel has no
 * result, so look at the object afterwards: gone, or no longer in a reserved state (2, 3, 8). */
__attribute__((noinline)) static int jpeg_cancelled(u32 jid) {
    u64 o; u32 st;
    DB_CANCEL(jid);
    o=DCF_GET(jid); if(!o) return 1;
    st=LOAD32(o+0x70); DCF_PUT(o);
    return !(st==2 || st==3 || st==8);
}

static void release_e(const job_t *jb) { unbind(jb->q); FREE_E(jb->e); STORE64(jb->r+0x748,0); }

/* Everything after the header is built: register, write the JPEG and the NEF, or fall back. */
__attribute__((noinline)) static u32 flow(plan_t *p,u64 J) {
    u32 st;
    if(!(p->flags&F_DCF)) {                                              /* patch behaviour */
        st=ORIG_WRITE(0,p->stock_mode,J); p->st_jpeg=st;
        if(st==0) raw_route(p);
        return st;
    }
    p->t_reg0=now(); p->reg_rc=register_member(p,p->mtype); p->t_reg1=now();
    if(p->reg_rc!=DB_OK) {                                               /* no stock registration: JPEG, then patch route */
        st=ORIG_WRITE(0,p->stock_mode,J); p->st_jpeg=st;
        if(st==0) raw_route(p);
    } else if(!(p->flags&F_RAWONLY)) {                                   /* RAW+JPEG: stock order JPEG, NEF */
#ifdef NEG_ORDER                      /* negative-control builds only: NEF before JPEG */
        p->st_nef=stock_nef(p,0);
#endif
        p->t_jpeg0=now(); st=ORIG_WRITE(0,p->stock_mode,J); p->t_jpeg1=now(); p->st_jpeg=st;
#ifndef NEG_ORDER
        p->st_nef=stock_nef(p,0);
#endif
    } else {                                                             /* RAW-only: NEF first, then drop the JPEG member */
        p->st_nef=stock_nef(p,1);
        if(p->st_nef==0) p->cancel_ok=jpeg_cancelled(p->jid);
        if(p->st_nef==0 && p->cancel_ok==1) st=0;
        else { p->t_jpeg0=now(); st=ORIG_WRITE(0,p->stock_mode,J); p->t_jpeg1=now(); p->st_jpeg=st; }   /* NEF failed or the cancel did not hold */
    }
    return st;
}

__attribute__((noinline,unused)) static u32 take(const job_t *jb,u64 J) {
    plan_t *p; u32 st;
    if(stopped(jb->drive)) { st=ORIG_WRITE(0,0,J); release_e(jb); return st; }   /* an earlier failure: JPEG only */
    p=prepare(jb);
    if(!p) { st=ORIG_WRITE(0,0,J); release_e(jb); return st; }          /* JPEG only, E released below */
    st=flow(p,J);
    FREE(p->raw);
#ifndef NEG_LEAK_E                    /* negative-control builds only */
    release_e(jb);
#endif
    return st;
}

/* P3'. Original: mov w0,wzr; mov w1,w21; mov x2,x20; bl 0x406cc134 (result stored by the caller). */
__attribute__((used)) u32 precapture_write_file(u32 op,u32 mode,u64 J) {
    job_t jb;
    if(op!=0 || !eligible(J,mode,&jb)) return ORIG_WRITE(op,mode,J);
    return take(&jb,J);
}
