#!/usr/bin/env python3
"""Feature-composition regression and rejection tests with an external stock fixture."""
import argparse
import binascii
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import zlib

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features import compatibility, selected_features
from z8prores.package import Package, sha
from z8prores import base as basemod
from z8precapture.config import build_config
from verify import verify_pair


FIXTURES = {
    '03.11': dict(sha256='d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96',
                  module='eg2070_0311b0.bi'),
    '03.12': dict(sha256='d662dd9dd5da937cb418162c238065e918dcefafd47b47537c3f934d39e83037',
                  module='eg2070_031200.bi'),
}


def check(ok, message):
    if not ok:
        raise RuntimeError(message)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stock', required=True, type=Path)
    ap.add_argument('--report', type=Path, required=True)
    ap.add_argument('--compiler', default='clang')
    a = ap.parse_args()
    check(not a.report.exists(), 'Report already exists')
    data = a.stock.read_bytes()
    fixture = next((v for v in FIXTURES.values() if sha(data) == v['sha256']), None)
    check(fixture is not None, 'Expected a pinned fixture: official 03.11 or official 03.12')
    basemod.CURRENT['base'] = next(k for k, v in FIXTURES.items() if v is fixture)

    def A(off):
        return basemod.at(off)          # recipe offset -> the fixture's base

    package = Package(data)
    rows = []

    def reject(name, fn, reason):
        try:
            fn()
        except ValueError as exc:
            check(reason in str(exc), name + ': unexpected error ' + str(exc))
            rows.append(dict(test=name, result='REJECTED'))
        else:
            raise RuntimeError('Negative control accepted: ' + name)

    with tempfile.TemporaryDirectory(prefix='z8-feature-tests-') as temporary:
        temp = Path(temporary)
        for names in [['prores'], ['precapture'], ['prores', 'precapture']]:
            name = '+'.join(names)
            out = temp/name
            cmd = [sys.executable, '-B', str(ROOT/'patch.py'), str(a.stock.resolve()), '--features', *names,
                   '--version', '04.01', '--output', str(out), '--compiler', a.compiler]
            pr = subprocess.run(cmd, capture_output=True, text=True)
            check(pr.returncode == 0, pr.stderr)
            candidate = (out/'Z_8_0401.bin').read_bytes()
            verified = verify_pair(data, candidate, names)
            auto = verify_pair(data, candidate)
            check(set(auto['features']) == set(names), 'Feature detection differs')
            manifest = json.loads((out/'manifest.json').read_text())
            check(manifest['features'] == names and manifest['output_sha256'] == sha(candidate), 'Manifest mismatch')
            cpath = out/'Z8PRE.CFG'
            check(cpath.exists() == ('precapture' in names), 'Unexpected card configuration')
            if cpath.exists():
                c = cpath.read_bytes()
                check(len(c) == 64 and c[:16] == b'Z8PRECFGv4'.ljust(16, b'\0'), 'Configuration format')
                check(struct.unpack_from('<4I', c, 16) == (0x293,20,1500000,14), 'Default configuration values')
                check(zlib.crc32(c[:60]) == struct.unpack_from('<I', c, 60)[0], 'Configuration CRC')
            rows.append(dict(test=name, result='PASS', output_sha256=sha(candidate), independently_verified=verified['status']))
            print(name + ': PASS', flush=True)
            reject(name+' repeated patch', lambda names=names: compatibility(Package(candidate).eg, names), 'Incompatible')
            wrong = ['precapture'] if names == ['prores'] else ['prores']
            reject(name+' wrong feature claim', lambda: verify_pair(data, candidate, wrong), 'Output differs')
            repeated = subprocess.run(cmd, capture_output=True, text=True)
            check(repeated.returncode != 0 and 'already exists' in repeated.stderr and
                  (out/'Z_8_0401.bin').read_bytes() == candidate, 'Existing output changed')
        # Reject validly checksummed changes to required code and occupied patch space.
        for offset0 in [0xe0fe90,0xe0ff38,0xee8e1c,0xd49fac,0xd4eeec,0xd4ef10,0x47add4,0x3ec44c8,0xd4915c,0xd43638,0xd4367c,0xd4eb60,0x56c134,0x7002cc,0x7148a8,0x715834,0x4cf4fd0,0x800000,0x4d2ffc0,0x17aa4c]:
            offset = A(offset0)
            bad = bytearray(package.eg); bad[offset] ^= 1
            bad[-2:] = binascii.crc_hqx(bad[:-2],0).to_bytes(2,'big')
            reject(f'conflicting input {offset:#x}', lambda bad=bad: compatibility(bytes(bad),['precapture']), 'Incompatible')
        bad = bytearray(Package(candidate).eg); bad[A(0x2400000)] ^= 1
        bad[-2:] = binascii.crc_hqx(bad[:-2],0).to_bytes(2,'big')
        packet,_ = package.replace_eg(bytes(bad),'eg2070_0401p0.bi')
        reject('repaired checksums do not hide unrelated edits',lambda:verify_pair(data,packet,['prores','precapture']), 'outside declared')
        # Build from a layout-compatible input with an unrelated sentinel; preserve it exactly.
        source = bytearray(package.eg); source[A(0x2400000):A(0x2400000)+4] = b'\x13\x27\x42\x91'
        source[-2:] = binascii.crc_hqx(source[:-2],0).to_bytes(2,'big')
        from features import build
        output,_ = build(bytes(source),'04.02','p0',['prores','precapture'],a.compiler)
        check(output[A(0x2400000):A(0x2400000)+4] == source[A(0x2400000):A(0x2400000)+4], 'Unselected bytes changed')
        rows.append(dict(test='unselected input bytes preserved',result='PASS'))
        # Optimized Python must not disable the input guards.
        bad = bytearray(package.eg); bad[A(0x800000)] ^= 1
        bad[-2:] = binascii.crc_hqx(bad[:-2],0).to_bytes(2,'big')
        packet,_ = package.replace_eg(bytes(bad), fixture['module'])
        input_path = temp/'bad.bin'; input_path.write_bytes(packet)
        out = temp/'optimized-rejected'
        pr = subprocess.run([sys.executable,'-O',str(ROOT/'patch.py'),str(input_path),'--features','precapture',
                             '--version','04.01','--output',str(out)],capture_output=True,text=True)
        check(pr.returncode != 0 and not out.exists(), 'python -O disabled the compatibility guard')
        rows.append(dict(test='optimized Python rejects incompatible input without output',result='PASS'))
    # Menu-controlled configuration and explicit rejection of obsolete fixed-output switches.
    with tempfile.TemporaryDirectory(prefix='z8-config-tests-') as temporary:
        temp = Path(temporary)
        for diagnostic in (False, True):
            out = temp/str(diagnostic)
            cmd = [sys.executable, '-B', str(ROOT/'configure.py'), '--output', str(out)]
            if diagnostic: cmd.append('--diagnostic-footer')
            pr = subprocess.run(cmd, capture_output=True, text=True)
            check(pr.returncode == 0, pr.stderr)
            c = (out/'Z8PRE.CFG').read_bytes()
            check(c == build_config(diagnostic_footer=diagnostic), 'Configuration command differs')
            check(c[:16] == b'Z8PRECFGv4'.ljust(16, b'\0'), 'Configuration version')
            check(struct.unpack_from('<4I', c, 16) == (0x29b if diagnostic else 0x293,20,1500000,14), 'Menu configuration fields')
            check(zlib.crc32(c[:60]) == struct.unpack_from('<I', c, 60)[0], 'Configuration CRC')
            pr = subprocess.run(cmd, capture_output=True, text=True)
            check(pr.returncode != 0 and (out/'Z8PRE.CFG').read_bytes() == c, 'Existing configuration overwritten')
            rows.append(dict(test='menu configuration and overwrite refusal, diagnostic='+str(diagnostic), result='PASS'))
        for options in (['--capture-mode','raw-jpeg'],['--capture-mode','raw-only'],['--frames','5'],['--c15-only']):
            cmd = [sys.executable,'-B',str(ROOT/'configure.py'),'--output',str(temp/'rejected'),*options]
            pr = subprocess.run(cmd,capture_output=True,text=True)
            check(pr.returncode != 0 and not (temp/'rejected').exists(), 'Obsolete configuration option accepted')
            rows.append(dict(test='obsolete option rejected: '+options[0]+' '+options[-1], result='PASS'))
        pr = subprocess.run([sys.executable,'-B',str(ROOT/'patch.py'),str(a.stock.resolve()),'--features','precapture',
                             '--capture-mode','raw-only','--version','04.03','--output',str(temp/'rejected')],capture_output=True,text=True)
        check(pr.returncode != 0 and not (temp/'rejected').exists(), 'Old build mode silently accepted')
        rows.append(dict(test='obsolete fixed capture mode rejected by builder',result='PASS'))
    for selection in [[],['unknown'],['prores','prores']]:
        reject('invalid feature selection '+str(selection),lambda selection=selection:selected_features(selection),'Select')
    check(a.stock.read_bytes() == data, 'Input firmware modified')
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(dict(status='PASS',tests=rows),indent=2)+'\n')
    print('PASS: ' + str(len(rows)) + ' feature and rejection checks')


if __name__ == '__main__':
    main()
