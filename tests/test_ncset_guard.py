"""NCSET load-walk bounds guard: per-item unit + mutation tests (c2-fix-plan Fix 1 + Fix 4).

Models the six per-item walks of the settings loader (123_T4_CHAIN §3) and the guard stub
semantics v11.1 installs at every walk site (z8precapture/firmware.c):

    an item is applied iff   0x80 <= total <= 2 MiB   and
        (item pointer - file-image base) + item size <= total      (64-bit unsigned)

Both comparison operands are file-image-base relative — unlike the v10 stub, which added the
header length to the 32B header copy at x25 and compared across two regions ("skip everything
or allow everything" depending on heap placement, 126 §2).

Cases (one per loop family where it matters):
  * real camera sample: every item in range -> everything applied
  * short files (old firmware, fewer slots): tail items skipped individually, siblings applied
  * forged over-long entries: that item refused, siblings applied (per family)
  * corrupt header length: fail-safe refusal, never "allow everything"
  * v10's cross-region bound as a negative control: placement-dependent all-skip/all-allow

Blob item sizes come from firmware-side SIZES tables whose bytes are not part of the file; the
model uses uniform sizes within each blob family. The decision under test is base-relative and
distribution-independent for items that tile their segment, so this loses no coverage of the
boundary predicate itself.
"""
import os
import struct
import sys
from pathlib import Path

# A device settings sample is user-supplied and never distributed (see NOTICE.md).
# Point NIJIN_SETTINGS_SAMPLE at your own local copy to run the real-sample test;
# it skips loudly when the variable is absent.
SAMPLE = Path(os.environ['NIJIN_SETTINGS_SAMPLE']) if os.environ.get('NIJIN_SETTINGS_SAMPLE') else None
MASK = (1 << 64) - 1

# firmware walk counts (variant 3, 4 banks) — 123 §2 (ROM variant table / R2)
COUNT1, COUNT2, COUNT3, COUNT4, SCOUNT, S3COUNT = 1112, 184, 331, 79, 11, 617


# ---------------------------------------------------------------- stub semantics

def guard_item(item_ptr, item_size, base, total):
    """precapture_ncset_guard / _s28 / _s24 decision for one item (True = apply)."""
    if total < 0x80 or total > 0x200000:              # header-length plausibility clamp
        return False
    end_off = ((item_ptr - base) & MASK) + item_size  # wraps huge when item_ptr < base
    return end_off <= total


def guard_item_v10(item_ptr, item_size, header_copy, total):
    """v10 stub: bound = header copy + total — a cross-region compare (126 §2)."""
    return ((item_ptr + item_size) & MASK) <= ((header_copy + total) & MASK)


# ---------------------------------------------------------------- walk model

def parse(data):
    total = struct.unpack_from('<I', data, 0x10)[0]
    banks = struct.unpack_from('<I', data, 0x14)[0]
    dirs = [struct.unpack_from('<I', data, 0x20 + 4 * i)[0] for i in range(18)]
    groups = [(dirs[0], dirs[1:2]), (dirs[2], dirs[3:7]), (dirs[7], dirs[8:13]), (dirs[13], dirs[14:18])]
    return total, banks, groups


def walks(data, counts=(COUNT1, COUNT2, COUNT3, COUNT4, SCOUNT, S3COUNT)):
    """Yield (family, item_ptr, item_size) for every per-item apply of the load walk.

    Streaming follows the loader (t4_dis_load disassembly): L1 scalars then L2 blobs fill the
    g0 segment, (LB scalars + LC blobs) run per g1 bank segment, LS scalars per g2 record
    segment, L3 scalars per g3 bank segment; the cursor is contiguous from 0x68.
    """
    c1, c2, c3, c4, c5, c6 = counts
    cursor = 0x68                                 # 0x20 header + 0x48 directory
    for i in range(c1):
        yield 'L1', cursor + 4 * i, 4
    cursor += 4 * c1
    blob = 4                                      # uniform blob size (see module docstring)
    for i in range(c2):
        yield 'L2', cursor + blob * i, blob
    cursor += blob * c2
    for _ in range(4):
        for i in range(c3):
            yield 'LB', cursor + 4 * i, 4
        cursor += 4 * c3
        for i in range(c4):
            yield 'LC', cursor + blob * i, blob
        cursor += blob * c4
    for _ in range(5):
        for i in range(c5):
            yield 'LS', cursor + 4 * i, 4
        cursor += 4 * c5
    for _ in range(4):
        for i in range(c6):
            yield 'L3', cursor + 4 * i, 4
        cursor += 4 * c6


