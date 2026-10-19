#!/usr/bin/env python3
"""Cross-check documentation against the repository: paths, file names and hashes.

Every path-looking code span must resolve to a file in this repository, and every
hash mentioned in the docs must be a real hash pinned by the sources (resources/
recipes, anchors, tools). Anything else is a stale doc claim.

    python3 tools/check_consistency.py
"""
import json
import re
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


def main():
    root = Path(__file__).resolve().parents[1]
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
        for token in sorted(zh - en):
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
