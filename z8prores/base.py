"""Firmware base descriptors: which public base an EG belongs to and where a recipe
offset lands in it.

The 03.11 -> 03.12 displacement is not a flat shift: code between the three documented
insertions moves +24 / +104, the struct-field band moves +128, and data tables and the
feature caves stay put. The table below is the measured per-1KiB-page displacement
(tmp_0312/align.json, comparison campaign 152_COMPARE_0312), reduced to segments.

`anchor()` is the only place that knows about base geometry. Recipes are written once in
03.11 coordinates; `at()` translates a recipe offset into the base under construction and
`va()` gives the same location as a guest virtual address (eg file offset + 0x40160000,
uniform in this image). Every translated window is still hash-checked against the base
before a byte is written, so a wrong anchor fails the build instead of landing a patch on
the wrong code.
"""
SEGMENTS_0312 = (
    (0x0, 0xd30c00, 0),
    (0xd30c00, 0xd38000, 24),
    (0xd38000, 0xd78000, 104),
    (0xd78000, 0xd78400, 640),
    (0xd78400, 0xd7cc00, 104),
    (0xd7cc00, 0xd7d000, -19424),
    (0xd7d000, 0xd7d400, -2272),
    (0xd7d400, 0xd85400, 104),
    (0xd85400, 0xd86000, -3168),
    (0xd86000, 0xd89800, 104),
    (0xd89800, 0xd8a000, 4256),
    (0xd8a000, 0xd8a800, 104),
    (0xd8a800, 0xd8b000, -1280),
    (0xd8b000, 0xd96c00, 104),
    (0xd96c00, 0xd97000, 51040),
    (0xd97000, 0xd97800, 104),
    (0xd97800, 0xd97c00, -5120),
    (0xd97c00, 0xd98000, 47552),
    (0xd98000, 0xd98400, 104),
    (0xd98400, 0xd98800, -8608),
    (0xd98800, 0xd98c00, 44064),
    (0xd98c00, 0xd99000, 104),
    (0xd99000, 0xd99400, -12096),
    (0xd99400, 0xd9a000, 104),
    (0xd9a000, 0xd9a400, -15584),
    (0xd9a400, 0xd9a800, 37088),
    (0xd9a800, 0xd9ac00, 104),
    (0xd9ac00, 0xd9b000, -19072),
    (0xd9b000, 0xd9b400, 33600),
    (0xd9b400, 0xd9bc00, 104),
    (0xd9bc00, 0xd9c000, -22560),
    (0xd9c000, 0xd9c400, 30112),
    (0xd9c400, 0xd9c800, 104),
    (0xd9c800, 0xd9cc00, -26048),
    (0xd9cc00, 0xd9d000, 26624),
    (0xd9d000, 0xd9d400, 104),
    (0xd9d400, 0xd9d800, -29536),
    (0xd9d800, 0xd9e000, 104),
    (0xd9e000, 0xd9e400, -704),
    (0xd9e400, 0xda1000, 104),
    (0xda1000, 0xda1400, 9760),
    (0xda1400, 0xda1800, 12992),
    (0xda1800, 0xda1c00, 8160),
    (0xda1c00, 0xda2000, 104),
    (0xda2000, 0xda4400, 3328),
    (0xda4400, 0xda5400, 104),
    (0xda5400, 0xda5c00, -9568),
    (0xda5c00, 0xda6400, 1920),
    (0xda6400, 0xda6800, -2144),
    (0xda6800, 0xdaec00, 104),
    (0xdaec00, 0xdaf000, 1120),
    (0xdaf000, 0xdb3800, 104),
    (0xdb3800, 0xdb3c00, -250304),
    (0xdb3c00, 0xdb4c00, 104),
    (0xdb4c00, 0xdb5000, 736),
    (0xdb5000, 0xdb5800, 104),
    (0xdb5800, 0xdb5c00, 416),
    (0xdb5c00, 0xdc5c00, 104),
    (0xdc5c00, 0xdc6000, -64),
    (0xdc6000, 0xdfb800, 104),
    (0xdfb800, 0xdfbc00, 864),
    (0xdfbc00, 0xe78000, 104),
    (0xe78000, 0xe78400, -352),
    (0xe78400, 0xe87c00, 104),
    (0xe87c00, 0xe88000, -4896),
    (0xe88000, 0xe88400, -5504),
    (0xe88400, 0xec9c00, 104),
    (0xec9c00, 0xeca000, 1280),
    (0xeca000, 0xeeb000, 104),
    (0xeeb000, 0xeeb400, 2272),
    (0xeeb400, 0xef6800, 104),
    (0xef6800, 0xef6c00, 4672),
    (0xef6c00, 0xef7000, 2848),
    (0xef7000, 0xef7400, 4384),
    (0xef7400, 0xef7800, 0),
    (0xef7800, 0xef7c00, 104),
    (0xef7c00, 0xef8000, 1056),
    (0xef8000, 0xefa400, 104),
    (0xefa400, 0xefa800, -160),
    (0xefa800, 0xefc800, 104),
    (0xefc800, 0xefcc00, 9280),
    (0xefcc00, 0xefec00, 104),
    (0xefec00, 0xeff000, -736),
    (0xeff000, 0xf03400, 104),
    (0xf03400, 0xf03800, -64),
    (0xf03800, 0xf05400, 104),
    (0xf05400, 0xf05800, -192),
    (0xf05800, 0xf05c00, 104),
    (0xf05c00, 0xf06000, -1984),
    (0xf06000, 0xf1d000, 104),
    (0xf1d000, 0xf1d400, 1632),
    (0xf1d400, 0xf1d800, 544),
    (0xf1d800, 0xf27c00, 104),
    (0xf27c00, 0xf28400, -640),
    (0xf28400, 0xf28800, 104),
    (0xf28800, 0xf28c00, -2848),
    (0xf28c00, 0xf38000, 104),
    (0xf38000, 0xf38400, 320),
    (0xf38400, 0xf3e800, 104),
    (0xf3e800, 0xf3ec00, 480),
    (0xf3ec00, 0xf40400, 104),
    (0xf40400, 0xf40800, 352),
    (0xf40800, 0xf40c00, 104),
    (0xf40c00, 0xf41000, -64),
    (0xf41000, 0xf41800, 104),
    (0xf41800, 0xf41c00, 320),
    (0xf41c00, 0xf42800, 104),
    (0xf42800, 0xf43000, 512),
    (0xf43000, 0xf43400, -1120),
    (0xf43400, 0xf43800, 736),
    (0xf43800, 0xf49000, 104),
    (0xf49000, 0xf49400, -9384096),
    (0xf49400, 0xf4a400, 104),
    (0xf4a400, 0xf4a800, -800),
    (0xf4a800, 0xf4fc00, 104),
    (0xf4fc00, 0xf50000, -542912),
    (0xf50000, 0xf76800, 104),
    (0xf76800, 0xf76c00, -736),
    (0xf76c00, 0xf7c000, 104),
    (0xf7c000, 0xf7c400, 288),
    (0xf7c400, 0xfaa400, 104),
    (0xfaa400, 0xfaa800, -352),
    (0xfaa800, 0xfb6c00, 104),
    (0xfb6c00, 0xfb7000, 192),
    (0xfb7000, 0xfb7800, 104),
    (0xfb7800, 0xfb7c00, 192),
    (0xfb7c00, 0xfbac00, 104),
    (0xfbac00, 0xfbb000, 0),
    (0xfbb000, 0xfbb400, -96),
    (0xfbb400, 0xfbc400, 104),
    (0xfbc400, 0xfbc800, 32),
    (0xfbc800, 0xfbcc00, 104),
    (0xfbcc00, 0xfbd000, 256),
    (0xfbd000, 0xfc2c00, 104),
    (0xfc2c00, 0xfc3c00, 2912),
    (0xfc3c00, 0xfc5000, 104),
    (0xfc5000, 0xfc5c00, -5504),
    (0xfc5c00, 0xfcd000, 104),
    (0xfcd000, 0xfcd400, -114112),
    (0xfcd400, 0xfe4c00, 104),
    (0xfe4c00, 0xfe5000, -97440),
    (0xfe5000, 0x1004800, 104),
    (0x1004800, 0x1004c00, 2080),
    (0x1004c00, 0x100c800, 104),
    (0x100c800, 0x100d000, -448),
    (0x100d000, 0x100d400, 104),
    (0x100d400, 0x100d800, 3840),
    (0x100d800, 0x1021c00, 104),
    (0x1021c00, 0x1022000, -160),
    (0x1022000, 0x1024000, 104),
    (0x1024000, 0x1024400, -96),
    (0x1024400, 0x103cc00, 104),
    (0x103cc00, 0x103d000, -1088),
    (0x103d000, 0x1046c00, 104),
    (0x1046c00, 0x1047000, -640),
    (0x1047000, 0x1052800, 104),
    (0x1052800, 0x1052c00, 512),
    (0x1052c00, 0x1078000, 104),
    (0x1078000, 0x1078400, 1376),
    (0x1078400, 0x10b9400, 104),
    (0x10b9400, 0x10b9800, 576),
    (0x10b9800, 0x10fd000, 104),
    (0x10fd000, 0x10fd400, 2624),
    (0x10fd400, 0x10fd800, 104),
    (0x10fd800, 0x10fdc00, 1152),
    (0x10fdc00, 0x110c000, 104),
    (0x110c000, 0x110c400, 12192),
    (0x110c400, 0x110fc00, 104),
    (0x110fc00, 0x1110000, 320),
    (0x1110000, 0x111a800, 104),
    (0x111a800, 0x1143400, 128),
    (0x1143400, 0x3f7e000, 0),
    (0x3f7e000, 0x3f7e400, -40),
    (0x3f7e400, 0x3f7e800, -48),
    (0x3f7e800, 0x3f7ec00, -40),
    (0x3f7ec00, 0x4cd1400, 0),
    (0x4cd1400, 0x4cd1800, -16),
    (0x4cd1800, 0x4cd2000, 0),
    (0x4cd2000, 0x4cd2400, -8),
    (0x4cd2400, 0x4d2a400, 0),
    (0x4d2a400, 0x4d2a800, -24),
    (0x4d2a800, 0x4d30400, 0),
    (0x4d30400, 0x4d30800, -104),
    (0x4d30800, 0x4d32400, 0),
    (0x4d32400, 0x4d32800, -64),
    (0x4d32800, 0x4d33000, 0),
    (0x4d33000, 0x4d33400, -104),
    (0x4d33400, 0x4d6b400, 0),
    (0x4d6b400, 0x4d6b800, -16),
    (0x4d6b800, 0x4da4800, 0),
    (0x4da4800, 0x4da4c00, -24),
    (0x4da4c00, 0x4e04c00, 0)
)

