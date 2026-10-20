#!/usr/bin/env python3
"""Independent Z8 3.11-family package codec + integrity chain (no builder imports).

Layout (body offsets are relative to the decoded body):
  raw  = [20B SHA1(body‖K8)] [12B outer context] [cipher]
  body = [32B plaintext spaces] [dir hdr 16B] [5×32B module entries] [modules] [2B body CRC16][14B zero trailer]

Integrity chain (recomputed in this order; reverse-checked by gauntlet):
  per-module CRC16-XMODEM (crc_hqx(module,0)==0, each module ends with its own CRC16)
  -> body CRC16 at body[-16:-14] over body[:-16] (crc_hqx(body[:-14],0)==0)
  -> outer SHA1 over body‖K8 (K8=6c12037e6fcec19a) at raw[:20]

Keystream: K[i] = A1[i&255] ^ A2[(i>>8)&255] ^ A3[(i>>16)&255], i body-relative.
Tables are recovered from the package itself with a normalization different from the
packer (same idea as merged/verify.py): an equivalent XOR factorization, same K.
body[0:32] is stored in the clear at raw[32:64]; the XOR covers every body index.
"""
import binascii
import hashlib
import struct

PACKAGE_BYTES = 99051117
OUTER_FIELD = bytes.fromhex('5866cd124269c27e621da226')          # 03.11 base
OUTER_FIELDS = (OUTER_FIELD, bytes.fromhex('196c6c7571a444b0b829e868'))  # + 03.12 base
def _k8():
    """Package authentication constant from local configuration; never a literal here.

    $Z8_AUTH_APPEND (hex) -> $Z8_AUTH_CONFIG (json path) -> auth_append.local.json
    or secrets/auth_append.local.json walking up from this file (see z8auth.py setup).
    """
    import json as _j, os as _o
    from pathlib import Path as _P
    raw = _o.environ.get('Z8_AUTH_APPEND')
    if raw:
        return bytes.fromhex(raw.strip())
    named = _o.environ.get('Z8_AUTH_CONFIG')
    cands = [_P(named)] if named else []
    here = _P(__file__).resolve()
    for parent in (here.parent, *here.parents):
        cands += [parent / 'auth_append.local.json', parent / 'secrets' / 'auth_append.local.json']
    for c in cands:
        if c.is_file():
            return bytes.fromhex(_j.loads(c.read_text())['auth_append'])
    raise ValueError('authentication constant is not configured: bring your own key — '
                     'python3 z8auth.py setup --package /path/to/your/official.bin')


K8 = _k8()   # local configuration, not source
EG_START, EG_LEN = 581844, 81807711
EG_END = EG_START + EG_LEN                     # 82389555
BODY_BYTES = PACKAGE_BYTES - 32                # 99051085
_ZERO_WINDOW = 0xB10000                        # body-relative known-zero 64 KiB window
_EMBEDDED_C = 0x3FF1F84                        # body-relative embedded C table

# (fixed name or None for EG, start, size) — official 03.11 layout, cross-checked vs directory
MODULES = (
    ('ex2070_030000.bi', 208, 524290),
    ('_tpj01_0210.bin', 524498, 57346),
    (None, EG_START, EG_LEN),
    ('vr2070_010100.bi', 82389555, 838664),
    (('li2070_0311b0.bi', 'li2070_031200.bi'), 83228219, 15822850),   # per base
)

IDENTITY_AT = 0x14eaa90                        # 8B runtime identity inside EG
PUBLIC_WORDS_AT = 0xeb29fc                     # 12B public version instructions inside EG


def sha256(data):
    return hashlib.sha256(data).hexdigest()


class PackageError(ValueError):
    pass


def _need(ok, message):
    if not ok:
        raise PackageError(message)


def recover_tables(cipher):
    """Recover A1/A2/A3 (normalized factorization) from one package's cipher."""
    _need(len(cipher) > _EMBEDDED_C + 256, 'cipher too short for table recovery')
    a1 = bytes(cipher[_ZERO_WINDOW:_ZERO_WINDOW + 256])
    a2 = bytes(cipher[_ZERO_WINDOW + 256 * y] ^ cipher[_ZERO_WINDOW] for y in range(256))
    partial = bytes(cipher[_EMBEDDED_C + x] ^ a1[(_EMBEDDED_C + x) & 255] ^ a2[((_EMBEDDED_C + x) >> 8) & 255]
                    for x in range(256))
    shift = partial[(_ZERO_WINDOW >> 16) & 255]
    a3 = bytes(t ^ shift for t in partial)
    return a1, a2, a3


