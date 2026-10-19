#!/usr/bin/env python3
"""fill_c1 — turn a finished crash verdict into the C1 evidence slot, mechanically.

The verdict record (136_CRASH_VERDICT.md in the crash-forensics workstream) is
the source of truth. This tool copies its verdict **verbatim** — it never
rewrites, softens or strengthens the wording — computes the record anchor
(file + section + SHA-256) itself, and refuses to emit anything while a
required piece is still missing. An unfilled verdict is rejected; that is the
correct behaviour, not an error.

    python3 tools/fill_c1.py /path/to/136_CRASH_VERDICT.md           # preview
    python3 tools/fill_c1.py /path/to/136_CRASH_VERDICT.md --write   # fill risks.md

它从终审记录里**逐字**抽取判词（不改写、不加强措辞），自动计算记录锚
（文件+章节+sha256），八格缺任何一格即拒绝出链。骨架状态被拒填=正确行为。
`--write` 会把八格写入 docs/risks.md 的 C1 证据槽；不加则只预览。
"""
import argparse
import datetime
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLOT = ROOT / 'docs' / 'risks.md'

PLACEHOLDER = re.compile(r'待填|TBD|TODO|（待填）|\(to be filled\)', re.I)
GRADE = re.compile(r'(?:证据分级|分级|grade)[^\n]{0,12}?([ABC])(?=[）)\s。，、,.\n]|$)'
                   r'|(?:^|\s)([ABC])\s*[=＝:：]\s*(?:模拟器|字节|结构|未闭环)')
CODE_ANCHOR = re.compile(r'0x[0-9A-Fa-f]{4,}|eg\s+0x[0-9A-Fa-f]+|VA\s*[=＝]\s*0x[0-9A-Fa-f]+')
EXCLUSION = re.compile(r'排除|已排除|ruled out|exclud', re.I)
METHOD = re.compile(r'反汇编|逐字节|实测|观测|模拟器|差分|disassembly|measured|observed', re.I)
HARDWARE = re.compile(r'真机|上机|实机|on hardware|camera test', re.I)
UNPROVEN = re.compile(r'未证明|未定案|未闭环|尚未|仍[^，。]{0,8}(未知|未解)|unproven|not established', re.I)
VERDICT_MARK = re.compile(r'判词|verdict', re.I)


def sections(text):
    """Split the verdict record into its §0..§4 sections by heading."""
    out = {}
    for m in re.finditer(r'^##\s+(§\d[^\n]*)\n(.*?)(?=^##\s|\Z)', text, re.M | re.S):
        out[m.group(1).strip()] = m.group(2).strip()
    return out


def first_sentence(block):
    """Verbatim leading content of a section: the claim itself, untouched."""
    lines = [l for l in block.splitlines() if l.strip() and not PLACEHOLDER.search(l)]
    return '\n'.join(lines).strip()


