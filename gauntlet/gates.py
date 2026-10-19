#!/usr/bin/env python3
"""The seven mandatory gates (preflight subset of the gauntlet). Independent checks +
subprocess invocation of the toolchain's own verifier/tests. No builder imports.

  G1 byte      verify.py full run / reviewed windows match / outside windows preserved /
               other modules unchanged / A-B diff vs baseline inside whitelist ∪ EG CRC16 /
               fingerprint lock (stock 03.11 old-sha assertions)
  G2 identity  identity=03.11.p0 (04.01 forbidden) / three-way identity consistency /
               module directory consistency / segment CRC16 chain / outer SHA1 / input sha
  G3 combo     opengate⇒precapture / LOADER form 0x40970000 / feature window overlap scan /
               rollback anchors
  G4 cfg       Z8PRE v4 & Z8OG v1 magic / flags F_KNOWN / frames≤RING_CAP / CRC32 / orthogonality
  G5 tests     tests/validate.py + tests/validate_features.py + 113 P1–P3 baseline standards
  G6 hygiene   single firmware file / shasum -c / no 0401 or test residue / manifest↔artefact
  G7 checklist human-readable pre-flash checklist generator
"""
import binascii
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import cfgcheck as cc
import pkgcodec as pc

HERE = Path(__file__).resolve().parent
# Toolchain checkout and local inputs are provided by the caller, never shipped:
#   NIJIN_HOME     repository root (default: the parent of this gauntlet/ directory)
#   NIJIN_KIT      directory with the locally built package (+ manifest.json, *.CFG)
#   NIJIN_STOCK    user-supplied official input package
#   NIJIN_BASELINE locally kept baseline build for A/B diffing (optional)
#   NIJIN_LEGACY_DIR  locally kept older builds named in anchors.json (optional)
REPO = Path(os.environ.get('NIJIN_HOME', HERE.parent))
MERGED = Path(os.environ.get('NIJIN_TOOLCHAIN', REPO))
KIT_DEFAULT = Path(os.environ['NIJIN_KIT']) if os.environ.get('NIJIN_KIT') else None
STOCK_DEFAULT = Path(os.environ['NIJIN_STOCK']) if os.environ.get('NIJIN_STOCK') else None
BASELINE_DEFAULT = Path(os.environ['NIJIN_BASELINE']) if os.environ.get('NIJIN_BASELINE') else None
LEGACY_DIR = Path(os.environ['NIJIN_LEGACY_DIR']) if os.environ.get('NIJIN_LEGACY_DIR') else None
ANCHORS = HERE / 'anchors.json'

STOCK_SHA256 = 'd67413c2ede6b9ce8887175f20700bd9fbad2a973a4820968c45503d15d80d96'
BASELINE_V5_SHA256 = '79fa7b3274ec19f100d9361c836a3cfc6128be4090da755e167018c4b2e5da79'
EXPECTED_IDENTITY = '03.11.p0'
FORBIDDEN_IDENTITY = re.compile(r'04\.01')
IDENTITY_RE = re.compile(r'[0-9]{2}\.[0-9]{2}\.[a-z]\d')

FEATURES = ('prores', 'precapture', 'opengate', 'menuh')
PROFILE_FILES = {'prores': 'resources/profile.json', 'precapture': 'resources/precapture.json',
                 'opengate': 'resources/opengate.json', 'menuh': 'resources/menuh.json'}
ENTRY_HOOK = {'prores': 0xeb62ec, 'precapture': 0xe0fe90, 'opengate': 0x573120, 'menuh': 0xeb5598}
LOADER = 0x1024d8c
# 共享 text-loader 窗（111 §6.5）：组合构建取各 feature 要求的最大者；单调上调
LOADER_REQ = {'prores': 0x4094F000, 'precapture': 0x40970000, 'menuh': 0x4098F000}
LOADER_STOCK = 0x408BF8F0
PUBLIC_WORDS_AT = pc.PUBLIC_WORDS_AT
IDENTITY_AT = pc.IDENTITY_AT
EG_LEN = pc.EG_LEN


def loader_limit(buf8):
    """Decode the shared loader window (movz x8,#lo / movk x8,#hi,lsl#16) -> end VA, or None."""
    import struct
    if len(buf8) != 8:
        return None
    w0, w1 = struct.unpack('<2I', buf8)
    if (w0 & 0xFF80001F) != 0xD2800008 or (w1 & 0xFF80001F) != 0xF2800008:
        return None
    return (((w0 >> 5) & 0xFFFF) << (16 * ((w0 >> 21) & 3))) | (((w1 >> 5) & 0xFFFF) << (16 * ((w1 >> 21) & 3)))


