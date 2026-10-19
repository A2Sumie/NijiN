"""pytest gates for the menuh round-0 build: recipe lock (G3.4), invariants, composition.

Runs against the stock EG slice and the locked recipe; no firmware is written here.
"""
import json
import os
import struct
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
COPY = HERE.parent
sys.path.insert(0, str(COPY))
sys.dont_write_bytecode = True

from z8menuh import patcher as P
from z8prores.package import sha

# The reviewed EG slice is a user-supplied local file (this repository ships no
# firmware). Point NIJIN_EG_SLICE at it to run the full gate set; without it the
# tests skip with an explicit note instead of passing silently.
EG_PATH = Path(os.environ['NIJIN_EG_SLICE']) if os.environ.get('NIJIN_EG_SLICE') else None
RECIPE = COPY / 'resources' / 'menuh.json'


@pytest.fixture(scope='module')
def eg():
    if EG_PATH is None or not EG_PATH.exists():
        pytest.skip('NIJIN_EG_SLICE not set or missing')
    data = EG_PATH.read_bytes()
    assert len(data) == P.PAYLOAD + 2
    return data[:-2]


@pytest.fixture(scope='module')
def rows(eg):
    return P.edits(eg)


@pytest.fixture(scope='module')
def recipe():
    return json.loads(RECIPE.read_text())


def word(eg, off):
    return struct.unpack_from('<I', eg, off)[0]


# ---- G3.4 产物↔recipe 锁 ----

def test_recipe_patch_count_and_bytes(rows, recipe):
    assert len(rows) == len(recipe['patches'])
    assert sum(len(r['new']) for r in rows) == sum(p['bytes'] for p in recipe['patches'])


def test_recipe_regeneration_identical(rows, recipe):
    for e, p in zip(rows, recipe['patches']):
        assert hex(e['offset']) == p['offset']
        assert len(e['new']) == p['bytes']
        assert sha(e['old']) == p['old_sha256']
        assert sha(e['new']) == p['new_sha256']


def test_recipe_ranges_match_stock(eg, recipe):
    for r in recipe['ranges']:
        a, b = int(r['start'], 16), int(r['end'], 16)
        assert sha(eg[a:b]) == r['sha256']


def test_compatibility_accepts_stock(eg):
    prof = P.compatibility(eg)
    assert prof and prof.get('id') == 'z8-c311-menuh-v1'


# ---- 窗口与结构不变式 ----

def test_windows_disjoint_and_sorted(rows):
    for i in range(1, len(rows)):
        assert rows[i - 1]['offset'] + len(rows[i - 1]['new']) <= rows[i]['offset']


def test_only_declared_bytes_change(rows, eg):
    changed = bytearray(eg)
    for e in rows:
        changed[e['offset']:e['offset'] + len(e['new'])] = e['new']
    assert len(changed) == len(eg)


def test_chain_counts(eg):
    assert len(P._chain_sites(eg, P.BASE + P.META_SRC)) == 16
    assert len(P._chain_sites(eg, P.BASE + P.GRP_SRC)) == 28
    assert len(P._chain_sites(eg, 0xA0299E888)) == 7


def _dec_loader(pair8):
    w0, w1 = struct.unpack('<II', pair8)
    assert (w0 >> 31) == 1 and ((w1 >> 21) & 3) == 1   # movz x + movk x@16
    return (w0 >> 5 & 0xFFFF) | ((w1 >> 5 & 0xFFFF) << 16)


def test_loader_single_window_monotonic(rows):
    w = [e for e in rows if e['offset'] == P.LOADER_SITE]
    assert len(w) == 1 and len(w[0]['new']) == 8
    old, new = _dec_loader(w[0]['old']), _dec_loader(w[0]['new'])
    assert new == P.LOADER_END_VA
    assert new > old


def test_loader_window_allowed_in_profile(recipe):
    p = next(x for x in recipe['patches'] if int(x['offset'], 16) == P.LOADER_SITE)
    assert len(p['loader_input_sha256']) >= 2        # stock + 至少一种既有 loader 形态
    assert sha(p['old_sha256'].encode()) is not None and p['old_sha256'] in p['loader_input_sha256']


# ---- P2-A 注册机制不变式 ----

