"""Compile and validate the pre-capture patch against a pinned public recipe."""
import json
from pathlib import Path
import struct
import subprocess
import tempfile

from z8prores.package import RESOURCES, require, sha
from z8prores.base import at, va, locked, profile_path, adopt as _adopt
from .linker import link

HERE = Path(__file__).resolve().parent
LOADER = 0x1024D8C


def compatibility(eg):
    _adopt(eg)
    profile = json.loads(profile_path('precapture.json').read_text())
    require(len(eg) == profile['payload_bytes'], 'Unsupported EG length')
    for r in profile['ranges']:
        a, b = int(r['start'], 16), int(r['end'], 16)
        require(sha(eg[a:b]) == r['sha256'], 'Incompatible region: ' + r['purpose'])
    for e in profile['patches']:
        a, n = int(e['offset'], 16), e['bytes']   # profile offsets are base-absolute
        allowed = profile['loader_input_sha256'] if a == at(LOADER) else [locked(e, 'old_sha256')]
        require(sha(eg[a:a+n]) in allowed, 'Pre-capture patch input conflicts at ' + e['offset'])
    return profile


def compile_code(compiler='clang'):
    profile = json.loads((RESOURCES / 'precapture.json').read_text())   # recipe lock is base-independent
    for name, expected in profile['source_sha256'].items():
        require(sha((HERE / name).read_bytes()) == expected, 'Pre-capture source changed: ' + name)
    with tempfile.TemporaryDirectory(prefix='z8-precapture-compile-') as folder:
        obj = Path(folder) / 'patch.o'
        command = [compiler, *profile['compiler_flags'], '-c', str(HERE / 'firmware.c'), '-o', str(obj)]
        run = subprocess.run(command, capture_output=True, text=True)
        require(run.returncode == 0, 'AArch64 compilation failed: ' + run.stderr[-4000:])
        code, sections, symbols, _ = link(obj.read_bytes())
    require(len(code) == profile['code_bytes'] and sha(code) == profile['code_sha256'],
            'Compiler output differs from the reviewed recipe. Tested compiler: ' + profile['compiler'] +
            '. No firmware output was written; use a matching toolchain.')
    for name, address in profile['entries'].items():
        require(symbols[name]['va'] == address, 'Compiled entry address differs: ' + name)
    return code, dict(compiler=subprocess.check_output([compiler, '--version'], text=True).splitlines()[0],
                     code_sha256=sha(code), code_bytes=len(code), sections=sections)


