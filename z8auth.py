#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2026 the NijiN authors
"""z8auth — bring your own key.

The package authentication constant is a per-model key. This tree ships the method,
never the key: you supply your own official update package (or your own key value),
the tool derives the key from that package, proves it against the package's own
header digest, and writes it to local configuration. Nothing is downloaded, nothing
is built in, and no key value is ever printed or logged.

    python3 z8auth.py setup --package /path/to/your/Z_8_0311.bin
    python3 z8auth.py setup --package /path/to/your/Z_8_0311.bin --also /path/to/Z_8_0312.bin
    python3 z8auth.py setup --package /path/to/your/Z_8_0311.bin --k8 <your hex value>
    python3 z8auth.py status

Method (93_KEYTOOL_CROSSVAL §1.2): the outer header carries SHA1(plain body ‖ K8) with
K8 = seed XOR k. The seed is the 8-byte constant 24 bytes before the SHA-1 IV literal in
your own package; k[i] = (b + a*((i+1)*M + i*(i+1)//2)) & 0xFF over 131,072 (a, b, M)
candidates. A candidate is accepted only when the digest verifies against your package,
and a second package of the same model must agree (93: one model, one key).

Output: secrets/auth_append.local.json, mode 0600, never overwritten.
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True

CONFIG_NAME = 'auth_append.local.json'
SHA1_IV = bytes.fromhex('0123456789abcdef')  # SHA-1 H0,H1 as stored (little-endian), 8B binary
SEED_BACK = 24                          # seed sits this many bytes before that literal
MODELS = (0x260, 0xD3)                  # the two k-period constants (93 §1.2)


class Rejected(ValueError):
    """The supplied material did not verify; nothing was written."""


def _body_of(raw):
    """Plain body of a package. Tables are recovered from the input itself (method, not key)."""
    from z8prores.package import Package
    return Package(raw).body


def _digest_ok(state, key, raw):
    """SHA1(body ‖ key) against the package header, from a pre-fed hash state.

    The body is 80+ MiB and the search is 131,072 candidates: feed the body once,
    then finish a copy per candidate. Same digest, no re-hashing.
    """
    h = state.copy()
    h.update(key)
    return h.digest() == raw[:20]


def _seeds_from(body):
    """Seed candidates: 8 bytes before *every* SHA-1 IV literal (93 §1.2 seed_offsets)."""
    out, at = [], body.find(SHA1_IV)
    while at >= 0:
        if at >= SEED_BACK + 8:
            out.append(body[at - SEED_BACK:at - SEED_BACK + 8])
        at = body.find(SHA1_IV, at + 1)
    if not out:
        raise Rejected('no key seed in this package: the SHA-1 IV constant is missing')
    return out


def _kstream(a, b, m):
    """93 §1.2 keystream: an accumulator whose step grows by a each round."""
    out, acc, step = bytearray(), b, (a * m) & 0xFFFFFFFF
    for _ in range(8):
        acc = (acc + step) & 0xFFFFFFFF
        out.append(acc & 0xFF)
        step = (step + a) & 0xFFFFFFFF
    return bytes(out)


def derive(raw):
    """Derive the key from one package: seed from the image, k by search, digest as the judge."""
    body = _body_of(raw)
    state = hashlib.sha1(body)              # fed, not finalized
    found = []
    for seed in _seeds_from(body):
        for m in MODELS:
            for a in range(256):
                for b in range(256):
                    ks = _kstream(a, b, m)
                    key = bytes(seed[i] ^ ks[i] for i in range(8))
                    if _digest_ok(state, key, raw):
                        found.append(key)
    unique = {k for k in found}
    if not unique:
        raise Rejected('no key matches this package: wrong package family, or not an official image')
    if len(unique) > 1:
        raise Rejected('ambiguous derivation: %d keys verify against this package' % len(unique))
    return body, unique.pop()


def _locate_out(explicit):
    if explicit:
        return Path(explicit)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / 'secrets').is_dir():
            return parent / 'secrets' / CONFIG_NAME
    return here.parents[4] / 'secrets' / CONFIG_NAME


def write_config(path, key, source_note):
    """Atomic, exclusive, 0600. A failed write leaves nothing behind and never overwrites."""
    if path.exists():
        raise Rejected('%s already exists: refusing to overwrite a key you supplied' % path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({'auth_append': key.hex(), 'note': source_note}, indent=2) + '\n'
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix='.auth_append.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, 0o600)
        os.link(tmp, path)            # exclusive: fails if someone else created it first
    finally:
        os.unlink(tmp) if os.path.exists(tmp) else None
    return path


def cmd_setup(args):
    raw = Path(args.package).read_bytes()
    if args.k8:
        body = _body_of(raw)
        key = bytes.fromhex(args.k8.strip())
        if len(key) != 8:
            raise Rejected('the key must be 8 bytes')
        if not _digest_ok(hashlib.sha1(body), key, raw):
            raise Rejected('your key does not verify against your package (SHA1(body‖K8) mismatch)')
    else:
        body, key = derive(raw)
    if args.also:
        raw2 = Path(args.also).read_bytes()
        body2, key2 = derive(raw2)
        if key2 != key:
            raise Rejected('your two packages disagree on the key: different models, or one is not official')
    out = _locate_out(args.out)
    write_config(out, key, 'supplied by the operator from their own package; derived and verified by z8auth setup')
    print('verified against your package: SHA1(body‖K8) holds')
    if args.also:
        print('cross-checked: both packages agree (one model, one key)')
    print('written: %s (mode 0600)' % out)
    print('note: this file is local configuration. It is not part of the tree and not distributed.')
    return 0


def cmd_status(args):
    out = _locate_out(args.out)
    if not out.exists():
        print('missing: %s' % out)
        print('supply your own key:  python3 z8auth.py setup --package /path/to/your/official.bin')
        return 1
    from z8prores.authkey import auth_append
    key = auth_append()
    print('present: %s' % out)
    print('key length: %d bytes; value not shown' % len(key))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('setup', help='derive the key from your own package and store it locally')
    s.add_argument('--package', required=True, help='your own official update package')
    s.add_argument('--also', help='a second package of the same model, for the one-model-one-key check')
    s.add_argument('--k8', help='your own key value (hex, 8 bytes) instead of deriving it')
    s.add_argument('--out', help='where to write the local configuration (default: secrets/ above this tree)')
    s.set_defaults(fn=cmd_setup)
    t = sub.add_parser('status', help='is a key configured? (never prints the value)')
    t.add_argument('--out')
    t.set_defaults(fn=cmd_status)
    a = ap.parse_args()
    try:
        return a.fn(a)
    except (Rejected, ValueError, OSError, KeyError) as exc:
        print('ERROR: %s' % exc, file=sys.stderr)
        print('nothing was written; supply your own key and run setup again', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