# ---------------------------------------------------------------- artifacts / results

class Artifact:
    """A package under test: raw bytes + lazily decoded body (shared codec for mutants)."""

    def __init__(self, label, raw=None, path=None, body=None, codec=None):
        self.label = label
        if raw is None:
            raw = Path(path).read_bytes()
        self.raw = raw
        self._codec = codec
        self._body = body

    @property
    def codec(self):
        if self._codec is None:
            self._codec = pc.Codec(self.raw)
        return self._codec

    @property
    def body(self):
        if self._body is None:
            self._body = self.codec.body
        return self._body

    @property
    def eg(self):
        return pc.eg_of(self.body)

    @property
    def sha256(self):
        return hashlib.sha256(self.raw).hexdigest()


class Check:
    def __init__(self, cid, gate, title, ok, detail='', skipped=False):
        self.cid, self.gate, self.title = cid, gate, title
        self.ok, self.detail, self.skipped = bool(ok), str(detail), bool(skipped)

    @property
    def status(self):
        if self.skipped:
            return 'SKIPPED'          # input not provided; never reported as PASS
        return 'PASS' if self.ok else 'FAIL'

    def as_dict(self):
        return dict(id=self.cid, gate=self.gate, title=self.title, status=self.status, detail=self.detail)


class GateRun:
    def __init__(self, gate, title):
        self.gate, self.title, self.checks = gate, title, []

    def add(self, cid, title, ok, detail='', skipped=False):
        self.checks.append(Check(cid, self.gate, title, ok, detail, skipped))
        return self.checks[-1]

    @property
    def ok(self):
        return all(c.ok or c.skipped for c in self.checks)

    @property
    def status(self):
        if any(c.skipped for c in self.checks) and all(c.ok or c.skipped for c in self.checks):
            return 'SKIPPED'
        return 'PASS' if self.ok else 'FAIL'

    def as_dict(self):
        return dict(id=self.gate, title=self.title, status=self.status,
                    checks=[c.as_dict() for c in self.checks])


# ---------------------------------------------------------------- shared helpers

def load_profiles():
    return {f: json.loads((MERGED / p).read_text()) for f, p in PROFILE_FILES.items()}


def merge_spans(spans):
    out = []
    for a, b in sorted(spans):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def eg_whitelist(profiles):
    """Union of every reviewed patch window + identity windows + EG CRC16 (EG coordinates)."""
    spans = []
    for prof in profiles.values():
        for p in prof['patches']:
            a = int(p['offset'], 16)
            spans.append((a, a + p['bytes']))
    spans += [(PUBLIC_WORDS_AT, PUBLIC_WORDS_AT + 12), (IDENTITY_AT, IDENTITY_AT + 8),
              (EG_LEN - 11, EG_LEN - 3), (EG_LEN - 2, EG_LEN)]
    return merge_spans(spans)


def body_whitelist(profiles):
    """Same union mapped to body coordinates + directory EG-name slot + body CRC16 field."""
    spans = [(a + pc.EG_START, b + pc.EG_START) for a, b in eg_whitelist(profiles)]
    spans += [(112, 128), (pc.BODY_BYTES - 16, pc.BODY_BYTES - 14)]
    return merge_spans(spans)


def covered(spans, lo, hi):
    return any(a <= lo and hi <= b for a, b in spans)


def detect_features(stock_eg, cand_eg):
    return [f for f in FEATURES if stock_eg[ENTRY_HOOK[f]:ENTRY_HOOK[f] + 4] != cand_eg[ENTRY_HOOK[f]:ENTRY_HOOK[f] + 4]]


def patch_index(profiles):
    """offset -> list of (feature, patch row) so shared windows (LOADER) are visible."""
    idx = {}
    for f, prof in profiles.items():
        for p in prof['patches']:
            idx.setdefault(int(p['offset'], 16), []).append((f, p))
    return idx


def expected_at(offset, rows, features):
    """Reviewed new bytes hash expected at a patch offset for this feature selection."""
    chosen = [(f, p) for f, p in rows if f in features]
    if not chosen:
        return None
    # shared LOADER: precapture wins (features.py overwrite order)
    chosen.sort(key=lambda fp: 0 if fp[0] == 'precapture' else 1)
    return chosen[0]


def public_words_ok(buf, version5):
    w0, w1, w2 = struct.unpack_from('<3I', buf, PUBLIC_WORDS_AT)
    if (w0 & ~0x1FFFE0, w1 & ~0x1FFFE0, w2 & ~0x1FFFE0) != (0x52800008, 0x72A00008, 0x52800009):
        return False
    value = struct.pack('<I', ((w0 >> 5) & 65535) | (((w1 >> 5) & 65535) << 16)) + struct.pack('<H', (w2 >> 5) & 65535)
    return value == version5.encode() + b'\0'


