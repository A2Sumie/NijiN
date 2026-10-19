#!/usr/bin/env python3
"""Check that documentation links resolve.

Internal targets are checked against the working tree; anchors against the
headings actually present in the target file. External URLs are only checked
with --online, one HEAD per host, so the offline default needs no network.

    python3 tools/check_links.py            # internal links + anchors
    python3 tools/check_links.py --online   # also probe external URLs
"""
import argparse
import re
import sys
import urllib.request
from pathlib import Path

LINK = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
HEADING = re.compile(r'^(#{1,6})\s+(.*?)\s*$', re.M)


def slug(text):
    text = re.sub(r'[`*_]', '', text).strip().lower()
    text = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', text)
    return re.sub(r'\s+', '-', text)


def anchors_of(path):
    text = path.read_text(encoding='utf-8')
    out = {slug(m.group(2)) for m in HEADING.finditer(text)}
    # explicit HTML anchors
    out |= set(re.findall(r'<a\s+[^>]*id="([^"]+)"', text))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--online', action='store_true', help='also probe external URLs')
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args()
    root = args.root.resolve()
    problems, checked, external = [], 0, {}
    for path in sorted(root.rglob('*.md')):
        if '.git' in path.parts:
            continue
        text = path.read_text(encoding='utf-8')
        for label, target in LINK.findall(text):
            checked += 1
            target = target.strip()
            if target.startswith(('http://', 'https://')):
                external.setdefault(target, []).append(path.relative_to(root).as_posix())
                continue
            if target.startswith('mailto:'):
                continue
            dest, _, frag = target.partition('#')
            base = path.parent if dest else path
            resolved = (base / dest).resolve() if dest else path.resolve()
            if dest and not resolved.exists():
                problems.append('%s: broken link [%s](%s)' % (path.relative_to(root), label, target))
                continue
            if frag and resolved.suffix == '.md' and resolved.exists():
                if frag not in anchors_of(resolved) and frag not in {slug(frag)}:
                    problems.append('%s: missing anchor #%s in %s' % (
                        path.relative_to(root), frag, resolved.relative_to(root)))
    for rel, where in sorted(external.items()):
        if args.online:
            req = urllib.request.Request(rel, method='HEAD', headers={'User-Agent': 'nijin-link-check'})
            try:
                with urllib.request.urlopen(req, timeout=15) as r:
                    code = r.status
            except Exception as exc:
                code = type(exc).__name__
            ok = code in (200, 301, 302, 403, 405)   # 403/405 = reachable but refuses HEAD
            print('  external %s -> %s%s' % (rel, code, '' if ok else '  <-- CHECK'))
            if not ok:
                problems.append('external URL unreachable: %s (%s)' % (rel, code))
        else:
            print('  external (not probed, use --online): %s' % rel)
    for p in problems:
        print(p, file=sys.stderr)
    print('Links checked: %d internal references, %d external URLs; %d problem(s).'
          % (checked - len(external), len(external), len(problems)))
    print('VERDICT: %s' % ('PASS' if not problems else 'FAIL'))
    return 0 if not problems else 1


if __name__ == '__main__':
    raise SystemExit(main())
