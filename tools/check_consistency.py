#!/usr/bin/env python3
"""Cross-check documentation against the repository: paths, file names and hashes.

Every path-looking code span must resolve to a file in this repository, and every
hash mentioned in the docs must be a real hash pinned by the sources (resources/
recipes, anchors, tools). Anything else is a stale doc claim.

    python3 tools/check_consistency.py
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT_DIRS = ('docs/', 'tools/', 'tests/', 'gauntlet/', 'resources/', 'z8prores/',
             'z8precapture/', 'z8opengate/', 'z8menuh/', 'assets/', 'recipes/', '.githooks/')
ROOT_FILES = {'patch.py', 'verify.py', 'features.py', 'configure.py', 'requirements.txt',
              'README.md', 'NOTICE.md', 'CONTRIBUTING.md', 'LICENSE'}
HASH_TOKEN = re.compile(r'\b([0-9a-f]{8,64})(…|\.\.\.)?')
CODE_SPAN = re.compile(r'`([^`\n]+)`')


def pinned_hashes(root):
    """Hashes the repository itself pins, from machine-readable sources and code."""
    out = set()
    sources = list((root / 'resources').glob('*.json')) + [root / 'gauntlet' / 'anchors.json']
    for p in sources:
        for m in re.finditer(r'"([0-9a-f]{64})"', p.read_text()):
            out.add(m.group(1))
    for p in list(root.rglob('*.py')) + list(root.rglob('*.c')) + list(root.rglob('*.inc')):
        if '.git' in p.parts:
            continue
        for m in re.finditer(r"'([0-9a-f]{64})'|\"([0-9a-f]{64})\"", p.read_text()):
            out.add(m.group(1) or m.group(2))
    return out


def release_kit_check(kit, notes_path, zip_path):
    """Reconcile a prepared (unpublished) release kit against the pins in this repository."""
    problems = []
    manifest_path = kit / 'manifest.json'
    if not manifest_path.exists():
        return ['release kit needs manifest.json'], 0
    manifest = json.loads(manifest_path.read_text())
    pinned = pinned_hashes(Path(__file__).resolve().parents[1])
    # 1. the recorded commit must be a real commit of this repository
    try:
        commit = subprocess.run(['git', 'cat-file', '-e', manifest['commit'] + '^{commit}'],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True)
        if commit.returncode != 0:
            problems.append('manifest commit is not in the repository: %s' % manifest.get('commit'))
    except OSError as exc:
        problems.append('cannot verify manifest commit: %s' % exc)
    # 2. every object: bytes match the manifest, and the manifest matches a recipe pin
    checked = 0
    for entry in manifest.get('files', []):
        p = kit / entry['name']
        if not p.exists():
            problems.append('listed object missing: %s' % entry['name'])
            continue
        checked += 1
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        if digest != entry.get('sha256'):
            problems.append('%s: bytes differ from the manifest' % entry['name'])
        if entry.get('code_sha256') != digest:
            problems.append('%s: object does not match its own code_sha256' % entry['name'])
        if str(entry.get('code_sha256', '')).lower() not in pinned:
            problems.append('%s: code_sha256 is not pinned by resources/' % entry['name'])
        if not entry.get('source_hashes'):
            problems.append('%s: manifest entry lacks source hashes' % entry['name'])
    # 3. SHA256SUMS.txt must cover the kit and agree
    sums_path = kit / 'SHA256SUMS.txt'
    if sums_path.exists():
        listed = {}
        for line in sums_path.read_text().splitlines():
            if line.strip():
                h, _, n = line.partition('  ')
                listed[n] = h
        for name, want in listed.items():
            p = kit / name
            if not p.exists():
                problems.append('SHA256SUMS lists a missing file: %s' % name)
            elif hashlib.sha256(p.read_bytes()).hexdigest() != want:
                problems.append('SHA256SUMS mismatch: %s' % name)
        missing = [p.relative_to(kit).as_posix() for p in kit.rglob('*')
                   if p.is_file() and p.name != 'SHA256SUMS.txt' and p.relative_to(kit).as_posix() not in listed]
        for name in missing:
            problems.append('file not covered by SHA256SUMS: %s' % name)
    else:
        problems.append('release kit needs SHA256SUMS.txt')
    # 4. the archived notes must agree with the kit and the zip
    if notes_path and notes_path.exists():
        text = notes_path.read_text()
        if manifest.get('commit', '')[:7] not in text:
            problems.append('release notes do not mention the manifest commit')
        for line in ("WIP. Owner's Z8 bricked! Use at your own risk.", '施工中。作者的 Z8 已经刷砖！风险自担。'):
            if line not in text:
                problems.append('release notes miss the warning line: %s' % line)
        if zip_path and zip_path.exists():
            digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
            if digest not in text:
                problems.append('release notes cite a different zip hash than the prepared zip')
        for entry in manifest.get('files', []):
            if entry['sha256'][:8] not in text:
                problems.append('release notes do not cite object %s' % entry['name'])
    return problems, checked


def main():
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--release-kit', type=Path,
                    help='prepared release kit directory: reconcile it against the repository pins')
    ap.add_argument('--release-notes', type=Path, help='archived release notes to reconcile')
    ap.add_argument('--release-zip', type=Path, help='prepared release zip to reconcile')
    args = ap.parse_args()
    if args.release_kit:
        problems, checked = release_kit_check(args.release_kit.resolve(), args.release_notes, args.release_zip)
        for p in problems:
            print(p, file=sys.stderr)
        print('Release reconciliation: %d object(s) checked; %d problem(s).' % (checked, len(problems)))
        print('VERDICT: %s' % ('PASS' if not problems else 'FAIL'))
        return 0 if not problems else 1
    pinned = pinned_hashes(root)
    problems = []
    docs = [p for p in sorted(root.rglob('*.md'))
            if not any(part in {'.git', '__pycache__', '.pytest_cache', '.ruff_cache'} for part in p.parts)]
    path_refs = hash_refs = 0
    for doc in docs:
        text = doc.read_text(encoding='utf-8')
        rel = doc.relative_to(root).as_posix()
        for span in CODE_SPAN.findall(text):
            head = span.split()[0] if span.split() else span      # command spans carry arguments
            if head.startswith(ROOT_DIRS) or head in ROOT_FILES:
                path_refs += 1
                target = head.split('#')[0]
                if '*' in target or '<' in target:
                    continue
                if not (root / target).exists():
                    problems.append('%s: documented path does not exist: `%s`' % (rel, head))
        for match in HASH_TOKEN.finditer(text):
            token, truncated = match.group(1), bool(match.group(2))
            if len(token) == 64 and not truncated:
                hash_refs += 1
                if token not in pinned:
                    problems.append('%s: hash not pinned by any source: %s…' % (rel, token[:16]))
            elif truncated and len(token) >= 8:
                hash_refs += 1
                if not any(h.startswith(token) for h in pinned):
                    problems.append('%s: truncated hash not found in sources: %s…' % (rel, token))
    for p in problems:
        print(p, file=sys.stderr)
    # bilingual rule: documents carry a Chinese section, and it introduces no
    # hash that the English part does not already carry
    bilingual_problems = []
    allow_english_only = {'CONTRIBUTING.md', 'assets/ASSETS.md'}
    for doc in docs:
        rel = doc.relative_to(root).as_posix()
        text = doc.read_text(encoding='utf-8')
        cut = text.find('## 简体中文')
        if cut < 0:
            if rel not in allow_english_only:
                bilingual_problems.append('%s: no 简体中文 section' % rel)
            continue
        zh = set(re.findall(r'[0-9a-f]{8,}', text[cut:]))
        en = set(re.findall(r'[0-9a-f]{8,}', text[:cut]))
        for token in sorted(zh):
            if any(e.startswith(token) or token.startswith(e) for e in en):
                continue    # truncated citation of a hash the English part carries
            bilingual_problems.append('%s: Chinese section mentions hash not in the English part: %s' % (rel, token[:16]))
    for p in bilingual_problems:
        print(p, file=sys.stderr)
    total = len(problems) + len(bilingual_problems)
    print('Consistency: %d docs, %d path references, %d hash references; %d problem(s), %d bilingual problem(s).'
          % (len(docs), path_refs, hash_refs, len(problems), len(bilingual_problems)))
    print('VERDICT: %s' % ('PASS' if total == 0 else 'FAIL'))
    return 0 if total == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