def eg_module_name(identity):
    return 'eg2070_' + identity[:5].replace('.', '') + identity[6:] + '.bi'


# ---------------------------------------------------------------- package-level evaluation
# Used by G1/G2/G3 and by the mutation battery; everything in memory.

def evaluate_package(stock, cand, profiles, features=None, expect_identity=EXPECTED_IDENTITY,
                     baseline=None, anchors=None, pin_baseline=True, baseline_windows=None,
                     extra_windows=None):
    """Return a GateRun dict covering G1 (in-memory part), G2, G3 (product side).

    Never raises on malformed candidates: broken structure becomes attributed FAILs.
    baseline_windows / extra_windows: (start,end) EG-coordinate windows added to the A/B
    whitelist — 基线构建记录 + 产物构建记录 + 共享窗重定位族（如 og cave 0x808000→0x80F000）
    —— so window relocations between generations do not masquerade as undeclared changes.
    """
    anchors = anchors or {}
    out = {}
    try:
        body_cache = cand.body
    except pc.PackageError:
        body_cache = None
    rec = pc.audit(cand.raw, body_cache)
    decoded = rec['decode_ok']
    stock_eg = stock.eg
    cand_eg = pc.eg_of(cand.body) if decoded else b''
    detected = detect_features(stock_eg, cand_eg) if decoded else []
    features = list(features) if features else detected

    # ---- G1 byte gate (in-memory checks) ----
    g1 = GateRun('G1', '字节级门（窗口/保持/差分/指纹）')
    out['G1'] = g1
    idx = patch_index(profiles)
    wl = eg_whitelist(profiles)
    if not decoded:
        for cid, title in [('G1.2', 'reviewed 窗口逐个匹配'), ('G1.3', '窗口外逐字节全保持'),
                           ('G1.4', '其它模块逐字节不变'), ('G1.5', 'A/B 差分白名单')]:
            g1.add(cid, title, False, '候选包无法解码（%s），窗口类检查不可执行' % rec['error'])
    else:
        bad_win, bad_keep, loader_bad, win_ok = [], [], [], 0
        for off in sorted(idx):
            rows = idx[off]
            if off == LOADER:
                continue     # 共享窗：走语义断言（≥ 各 feature 要求），不走字节相等
            exp = expected_at(off, rows, features)
            n = rows[0][1]['bytes']
            got = hashlib.sha256(cand_eg[off:off + n]).hexdigest()
            if exp is not None:
                feat, row = exp
                win_ok += 1
                if got != row['new_sha256']:
                    bad_win.append('%s@0x%x want %s got %s' % (feat, off, row['new_sha256'][:12], got[:12]))
            else:
                if cand_eg[off:off + n] != stock_eg[off:off + n]:
                    bad_keep.append('unselected window 0x%x (%s) changed' % (off, rows[0][0]))
        limit = loader_limit(cand_eg[LOADER:LOADER + 8])
        for f in features:
            req = LOADER_REQ.get(f)
            if req is None:
                continue
            if limit is None:
                loader_bad.append('%s: LOADER 非 movz/movk x8 形态' % f)
            elif limit < req:
                loader_bad.append('%s 要求 ≥0x%X，实际 %s' % (f, req, hex(limit)))
        g1.add('G1.2', 'reviewed 窗口逐个匹配（sha==new_sha256）+ 共享 LOADER 窗 ≥ 各 feature 要求',
               not bad_win and not loader_bad,
               '; '.join((bad_win + loader_bad)[:6]) or '%d 窗口全匹配 + LOADER %s ≥ %s'
               % (win_ok, hex(limit) if limit is not None else '?',
                  ','.join('%s:0x%X' % (f, LOADER_REQ[f]) for f in features if f in LOADER_REQ) or '(无要求)'))
        out_spans = [(a, b) for a, b in pc.diff_spans(stock_eg, cand_eg) if not covered(wl, a, b)]
        drift = sum(b - a for a, b in out_spans)
        g1.add('G1.3', '窗口外逐字节全保持（EG 81,807,711B 全量比对）', not out_spans and not bad_keep,
               ('窗口外漂移 %d 字节 / %d 段，如 EG 0x%x-0x%x' % (drift, len(out_spans), out_spans[0][0], out_spans[0][1])
                if out_spans else '零漂移') +
               (('；' + '; '.join(bad_keep[:4])) if bad_keep else ''))
        mod_bad = []
        for i, m in enumerate(pc.MODULES):
            if i == 2:
                continue
            if stock.body[m[1]:m[1] + m[2]] != cand.body[m[1]:m[1] + m[2]]:
                mod_bad.append(m[0])
        g1.add('G1.4', '其它模块逐字节不变（ex/_tpj/vr/li 四模块）', not mod_bad,
               'changed: %s' % mod_bad if mod_bad else '4/4 不变')
        if baseline is not None:
            base_sha = hashlib.sha256(baseline.raw).hexdigest()
            want = anchors.get('baseline_v5_sha256', BASELINE_V5_SHA256)
            if pin_baseline:
                g1.add('G1.5a', 'A/B 基线指纹锁（基线自身 sha==%s…）' % want[:8], base_sha == want, base_sha[:16] + '…')
            spans = pc.diff_spans(baseline.body, cand.body)
            bwl = body_whitelist(profiles)
            extra = list(baseline_windows or []) + list(extra_windows or [])
            if extra:
                bwl = merge_spans([(a + pc.EG_START, b + pc.EG_START) for a, b in extra] + bwl)
            outside = [(a, b) for a, b in spans if not covered(bwl, a, b)]
            g1.add('G1.5', 'A/B 差分 vs 基线 ⊆ 白名单（产物∪基线构建记录∪reviewed∪共享窗重定位族）+EG CRC16（多一字节即 FAIL）',
                   not outside,
                   ('越界差分 %d 段，如 0x%x-0x%x' % (len(outside), outside[0][0], outside[0][1])) if outside
                   else '差分 %d 段全部落在白名单（%d 段合并窗口）内' % (len(spans), len(bwl)))
        else:
            g1.add('G1.5', 'A/B 差分 vs 基线', False, '未提供基线包（--baseline）')
    fp = []
    if hashlib.sha256(stock.raw).hexdigest() != STOCK_SHA256:
        fp.append('stock package sha != d67413c2…')
    stock_prof = profiles.get('prores', {}).get('stock_payload_sha256')
    if stock_prof and hashlib.sha256(stock_eg).hexdigest() != stock_prof:
        fp.append('stock EG sha != profile stock_payload_sha256')
    for f, prof in profiles.items():
        for r in prof['ranges']:
            a, b = int(r['start'], 16), int(r['end'], 16)
            if hashlib.sha256(stock_eg[a:b]).hexdigest() != r['sha256']:
                fp.append('%s range %s-%s 漂移' % (f, r['start'], r['end']))
        for p in prof['patches']:
            a, n = int(p['offset'], 16), p['bytes']
            if a == LOADER:
                allowed = p.get('loader_input_sha256') or prof.get('loader_input_sha256') or [p['old_sha256']]
            else:
                allowed = [p['old_sha256']]
            if hashlib.sha256(stock_eg[a:a + n]).hexdigest() not in allowed:
                fp.append('%s patch %s old-sha 漂移' % (f, p['offset']))
    g1.add('G1.6', '指纹锁 old-sha（官方 03.11 输入字节未漂：包/EG/全部 ranges+patches）', not fp,
           '; '.join(fp[:5]) or '包+EG+%d ranges+%d patches 全锚定'
           % (sum(len(p['ranges']) for p in profiles.values()), sum(len(p['patches']) for p in profiles.values())))

    # ---- G2 identity / package gate (granular attribution via pc.audit) ----
    g2 = GateRun('G2', '身份/包门（身份/目录/段 CRC16 链/外层 SHA1）')
    out['G2'] = g2
    identity = pc.eg_identity(cand_eg) if decoded else b''
    id_text = identity.decode('ascii', 'replace')
    ok_id = decoded and bool(IDENTITY_RE.fullmatch(id_text)) and id_text == expect_identity
    ok_forbid = not FORBIDDEN_IDENTITY.search(id_text) and not FORBIDDEN_IDENTITY.search((rec['facts'] or {}).get('eg_name', ''))
    g2.add('G2.1', '身份=03.11.p0 且严禁 04.01（运行时槽位）', ok_id and ok_forbid,
           'identity=%s expect=%s' % (id_text or '(decode-failed)', expect_identity))
    trailer = cand_eg[-11:-3] if decoded else b''
    three = bool(decoded and IDENTITY_RE.fullmatch(id_text) and identity == trailer
                 and public_words_ok(cand_eg, id_text[:5]))
    g2.add('G2.2', '身份三方一致（运行时 0x14EAA90 == 尾部 == 公开版本指令 0xEB29FC）', three,
           'runtime=%s trailer=%s' % (id_text, trailer.decode('ascii', 'replace')))
    want_name = eg_module_name(id_text) if IDENTITY_RE.fullmatch(id_text) else ''
    ok_dir = rec['header_ok'] and rec['dir_hdr_ok'] and rec['dir_ok'] and bool(want_name) \
        and (rec['facts'] or {}).get('eg_name') == want_name
    g2.add('G2.3', '段目录一致性（count=5/headerlen=208/边界/名称规范化/EG 名↔身份）', ok_dir,
           'dir=%s/%s/%s eg_name=%s want=%s' % (rec['header_ok'], rec['dir_hdr_ok'], rec['dir_ok'],
                                                (rec['facts'] or {}).get('eg_name', '-'), want_name or '-'))
    ok_chain = rec['modules_crc_ok'] and rec['trailer_ok'] and rec['body_crc_ok']
    g2.add('G2.4', '段 CRC16 链反向重算（模块 CRC16×5 → body CRC16；尾部 14B 置零）', ok_chain,
           'modules=%s trailer=%s body_crc=%s' % (rec['modules_crc_ok'], rec['trailer_ok'], rec['body_crc_ok']))
    ok_pkg = rec['sha1_ok'] and rec['context_ok'] and rec['length_ok']
    g2.add('G2.5', '包外层 SHA1 重算比对 + 外层 context + 长度', ok_pkg,
           'sha1(body‖K8)==raw[:20]: %s; outer: %s; len=%d ok=%s' % (rec['sha1_ok'], rec['context_ok'],
                                                                    len(cand.raw), rec['length_ok']))
    g2.add('G2.6', '输入固件 sha 断言（官方原件 d67413c2…）',
           hashlib.sha256(stock.raw).hexdigest() == STOCK_SHA256,
           'input sha=' + hashlib.sha256(stock.raw).hexdigest()[:16] + '…')

    # ---- G3 combo rules gate (product side) ----
    g3 = GateRun('G3', '组合规则门（opengate⇒precapture/LOADER/重叠/回退锚）')
    out['G3'] = g3
    ok_rule = decoded and ('opengate' not in detected or 'precapture' in detected)
    g3.add('G3.1', 'opengate ⇒ precapture 强制（110 §E 硬规则，违反=hook 跳进未装载内存）',
           ok_rule, 'detected=%s' % (detected or ['(none)']))
    loader = cand_eg[LOADER:LOADER + 8] if decoded else b''
    limit = loader_limit(loader) if decoded else None
    reqs = {f: LOADER_REQ[f] for f in detected if f in LOADER_REQ}
    want = max(reqs.values()) if reqs else LOADER_STOCK
    ok_loader = limit is not None and all(limit >= r for r in reqs.values()) and limit == want
    g3.add('G3.2', 'LOADER 形态断言（共享窗 0x1024D8C：≥ 各 feature 要求 且 == 最大者，111 §6.5）',
           ok_loader, 'want 0x%X（取最大者 %s），实际 %s = %s'
           % (want, {f: hex(r) for f, r in reqs.items()} or {'(none)': 'stock'},
              limit if limit is not None else '(non-movz/movk 形态)', loader.hex() or '(decode-failed)'))
    ov = []
    keys = [k for k in FEATURES if k in profiles]
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            fa = [(int(p['offset'], 16), int(p['offset'], 16) + p['bytes']) for p in profiles[keys[i]]['patches']]
            fb = [(int(p['offset'], 16), int(p['offset'], 16) + p['bytes']) for p in profiles[keys[j]]['patches']]
            for a1, a2 in fa:
                for b1, b2 in fb:
                    if a1 < b2 and b1 < a2:
                        ov.append((keys[i], keys[j], hex(a1), hex(max(a1, b1)), hex(min(a2, b2))))
    bad_ov = [o for o in ov if o[2:] != (hex(LOADER), hex(LOADER), hex(LOADER + 8))]
    ok_ov = not bad_ov
    g3.add('G3.3', 'feature 窗口重叠扫描（预期唯一重叠=共享 LOADER 0x1024D8C 8B）', ok_ov,
           ('越权重叠：%s' % bad_ov[:4]) if bad_ov else
           '重叠 %d 处全部=LOADER 窗：%s' % (len(ov), [(o[0], o[1]) for o in ov]))
    anchor_bad = []
    src = anchors.get('manifest_source_hashes')
    if src:
        for rel, want in src.items():
            p = MERGED / rel
            if not p.exists():
                anchor_bad.append('%s 缺失（recipe 文件没了）' % rel)
            elif hashlib.sha256(p.read_bytes()).hexdigest() != want:
                anchor_bad.append('%s 现行字节≠构建时记录（recipe 漂移，产物不可复核）' % rel)
    g3.add('G3.4', '产物↔recipe 源码指纹锁（manifest source_hashes 对现行工具链复核）', not anchor_bad,
           '; '.join(anchor_bad[:6]) if anchor_bad else
           'manifest source_hashes ×%d 与现行工具链全一致' % len(src or {}))
    legacy_bad = []
    legacy = anchors.get('legacy_artifacts', {})
    if LEGACY_DIR is None:
        g3.add('G3.5', '旧世代产物哈希锚（本地归档，未随仓库分发）', True,
               'SKIPPED：未提供 NIJIN_LEGACY_DIR，%d 个旧世代锚未核' % len(legacy), skipped=True)
    else:
        for name, want in legacy.items():
            path = LEGACY_DIR / name
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != want:
                legacy_bad.append('legacy anchor 丢失/漂移: %s' % name)
        g3.add('G3.5', '旧世代产物哈希锚（本地归档，未随仓库分发）', not legacy_bad,
               '; '.join(legacy_bad[:6]) if legacy_bad else
               'legacy 锚 %d 个在位；单 feature 构建锚由组合矩阵落锚/复核' % len(legacy))
    return out


