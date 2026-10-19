#!/usr/bin/env python3
"""Three-gate behaviour regression (143): STP self-heal + gate observability, at the real entry
point. Compiles z8precapture/firmware.c twice for the host — as shipped and as the V11.1 base
(tests/reference/firmware_v111_p1_seam.c) — runs the same 19 vectors of tests/host_gate_harness.c
through precapture_tdec_release() and asserts

  1. the shipped decisions match the per-vector expectation table (keep + gate code + counters),
  2. the base/shipped behaviour delta is exactly the three designed changes:
       v07, v16  leftover Z8PRESTP.BIN from an earlier session -> self-healed (kept)   [the fix]
       v10      error latch survives even if the evidence file is removed              [strengthened]
     and nothing else moved (every gate still refuses what it refused before),
  3. the source under test is the recipe source (source hash) and links to the shipped blob
     (code hash), so the tested behaviour is the delivered behaviour,
  4. the optional candidate package carries zero bytes in the gate-status cave window
     (0x7F8040..0x7F80C0 stays image-zero: the observability block costs no image bytes) and the
     counter-scale cave (0x7F8000..0x7F8040) is unchanged.

Usage: python3 tests/test_threegate.py [--kit <Z_8_0311.bin or kit dir>] [--keep]
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

TESTS = Path(__file__).resolve().parent
MERGED = TESTS.parent
sys.path.insert(0, str(MERGED))
sys.dont_write_bytecode = True

BASE_FW = TESTS / 'reference' / 'firmware_v111_p1_seam.c'
GATE_STATUS_VA = 0x40958040
GATE_STATUS_LEN = 0xC0
EG_CAVE = 0x7F8000                      # counter-scale cave (111 §6.2) + 143 status block at +0x40

# name -> (keep on the base, keep as shipped, gate code as shipped, note)
EXPECT = {
    'v01_retain_fixed':            (1, 1, 0, 'retention path unchanged'),
    'v02_dual_both_valid':         (0, 0, 4, 'gate 1 holds'),
    'v03_dual_none':               (0, 0, 4, 'gate 1 holds'),
    'v04_cfg_refused':             (0, 0, 3, 'gate 3 holds, now visible'),
    'v05_cfg_refused_other_valid': (1, 1, 0, 'gate 3 counted without blocking the good card'),
    'v06_stop_session_error':      (0, 0, 7, 'gate 2 holds for the incident session'),
    'v07_stop_leftover_record':    (0, 1, 0, 'SELF-HEAL: earlier-session record no longer permanent'),
    'v08_stop_foreign_empty':      (0, 0, 7, 'gate 2 fail-safe: unknown file still stops'),
    'v09_stop_foreign_garbage':    (0, 0, 7, 'gate 2 fail-safe: unknown file still stops'),
    'v10_stop_latch_file_gone':    (1, 0, 7, 'STRENGTHENED: session latch survives file removal'),
    'v11_stale_record':            (0, 0, 5, 'freshness gate unchanged'),
    'v12_bad_shape_menu':          (0, 0, 6, 'shape gate unchanged'),
    'v13_current_frame_fixed':     (0, 0, 1, 'not a retention candidate'),
    'v14_menu_retain':             (1, 1, 0, 'menu retention path unchanged'),
    'v15_menu_jpeg_only':          (0, 0, 1, 'not a retention candidate'),
    'v16_menu_stop_hold':          (0, 1, 0, 'SELF-HEAL: menu path too'),
    'v17_outside_window':          (0, 0, 1, 'not a retention candidate'),
    'v18_stop_on_other_card':      (1, 1, 0, 'only the config card is consulted'),
    'v19_mode_gate_fixed':         (0, 0, 6, 'fixed-path mode gate unchanged'),
}
DESIGNED_DELTAS = {'v07_stop_leftover_record', 'v10_stop_latch_file_gone', 'v16_menu_stop_hold'}
VEC = re.compile(r'^VEC (\S+)\s+keep=(\d+) magic=(\w+) code=(\d+) latch=(\d+) why=(\d+) '
                 r'counts=(\d+)/(\d+)/(\d+)/(\d+)/(\d+)/(\d+) dec=(\d+) stopw=(\d+)$')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def build_harness(src: Path, out: Path) -> None:
    cmd = ['clang', '-DPREC_CAPTURE_HOST_TEST', '-I', str(TESTS), '-I', str(MERGED / 'z8precapture'),
           '-DFW_SOURCE="%s"' % src, str(TESTS / 'host_gate_harness.c'), '-o', str(out)]
    run = subprocess.run(cmd, capture_output=True, text=True)
    if run.returncode:
        raise SystemExit('harness build failed for %s:\n%s' % (src.name, run.stderr[-3000:]))


def run_harness(binary: Path):
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    rows = {}
    for line in (run.stdout or '').splitlines():
        m = VEC.match(line.strip())
        if m:
            name = m.group(1)
            rows[name] = dict(keep=int(m.group(2)), magic=m.group(3), code=int(m.group(4)),
                              latch=int(m.group(5)), why=int(m.group(6)),
                              counts=[int(m.group(i)) for i in range(7, 13)],
                              dec=int(m.group(13)), stopw=int(m.group(14)))
    if 'HARNESS PASS' not in (run.stdout or '') or not rows:
        raise SystemExit('harness did not complete:\n%s' % (run.stdout or '')[-2000:] + (run.stderr or '')[-500:])
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--kit', type=Path, default=None, help='candidate Z_8_0311.bin or kit dir')
    ap.add_argument('--keep', action='store_true', help='keep the harness binaries')
    a = ap.parse_args()
    if a.kit:
        a.kit = a.kit.resolve()          # callers (gauntlet G5.7) may pass a relative path with another cwd
    checks = []

    def check(name, ok, detail):
        checks.append((name, ok, detail))
        print('%-4s %s — %s' % ('PASS' if ok else 'FAIL', name, detail))
        return ok

    # 3. the tested source is the recipe source and links to the shipped blob
    from z8precapture import patcher           # noqa: E402  (import after sys.path)
    profile = json.loads((MERGED / 'resources' / 'precapture.json').read_text())
    src = MERGED / 'z8precapture' / 'firmware.c'
    check('source hash = recipe source', sha(src.read_bytes()) == profile['source_sha256']['firmware.c'],
          'firmware.c %s' % sha(src.read_bytes())[:16])
    code, meta = patcher.compile_code()
    check('blob = compiled recipe source', sha(code) == profile['code_sha256'] and len(code) == profile['code_bytes'],
          '%d B %s' % (len(code), sha(code)[:16]))
    check('gate status VA declared', int(profile.get('merged', {}).get('gate_status', '0'), 16) == GATE_STATUS_VA,
          'merged.gate_status = %s' % profile.get('merged', {}).get('gate_status'))

    with tempfile.TemporaryDirectory(prefix='threegate-') as td:
        td = Path(td)
        new_bin, base_bin = td / 'harness_new', td / 'harness_base'
        build_harness(src, new_bin)
        build_harness(BASE_FW, base_bin)
        new = run_harness(new_bin)
        base = run_harness(base_bin)
        if a.keep:
            print('harness binaries kept in', td)

        ok = True
        for name, (exp_base, exp_new, exp_code, note) in EXPECT.items():
            if name not in new or name not in base:
                ok = check('vector %s' % name, False, 'missing from harness output') and ok
                continue
            good = (base[name]['keep'] == exp_base and new[name]['keep'] == exp_new
                    and new[name]['code'] == exp_code)
            ok = check('vector %-26s' % name, good,
                       'base keep=%d (want %d) / new keep=%d code=%d (want %d/%d) — %s'
                       % (base[name]['keep'], exp_base, new[name]['keep'], new[name]['code'],
                          exp_new, exp_code, note)) and ok
            if new[name]['keep']:
                ok = check('  retain accounting %s' % name,
                           new[name]['counts'][0] == 1 and new[name]['magic'] == '31385447',
                           'retained=1, block magic %s' % new[name]['magic']) and ok

        delta = {n for n in EXPECT if base[n]['keep'] != new[n]['keep']}
        check('behaviour delta = designed set', delta == DESIGNED_DELTAS,
              'delta %s (want %s)' % (sorted(delta), sorted(DESIGNED_DELTAS)))
        check('no gate silently opens', all(new[n]['keep'] == EXPECT[n][1] for n in EXPECT),
              'every vector keeps exactly what the design says')
        # observability: each refusal is accounted for exactly once
        bad = []
        for n, row in new.items():
            retain, na, cfgr, dual, stp, other = row['counts']
            if row['dec'] != 1 or retain + na + dual + stp + other != 1:
                bad.append(n)
        check('decision accounting (1 decision = 1 outcome)', not bad, 'offenders: %s' % (bad or 'none'))

    # 4. candidate package: zero bytes in the status cave window
    if a.kit:
        try:
            from z8prores.package import Package
            kit = a.kit if a.kit.is_dir() else a.kit.parent
            bins = sorted(kit.glob('*.bin'))
            raw = (a.kit if a.kit.is_file() else bins[0]).read_bytes()
            eg = Package(raw).eg
            tail = eg[EG_CAVE + 0x40:EG_CAVE + 0x40 + GATE_STATUS_LEN]
            cave = eg[EG_CAVE:EG_CAVE + 0x40]
            check('status cave is image-zero (no new image bytes)', all(b == 0 for b in tail),
                  'eg %#x..%#x all zero' % (EG_CAVE + 0x40, EG_CAVE + 0x40 + GATE_STATUS_LEN))
            cave_row = [r for r in profile['patches'] if int(r['offset'], 16) == EG_CAVE][0]
            check('counter-scale cave = recipe bytes', sha(cave) == cave_row['new_sha256'] and cave[0x3c] == 0,
                  'eg %#x..%#x sha %s (ctrl byte %d)' % (EG_CAVE, EG_CAVE + 0x40, sha(cave)[:16], cave[0x3c]))
        except Exception as exc:                       # noqa: BLE001 - a broken package check is a red gate
            kit_dir = a.kit if a.kit.is_dir() else a.kit.parent
            check('candidate package checks', False,
                  '%s: %s | kit=%s is_file=%s bins=%s cave_rows=%s merged=%s' % (
                      type(exc).__name__, exc, a.kit, a.kit.is_file(),
                      [b.name for b in sorted(kit_dir.glob('*.bin'))],
                      [r['offset'] for r in profile['patches'] if str(r['offset']).lower() in ('0x7f8000', '0x7f8040')],
                      MERGED))

    failed = [(n, d) for n, ok, d in checks if not ok]
    print('%d checks, %d failed' % (len(checks), len(failed)))
    print('TESTS PASS' if not failed else 'TESTS FAIL: %s' % '; '.join('%s (%s)' % (n, d) for n, d in failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
