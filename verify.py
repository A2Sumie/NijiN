#!/usr/bin/env python3
"""Independent byte/container verification. Imports no builder, encoder or packer."""
import argparse
import binascii
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys

HERE = Path(__file__).resolve().parent

def auth_append():
    """Package authentication constant from local configuration; never a literal here.

    $Z8_AUTH_APPEND (hex) -> $Z8_AUTH_CONFIG (json path) -> auth_append.local.json
    or secrets/auth_append.local.json walking up from this file.
    """
    raw = os.environ.get('Z8_AUTH_APPEND')
    if raw:
        return bytes.fromhex(raw.strip())
    named = os.environ.get('Z8_AUTH_CONFIG')
    candidates = [Path(named)] if named else []
    for parent in (HERE, *HERE.parents):
        candidates += [parent / 'auth_append.local.json', parent / 'secrets' / 'auth_append.local.json']
    for candidate in candidates:
        if candidate.is_file():
            return bytes.fromhex(json.loads(candidate.read_text())['auth_append'])
    raise ValueError('authentication constant is not configured: bring your own key — python3 z8auth.py setup --package /path/to/your/official.bin')

sys.path.insert(0, str(HERE))
from z8prores import base as basemod  # noqa: E402


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(raw):
    need(len(raw) == 99051117 and raw[20:32] in (bytes.fromhex('5866cd124269c27e621da226'), bytes.fromhex('196c6c7571a444b0b829e868')), 'Wrong Z8 package context')
    # Independent recovery, with a different normalization than the packer:
    # A'[x]=cipher(zero+x), B'[y]=cipher(zero+256y)^cipher(zero), C'[g]=0.
    cipher = memoryview(raw)[32:]
    zero, embedded = 0xB10000, 0x3FF1F84
    low = bytes(cipher[zero:zero+256])
    middle = bytes(cipher[zero+256*y] ^ cipher[zero] for y in range(256))
    temporary = bytes(cipher[embedded+i] ^ low[(embedded+i)%256] ^ middle[((embedded+i)//256)%256] for i in range(256))
    plane = (zero//65536)%256
    high_key = bytes(t ^ temporary[plane] for t in temporary)
    keys = low, middle, high_key
    b = bytearray(raw[32:])
    masks = {}
    # Separate 64 KiB stream construction, indexed by absolute position in body.
    for a in range(0, len(b), 65536):
        z = min(a + 65536, len(b))
        high = (a >> 16) & 255
        if high not in masks:
            masks[high] = b''.join(bytes(x ^ keys[1][j] ^ keys[2][high] for x in keys[0]) for j in range(256))
        mask = masks[high]
        value = int.from_bytes(b[a:z], 'little') ^ int.from_bytes(mask[:z-a], 'little')
        b[a:z] = value.to_bytes(z-a, 'little')
    b[:32] = raw[32:64]
    b = bytes(b)
    need(b[:32] == b' '*32 and struct.unpack_from('>4I', b, 32) == (5, 208, 0, 0), 'Wrong directory')
    need(b[-14:] == bytes(14) and binascii.crc_hqx(b[:-14], 0) == 0, 'Body CRC or trailer mismatch')
    need(hashlib.sha1(b + auth_append()).digest() == raw[:20], 'SHA1 mismatch')
    expected = [(208,524290),(524498,57346),(581844,81807711),(82389555,838664),(83228219,15822850)]
    for i,(a,n) in enumerate(expected):
        _, start, size, r0, r1 = struct.unpack_from('>16s4I', b, 48+32*i)
        need((start,size,r0,r1) == (a,n,0,0), 'Module boundary mismatch')
        need(binascii.crc_hqx(b[a:a+n], 0) == 0, 'Module CRC mismatch')
    return b


def verify_pair(original, candidate, features=None):
    a, b = decode(original), decode(candidate)
    need(a[:112] == b[:112] and a[128:581844] == b[128:581844] and
         a[82389555:-16] == b[82389555:-16], 'Non-EG module or header changed')
    old, new = a[581844:82389555], b[581844:82389555]
    basemod.CURRENT['base'] = basemod.identity_of(old)
    profile_files = {'prores': 'profile.json', 'precapture': 'precapture.json',
                     'opengate': 'opengate.json', 'menuh': 'menuh.json'}
    profiles = {name: json.loads(basemod.profile_path(f).read_text()) for name, f in profile_files.items()}
    if features is None:
        features = []
        for name, offset in [('prores', 0xeb62ec), ('precapture', 0xe0fe90), ('opengate', 0x573120), ('menuh', 0xeb5598)]:
            offset = basemod.at(offset)
            if old[offset:offset+4] != new[offset:offset+4]:
                features.append(name)
    need(features and len(features) == len(set(features)) and set(features) <= set(profiles), 'Invalid feature selection')
    for name in features:
        for r in profiles[name]['ranges']:
            start, end = int(r['start'],16), int(r['end'],16)
            need(sha(old[start:end]) == r['sha256'], 'Input compatibility guard: ' + r['purpose'])
    identity = new[0x14EAA90:0x14EAA98]
    old_identity = old[0x14EAA90:0x14EAA98]
    spans = []
    for buf, text in [(old, old_identity), (new, identity)]:
        need(re.fullmatch(rb'[0-9]{2}\.[0-9]{2}\.(?:[a-z]\d|[0-9]{2})', text) and buf[-11:-3] == text, 'Internal identity mismatch')  # LOCAL DEVIATION: 03.12 stock tag is numeric
        w0,w1,w2 = struct.unpack_from('<3I',buf,basemod.at(0xEB29FC))
        need((w0 & ~0x1FFFE0,w1 & ~0x1FFFE0,w2 & ~0x1FFFE0) == (0x52800008,0x72A00008,0x52800009), 'Version instruction shape')
        value = struct.pack('<I',((w0>>5)&65535)|(((w1>>5)&65535)<<16)) + struct.pack('<H',(w2>>5)&65535)
        need(value == text[:5] + b'\0', 'Public identity mismatch')
    need(tuple(map(int,identity[:5].split(b'.'))) >= tuple(map(int,old_identity[:5].split(b'.'))), 'Version must increase')  # LOCAL DEVIATION
    module = b'eg2070_' + identity[:5].replace(b'.',b'') + identity[6:] + b'.bi'
    need(b[112:128] == module.ljust(16,b'\0'), 'Output directory EG name mismatch')
    expected = {}
    for name in ('prores', 'precapture', 'opengate', 'menuh'):
        if name not in features:
            continue
        for e in profiles[name]['patches']:
            start, size = int(e['offset'],16), e['bytes']
            allowed = e.get('loader_input_sha256', profiles[name].get('loader_input_sha256', [e['old_sha256']])) \
                if start == basemod.at(0x1024d8c) else [e['old_sha256']]  # LOCAL DEVIATION: loader end shared by several features
            need(sha(old[start:start+size]) in allowed, 'Input patch bytes differ')
            if start in expected:
                need(start in (basemod.at(0x1024d8c), basemod.at(0x1024d8c) + 4) and size == expected[start]['bytes'] == 8, 'Unapproved feature overlap')
            expected[start] = e
    for start, e in expected.items():
        size = e['bytes']
        need(sha(new[start:start+size]) == e['new_sha256'], 'Output differs from reviewed feature patch bytes')
        spans.append((start,start+size))
    spans += [(basemod.at(0xEB29FC),basemod.at(0xEB29FC)+12),(0x14EAA90,0x14EAA98),(len(old)-11,len(old)-3),(len(old)-2,len(old))]
    end = 0
    for lo,hi in sorted(spans):
        need(end <= lo and old[end:lo] == new[end:lo], 'Overlapping edits or change outside declared windows')
        end = hi
    need(old[end:] == new[end:], 'Unlisted final change')
    return dict(status='PASS', input_sha256=sha(original), output_sha256=sha(candidate),
                output_identity=identity.decode(), features=sorted(features), patch_matches_reviewed_profile=True,
                all_non_patch_EG_bytes_preserved=True, other_modules_preserved=True,
                scope='Offline byte equivalence and integrity; not a camera test')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('original',type=Path)
    ap.add_argument('candidate',type=Path)
    ap.add_argument('--features', nargs='+', choices=['prores','precapture','opengate','menuh'], help='Expected new features; otherwise detect changed entry hooks')
    a = ap.parse_args()
    # Bound file reads before decoding.
    need(a.original.stat().st_size == a.candidate.stat().st_size == 99051117, 'Wrong file lengths')
    print(json.dumps(verify_pair(a.original.read_bytes(),a.candidate.read_bytes(),a.features),indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as e:
        raise SystemExit('ERROR: ' + str(e))