# ---------------------------------------------------------------- G1.1 / G5 subprocess gates

def run_verify_py(stock_path, cand_path, features):
    g = GateRun('G1', '字节级门（verify.py 全量）')
    cmd = [sys.executable, str(MERGED / 'verify.py'), str(stock_path), str(cand_path),
           '--features', *features]
    run = subprocess.run(cmd, capture_output=True, text=True)
    ok = run.returncode == 0
    detail = 'rc=%d' % run.returncode
    if ok:
        try:
            rec = json.loads(run.stdout)
            ok = (rec.get('status') == 'PASS' and rec.get('patch_matches_reviewed_profile')
                  and rec.get('all_non_patch_EG_bytes_preserved') and rec.get('other_modules_preserved'))
            detail = 'status=%s reviewed=%s preserved=%s modules=%s' % (
                rec.get('status'), rec.get('patch_matches_reviewed_profile'),
                rec.get('all_non_patch_EG_bytes_preserved'), rec.get('other_modules_preserved'))
        except ValueError:
            ok, detail = False, 'verify.py 输出非 JSON: ' + run.stdout[:200]
    else:
        detail += ' ' + (run.stderr or run.stdout)[:300]
    g.add('G1.1', 'verify.py 全量（reviewed 窗口匹配/窗口外全保持/其它模块不变）', ok, detail)
    return g


