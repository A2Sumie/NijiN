#!/usr/bin/env python3
"""Synthetic gate self-tests (138 §4 / 143 §5): the new gates must fire and must pass.

No firmware is involved anywhere: the bytes under test are built here from the
gate's own declared word forms, and the card files are 64-byte synthetic CFGs.
Every gate gets a positive case (a defect must be intercepted) and a negative
case (a clean input must not be flagged) — a gate that only ever passes is not
a gate.

Usage: python3 tests/test_gates_synthetic.py
"""
import struct
import sys
import tempfile
import zlib
from pathlib import Path

TESTS = Path(__file__).resolve().parent
GAUNTLET = TESTS.parent / 'gauntlet'
sys.path.insert(0, str(GAUNTLET))
sys.dont_write_bytecode = True

import cfgcheck as cc          # noqa: E402
import gates as G              # noqa: E402

CHECKS = []


def check(label, ok, detail=''):
    CHECKS.append((label, bool(ok), str(detail)))


def pristine_stub(name):
    """The declared stub word sequence for one guard entry, in rule order.

    Bound-check branches are encoded as jumps to the epilogue, which is what the
    real stub does with its own immediates: the rule set only pins the opcode and
    the condition code, the offset belongs to the site.
    """
    rules = G.GUARD_PROLOGUE + [('eq', w) for w in G.GUARD_BODY[name]] + G.GUARD_TAIL
    words = []
    last = len(rules) - 1                       # the epilogue `ret`
    for i, rule in enumerate(rules):
        kind, want = rule if isinstance(rule, tuple) else ('eq', rule)
        if kind == 'apply_lo':
            want = G._mov(16, G.APPLY_OF[name] & 0xFFFF, 0, 'movz64')
        elif kind == 'apply_hi':
            want = G._mov(16, (G.APPLY_OF[name] >> 16) & 0xFFFF, 1, 'movk64')
        elif kind == 'mask':
            want = (want & 0xFF00001F) | ((last - i) << 5)
        words.append(want)
    return words


def stub_image(entries, mutate=None):
    """A synthetic EG image carrying the declared stubs at their entry points."""
    span = max(entries.values()) - G.VA_BASE + 256
    eg = bytearray(span)
    for name, va in entries.items():
        words = pristine_stub(name)
        if mutate is not None:
            words = mutate(words)
        for i, word in enumerate(words):
            struct.pack_into('<I', eg, va - G.VA_BASE + 4 * i, word)
    return bytes(eg)


def cfg_pre(frames, flags=0x4):
    raw = bytearray(64)
    raw[:10] = b'Z8PRECFGv4'
    struct.pack_into('<4I', raw, 16, flags, frames, cc.BUDGET_US, 12)
    struct.pack_into('<I', raw, 60, zlib.crc32(bytes(raw[:60])) & 0xffffffff)
    return bytes(raw)


