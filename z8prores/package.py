"""Equal-size Z8 3.11-family envelope reader/writer; no filesystem output or devices.

XOR parameters are recovered from the caller's input (see NOTICE.md).
The first 32 body bytes are unencrypted; stream indices remain body-relative.
"""
import binascii
import hashlib
import json
from pathlib import Path
import re
import struct

RESOURCES = Path(__file__).resolve().parents[1] / 'resources'
PACKAGE_BYTES = 99051117
OUTER_FIELD = bytes.fromhex('5866cd124269c27e621da226')
AUTH_APPEND = bytes.fromhex('6c12037e6fcec19a')
MODULES = (
    ('ex2070_030000.bi', 208, 524290, '4b7ea2ea40360717ceffd3d8db6fe48f5fae9d5c13b69632dc750bdc41b571c2'),
    ('_tpj01_0210.bin', 524498, 57346, '689f80feb0d271d73ac719e0c5872cfc0dac643097e528b6a1b156d4c55efe1a'),
    (None, 581844, 81807711, None),
    ('vr2070_010100.bi', 82389555, 838664, '30e363077655f9936894fdc00104263eac4a33892e621199f84bf8f4cecea3bb'),
    ('li2070_0311b0.bi', 83228219, 15822850, '804a55508cd6b323336fbba14034810e4b22fcc5fd1030d3a7dc08d62767cc55'),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    # Always enforced, including python -O.
    if not condition:
        raise ValueError(message)


def recover_tables(encoded):
    """Recover an equivalent XOR factorization without shipping reference tables.

    A known zero 64 KiB window yields A[x]^A[0] and B[y]^B[0].
    The encrypted embedded C table then yields C[z]^A[0]^B[0], using
    the known zero-window plane to remove its remaining constant.
    These normalized factors produce the original stream for every index.
    CRC/SHA1 and fixed module hashes validate the reconstruction afterward.
    """
    zero = 0xB10000                 # body-relative; EG offset A81F2Ch, outside the ProRes patch
    embedded_c = 0x3FF1F84          # body-relative; EG offset 3F63EB0h
    require(len(encoded) > embedded_c + 256, 'Input too short for format recovery')
    a = bytes(encoded[zero + x] ^ encoded[zero] for x in range(256))
    b = bytes(encoded[zero + 256*y] ^ encoded[zero] for y in range(256))
    partial = bytes(encoded[embedded_c+x] ^ a[(embedded_c+x)&255] ^
                    b[((embedded_c+x)>>8)&255] for x in range(256))
    shift = partial[(zero>>16)&255] ^ encoded[zero]
    return a, b, bytes(value ^ shift for value in partial)


def transform(body, tables):
    a, b, c = tables
    masks = [bytes(x ^ k for x in a) for k in range(256)]
    stream = b''.join(masks[y ^ z] for z in c for y in b)
    out = bytearray()
    for first in range(0, len(body), len(stream)):
        block = body[first:first + len(stream)]
        value = int.from_bytes(block, 'little') ^ int.from_bytes(stream[:len(block)], 'little')
        out.extend(value.to_bytes(len(block), 'little'))
    out[:32] = body[:32]
    return bytes(out)


class Package:
    def __init__(self, raw):
        require(len(raw) == PACKAGE_BYTES, 'Unsupported package length; expected Z8 3.11 layout')
        require(raw[20:32] == OUTER_FIELD, 'Unsupported outer package context')
        self.tables = recover_tables(raw[32:])
        self.body = transform(raw[32:], self.tables)
        body = self.body
        require(body[:32] == b' ' * 32, 'Invalid body header')
        require(struct.unpack_from('>4I', body, 32) == (5, 208, 0, 0), 'Unsupported module directory')
        require(body[-14:] == bytes(14), 'Invalid trailer')
        require(binascii.crc_hqx(body[:-14], 0) == 0, 'Package body CRC mismatch')
        require(hashlib.sha1(body + AUTH_APPEND).digest() == raw[:20], 'Package SHA1 mismatch')
        self.modules = []
        for i, (expected_name, start, size, expected_sha) in enumerate(MODULES):
            name_bytes, a, n, r0, r1 = struct.unpack_from('>16s4I', body, 48 + i * 32)
            name = name_bytes.rstrip(b'\0').decode('ascii')
            require(name_bytes == name.encode().ljust(16, b'\0'), 'Noncanonical module name')
            require((a, n, r0, r1) == (start, size, 0, 0), f'Module {i} layout mismatch')
            if i == 2:
                require(re.fullmatch(r'eg2070_\d{4}[a-z]\d\.bi', name), 'Unsupported EG module identity')
            else:
                require(name == expected_name, f'Unsupported module {i}')
            data = body[a:a + n]
            require(binascii.crc_hqx(data, 0) == 0, f'{name}: module CRC mismatch')
            require(expected_sha is None or sha(data) == expected_sha, f'{name}: not a supported 3.11 module')
            self.modules.append(dict(name=name, start=a, bytes=n, sha256=sha(data)))
        self.eg = body[581844:581844 + 81807711]
        self.sha256 = sha(raw)

    def replace_eg(self, eg, name):
        require(len(eg) == 81807711 and binascii.crc_hqx(eg, 0) == 0, 'Invalid replacement EG')
        require(re.fullmatch(r'eg2070_\d{4}[a-z]\d\.bi', name), 'Invalid output EG name')
        body = bytearray(self.body)
        body[112:128] = name.encode().ljust(16, b'\0')
        body[581844:581844 + len(eg)] = eg
        body[-16:-14] = binascii.crc_hqx(body[:-16], 0).to_bytes(2, 'big')
        packet = hashlib.sha1(body + AUTH_APPEND).digest() + OUTER_FIELD + transform(body, self.tables)
        checked = Package(packet)
        require(checked.eg == eg, 'Replacement did not round-trip')
        for i in [0, 1, 3, 4]:
            require(checked.modules[i] == self.modules[i], 'Unselected module changed')
        return packet, checked