BASES = {
    '03.11': dict(module='eg2070_0311b0.bi', identity='03.11.b0', segments=()),
    '03.12': dict(module='eg2070_031200.bi', identity='03.12.00', segments=SEGMENTS_0312),
}
EG_VA = 0x40160000
CURRENT = {'base': '03.11'}


def identity_of(eg):
    text = bytes(eg[0x14EAA90:0x14EAA98])
    for name, base in BASES.items():
        # match the version family (03.12.p2 and 03.12.00 are the same base)
        if text[:5] == base['identity'][:5].encode():
            return name
    # Synthetic identities (test images) keep the 03.11 recipe anchors: that is the family
    # every recipe is written in. Known public bases override above.
    return '03.11'


def anchor(base, off):
    for lo, hi, delta in BASES[base]['segments']:
        if lo <= off < hi:
            return off + delta
    return off


def at(off, base=None):
    return anchor(base or CURRENT['base'], off)


def va(off, base=None):
    return EG_VA + at(off, base)


def locked(row, field):
    """Review hash of a window in the base under construction.

    Recipes are reviewed in 03.11 coordinates; a base whose window content or branch
    encoding differs carries its own lock under `<field>_<base>`. A window without a
    lock for the current base is refused at build time.
    """
    return row.get(field + '_' + CURRENT['base'], row[field])


def profile_path(name):
    """Review profile for the base under construction (03.11 keeps the original file)."""
    from pathlib import Path as _P
    here = _P(__file__).resolve().parent.parent / 'resources'
    if CURRENT['base'] == '03.11':
        return here / name
    return here / (name.replace('.json', '') + '_' + CURRENT['base'].replace('.', '') + '.json')