def run_tests_gate(stock_path, out_dir):
    g = GateRun('G5', '测试门（上游测试栈 + 113 口径）')
    out_dir.mkdir(parents=True, exist_ok=True)
    v = subprocess.run([sys.executable, '-B', str(MERGED / 'tests' / 'validate.py'),
                        '--stock', str(stock_path), '--report', str(out_dir / 'validate_report.json')],
                       capture_output=True, text=True)
    try:
        rec = json.loads(v.stdout)
        ok1 = v.returncode == 0 and rec.get('status') == 'PASS'
        n1 = len(rec.get('tests', []))
    except ValueError:
        ok1, n1 = False, 0
    g.add('G5.1', 'tests/validate.py（16 项：配方回归+负控+CLI+python -O）', ok1,
          'rc=%d tests=%d %s' % (v.returncode, n1, (v.stderr or '')[:200]))
    vf_report = out_dir / 'validate_features_report.json'
    if vf_report.exists():
        vf_report.unlink()
    f = subprocess.run([sys.executable, '-B', str(MERGED / 'tests' / 'validate_features.py'),
                        '--stock', str(stock_path), '--report', str(vf_report)],
                       capture_output=True, text=True)
    try:
        rec = json.loads(vf_report.read_text())
        ok2 = f.returncode == 0 and rec.get('status') == 'PASS'
        n2 = len(rec.get('tests', []))
    except (ValueError, OSError):
        ok2, n2 = False, 0
    g.add('G5.2', 'tests/validate_features.py（组合回归+负控矩阵）', ok2,
          'rc=%d tests=%d %s' % (f.returncode, n2, (f.stderr or '')[:200]))
    # 113 P1-P3 baseline patch standards (static source assertions)
    p1 = (MERGED / 'z8precapture' / 'config.py').read_text()
    p2 = (MERGED / 'tests' / 'validate_features.py').read_text()
    cfg_py = (MERGED / 'configure.py').read_text()
    ok_p1 = re.search(r'def build_config\(\s*diagnostic_footer', p1) is not None
    ok_p2 = 'Z8PRECFGv4' in p2 and '0x293' in p2 and 'build_config(diagnostic_footer=diagnostic)' in p2
    ok_p3 = 'build_config(a.diagnostic_footer)' in cfg_py
    g.add('G5.3', '113 P1–P3 基线补丁口径（config.py 首参=diagnostic_footer / 测试期望 v4 / configure 位置传参）',
          ok_p1 and ok_p2 and ok_p3, 'P1=%s P2=%s P3=%s' % (ok_p1, ok_p2, ok_p3))
    menuh_test = MERGED / 'tests' / 'test_menuh.py'
    if menuh_test.exists():
        pt = subprocess.run([sys.executable, '-m', 'pytest', '-q', str(menuh_test)],
                            capture_output=True, text=True, cwd=str(MERGED))
        lines = [l for l in (pt.stdout or '').strip().splitlines() if l.strip()]
        g.add('G5.4', 'tests/test_menuh.py（pytest：menuh 配方重生成机械锁等）', pt.returncode == 0,
              'rc=%d %s' % (pt.returncode, (lines[-1] if lines else (pt.stderr or '')[-160:])[:160]))
    else:
        g.add('G5.4', 'tests/test_menuh.py', False, 'menuh 测试缺失')
    return g