def _keystream(a1, a2, a3, n):
    out = bytearray(n)
    plane = [bytes(a1[i & 255] ^ a2[(i >> 8) & 255] for i in range(65536)) for _ in range(1)]
    for hi in range((n + 65535) // 65536):
        base = hi * 65536
        z = min(base + 65536, n)
        k = a3[hi & 255]
        block = bytes(x ^ k for x in plane[0])
        out[base:z] = block[:z - base]
    return bytes(out)


class Codec:
    """One package's tables; decode once, re-encode mutated bodies with the same gauge."""

    def __init__(self, raw):
        _need(len(raw) == PACKAGE_BYTES, 'wrong package length: %d' % len(raw))
        _need(raw[20:32] in OUTER_FIELDS, 'wrong outer package context')
        self.outer = raw[20:32]
        self.raw = raw
        self.tables = recover_tables(raw[32:])
        self.ks = _keystream(*self.tables, BODY_BYTES)
        self.body = self._xor(raw[64:])   # cipher[32:] pairs with ks[32:]

    def _xor(self, cipher_tail):
        # int-block XOR: same math as the 64 KiB mask walk, ~10x faster.
        body = bytearray(BODY_BYTES)
        body[:32] = self.raw[32:64]
        n = len(cipher_tail)
        step = 1 << 23
        for base in range(0, n, step):
            z = min(base + step, n)
            x = int.from_bytes(cipher_tail[base:z], 'little') ^ int.from_bytes(self.ks[32 + base:32 + z], 'little')
            body[32 + base:32 + z] = x.to_bytes(z - base, 'little')
        return bytes(body)

    def encode(self, body):
        """plain body -> raw package (same XOR gauge + SHA1/outer envelope)."""
        _need(len(body) == BODY_BYTES, 'wrong body length: %d' % len(body))
        cipher = bytearray(BODY_BYTES)
        cipher[:32] = body[:32]
        n = BODY_BYTES - 32
        step = 1 << 23
        for base in range(0, n, step):
            z = min(base + step, n)
            x = int.from_bytes(body[32 + base:32 + z], 'little') ^ int.from_bytes(self.ks[32 + base:32 + z], 'little')
            cipher[32 + base:32 + z] = x.to_bytes(z - base, 'little')
        return hashlib.sha1(body + K8).digest() + self.outer + bytes(cipher)


def decode(raw):
    return Codec(raw).body


def module_crc16_fix(module):
    out = bytearray(module)
    out[-2:] = binascii.crc_hqx(out[:-2], 0).to_bytes(2, 'big')
    return bytes(out)


def eg_of(body):
    return body[EG_START:EG_END]


def set_eg(body, eg, name=None):
    """Replace EG payload (and optionally the directory EG name); CRC chain NOT repaired."""
    _need(len(eg) == EG_LEN, 'wrong EG length')
    out = bytearray(body)
    out[EG_START:EG_END] = eg
    if name is not None:
        out[112:128] = name.encode('ascii').ljust(16, b'\0')
    return bytes(out)


def repair_chain(body):
    """Repair every module CRC16 -> body CRC16 in chain order (outer SHA1 done by encode).

    This is what a competent attacker does: fully self-consistent envelopes, so only
    content gates can catch the edit.
    """
    out = bytearray(body)
    for _, start, size in MODULES:
        out[start:start + size] = module_crc16_fix(out[start:start + size])
    out[-16:-14] = binascii.crc_hqx(out[:-16], 0).to_bytes(2, 'big')
    return bytes(out)


def parse(raw):
    """Full structural verification: context, directory, CRC16 chain, outer SHA1.

    Returns parsed facts; raises PackageError with the first red reason.
    """
    rec = audit(raw)
    for key, msg in [('length_ok', 'wrong package length'), ('context_ok', 'wrong outer package context'),
                     ('header_ok', 'body header is not the 32B space label'),
                     ('dir_hdr_ok', 'module directory header mismatch'),
                     ('dir_ok', 'module boundary/name mismatch'),
                     ('modules_crc_ok', 'module CRC16 chain broken'), ('trailer_ok', 'body trailer is not 14 zero bytes'),
                     ('body_crc_ok', 'body CRC16 chain broken'), ('sha1_ok', 'outer SHA1 mismatch')]:
        _need(rec.get(key, False), msg + (': ' + rec['error'] if rec.get('error') else ''))
    return rec['facts']


def audit(raw, body=None):
    """Granular structural audit; never raises. Per-field booleans for gate attribution.

    Pass a pre-decoded `body` (mutant case) to skip the 99 MB re-decode.
    """
    rec = dict(length_ok=len(raw) == PACKAGE_BYTES, context_ok=False, decode_ok=False,
               header_ok=False, dir_hdr_ok=False, dir_ok=False, modules_crc_ok=False,
               trailer_ok=False, body_crc_ok=False, sha1_ok=False, error='', facts=None)
    if not rec['length_ok']:
        rec['error'] = 'length %d != %d' % (len(raw), PACKAGE_BYTES)
        return rec
    rec['context_ok'] = raw[20:32] in OUTER_FIELDS
    if body is None:
        try:
            body = decode(raw)
        except PackageError as exc:
            rec['error'] = str(exc)
            return rec
    elif len(body) != BODY_BYTES:
        rec['error'] = 'body length %d != %d' % (len(body), BODY_BYTES)
        return rec
    rec['decode_ok'] = True
    rec['header_ok'] = body[:32] == b' ' * 32
    count, headerlen, d1, d2 = struct.unpack_from('>4I', body, 32)
    rec['dir_hdr_ok'] = (count, headerlen, d1, d2) == (5, 208, 0, 0)
    entries, dir_ok, mods_crc = [], True, True
    for i, (want_name, start, size) in enumerate(MODULES):
        name_bytes, a, n, r0, r1 = struct.unpack_from('>16s4I', body, 48 + 32 * i)
        name = name_bytes.rstrip(b'\0')
        if name_bytes != name.ljust(16, b'\0') or (a, n, r0, r1) != (start, size, 0, 0):
            dir_ok = False
        want_names = (want_name,) if isinstance(want_name, str) else want_name
        if want_names is not None and name not in [w.encode() for w in (want_names or ())]:
            dir_ok = False
        module = body[a:a + n] if (a, n) == (start, size) else b''
        if binascii.crc_hqx(module, 0) != 0:
            mods_crc = False
        entries.append(dict(name=name.decode('ascii', 'replace'), start=a, bytes=n,
                            sha256=sha256(module) if module else ''))
    rec['dir_ok'] = dir_ok
    rec['modules_crc_ok'] = mods_crc
    rec['trailer_ok'] = body[-14:] == bytes(14)
    rec['body_crc_ok'] = binascii.crc_hqx(body[:-14], 0) == 0
    rec['sha1_ok'] = hashlib.sha1(body + K8).digest() == raw[:20]
    facts = {'body_sha256': sha256(body), 'package_sha256': sha256(raw), 'modules': entries,
             'eg_name': entries[2]['name'], 'identity': eg_identity(body[EG_START:EG_END]).decode('ascii', 'replace')}
    rec['facts'] = facts
    return rec


def eg_identity(eg):
    """8B runtime identity slot of an EG payload."""
    return eg[IDENTITY_AT:IDENTITY_AT + 8]


def diff_spans(a, b):
    """Merged [start,end) spans where two equal-length buffers differ.

    Block fast path (64 KiB slice compare) keeps the pure-Python scan proportional
    to the amount of difference, not to the 99 MB corpus.
    """
    _need(len(a) == len(b), 'diff on different lengths')
    spans = []
    start = end = None
    step = 1 << 16
    for base in range(0, len(a), step):
        z = min(base + step, len(a))
        if a[base:z] == b[base:z]:
            if start is not None:
                spans.append((start, end))
                start = None
            continue
        for i, (x, y) in enumerate(zip(a[base:z], b[base:z])):
            if x != y:
                at = base + i
                if start is None:
                    start = at
                end = at + 1
            elif start is not None:
                spans.append((start, end))
                start = None
    if start is not None:
        spans.append((start, end))
    return spans
