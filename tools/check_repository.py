#!/usr/bin/env python3
"""Check index content without printing potential credential values."""
import argparse
import pathlib
import re
import subprocess
import sys
import zlib

MAX_BYTES = 512 * 1024
# Only the project's own brand PNGs may hold binary content, and only as plain PNG
# (IHDR/IDAT/IEND chunks, no metadata). Provenance: assets/ASSETS.md.
ASSET_PNGS = {
    'assets/icon/nijin-icon-transparent.png',
    'assets/icon/nijin-icon-white.png',
    'assets/icon/nijin-icon-black.png',
    'assets/wordmark/nijin-wordmark-transparent.png',
    'assets/wordmark/nijin-wordmark-white.png',
    'assets/wordmark/nijin-wordmark-black.png',
    'assets/lockup/nijin-lockup-transparent.png',
    'assets/lockup/nijin-lockup-white.png',
    'assets/lockup/nijin-lockup-black.png',
}


def plain_png(data):
    """Accept small screenshots with valid chunks and no embedded metadata."""
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        return False
    at, chunks = 8, []
    while at + 12 <= len(data):
        n = int.from_bytes(data[at:at+4], 'big')
        kind = data[at+4:at+8]
        if kind not in (b'IHDR', b'IDAT', b'IEND') or at + n + 12 > len(data):
            return False
        payload = data[at+8:at+8+n]
        stored = int.from_bytes(data[at+8+n:at+12+n], 'big')
        if zlib.crc32(kind + payload) & 0xffffffff != stored:
            return False
        if kind == b'IHDR':
            if chunks or n != 13 or not all(0 < int.from_bytes(payload[k:k+4], 'big') <= 4096 for k in (0, 4)):
                return False
        chunks.append(kind)
        at += n + 12
        if kind == b'IEND':
            return n == 0 and at == len(data) and chunks[0] == b'IHDR' and b'IDAT' in chunks
    return False


BLOCKED_SUFFIXES = {
    '.bin', '.payload', '.bi', '.elf', '.dtb', '.img', '.iso', '.dmg',
    '.zip', '.tar', '.tgz', '.7z', '.cube', '.dylib', '.so', '.dll', '.a',
    '.o', '.class', '.nef', '.dng', '.dmp', '.cfg', '.mov', '.mp4', '.nev', '.r3d', '.rmd', '.exr', '.mxf', '.avi', '.wav',
    '.yuv', '.rgb', '.npz', '.npy', '.gpr', '.gzf', '.idb', '.i64', '.pem', '.key',
}
BLOCKED_PARTS = {
    'vendor', '.runtime', 'ghidra_work', '.ghidra', '.venv', 'venv',
    'node_modules', '__pycache__', '.aws', '.ssh', 'frames', 'cache', 'local_data', '.codex', '.agents',
}
SECRET_PATTERNS = [
    re.compile(rb'-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----'),
    re.compile(rb'\bgh[pousr]_[A-Za-z0-9]{30,}\b'),
    re.compile(rb'\bgithub_pat_[A-Za-z0-9_]{50,}\b'),
    re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    re.compile(rb'\bsk-(?:proj-)?[A-Za-z0-9_-]{30,}\b'),
    re.compile(rb'\bolp_[A-Za-z0-9]{25,}\b'),
]
EXECUTABLE_MAGIC = (b'\x7fELF', b'\xcf\xfa\xed\xfe', b'\xce\xfa\xed\xfe',
                    b'\xfe\xed\xfa\xcf', b'\xfe\xed\xfa\xce', b'\xca\xfe\xba\xbe')


def git(*args, data=None):
    return subprocess.run(['git', *args], input=data, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=True).stdout


def git_modes():
    """(mode, path) for every indexed file; symlinks and submodules are refused."""
    out = git('ls-files', '-s', '-z')
    rows = []
    for entry in out.split(b'\0'):
        if not entry:
            continue
        meta, _, path = entry.partition(b'\t')
        rows.append((meta.split()[0].decode(), path.decode('utf-8', 'replace')))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--staged', action='store_true')
    group.add_argument('--all', action='store_true')
    args = parser.parse_args()
    command = ('ls-files', '-z', '--cached') if args.all else (
        'diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z')
    names = sorted(set(filter(None, git(*command).split(b'\0'))))
    if any(b'\n' in name or b'\r' in name for name in names):
        raise ValueError('Newline-containing filenames are not supported')
    raw = git('cat-file', '--batch', data=b''.join(b':'+name+b'\n' for name in names)) if names else b''
    position = 0
    total = 0
    issues = []
    largest = ('', 0)
    for mode, mpath in git_modes():
        if mode in ('120000', '160000'):
            issues.append((mpath, 'symlink or submodule entry (mode %s)' % mode))
        elif mode not in ('100644', '100755'):
            issues.append((mpath, 'unexpected index mode ' + mode))
    for name in names:
        end = raw.index(b'\n', position)
        header = raw[position:end].rsplit(b' ', 2)
        if len(header) != 3 or header[1] != b'blob':
            raise ValueError('Unexpected index object: '+name.decode('utf-8', 'replace'))
        size = int(header[2])
        content = raw[end+1:end+1+size]
        if len(content) != size or raw[end+1+size:end+2+size] != b'\n':
            raise ValueError('Truncated Git object stream')
        position = end+2+size
        path = name.decode('utf-8', 'strict')
        item = pathlib.PurePosixPath(path)
        total += size
        if size > largest[1]:
            largest = (path, size)
        blocked = item.suffix.lower() in BLOCKED_SUFFIXES or any(p in BLOCKED_PARTS for p in item.parts)
        blocked |= item.name in {'.DS_Store', '.env', 'credentials.json', 'secrets.json'}
        blocked |= item.name.startswith('.env.') and item.name != '.env.example'
        if blocked:
            issues.append((path, 'excluded input, private record, or runtime path'))
        if size > MAX_BYTES:
            issues.append((path, 'file exceeds the 512 KiB source-resource limit'))
        asset_png = path in ASSET_PNGS and plain_png(content)
        if path in ASSET_PNGS and not asset_png:
            issues.append((path, 'invalid brand PNG or embedded PNG metadata'))
        if not asset_png:
            try:
                content.decode('utf-8')
            except UnicodeDecodeError:
                issues.append((path, 'only the reviewed brand PNGs may contain binary content'))
            if b'\0' in content:
                issues.append((path, 'NUL bytes suggest binary content'))
        if content.startswith(EXECUTABLE_MAGIC):
            issues.append((path, 'compiled executable magic'))
        if item.suffix.lower() == '.svg' and (b'data:image' in content or b'data:application' in content):
            issues.append((path, 'SVG embeds raster or foreign data'))
        for pattern in SECRET_PATTERNS:
            match = pattern.search(content)
            if match:
                line = content.count(b'\n', 0, match.start())+1
                issues.append((path, f'possible credential at line {line} (value withheld)'))
    if position != len(raw):
        raise ValueError('Unconsumed Git object data')
    for path, reason in issues:
        print(f'{path}: {reason}', file=sys.stderr)
    print(f'Checked {len(names)} indexed files, {total/1024**2:.2f} MiB; issues: {len(issues)}.')
    if largest[0]:
        print(f'Largest: {largest[0]} ({largest[1]/1024**2:.2f} MiB).')
    return 1 if issues else 0


if __name__ == '__main__':
    raise SystemExit(main())
