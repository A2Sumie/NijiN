#!/usr/bin/env python3
"""Red-line scanner: refuse to publish third-party proprietary or personal content.

Run before every push:

    python3 tools/redline_scan.py            # scan the working tree
    python3 tools/redline_scan.py --staged   # scan what Git has staged

What it refuses (the publication red lines):

  1. firmware-shaped files      .bin/.bi/.payload/.img/.elf/.dmp and friends
  2. binary content             anything that is not text, except the reviewed
                                brand PNGs in assets/ (plain PNG only)
  3. extracted device assets    settings-save files, font/icon/string dumps
  4. third-party commercial software and manufacturer repair documentation
  5. local identity             absolute paths, home directories, downloads,
                                hostnames, personal names
  6. credential-shaped strings  private keys, tokens, cloud keys
  7. embedded byte blobs        long hex/base64 payloads inline in source

Words that must never appear are written as patterns with a character class
(e.g. 'Tornado[N]KN') so this file does not contain them literally.
"""
import argparse
import pathlib
import re
import subprocess
import sys
import zlib

MAX_BYTES = 512 * 1024

# Brand PNGs are the only binary files allowed, and only as plain PNG.
ASSET_PNGS = {
    'assets/icon/nijin-icon-transparent.png', 'assets/icon/nijin-icon-white.png',
    'assets/icon/nijin-icon-black.png',
    'assets/wordmark/nijin-wordmark-transparent.png', 'assets/wordmark/nijin-wordmark-white.png',
    'assets/wordmark/nijin-wordmark-black.png',
    'assets/lockup/nijin-lockup-transparent.png', 'assets/lockup/nijin-lockup-white.png',
    'assets/lockup/nijin-lockup-black.png',
}

BLOCKED_SUFFIXES = {
    '.bin', '.bi', '.payload', '.bi2', '.elf', '.dtb', '.img', '.iso', '.dmg',
    '.zip', '.tar', '.tgz', '.7z', '.rar', '.pdf', '.cube', '.dylib', '.so',
    '.dll', '.a', '.o', '.class', '.nef', '.dng', '.nef~', '.dmp', '.cfg',
    '.mov', '.mp4', '.nev', '.r3d', '.rmd', '.exr', '.mxf', '.avi', '.wav',
    '.yuv', '.rgb', '.npz', '.npy', '.gpr', '.gzf', '.idb', '.i64', '.pem',
    '.key', '.p12', '.pfx', '.db', '.sqlite', '.bin16',
}
BLOCKED_PARTS = {
    'vendor', '.runtime', 'ghidra_work', '.ghidra', '.venv', 'venv',
    'node_modules', '__pycache__', '.aws', '.ssh', 'frames', 'cache',
    'local_data', '.codex', '.agents', 'Downloads', 'build', 'flash_kit',
}
BLOCKED_NAMES = {'.DS_Store', '.env', 'credentials.json', 'secrets.json',
                 'key.json', 'cookies.json'}

# Local identity and personal data.
LOCAL_PATHS = [
    (re.compile(rb'/Use' rb'rs/'), 'absolute macOS home path'),
    (re.compile(rb'/hom' rb'e/[a-z]'), 'absolute Linux home path'),
    (re.compile(rb'[A-Z]:\\+Use' rb'rs\\+'), 'absolute Windows home path'),
    (re.compile(rb'~/Down' rb'loads'), 'downloads path'),
]
PERSONAL = [
    (re.compile(rb'@gmail\.com|@qq\.com|@outlook\.com|@icloud\.com'), 'personal email'),
    (re.compile(rb'@users\.noreply\.github\.com'), 'personal GitHub noreply address'),
    (re.compile(rb'(?i)real[ _-]?name|user[ _-]?name\s*[:=]'), 'personal name field'),
]
FORBIDDEN_MARKS = [
    (re.compile(rb'Tornado[N]KN'), 'third-party commercial software reference'),
    (re.compile(rb'NCSE[T]\d+\.(BIN|bin)'), 'device settings file reference'),
    (re.compile(rb'servic' rb'e[ _-]?manua' rb'l', re.IGNORECASE), 'manufacturer repair documentation reference'),
]
SECRET_PATTERNS = [
    re.compile(rb'-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----'),
    re.compile(rb'\bgh[pousr]_[A-Za-z0-9]{30,}\b'),
    re.compile(rb'\bgithub_pat_[A-Za-z0-9_]{50,}\b'),
    re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    re.compile(rb'\bsk-(?:proj-)?[A-Za-z0-9_-]{30,}\b'),
    (re.compile(rb'\bolp_[A-Za-z0-9]{25,}\b')),
]
# Inline byte payloads: a hex literal of 128+ hex chars or a long base64 run.
BLOB_PATTERNS = [
    re.compile(rb'"[0-9a-fA-F]{128,}"'),
    re.compile(rb"'[0-9a-fA-F]{128,}'"),
    re.compile(rb'[A-Za-z0-9+/]{200,}={0,2}'),
]
# Exactly one reviewed exception: a short instruction sequence this project's own
# tooling emits into a code cave (its source is in z8precapture/firmware.c). Any
# other literal of this size is refused. Key = (path, first 16 hex characters).
REVIEWED_GENERATED_CODE = {
    ('z8precapture/patcher.py', 'c99ffc97880790d2'),
}
EXECUTABLE_MAGIC = (b'\x7fELF', b'\xcf\xfa\xed\xfe', b'\xce\xfa\xed\xfe',
                    b'\xfe\xed\xfa\xcf', b'\xfe\xed\xfa\xce', b'\xca\xfe\xba\xbe')


