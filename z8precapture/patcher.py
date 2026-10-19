"""Compile and validate the pre-capture patch against a pinned public recipe."""
import json
from pathlib import Path
import struct
import subprocess
import tempfile

from z8prores.package import RESOURCES, require, sha
from .linker import link

HERE = Path(__file__).resolve().parent
LOADER = 0x1024D8C


def compatibility(eg):
    profile = json.loads((RESOURCES / 'precapture.json').read_text())
    require(len(eg) == profile['payload_bytes'], 'Unsupported EG length')
    for r in profile['ranges']:
        a, b = int(r['start'], 16), int(r['end'], 16)
        require(sha(eg[a:b]) == r['sha256'], 'Incompatible region: ' + r['purpose'])
    for e in profile['patches']:
        a, n = int(e['offset'], 16), e['bytes']
        allowed = profile['loader_input_sha256'] if a == LOADER else [e['old_sha256']]
        require(sha(eg[a:a+n]) in allowed, 'Pre-capture patch input conflicts at ' + e['offset'])
    return profile


def compile_code(compiler='clang'):
    profile = json.loads((RESOURCES / 'precapture.json').read_text())
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


def edits(code):
    profile = json.loads((RESOURCES / 'precapture.json').read_text())
    entries = {k: int(v, 16) for k, v in profile['entries'].items()}

    def bl(at, to):
        d = to-at
        require(d % 4 == 0 and -(1 << 27) <= d < (1 << 27), 'Branch target out of range')
        return struct.pack('<I', 0x94000000 | ((d // 4) & 0x3ffffff))

    values = {
        0xe0fe90: bl(0x40f6fe90, entries['precapture_history_entry']),
        0xd4915c: bytes.fromhex('e00317aa') + bl(0x40ea9160, entries['precapture_tdec_release']) + bytes.fromhex('1f2003d5'),
        0xd43638: bl(0x40ea3638, entries['precapture_write_file']),
        0xd4eb60: bl(0x40eaeb60, entries['precapture_main_rc']),
        0xe0ff38: bl(0x40f6ff38, entries['precapture_current_entry']),
        0xee8e1c: bl(0x41048e1c, entries['precapture_y_size_entry']),
        0xd49fac: bl(0x40ea9fac, entries['precapture_y_alloc_entry']),
        0xd4eeec: bl(0x40eaeeec, entries['precapture_main_step']),
        0xd4ef10: bl(0x40eaef10, entries['precapture_main_step']),
        0x4d2ffc0: struct.pack('<I', 0x01B68000),
        0x4d2ffcc: struct.pack('<I', 0x01B68000),
        0x800000: code,
        # v7: D3-MAX boundary + case bases, counter hook/cave
        0xe3a4c4: struct.pack('<I', 0x7100111f),
        0xe3a4e8: struct.pack('<I', 0x7100111f),
        0xe3a50c: struct.pack('<I', 0x7100111f),
        0xe3a530: struct.pack('<I', 0x7100111f),
        0xe3a4cc: 0xf2a812c9d28efa09.to_bytes(8,'little'),
        0xe3a538: 0xf2a812c9d28efc09.to_bytes(8,'little'),
        0xe3a4f0: 0xf2a812c9d28efe09.to_bytes(8,'little'),
        0xe3a514: 0xf2a812c9d28f0009.to_bytes(8,'little'),
        0x71e5d4: bytes.fromhex('8b660314'),
        0x7f8000: bytes.fromhex('c99ffc97880790d2a812a8f20800c0f20800e0f209014039090100344a018052007c0a1b3f0500710b0280526c0380526b018c1a0008cb1a6899fc1700000000'),
        # v6: bank packing hooks (112 P1)
        0xEB56D0: bl(0x410156d0, entries['precapture_bank_get']),
        0xEB5860: bl(0x41015860, entries['precapture_bank_set']),
        # merged: extra windows (HE* budget + C30 1s capacity clamp; 103勘误: 0x4CD59D8=C120 不钳)
        0xD52564: struct.pack('<I', 0x14000000 | (((entries['precapture_grade_entry']-0x40EB2564)//4) & 0x3ffffff)),  # v9: per-grade +0x2ac
        # v10 (122_NCSET_REAL): card serialization of menuh item 0x0800 + old-file load guard
        0x4CBC9B8: struct.pack('<II', 0x00000800, 0x00000100),        # T4[628] tail: id 0x0800, S3 slot tag
        0xF803D4: struct.pack('<I', 0x52804d46),                          # card S3 slot count 617 -> 618 (save side)
        0xF80F68: struct.pack('<I', 0x52804d40),                          # card S3 slot count 617 -> 618 (load side)
        0xF7F9D4: bl(0x410df9d4, entries['precapture_ncset_guard']),  # per-item apply -> bounds guard

        0x4CD59D4: struct.pack('<I', 20),
        LOADER: bytes.fromhex('080080d2e812a8f2'),
    }
    result = []
    for row in profile['patches']:
        at = int(row['offset'], 16)
        raw = values[at]
        require(len(raw) == row['bytes'] and sha(raw) == row['new_sha256'], 'Generated pre-capture edit differs')
        result.append(dict(offset=at, new=raw, purpose=row['purpose']))
    return result