def values(code, entries):
    """Single source of truth for every reviewed payload window (shared with work/lock_v111.py)."""

    def bl(site, to):
        d = to-site
        require(d % 4 == 0 and -(1 << 27) <= d < (1 << 27), 'Branch target out of range')
        return struct.pack('<I', 0x94000000 | ((d // 4) & 0x3ffffff))

    return {
        at(0xe0fe90): bl(va(0xe0fe90), entries['precapture_history_entry']),
        at(0xd4915c): bytes.fromhex('e00317aa') + bl(va(0xd49160), entries['precapture_tdec_release']) + bytes.fromhex('1f2003d5'),
        at(0xd43638): bl(va(0xd43638), entries['precapture_write_file']),
        at(0xd4eb60): bl(va(0xd4eb60), entries['precapture_main_rc']),
        at(0xe0ff38): bl(va(0xe0ff38), entries['precapture_current_entry']),
        at(0xee8e1c): bl(va(0xee8e1c), entries['precapture_y_size_entry']),
        at(0xd49fac): bl(va(0xd49fac), entries['precapture_y_alloc_entry']),
        at(0xd4eeec): bl(va(0xd4eeec), entries['precapture_main_step']),
        at(0xd4ef10): bl(va(0xd4ef10), entries['precapture_main_step']),
        at(0x4d2ffc0): struct.pack('<I', 0x01B68000),
        at(0x4d2ffcc): struct.pack('<I', 0x01B68000),
        at(0x800000): code,
        # v7: D3-MAX boundary + case bases, counter hook/cave
        at(0xe3a4c4): struct.pack('<I', 0x7100111f),
        at(0xe3a4e8): struct.pack('<I', 0x7100111f),
        at(0xe3a50c): struct.pack('<I', 0x7100111f),
        at(0xe3a530): struct.pack('<I', 0x7100111f),
        at(0xe3a4cc): 0xf2a812c9d28efa09.to_bytes(8,'little'),
        at(0xe3a538): 0xf2a812c9d28efc09.to_bytes(8,'little'),
        at(0xe3a4f0): 0xf2a812c9d28efe09.to_bytes(8,'little'),
        at(0xe3a514): 0xf2a812c9d28f0009.to_bytes(8,'little'),
        at(0x71e5d4): bytes.fromhex('8b660314'),
        at(0x7f8000): bytes.fromhex('c99ffc97880790d2a812a8f20800c0f20800e0f209014039090100344a018052007c0a1b3f0500710b0280526c0380526b018c1a0008cb1a6899fc1700000000'),
        # v6: bank packing hooks (112 P1)
        at(0xEB56D0): bl(va(0xeb56d0), entries['precapture_bank_get']),
        at(0xEB5860): bl(va(0xeb5860), entries['precapture_bank_set']),
        # merged: extra windows (HE* budget + C30 1s capacity clamp; 103勘误: 0x4CD59D8=C120 不钳)
        at(0xD52564): struct.pack('<I', 0x14000000 | (((entries['precapture_grade_entry']-va(0xd52564))//4) & 0x3ffffff)),  # v9: per-grade +0x2ac
        # v11.1 (c2-fix-plan Fix 1 + Fix 4): the corrected same-base bounds guard at every walk site.
        # v10's T4 tail write (0x4CBC9B8) and the two 617->618 count immediates (0xF803D4/0xF80F68)
        # are deliberately absent: Fix 3 proved no consumer of the table boundary (static triad +
        # watchpoint + 628-slot cross-check) -> the write is deleted; Fix 2 follows with option B
        # (all three count sources stay at the ROM variant value 617).
        at(0xF7F9D4): bl(va(0xf7f9d4), entries['precapture_ncset_guard']),        # L2 blob walk -> guard
        at(0xF7FBF8): bl(va(0xf7fbf8), entries['precapture_ncset_guard']),        # LC blob walk -> guard (same convention)
        at(0xF7F8D4): bl(va(0xf7f8d4), entries['precapture_ncset_guard_s28']),    # L1 scalar walk -> guard
        at(0xF7FB2C): bl(va(0xf7fb2c), entries['precapture_ncset_guard_s28']),    # LB scalar walk -> guard
        at(0xF7FD14): bl(va(0xf7fd14), entries['precapture_ncset_guard_s24']),    # LS scalar walk -> guard
        at(0xF7FE28): bl(va(0xf7fe28), entries['precapture_ncset_guard_s24']),    # L3 scalar walk -> guard

        # NOTE: no 0x4CD59D4 capacity-table row — v7 retired the firmware-side C30 clamp
        # (lock_v7.py drops the row; RING_CAP is the single truth, enforced via CFG frames).
        at(LOADER): bytes.fromhex('080080d2e812a8f2'),
    }


def edits(code):
    profile = json.loads(profile_path('precapture.json').read_text())
    entries = {k: int(v, 16) for k, v in profile['entries'].items()}
    vals = values(code, entries)
    result = []
    for row in profile['patches']:
        start = int(row['offset'], 16)   # base-absolute
        raw = vals[start]
        require(len(raw) == row['bytes'] and sha(raw) == locked(row, 'new_sha256'), 'Generated pre-capture edit differs')
        result.append(dict(offset=start, new=raw, purpose=row['purpose']))
    return result