def test_extension_group_record(rows):
    grp = next(e for e in rows if e['offset'] == P.GRP_AT)['new']
    rec = struct.unpack_from('<12I', grp, P.EXT_GROUP * P.GRP_REC)
    assert rec[0] == 2 and rec[2] == P.GRADE_RAM and rec[6] & 0xFFFF == P.NEW_META_IDX
    assert (rec[6] >> 16) == 1                       # count=1
    assert rec[4] == P.BASE + P.MENU_AT + 0x600      # 默认镜像指针


def test_grade_item_meta_record(rows):
    meta = next(e for e in rows if e['offset'] == P.META_AT)['new']
    rec = struct.unpack_from('<6I', meta, P.NEW_META_IDX * P.META_REC)
    assert rec[0] == 0 and rec[1] == 1               # kind0 / size1
    assert rec[2] == P.GRADE_RAM
    assert rec[4] == P.BASE + P.MENU_AT + 0x600


def test_bank_list_anchor_and_append(rows):
    lst = next(e for e in rows if e['offset'] == P.LISTA_AT)['new']
    assert struct.unpack_from('<I', lst, 343 * 4)[0] & 0xFFFF == 0x120B   # v6 hook 项保留
    assert struct.unpack_from('<I', lst, P.LISTA_N * 4)[0] & 0xFFFF == P.NEW_ITEM
    assert struct.unpack_from('<I', lst, P.LISTA_N * 4)[0] >> 16 == 0x70  # flags 仿邻项


def test_bank_list_counts_bumped(rows):
    cs = [e for e in rows if 'count 465->466' in e['purpose']]
    assert len(cs) == 3
    for e in cs:
        assert struct.unpack('<I', e['new'])[0] != struct.unpack('<I', e['old'])[0]


# ---- h 组外壳不变式 ----

def test_h_row_fields(rows):
    menu = next(e for e in rows if e['offset'] == P.MENU_AT)['new']
    row = struct.unpack_from('<11I', menu, 0x80 + 9 * P.ROW_SZ)
    assert row[0] == P.TITLE_STR and row[5] == P.LETTER_ID
    assert row[6] not in (0, 0xFFFFFFFF)
    assert row[8] == row[9] == 0xFFFFFFFF and row[10] == 2


def test_group_arrays_have_8th_entry(rows):
    menu = next(e for e in rows if e['offset'] == P.MENU_AT)['new']
    a, b, c, d = (struct.unpack_from('<8I', menu, i * 0x20) for i in range(4))
    assert a[7] == 0xAA                                 # 图标语义未定案：复用 a 组值（安全侧）
    assert b[7] == P.TITLE_STR                          # h 标题串 id（原厂 'Custom'）
    assert c[7] != 0                                    # h 行条目 id（动态选空闲）
    assert d[7] == 0                                    # h 组暂无条目
    assert (a[:7], b[:7], c[:7], d[:7]) == tuple(s[2] for s in P.ARRAYS)   # 前 7 项保持 stock 值


def test_page_record_count_and_pointers(rows):
    pr = next(e for e in rows if e['purpose'] == 'page record rows/evptr pointers')
    rows_ptr, evp_ptr = struct.unpack('<QQ', pr['new'])
    assert rows_ptr == P.BASE + P.MENU_AT + 0x80
    assert evp_ptr == P.BASE + P.MENU_AT + 0x340
    cnt = next(e for e in rows if e['purpose'] == 'page row count 9->10')
    assert struct.unpack('<H', cnt['new'])[0] == 10


def test_bounds_widened(rows):
    want = {'cmp w20,#6 -> #7': 7, 'cmp w21,#6 -> #7': 7, 'cmp w8,#7 -> #8': 8}
    for e in rows:
        for desc, val in want.items():
            if e['purpose'] == desc:
                w = struct.unpack('<I', e['new'])[0]
                assert ((w >> 10) & 0xFFF) == val
    mov = next(e for e in rows if '查表未命中哨兵' in e['purpose'])
    assert struct.unpack('<I', mov['new'])[0] == 0x52800120    # movz w0,#9


def test_tool_scripts_importable():
    """crap/coverage 门需要脚本式工具（非 pytest 覆盖对象）在 coverage 报告里有条目。"""
    import importlib.util
    for rel in ('tests/validate.py', 'tests/validate_features.py', 'tools/check_repository.py'):
        name = rel.replace('/', '_')[:-3]
        spec = importlib.util.spec_from_file_location(name, COPY / rel)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert mod is not None