def collect(record: Path):
    text = record.read_text()
    secs = sections(text)
    if not secs:
        raise SystemExit('ERROR: no §-numbered sections found — not a verdict record')
    verdict_sec = next((v for k, v in secs.items() if k.startswith('§0')), '')
    chain_sec = next((v for k, v in secs.items() if k.startswith('§1')), '')
    ub_sec = next((v for k, v in secs.items() if k.startswith('§2')), '')
    excl_sec = next((v for k, v in secs.items() if k.startswith('§3')), '')
    stance_sec = next((v for k, v in secs.items() if k.startswith('§4')), '')

    fields, problems = {}, []

    verdict = first_sentence(verdict_sec)
    if not verdict or PLACEHOLDER.search(verdict_sec):
        problems.append('verdict (§0): still a placeholder — nothing to copy')
    fields['Verdict'] = verdict

    grade_src = '\n'.join([verdict_sec, chain_sec])
    g = GRADE.search(grade_src)
    fields['Evidence grade'] = (g.group(1) or g.group(2)) if g else ''
    if not fields['Evidence grade']:
        problems.append('evidence grade: no explicit A/B/C grade found in §0/§1')

    anchors = []
    for m in CODE_ANCHOR.finditer('\n'.join([verdict_sec, chain_sec, ub_sec])):
        token = m.group(0)
        if token not in anchors:
            anchors.append(token)
    fields['Code anchors'] = '; '.join(anchors)
    if not anchors:
        problems.append('code anchors: no offset/symbol cited in §0–§2')
    mapping = re.search(r'(VA\s*[=＝][^\n；;]{0,40}|映射[^\n；;]{0,40}|mapping[^\n；;]{0,40})', ub_sec + chain_sec, re.I)
    fields['Address mapping'] = mapping.group(1).strip() if mapping else ''
    if not fields['Address mapping']:
        problems.append('address mapping: none stated alongside the code anchors')

    excl = excl_sec
    if not excl or PLACEHOLDER.search(excl):
        problems.append('delta exhaustion (§3): section is empty — a verdict that leaves a delta window unexcluded is a hypothesis')
    elif not EXCLUSION.search(excl):
        problems.append('delta exhaustion (§3): no exclusion statement found')
    elif not METHOD.search(excl):
        problems.append('delta exhaustion (§3): exclusion claims without naming a method')
    fields['Delta exhaustion'] = 'present in §3 (%d lines); method named: %s' % (
        len([l for l in excl.splitlines() if l.strip()]), 'yes' if METHOD.search(excl) else 'no')

    hw = [l.strip() for l in (verdict_sec + '\n' + ub_sec + '\n' + stance_sec).splitlines()
          if HARDWARE.search(l) and not PLACEHOLDER.search(l)]
    fields['Hardware reproduction'] = hw[0] if hw else ''
    if not hw:
        problems.append('hardware reproduction: no statement about real-device reproduction')

    un = [l.strip() for l in (verdict_sec + '\n' + ub_sec + '\n' + stance_sec + '\n' + excl_sec).splitlines()
          if UNPROVEN.search(l) and not PLACEHOLDER.search(l)]
    fields['What stays unproven'] = ' / '.join(un[:3])
    if not un:
        problems.append('what stays unproven: nothing stated — it must be spelled out')

    stamp = '%s (copied verbatim by tools/fill_c1.py on %s)'
    fields['Record anchor'] = '%s §0 终审判词, sha256 %s' % (
        record.name, hashlib.sha256(record.read_bytes()).hexdigest())
    fields['Filled by / date'] = stamp % (datetime.date.today().isoformat(), datetime.date.today().isoformat())
    return fields, problems


def render(fields):
    order = ['Verdict', 'Evidence grade', 'Record anchor', 'Code anchors', 'Address mapping',
             'Delta exhaustion', 'Hardware reproduction', 'What stays unproven', 'Filled by / date']
    rows = []
    for key in order:
        rows.append('| %s | *(filled)* | %s |' % (key, fields[key].replace('|', '\\|').replace('\n', ' ⏎ ')))
    return '\n'.join(rows)


def write_slot(fields):
    text = SLOT.read_text()
    start = text.index('## C1 evidence slot')
    end = text.index('\n## ', start + 5)
    block = text[start:end]
    filled = block
    for key, val in fields.items():
        filled = re.sub(r'(\| %s \|[^\n|]*)\| \*\(empty\)\* \|' % re.escape(key),
                        lambda m: m.group(1) + '| ' + val.replace('|', '\\|').replace('\n', ' ⏎ ') + ' |',
                        filled, count=1)
    filled = filled.replace('Status: **prepared, empty — awaiting the crash verdict.**',
                            'Status: **filled %s from the crash verdict record.**' % datetime.date.today().isoformat())
    SLOT.write_text(text[:start] + filled + text[end:])
    return SLOT


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog='Refusal is a feature: an unfinished verdict must not reach the slot.\n'
                                        '拒绝出链是设计行为：判词没写完就不该进证据槽。')
    ap.add_argument('record', type=Path, help='path to the finished verdict record (136_CRASH_VERDICT.md)')
    ap.add_argument('--write', action='store_true', help='fill docs/risks.md in place (default: preview only)')
    a = ap.parse_args()
    if not a.record.is_file():
        raise SystemExit('ERROR: verdict record not found: %s' % a.record)
    fields, problems = collect(a.record)
    if problems:
        print('REFUSED — the slot is not filled. Missing or invalid:')
        for p in problems:
            print('  - ' + p)
        print('Verdict records are copied, never repaired. Fix the record, not the tool.\n'
              '拒填：终审记录里缺什么就补什么，工具不代写、不润色。')
        return 2
    print('C1 slot content (verbatim verdict, mechanical anchors):')
    print(render(fields))
    if a.write:
        path = write_slot(fields)
        print('\nwritten to %s' % path)
    else:
        print('\n(preview only; rerun with --write to fill docs/risks.md)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