def plain_png(data):
    """Accept a small PNG with valid chunks and no embedded metadata."""
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        return False
    at, chunks = 8, []
    while at + 12 <= len(data):
        n = int.from_bytes(data[at:at + 4], 'big')
        kind = data[at + 4:at + 8]
        if kind not in (b'IHDR', b'IDAT', b'IEND') or at + n + 12 > len(data):
            return False
        payload = data[at + 8:at + 8 + n]
        stored = int.from_bytes(data[at + 8 + n:at + 12 + n], 'big')
        if zlib.crc32(kind + payload) & 0xffffffff != stored:
            return False
        if kind == b'IHDR':
            if chunks or n != 13 or not all(0 < int.from_bytes(payload[k:k + 4], 'big') <= 4096 for k in (0, 4)):
                return False
        chunks.append(kind)
        at += n + 12
        if kind == b'IEND':
            return n == 0 and at == len(data) and chunks[0] == b'IHDR' and b'IDAT' in chunks
    return False


def iter_files(root):
    skip = {'.git', '__pycache__', '.venv', 'venv', '.pytest_cache', '.ruff_cache'}
    for p in sorted(root.rglob('*')):
        if not p.is_file() or any(part in skip for part in p.parts):
            continue
        yield p


def git_staged():
    out = subprocess.run(['git', 'diff', '--cached', '--name-only', '-z'],
                         capture_output=True, check=True).stdout
    return [pathlib.Path(p) for p in out.decode().split('\0') if p]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--staged', action='store_true', help='scan staged files instead of the working tree')
    ap.add_argument('--root', type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1])
    args = ap.parse_args()
    root = args.root.resolve()
    files = [root / p for p in git_staged()] if args.staged else list(iter_files(root))
    issues = []
    scanned = 0
    for path in files:
        if not path.exists():
            continue
        rel = path.relative_to(root).as_posix()
        scanned += 1
        item = pathlib.PurePosixPath(rel)
        if item.suffix.lower() in BLOCKED_SUFFIXES:
            issues.append((rel, 'blocked suffix (firmware/dump/archive/settings shape)'))
        if any(part in BLOCKED_PARTS for part in item.parts):
            issues.append((rel, 'runtime/private path part'))
        if item.name in BLOCKED_NAMES or (item.name.startswith('.env.') and item.name != '.env.example'):
            issues.append((rel, 'private record name'))
        data = path.read_bytes()
        asset_png = rel in ASSET_PNGS and plain_png(data)
        if rel in ASSET_PNGS and not asset_png:
            issues.append((rel, 'brand PNG must be plain PNG (IHDR/IDAT/IEND only)'))
        if len(data) > MAX_BYTES:
            issues.append((rel, 'file exceeds the 512 KiB source limit'))
        if not asset_png:
            if b'\0' in data:
                issues.append((rel, 'NUL bytes suggest binary content'))
            else:
                try:
                    data.decode('utf-8')
                except UnicodeDecodeError:
                    issues.append((rel, 'non-text content outside the reviewed brand PNGs'))
        if data.startswith(EXECUTABLE_MAGIC):
            issues.append((rel, 'compiled executable magic'))
        for pattern, why in LOCAL_PATHS + PERSONAL + FORBIDDEN_MARKS:
            m = pattern.search(data)
            if m:
                line = data.count(b'\n', 0, m.start()) + 1
                issues.append((rel, '%s at line %d' % (why, line)))
        for pattern in SECRET_PATTERNS:
            m = pattern.search(data)
            if m:
                line = data.count(b'\n', 0, m.start()) + 1
                issues.append((rel, 'possible credential at line %d (value withheld)' % line))
        if not asset_png:
            for pattern in BLOB_PATTERNS:
                m = pattern.search(data)
                if m:
                    literal = m.group(0).strip(b'"\'')
                    if (rel, literal[:16].decode('ascii', 'ignore').lower()) in REVIEWED_GENERATED_CODE:
                        break
                    line = data.count(b'\n', 0, m.start()) + 1
                    issues.append((rel, 'inline byte blob at line %d' % line))
                    break
    for rel, why in issues:
        print('%s: %s' % (rel, why), file=sys.stderr)
    print('Red-line scan: %d files, %d issue(s).' % (scanned, len(issues)))
    if issues:
        print('VERDICT: FAIL — do not publish this tree.', file=sys.stderr)
        return 1
    print('VERDICT: PASS — no firmware bytes, no extracted assets, no personal data, '
          'no third-party commercial content, no local paths.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
