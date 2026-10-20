"""Profile guards, ProRes patch construction, identity changes and exact change accounting."""
import binascii
import json
import re
import struct
from .package import RESOURCES, require, sha
from .base import at as _at, profile_path, adopt as _adopt

VERSION_AT = 0x14EAA90
CODE_VERSION_AT = 0xEB29FC


def public_words(version):
    require(re.fullmatch(r'[0-9]{2}\.[0-9]{2}', version), 'Version must be two digits, a dot and two digits, e.g. 04.01')
    raw = version.encode()
    return struct.pack('<3I', 0x52800008 | (int.from_bytes(raw[:2], 'little') << 5),
                       0x72A00008 | (int.from_bytes(raw[2:4], 'little') << 5),
                       0x52800009 | (raw[4] << 5))


def compatibility(eg):
    _adopt(eg)
    profile = json.loads(profile_path('profile.json').read_text())
    require(len(eg) == profile['payload_bytes'], 'Unsupported EG length')
    require(binascii.crc_hqx(eg, 0) == 0, 'Input EG CRC mismatch')
    ident = eg[VERSION_AT:VERSION_AT + 8]
    require(re.fullmatch(rb'[0-9]{2}\.[0-9]{2}\.(?:[a-z]\d|[0-9]{2})', ident), 'Unsupported runtime identity')  # LOCAL DEVIATION: 03.12 stock carries a numeric tag
    require(eg[-11:-3] == ident, 'Runtime and trailer versions disagree')
    version = ident[:5].decode()
    require(eg[_at(CODE_VERSION_AT):_at(CODE_VERSION_AT) + 12] == public_words(version), 'Public and internal versions disagree')
    for r in profile['ranges']:
        a, b = int(r['start'], 16), int(r['end'], 16)
        require(sha(eg[a:b]) == r['sha256'], 'Incompatible region: ' + r['purpose'] +
                f' ({a:#x}..{b:#x}); already patched images are not supported')
    for e in profile['patches']:
        a, n = int(e['offset'], 16), e['bytes']
        require(sha(eg[a:a + n]) == e['old_sha256'], 'Patch input conflicts at ' + e['offset'])
    return profile, ident.decode()


def build(eg, version, tag):
    profile, old_identity = compatibility(eg)
    public_words(version)
    require(re.fullmatch(r'[a-z][0-9]', tag), 'Tag must be a lowercase letter and digit, e.g. p0')
    require(tuple(map(int, version.split('.'))) > tuple(map(int, old_identity[:5].split('.'))),
            'Output version must be higher than the input version')
    # Keep Capstone optional for --check; it is only needed to build/review emitted instructions.
    from .menu import build_main
    image, metadata = build_main(eg[:-2])
    actual = {e['offset']: e for e in image.edits}
    require(len(actual) == len(profile['patches']), 'Unexpected patch edit count')
    edits = []
    for expected in profile['patches']:
        offset = int(expected['offset'], 16)
        e = actual.get(offset)
        require(e is not None and len(e['new']) == expected['bytes'] and
                sha(e['old']) == expected['old_sha256'] and sha(e['new']) == expected['new_sha256'],
                f'Generated patch differs from the reviewed ProRes recipe at {offset:#x}')
        edits.append(dict(offset=offset, bytes=len(e['new']), purpose=e['purpose'],
                          before_sha256=sha(e['old']), after_sha256=sha(e['new'])))
    out = bytearray(image.new) + bytearray(eg[-2:])
    identity = f'{version}.{tag}'.encode()
    for offset, value, purpose in [(_at(CODE_VERSION_AT), public_words(version), 'public version instructions'),
                                    (VERSION_AT, identity, 'runtime identity'),
                                    (len(out) - 11, identity, 'trailer identity')]:
        require(not any(offset < e['offset'] + e['bytes'] and e['offset'] < offset + len(value) for e in edits), 'Identity overlaps patch')
        before = bytes(out[offset:offset + len(value)])
        out[offset:offset + len(value)] = value
        edits.append(dict(offset=offset, bytes=len(value), purpose=purpose,
                          before_sha256=sha(before), after_sha256=sha(value)))
    out[-2:] = binascii.crc_hqx(out[:-2], 0).to_bytes(2, 'big')
    edits.append(dict(offset=len(out)-2, bytes=2, purpose='EG CRC16',
                      before_sha256=sha(eg[-2:]), after_sha256=sha(out[-2:])))
    # Compare every interval outside the declared edit windows.
    end = 0
    preserved = []
    for e in sorted(edits, key=lambda r: r['offset']):
        start = e['offset']
        require(end <= start, 'Overlapping edits')
        require(eg[end:start] == out[end:start], 'Unlisted byte modification')
        if end < start:
            preserved.append(dict(start=end, end=start, sha256=sha(eg[end:start])))
        end = start + e['bytes']
    require(eg[end:] == out[end:], 'Unlisted tail modification')
    require(binascii.crc_hqx(out, 0) == 0, 'Output CRC mismatch')
    return bytes(out), dict(input_identity=old_identity, output_identity=identity.decode(),
                            profile=profile['id'], edits=edits, preserved_ranges=preserved,
                            all_bytes_outside_edits_preserved=True, menu=metadata)