def synthetic(slots_per_bank=S3COUNT):
    """A minimal well-formed 4-bank settings file; S3 segments hold slots_per_bank slots each."""
    blob = 4
    seg0 = 4 * COUNT1 + blob * COUNT2
    seg_bank = 4 * COUNT3 + blob * COUNT4
    seg_rec = 4 * SCOUNT
    seg_s3 = 4 * slots_per_bank
    dirs = [seg0, 0x68, seg_bank, 0, 0, 0, 0, seg_rec, 0, 0, 0, 0, 0, seg_s3, 0, 0, 0, 0]
    off = 0x68
    dirs[1] = off
    off += seg0
    for i in range(4):
        dirs[3 + i] = off
        off += seg_bank
    for i in range(5):
        dirs[8 + i] = off
        off += seg_rec
    for i in range(4):
        dirs[14 + i] = off
        off += seg_s3
    data = bytearray(off + 2)
    struct.pack_into('<I', data, 0x10, len(data))
    struct.pack_into('<I', data, 0x14, 4)
    for i, v in enumerate(dirs):
        struct.pack_into('<I', data, 0x20 + 4 * i, v)
    return bytes(data)


# ---------------------------------------------------------------- tests

def test_real_sample_every_item_applied():
    if SAMPLE is None or not SAMPLE.exists():
        import pytest
        pytest.skip('NIJIN_SETTINGS_SAMPLE not set: device settings sample is user-supplied and not distributed')
    data = SAMPLE.read_bytes()
    total, banks, _ = parse(data)
    items = list(walks(data))
    skipped = [(fam, ptr) for fam, ptr, size in items if not guard_item(ptr, size, 0, total)]
    assert not skipped, f'{len(skipped)} items out of file on the real sample: {skipped[:3]}'
    assert banks == 4 and total == len(data)
    assert len(items) == COUNT1 + COUNT2 + 4 * (COUNT3 + COUNT4) + 5 * SCOUNT + 4 * S3COUNT


def test_short_file_skips_tail_items_individually():
    # old file with 610 S3 slots/bank; the firmware walk still runs 617
    data = synthetic(slots_per_bank=610)
    total = len(data)
    items = list(walks(data, counts=(COUNT1, COUNT2, COUNT3, COUNT4, SCOUNT, S3COUNT)))
    s3 = [(ptr, guard_item(ptr, size, 0, total)) for fam, ptr, size in items if fam == 'L3']
    skipped = [p for p, ok in s3 if not ok]
    applied = [p for p, ok in s3 if ok]
    assert len(skipped) == 4 * 7, f'expected 28 tail items refused, got {len(skipped)}'
    assert len(applied) == 4 * 610, f'expected 2440 items applied, got {len(applied)}'
    for fam in ('L1', 'L2', 'LB', 'LC', 'LS'):
        assert all(guard_item(ptr, size, 0, total) for f, ptr, size in items if f == fam), fam


def test_short_file_skips_are_per_item_not_all_or_nothing():
    data = synthetic(slots_per_bank=610)
    total = len(data)
    verdicts = [guard_item(ptr, size, 0, total) for fam, ptr, size in walks(data)]
    assert any(verdicts) and not all(verdicts), 'must mix applied and refused items'