def main():
    entries = {name: G.VA_BASE + 0x200 + 0x80 * i for i, name in enumerate(G.GUARD_BODY)}

    # ---- G3.5 guard same-base content gate --------------------------------
    ok, detail = G.guard_semantics_ok(pristine_stub('precapture_ncset_guard'),
                                      'precapture_ncset_guard')
    check('G3.5 clean stub passes', ok, detail)

    def cross_region(words):
        out = list(words)
        out[len(G.GUARD_PROLOGUE)] = 0x8B090329        # add x9,x25,x9 = v10 bound
        return out

    ok, detail = G.guard_semantics_ok(cross_region(pristine_stub('precapture_ncset_guard')),
                                      'precapture_ncset_guard')
    check('G3.5 v10 cross-region bound is refused', not ok, detail)

    def cross_region_padding(words):
        out = list(words) + [0xD503201F] * 5
        out[-1] = 0x8B090329                        # add x9,x25,x9 outside the declared rules
        return out

    ok, detail = G.guard_semantics_ok(cross_region_padding(pristine_stub('precapture_ncset_guard')),
                                      'precapture_ncset_guard')
    check('G3.5 cross-region add is refused even outside the rule window', not ok, detail)

    # ---- G3.10 stub-level behaviour regression ----------------------------
    ok, detail = G.stub_behavior_check(stub_image(entries), entries)
    check('G3.10 clean stubs behave per vector table', ok, detail)

    def fail_open(words):
        out = list(words)
        out[11] = out[12] = 0xD503201F                      # tail cmp + b.hi -> NOP (M42)
        return out

    ok, detail = G.stub_behavior_check(stub_image(entries, fail_open), entries)
    check('G3.10 fail-open stub is intercepted', not ok, detail)

    def fail_closed(words):
        out = list(words)
        out[15] = 0xD65F03C0                                # apply -> ret (M43)
        return out

    ok, detail = G.stub_behavior_check(stub_image(entries, fail_closed), entries)
    check('G3.10 fail-closed stub is intercepted', not ok, detail)

    # ---- G3.9 multi-source consistency ------------------------------------
    rows = (0x1B68000, 0x1B68000)
    span = max(G.E_ROW_OFFS[1], G.E_TWIN_OFFS[1], 0x880000) + 64
    eg = bytearray(span)
    for off, value in zip(G.E_ROW_OFFS, rows):
        struct.pack_into('<I', eg, off, value)
    for off in G.E_TWIN_OFFS:
        struct.pack_into('<I', eg, off, rows[0])
    stock = bytes(eg)
    ok, detail = G.multi_source_gate(bytes(eg), {}, stock)
    check('G3.9 consistent family passes', ok, detail)

    struct.pack_into('<I', eg, G.E_ROW_OFFS[1], rows[1] + 0x200)     # M40
    ok, detail = G.multi_source_gate(bytes(eg), {}, stock)
    check('G3.9 diverged table row is intercepted', not ok, detail)

    struct.pack_into('<I', eg, G.E_ROW_OFFS[1], rows[1] - 0x200)     # M41, reverse
    ok, detail = G.multi_source_gate(bytes(eg), {}, stock)
    check('G3.9 reverse drift is intercepted', not ok, detail)

    # ---- G4.6 memory envelope assertion -----------------------------------
    per_frame = 0x1B68000
    with tempfile.TemporaryDirectory(prefix='gauntlet-synthetic-') as td:
        td = Path(td)
        good = td / 'Z8PRE_SAFE.CFG'
        good.write_bytes(cfg_pre(20))
        over = td / 'Z8PRE_OVER.CFG'
        over.write_bytes(cfg_pre(30, flags=0x4))
        g, _ = G.run_cfg_gate([good], 20, per_frame=per_frame)
        check('G4.6 in-envelope configuration passes',
              next(c for c in g.checks if c.cid == 'G4.6').ok,
              next(c for c in g.checks if c.cid == 'G4.6').detail)
        g, _ = G.run_cfg_gate([over], 30, per_frame=per_frame)
        check('G4.6 over-envelope configuration is intercepted',
              not next(c for c in g.checks if c.cid == 'G4.6').ok,
              next(c for c in g.checks if c.cid == 'G4.6').detail)
        g, _ = G.run_cfg_gate([good], 20, per_frame=None)
        skipped = [c for c in g.checks if c.cid == 'G4.6'][0]
        check('G4.6 without a frame size is SKIPPED, never PASS',
              skipped.skipped and skipped.status == 'SKIPPED', skipped.detail)

    failed = 0
    for label, ok, detail in CHECKS:
        print('%s %s%s' % ('PASS' if ok else 'FAIL', label, (' — ' + detail)[:120] if detail else ''))
        failed += 0 if ok else 1
    print('%d checks, %d failed' % (len(CHECKS), failed))
    print('TESTS PASS' if not failed else 'TESTS FAIL')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
