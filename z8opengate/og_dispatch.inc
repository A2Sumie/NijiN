/* og_rate_pick dispatch fragment (110 §E): base -> OG rows */
/* Merge: replace the two hard-coded base tests in og_rate_pick with this loop. */
static const struct { u64 base; const u32 *rows; u32 count; } og_rate_map[] = {
    {TYPE2_BASE, (const u32 *)og_rows_type2, 42},
    {TYPE1_BASE, (const u32 *)og_rows_type1, 15},
    {0x42ab3a50ul, (const u32 *)og_rows_type0_hq, 9},
    {0x408bfbd0ul, (const u32 *)og_rows_type0_422, 9},
    {0x408bfca8ul, (const u32 *)og_rows_type0_lt, 9},
    {0x408bfd80ul, (const u32 *)og_rows_type0_proxy, 9},
};
