#!/usr/bin/env python3
"""Integration/negative tests; firmware inputs are supplied externally, never bundled."""
import argparse
import binascii
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from z8prores.package import Package, sha
from z8prores.patcher import build, compatibility, public_words
from z8prores import base as basemod
from verify import verify_pair

# Pinned test fixtures: one per supported base. A fixture variant keeps the same checks;
# only the recipe coordinates, the module name and the reference output move with the base.
FIXTURES = {
    '03.11': dict(sha256='d67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96',
                  module='eg2070_0311b0.bi',
                  prores_ref='780d2a3a6f724743a4619ca646b22c29d2ca43ce17cf7d4c1ad2d0b7ae8df922'),
    '03.12': dict(sha256='d662dd9dd5da937cb418162c238065e918dcefafd47b47537c3f934d39e83037',
                  module='eg2070_031200.bi',
                  prores_ref='0f2f4ebf705576fb05fc119f06b8231d5f08e298b423f3b4b773c07a230d2108'),
}


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def crc(data):
    value = bytearray(data)
    value[-2:] = binascii.crc_hqx(value[:-2], 0).to_bytes(2, 'big')
    return bytes(value)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stock', type=Path, required=True)
    ap.add_argument('--report', type=Path)
    a = ap.parse_args()
    if a.report and a.report.exists():
        raise SystemExit('Report exists; use a new path')
    data = a.stock.read_bytes()
    fixture = next((v for v in FIXTURES.values() if sha(data) == v['sha256']), None)
    check(fixture is not None, 'Expected a pinned test fixture: official 03.11 or official 03.12')
    basemod.CURRENT['base'] = next(k for k, v in FIXTURES.items() if v is fixture)

    def A(off):
        return basemod.at(off)          # recipe offset -> the fixture's base

    package = Package(data)
    results = []

    def reject(name, fn, expected):
        try:
            fn()
        except ValueError as error:
            check(expected in str(error), name + ': wrong rejection reason: ' + str(error))
            results.append(dict(test=name, result='REJECTED', reason=str(error)))
        else:
            raise RuntimeError('Negative control accepted: ' + name)

    reject('truncated input', lambda: Package(data[:-1]), 'length')
    corrupt = bytearray(data); corrupt[200] ^= 1
    reject('damaged package', lambda: Package(bytes(corrupt)), 'CRC')
    corrupt = bytearray(data); corrupt[20] ^= 1
    reject('wrong package context', lambda: Package(bytes(corrupt)), 'context')
    for site, name in [(0x75F900,'occupied code gap'),(0xEB62EC,'changed bank hook'),(0x4BF3A60,'changed UI state')]:
        site = A(site)
        bad = bytearray(package.eg); bad[site] ^= 1
        reject(name, lambda bad=bad: compatibility(crc(bad)), 'Incompatible region')
    bad = bytearray(package.eg)          # flip one digit of the runtime identity, whatever the fixture
    bad[0x14EAA94] = ord('9') if bad[0x14EAA94] != ord('9') else ord('8')
    reject('inconsistent identity', lambda: compatibility(crc(bad)), 'versions disagree')
    reject('bad display version syntax', lambda: public_words('3.22'), 'two digits')
    reject('non-increasing version', lambda: build(package.eg,'03.11','p0'), 'higher')
    reject('bad tag', lambda: build(package.eg,'03.23','toolong'), 'Tag')

    # Build via public CLI to cover default tag, output naming, exclusive writes and independent verifier.
    with tempfile.TemporaryDirectory(prefix='z8-prores-test-') as temp:
        out = Path(temp)/'stock'
        run = subprocess.run([sys.executable,'-B',str(HERE/'patch.py'),str(a.stock.resolve()),
                              '--version','03.23','--output',str(out)],capture_output=True,text=True)
        check(run.returncode == 0, run.stderr)
        patched = (out/'Z_8_0323.bin').read_bytes()
        record = verify_pair(data,patched)
        check(record['output_identity'] == '03.23.p0','Default tag is not p0')
        check(sha(patched) == fixture['prores_ref'],
              'Stock ProRes output differs from the verified reference')
        results.append(dict(test='stock firmware via CLI',**record))
        run = subprocess.run([sys.executable,'-B',str(HERE/'patch.py'),str(a.stock.resolve()),
                              '--version','03.23','--output',str(out)],capture_output=True,text=True)
        check(run.returncode != 0 and 'already exists' in run.stderr,'Existing output was not refused')
        check((out/'Z_8_0323.bin').read_bytes() == patched,'Existing output changed')
        results.append(dict(test='existing output preserved',result='PASS'))
        wrong = Path(temp)/'wrong.bin'; wrong.write_bytes(data[:-1])
        rejected = Path(temp)/'rejected'
        run = subprocess.run([sys.executable,'-O',str(HERE/'patch.py'),str(wrong),
                              '--version','03.23','--output',str(rejected)],capture_output=True,text=True)
        check(run.returncode != 0 and not rejected.exists(),'Optimized Python bypassed guard or left output')
        results.append(dict(test='guards active under python -O; no output on rejection',result='PASS'))
        reject('already patched image',lambda: compatibility(Package(patched).eg),'Incompatible region')

    # Synthetic sentinels verify preservation outside the ProRes patch; never install this test image.
    sentinel = bytearray(package.eg)
    for site in [0x14E5000,0x2400000,0x3E00000]:
        sentinel[A(site):A(site)+4] = b'\x13\x27\x42\x91'
    sentinel = crc(sentinel)
    custom_packet,_ = package.replace_eg(sentinel, fixture['module'])
    custom = Package(custom_packet)
    changed,metadata = build(custom.eg,'04.07','p0')
    output,_ = custom.replace_eg(changed,'eg2070_0407p0.bi')
    record = verify_pair(custom_packet,output)
    results.append(dict(test='custom table bytes preserved; custom major/minor version 04.07',**record))
    for site in [0x14E5000,0x2400000,0x3E00000]:
        check(changed[A(site):A(site)+4] == sentinel[A(site):A(site)+4],'Input table changed')

    # Repair all envelopes, then ensure independent verifier still rejects an unrelated byte edit.
    bad = bytearray(changed);bad[A(0x14E5000)] ^= 1
    tampered,_ = custom.replace_eg(crc(bad),'eg2070_0407p0.bi')
    reject('repaired CRC/SHA1 with unrelated changed byte',lambda:verify_pair(custom_packet,tampered),'outside declared')

    check(a.stock.read_bytes() == data,'Stock input changed')
    result = dict(status='PASS',tests=results,
                  source_sha256={str(p.relative_to(HERE)):sha(p.read_bytes()) for p in
                                 sorted([*HERE.glob('*.py'),*HERE.glob('z8prores/*.py'),*HERE.glob('resources/*.json'),Path(__file__).resolve()])})
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        with a.report.open('x') as f:
            json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