def test_forged_short_directory_skips_only_crossing_items():
    # directory forged so the payload runs out before the walk does
    data = synthetic()
    cut = len(data) - 58                      # shave the last 58 bytes off the file end
    items = list(walks(data))
    crossing = [ptr for fam, ptr, size in items if ptr + size > cut]
    refused = [ptr for fam, ptr, size in items if not guard_item(ptr, size, 0, cut)]
    assert refused == crossing and refused, 'exactly the tail items must be refused'
    assert len(refused) < len(items) / 2, 'refusal must stay per-item, not all-or-nothing'
    inner = [ptr for fam, ptr, size in items if ptr + size <= cut and not guard_item(ptr, size, 0, cut)]
    assert not inner, f'in-file items must not be refused: {inner[:3]}'


def test_blob_family_overlong_size_refused_siblings_applied():
    data = synthetic()
    total = len(data)
    l2 = [(ptr, size) for fam, ptr, size in walks(data) if fam == 'L2']
    victim, _ = l2[-1]
    verdicts = [(ptr, guard_item(ptr, (1 << 40) if ptr == victim else size, 0, total)) for ptr, size in l2]
    assert not dict(verdicts)[victim], 'the forged over-long blob item must be refused'
    assert sum(1 for _, ok in verdicts if ok) == len(l2) - 1


def test_each_loop_family_refuses_only_its_forged_item():
    data = synthetic()
    total = len(data)
    items = list(walks(data))
    for target in ('L1', 'L2', 'LB', 'LC', 'LS', 'L3'):
        victim = [ptr for fam, ptr, size in items if fam == target][-1]
        refused = applied = 0
        for fam, ptr, size in items:
            ok = guard_item(ptr, (1 << 40) if ptr == victim else size, 0, total)
            refused += not ok
            applied += ok
        assert (refused, applied) == (1, len(items) - 1), f'{target}: refused={refused} applied={applied}'


def test_scalar_stub_uses_index_register_form():
    # s28 (L1/LB) and s24 (LS/L3) evaluate (cursor - base) + idx*4 + 4 == item end
    data = synthetic()
    total = len(data)
    for fam in ('L1', 'LB', 'LS', 'L3'):
        ptrs = [p for f, p, s in walks(data) if f == fam]
        cursor = ptrs[0]
        for idx, ptr in enumerate(ptrs[:8]):
            end_off = (cursor - 0) + idx * 4 + 4
            assert end_off == ptr + 4
            assert guard_item(ptr, 4, 0, total) == (end_off <= total)


def test_corrupt_header_length_is_fail_safe():
    data = synthetic()
    items = list(walks(data))
    for bad in (0, 0x7F, 0x200001, 0xFFFFFFFF):
        assert not any(guard_item(ptr, size, 0, bad) for fam, ptr, size in items), hex(bad)


def test_v10_cross_region_bound_is_placement_dependent():
    data = synthetic()
    total = len(data)
    items = list(walks(data))
    # file image below the header copy -> bound far above -> allow everything
    assert all(guard_item_v10(ptr, size, 1 << 32, total) for fam, ptr, size in items)
    # file image above the header copy -> bound below every item -> skip everything
    buf = 1 << 24
    assert not any(guard_item_v10(buf + ptr, size, 0x1000, total) for fam, ptr, size in items)
    # the fixed guard is placement-independent
    for base in (0x1000, 1 << 32):
        assert all(guard_item(base + ptr, size, base, total) for fam, ptr, size in items)


def main():
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith('test_') and callable(f)]
    failed = []
    for name, fn in tests:
        try:
            fn()
            print(f'PASS {name}')
        except AssertionError as exc:
            print(f'FAIL {name}: {exc}')
            failed.append(name)
    print('TESTS', 'PASS' if not failed else 'FAIL', f'{len(tests) - len(failed)}/{len(tests)}')
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