# ---------------------------------------------------------------- G4 / G6 / G7

def run_cfg_gate(cfg_files, ring_cap):
    g = GateRun('G4', 'CFG 门（magic/flags/frames/CRC32/正交性）')
    facts = []
    bad = {'G4.1': [], 'G4.2': [], 'G4.3': [], 'G4.4': []}
    for path in cfg_files:
        raw = path.read_bytes()
        try:
            if path.name.upper().startswith('Z8OG'):
                f = cc.parse_og(raw)
            else:
                f = cc.parse_pre(raw, ring_cap)
            f['file'] = path.name
            facts.append(f)
        except cc.CfgError as exc:
            bad.setdefault(exc.check, []).append('%s: %s' % (path.name, exc))
    g.add('G4.1', 'Z8PRE/Z8OG magic 版本（Z8PRECFGv4 / Z8OGCFGv1）', not bad['G4.1'],
          '; '.join(bad['G4.1']) or 'OK: %s' % ', '.join(f['file'] for f in facts))
    g.add('G4.2', 'flags 位合法性（F_KNOWN 掩码 0x7FF/0x1）', not bad['G4.2'], '; '.join(bad['G4.2']) or '全档位合法')
    g.add('G4.3', 'frames≤RING_CAP(%d) 且 budget/bit_depth 合法' % ring_cap, not bad['G4.3'],
          '; '.join(bad['G4.3']) or 'OK')
    g.add('G4.4', 'CRC32 重算（含保留位=0 语义）', not bad['G4.4'], '; '.join(bad['G4.4']) or 'OK')
    try:
        cc.orthogonality([f for f in facts if f['kind'] == 'Z8PRE'] + [f for f in facts if f['kind'] == 'Z8OG'])
        ok5, d5 = True, 'Z8PRE×%d + Z8OG×%d：magic/CRC 独立、保留位零、无共享状态（110 §E.3）' % (
            sum(1 for f in facts if f['kind'] == 'Z8PRE'), sum(1 for f in facts if f['kind'] == 'Z8OG'))
    except cc.CfgError as exc:
        ok5, d5 = False, str(exc)
    g.add('G4.5', '两文件正交性（Z8PRE ⟂ Z8OG）', ok5, d5)
    return g, facts


