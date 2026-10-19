"""OpenGate (3:2 full-frame) experimental recording option: compile, patch and lock.

Independent feature: no overlap with prores/precapture windows; when the feature is not
selected nothing of it reaches the output, and at runtime Z8OG.CFG-off falls through to
the exact stock values.
"""
import json
import struct
import subprocess
import tempfile
from pathlib import Path

from z8prores.package import RESOURCES, require, sha
from z8precapture.linker import link

HERE = Path(__file__).resolve().parent
CAVE_AT = 0x80F000                      # inside the loader-covered cave, after the precapture blob
CAVE_VA = 0x4096F000                    # CAVE_AT + 0x40160000
NOP = struct.pack('<I', 0xd503201f)


def compatibility(eg):
    profile = json.loads((RESOURCES / 'opengate.json').read_text())
    require(len(eg) == profile['payload_bytes'], 'Unsupported EG length')
    for r in profile['ranges']:
        a, b = int(r['start'], 16), int(r['end'], 16)
        require(sha(eg[a:b]) == r['sha256'], 'Incompatible region: ' + r['purpose'])
    for e in profile['patches']:
        a, n = int(e['offset'], 16), e['bytes']
        require(sha(eg[a:a + n]) == e['old_sha256'], 'OpenGate patch input conflicts at ' + e['offset'])
    return profile


def compile_code(compiler='clang'):
    profile = json.loads((RESOURCES / 'opengate.json').read_text())
    for name, expected in profile['source_sha256'].items():
        require(sha((HERE / name).read_bytes()) == expected, 'OpenGate source changed: ' + name)
    with tempfile.TemporaryDirectory(prefix='z8-opengate-compile-') as folder:
        obj = Path(folder) / 'patch.o'
        command = [compiler, *profile['compiler_flags'], '-c', str(HERE / 'firmware.c'), '-o', str(obj)]
        run = subprocess.run(command, capture_output=True, text=True)
        require(run.returncode == 0, 'AArch64 compilation failed: ' + run.stderr[-4000:])
        code, sections, symbols, _ = link(obj.read_bytes(), cave=CAVE_VA, entry=None)
    require(len(code) == profile['code_bytes'] and sha(code) == profile['code_sha256'],
            'Compiler output differs from the reviewed recipe. Tested compiler: ' + profile['compiler'] +
            '. No firmware output was written; use a matching toolchain.')
    for name, address in profile['entries'].items():
        require(symbols[name]['va'] == address, 'Compiled entry address differs: ' + name)
    return code, dict(compiler=subprocess.check_output([compiler, '--version'], text=True).splitlines()[0],
                      code_sha256=sha(code), code_bytes=len(code), sections=sections)


def branch(at, to):
    d = to - at
    require(d % 4 == 0 and -(1 << 27) <= d < 1 << 27, 'Branch target out of range')
    return struct.pack('<I', 0x14000000 | ((d // 4) & 0x3ffffff))


def edits(code, entries):
    entries = {k: int(v, 16) for k, v in entries.items()}
    # size switch cases (12 B each): b og_case_* + 2 nops; resume 0x406d3154
    size_cases = {0x573120: 'og_case_23x', 0x573134: 'og_case_41k',
                  0x573140: 'og_case_dx', 0x57314c: 'og_case_83k'}
    # padded switch cases (16 B each): b og_pad_* + 3 nops; the trailing b 0x40cfafc0 stays
    pad_cases = {0xb9af64: 'og_pad_83k', 0xb9af88: 'og_pad_dx',
                 0xb9af9c: 'og_pad_41k', 0xb9afb0: 'og_pad_23x'}
    out = {}
    for at, name in size_cases.items():
        out[at] = branch(0x40160000 + at, entries[name]) + NOP * 2
    for at, name in pad_cases.items():
        out[at] = branch(0x40160000 + at, entries[name]) + NOP * 3
    out[0xbbe650] = branch(0x40d1e650, entries['og_rate_row'])   # madd x8,x9,x8,x10 -> og_rate_row
    out[CAVE_AT] = code
    return [dict(offset=at, new=raw, purpose=purpose(at)) for at, raw in sorted(out.items())]


def purpose(at):
    return {
        0x573120: 'OG 3:2 size case 3840x2160 -> 3840x2560',
        0x573134: 'OG 3:2 size case 4128x2322 -> 4128x2752',
        0x573140: 'OG 3:2 size case 5392x3032 -> 5392x3592',
        0x57314c: 'OG 3:2 size case 8256x4644 -> 8256x5504',
        0xb9af64: 'OG padded case 8268x4652 -> 8268x5512',
        0xb9af88: 'OG padded case 5404x3040 -> 5404x3600',
        0xb9af9c: 'OG padded case 4140x2330 -> 4140x2760',
        0xb9afb0: 'OG padded case 3852x2168 -> 3852x2568',
        0xbbe650: 'OG bitrate-row redirect (type1/type2)',
    }.get(at, 'OpenGate code and 3:2 rate rows (experimental)')


def build_edits(compiler='clang'):
    """Compile the pinned sources and return the reviewed patch windows."""
    profile = json.loads((RESOURCES / 'opengate.json').read_text())
    code, _ = compile_code(compiler)
    rows = edits(code, profile['entries'])
    have = {int(r['offset'], 16): r for r in profile['patches']}
    require(len(rows) == len(have), 'OpenGate edit count differs from the reviewed profile')
    for e in rows:
        row = have[e['offset']]
        require(len(e['new']) == row['bytes'] and sha(e['new']) == row['new_sha256'],
                'OpenGate differs from the reviewed recipe')
    return rows
