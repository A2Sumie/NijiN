#!/usr/bin/env python3
"""bricking-edge line: revert the three suspect V10 changes, byte-exact elsewhere.

The V10 build caused a boot loop on hardware (see docs/risks.md). Its delta against the
previous build is exactly four payload windows plus the recompiled code blob, two
hook-target moves and the checksum chain. This recipe strips the suspect part: all four
windows take their previous values back, everything else stays byte-identical to V10,
and the package checksum chain is rebuilt with this repository's packer.

  payload 0x4CBC9B8  8B  settings-table tail write (table boundary, ownership unproven)
  payload 0xF803D4   4B  save-side settings-count immediate 617 -> 618
  payload 0xF80F68   4B  boot-registration settings-count immediate 617 -> 618
  payload 0xF7F9D4   4B  load-time bounds guard hook (bound semantics defective)

Nothing is written anywhere except the output directory you name. The flashing decision
is entirely yours; this project never touches a camera or a card.

Usage (bring your own builds as inputs):

    python3 recipes/revert_v10_tails.py --v10 /path/to/v10.bin --v9 /path/to/v9.bin \
        --out build/bricking-edge

Verification prints the A/B diffs against both inputs and requires them to be exactly
the declared windows plus the checksum chain.
"""
import argparse
import binascii
import hashlib
import sys
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from z8prores.package import Package, require  # noqa: E402

MODULE = 'eg2070_0311p0.bi'
EG_LEN = 81807711
EG_CRC_AT = EG_LEN - 2                       # trailing CRC16-XMODEM of the payload module

# (payload offset, length, purpose) — the suspect windows
REVERTS = [
    (0x4CBC9B8, 8, 'settings-table tail write (8B)'),
    (0xF803D4, 4, 'save-side settings-count immediate 617->618'),
    (0xF80F68, 4, 'boot-registration settings-count immediate 617->618'),
    (0xF7F9D4, 4, 'load-time bounds guard hook'),
]
HOOK_MOVED = [(0xD49FAC, 0xD49FB0), (0xEE8E1C, 0xEE8E20)]   # hook targets that follow the blob layout
V10_ANCHOR = '6198301e'      # accepted V10 input prefix
V9_ANCHOR = '7415654d'       # accepted previous-build input prefix


def diff_runs(a, b):
    runs, i, n = [], 0, min(len(a), len(b))
    while i < n:
        if a[i] != b[i]:
            j = i
            while j < n and a[j] != b[j]:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    return runs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--v10', type=Path, required=True, help='local V10 build (input package shape)')
    ap.add_argument('--v9', type=Path, required=True, help='local previous build to take the reverted bytes from')
    ap.add_argument('--out', type=Path, default=REPO / 'build' / 'bricking-edge', help='new output directory')
    a = ap.parse_args()
    require(a.v10.is_file() and a.v9.is_file(), 'both input builds are required (this repository ships none)')
    raw10, raw9 = a.v10.read_bytes(), a.v9.read_bytes()
    require(hashlib.sha256(raw10).hexdigest().startswith(V10_ANCHOR), 'the --v10 input is not the expected build')
    require(hashlib.sha256(raw9).hexdigest().startswith(V9_ANCHOR), 'the --v9 input is not the expected build')

    p10, p9 = Package(raw10), Package(raw9)
    eg10, eg9 = bytearray(p10.eg), p9.eg
    require(len(eg10) == len(eg9) == EG_LEN, 'payload length mismatch')

    print('== reverting the suspect windows (bytes taken from the previous build) ==')
    for off, n, why in REVERTS:
        old, new = bytes(eg10[off:off + n]), eg9[off:off + n]
        print('  payload %#x %dB  %s\n      before=%s  ->  after=%s' % (off, n, why, old.hex(), new.hex()))
        eg10[off:off + n] = new
    eg10[EG_CRC_AT:EG_CRC_AT + 2] = binascii.crc_hqx(eg10[:-2], 0).to_bytes(2, 'big')

    packet, checked = p10.replace_eg(bytes(eg10), MODULE)
    require(not a.out.exists(), 'output directory already exists: ' + str(a.out))
    a.out.mkdir(parents=True)
    (a.out / 'Z_8_0311.bin').write_bytes(packet)

    outsha = hashlib.sha256(packet).hexdigest()
    print('== output package ==\n  %s\n  sha256 %s' % (a.out / 'Z_8_0311.bin', outsha))

    p_out = Package(packet)
    require(len(p_out.eg) == EG_LEN, 'output payload length mismatch')
    windows = sorted([(off, off + n) for off, n, _ in REVERTS] + [(EG_CRC_AT, EG_CRC_AT + 2)])

    print('== A/B vs the V10 input (expect exactly the four windows + trailing CRC16) ==')
    for s, e in diff_runs(p10.eg, p_out.eg):
        inside = any(ws <= s and e <= we for ws, we in windows)
        print('  payload %#x..%#x (%dB) %s' % (s, e, e - s, 'declared-window' if inside else '**UNEXPECTED**'))
        require(inside, 'unexpected drift at %#x..%#x' % (s, e))
    require(all(any(ws < e and s < we for s, e in diff_runs(p10.eg, p_out.eg)) for ws, we in windows),
            'a declared window was not reverted')

    print('== A/B vs the previous build (expect code blob + hook-target windows only) ==')
    for s, e in diff_runs(p9.eg, p_out.eg):
        ok = (0x800000 <= s and e <= 0x810000) or (s >= EG_CRC_AT) \
             or any(ws <= s and e <= we for ws, we in HOOK_MOVED)
        print('  payload %#x..%#x (%dB) %s' % (s, e, e - s, 'expected' if ok else '**CHECK**'))
        require(ok, 'unexpected drift vs previous build at %#x..%#x' % (s, e))

    print('== container-level A/B (informational; body is encoded, chain bytes move) ==')
    mod = next(m for m in checked.modules if m['name'] == MODULE)
    eg_base = mod['start'] + 32                       # module record + 32B header
    body_hi = eg_base + EG_LEN
    cruns = diff_runs(raw10, packet)
    for s, e in cruns:
        mapped = any(eg_base + ws <= s and e <= eg_base + we for ws, we in windows)
        require(mapped or not (eg_base <= s and e <= body_hi),
                'container drift outside declared windows at %#x..%#x' % (s, e))
    print('  %d runs total; payload-body runs all map to the declared windows' % len(cruns))
    print('NOTE this script wrote only the output directory; the flashing decision is yours.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