def run_hygiene_gate(kit, manifest, features=None, cand_eg=None):
    g = GateRun('G6', 'flash_kit 卫生门（唯一固件/shasum/残留/manifest 一致）')
    bins = sorted(p.name for p in kit.glob('*.bin'))
    g.add('G6.1', '唯一固件文件（恰好一个 .bin）', len(bins) == 1, 'bins=%s' % bins)
    def resolve(name, want_sha):
        """Exact file, or a unique same-sha alias (kit renames the build's Z8PRE.CFG
        to tier names; content integrity is what matters, alias is annotated)."""
        p = kit / name
        if p.exists():
            return p, ''
        twins = [q for q in kit.iterdir() if q.is_file() and q.name != name
                 and hashlib.sha256(q.read_bytes()).hexdigest() == want_sha]
        if len(twins) == 1:
            return twins[0], '%s→%s（同 sha 别名）' % (name, twins[0].name)
        return None, ''

    sums_bad, alias_notes = [], []
    for sums_name, strict_set in [('SHA256SUMS_ALL.txt', True), ('SHA256SUMS.txt', False)]:
        sums_file = kit / sums_name
        if not sums_file.exists():
            sums_bad.append(sums_name + ' 缺失')
            continue
        lines = [l.split() for l in sums_file.read_text().splitlines() if l.strip()]
        listed = set()
        for h, name in lines:
            listed.add(name)
            p, note = resolve(name, h)
            if note:
                alias_notes.append(note)
            if p is None:
                sums_bad.append('%s: %s 不存在且无同 sha 别名' % (sums_name, name))
            elif hashlib.sha256(p.read_bytes()).hexdigest() != h:
                sums_bad.append('%s: %s 哈希不符' % (sums_name, name))
        if strict_set:
            actual = {p.name for p in kit.iterdir() if p.name != sums_name}
            if listed != actual:
                sums_bad.append('SHA256SUMS_ALL 与实物集合不一致: only-listed=%s only-actual=%s'
                                % (sorted(listed - actual), sorted(actual - listed)))
    g.add('G6.2', 'shasum -c（SHA256SUMS_ALL.txt + SHA256SUMS.txt 全量复核；别名须同 sha 唯一）',
          not sums_bad, '; '.join(sums_bad) or ('全匹配；别名 %s' % alias_notes if alias_notes else '全匹配'))
    residue = []
    for p in kit.iterdir():
        if FORBIDDEN_IDENTITY.search(p.name) or re.search(r'(?i)(tmp|mutant|_bad|test)', p.name):
            residue.append(p.name)
    text = json.dumps(manifest) if manifest else ''
    if FORBIDDEN_IDENTITY.search(text):
        residue.append('manifest 含 04.01')
    g.add('G6.3', '无 0401/测试残留（文件名+manifest 身份面）', not residue, 'residue=%s' % residue or '干净')
    ok_m, detail_m = False, 'manifest.json 缺失'
    if manifest:
        bad = []
        bin_name = bins[0] if bins else None
        if manifest.get('output_filename') != bin_name:
            bad.append('output_filename %s != %s' % (manifest.get('output_filename'), bin_name))
        if bin_name:
            got = hashlib.sha256((kit / bin_name).read_bytes()).hexdigest()
            if manifest.get('output_sha256') != got:
                bad.append('output_sha256 漂移')
            if manifest.get('output_bytes') != (kit / bin_name).stat().st_size:
                bad.append('output_bytes 不符')
        if manifest.get('input_sha256') != STOCK_SHA256:
            bad.append('input_sha256 != d67413c2…')
        cfg = manifest.get('configuration')
        if cfg:
            p, note = resolve(cfg['filename'], cfg['sha256'])
            if p is None or hashlib.sha256(p.read_bytes()).hexdigest() != cfg['sha256']:
                bad.append('configuration sha 不符（%s）' % cfg['filename'])
            elif note:
                alias_notes.append(note)
        else:
            bad.append('manifest 无 configuration 记录')
        vtxt = kit / 'VERIFY.txt'
        if not vtxt.exists():
            bad.append('VERIFY.txt 缺失')
        else:
            try:
                vrec = json.loads(vtxt.read_text())
                if vrec.get('status') != 'PASS' or vrec.get('output_sha256') != manifest.get('output_sha256'):
                    bad.append('VERIFY.txt 与 manifest 不一致或非 PASS')
            except ValueError:
                bad.append('VERIFY.txt 非 JSON')
        ok_m, detail_m = not bad, '; '.join(bad) or 'manifest↔实物/VERIFY/CFG 全一致'
    g.add('G6.4', 'manifest 与实物一致（输出/输入/CFG/VERIFY 交叉）', ok_m, detail_m)
    if manifest and features is not None:
        mfeat = sorted(manifest.get('features') or [])
        det = sorted(features)
        g.add('G6.5', 'manifest feature 自述 == 字节面检测（含 menuh 哨位 0xEB5598；包不撒谎）',
              mfeat == det, 'manifest=%s bytes=%s' % (mfeat, det))
    if manifest and cand_eg is not None:
        miss, rows = [], manifest.get('edits') or []
        for e in rows:
            at = e['offset'] if isinstance(e['offset'], int) else int(str(e['offset']), 16)
            n = e['bytes']
            got = hashlib.sha256(cand_eg[at:at + n]).hexdigest()
            if got != e.get('after_sha256'):
                miss.append('%s@0x%x' % (e.get('feature', '?'), at))
        g.add('G6.6', 'manifest 构建记录窗口字节实存（%d 编辑逐一 after_sha256 复核）' % len(rows),
              not miss, '; '.join(miss[:6]) or '%d/%d 窗口实存' % (len(rows) - len(miss), len(rows)))
    return g
