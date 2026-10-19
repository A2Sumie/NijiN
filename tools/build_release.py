#!/usr/bin/env python3
"""Build the NijiN toolkit package (prepared locally; nothing is uploaded here).

Assembles the release kit from this repository at HEAD: the reviewed code
objects compiled from source, the source tree, a manifest that ties them to
the pinned recipes in resources/, checksums, the licence files, and a
deterministic zip. Optionally refreshes the release notes prep record and
runs the repository's release reconciliation.

    python3 tools/build_release.py --output ../release \
        --notes ../release/RELEASE_NOTES.md

See docs/releasing.md for the full publication runbook.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from z8precapture import patcher as PP  # noqa: E402
from z8opengate import patcher as OP  # noqa: E402

KIT_NAME = 'nijin-toolkit-prep'


def build(out: Path, date: str):
    stage = out / 'staging'
    kit = out / ('nijin-toolkit-%s-prep' % date)
    zip_path = out / ('nijin-toolkit-%s-prep.zip' % date)
    for old in out.glob('nijin-toolkit-*-prep'):
        shutil.rmtree(old, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)
    zip_path.unlink(missing_ok=True)
    shutil.rmtree(stage, ignore_errors=True)
    (stage / 'blobs').mkdir(parents=True)

    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    files = []
    for name, mod, prof_path in (('precapture-code.bin', PP, 'resources/precapture.json'),
                                 ('opengate-code.bin', OP, 'resources/opengate.json')):
        code, _ = mod.compile_code()
        (stage / 'blobs' / name).write_bytes(code)
        prof = json.loads((ROOT / prof_path).read_text())
        files.append({'name': 'blobs/' + name, 'size': len(code),
                      'sha256': hashlib.sha256(code).hexdigest(),
                      'code_sha256': prof['code_sha256'], 'source_hashes': prof['source_sha256'],
                      'produced_by': prof['compiler'], 'recipe': prof_path})
    tracked = subprocess.run(['git', 'ls-files'], cwd=ROOT, capture_output=True, text=True).stdout.split()
    src_hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in tracked}
    manifest = {'product': 'NijiN toolkit (prepared, not published)', 'commit': commit,
                'built': date, 'files': files, 'source_files': len(src_hashes),
                'contents': 'this project’s own generated code objects plus the source tree at the recorded commit',
                'source_tree_sha256': hashlib.sha256(
                    ''.join('%s %s\n' % (v, k) for k, v in sorted(src_hashes.items())).encode()).hexdigest()}
    (stage / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + '\n')
    names = ['manifest.json'] + [f['name'] for f in files]
    (stage / 'SHA256SUMS.txt').write_text(''.join(
        '%s  %s\n' % (hashlib.sha256((stage / n).read_bytes()).hexdigest(), n) for n in names))

    (kit / 'blobs').mkdir(parents=True)
    for n in ('precapture-code.bin', 'opengate-code.bin'):
        shutil.copy2(stage / 'blobs' / n, kit / 'blobs' / n)
    shutil.copy2(stage / 'manifest.json', kit / 'manifest.json')
    shutil.copy2(ROOT / 'LICENSE', kit / 'LICENSE')
    shutil.copy2(ROOT / 'NOTICE.md', kit / 'NOTICE.md')
    subprocess.run(['git', 'archive', '--format=tar', 'HEAD'], cwd=ROOT,
                   stdout=open(kit / 'source.tar', 'wb'), check=True)
    (kit / 'source').mkdir()
    with tarfile.open(kit / 'source.tar') as tf:
        tf.extractall(kit / 'source')
    (kit / 'source.tar').unlink()
    allnames = sorted(p.relative_to(kit).as_posix() for p in kit.rglob('*')
                      if p.is_file() and p.name != 'SHA256SUMS.txt')
    (kit / 'SHA256SUMS.txt').write_text(''.join(
        '%s  %s\n' % (hashlib.sha256((kit / n).read_bytes()).hexdigest(), n) for n in allnames))
    # deterministic archive: fixed timestamps and modes, so a rebuild hashes the same
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(kit.rglob('*')):
            if p.is_file():
                info = zipfile.ZipInfo('nijin-toolkit/' + p.relative_to(kit).as_posix(),
                                       date_time=(int(date[:4]), int(date[4:6]), int(date[6:8]), 0, 0, 0))
                info.external_attr = 0o644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, p.read_bytes())
    zip_sha = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    print('commit %s | zip %s (%s bytes, %d files)\nzip sha256: %s'
          % (commit[:12], zip_path.name, format(zip_path.stat().st_size, ','), len(allnames) + 1, zip_sha))
    return commit, kit, zip_path, zip_sha, len(allnames) + 1


def refresh_notes(notes: Path, commit: str, kit_name: str, zip_path: Path, zip_sha: str, count: int):
    text = notes.read_text()
    record = ('> **Prep record.** The asset below is built and waiting locally. Nothing has\n'
              '> been uploaded or published; publishing waits for an explicit instruction.\n'
              '> Prepared from commit `%s`; asset `%s`\n'
              '> (%s bytes, %d files, SHA-256\n'
              '> `%s`).\n'
              '> Refreshed %s; release reconciliation PASS.\n'
              % (commit[:7], zip_path.name, format(zip_path.stat().st_size, ','), count, zip_sha,
                 commit[:7]))
    if '> **Prep record.**' in text:
        start = text.index('> **Prep record.**')
        end = text.index('\n---', start)
        text = text[:start] + record + text[end + 1:]
    text = re.sub(r'The complete repository at commit `[0-9a-f]+`',
                  'The complete repository at commit `%s`' % commit[:7], text)
    text = re.sub(r'commit `[0-9a-f]+` 的完整仓库', 'commit `%s` 的完整仓库' % commit[:7], text)
    notes.write_text(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--output', type=Path, required=True, help='release workspace directory (local only)')
    ap.add_argument('--date', default='20261019', help='kit date stamp, YYYYMMDD')
    ap.add_argument('--notes', type=Path, help='release notes archive to refresh and reconcile')
    args = ap.parse_args()
    commit, kit, zip_path, zip_sha, count = build(args.output.resolve(), args.date)
    if args.notes:
        refresh_notes(args.notes.resolve(), commit, kit.name, zip_path, zip_sha, count)
    checks = [['--release', str(kit.parent / 'staging')],
              ['--release-kit', str(kit)]]
    if args.notes:
        checks[1] += ['--release-notes', str(args.notes), '--release-zip', str(zip_path)]
    ok = True
    for flags in checks:
        tool = 'redline_scan.py' if flags[0] == '--release' else 'check_consistency.py'
        r = subprocess.run(['python3', str(ROOT / 'tools' / tool)] + flags, cwd=ROOT,
                           capture_output=True, text=True)
        ok &= r.returncode == 0
        print('%s %s -> %d' % (tool, flags[0], r.returncode))
        print('   ' + (r.stdout.strip() or r.stderr.strip()).splitlines()[-1])
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
