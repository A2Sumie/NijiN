"""Compose selected features once, sharing only the reviewed text-loader edit."""
import binascii
import re
from z8prores.package import require, sha
from z8prores.patcher import public_words, compatibility as prores_compatibility
from z8prores import base as basemod

FEATURES = ('prores', 'precapture', 'opengate', 'menuh')
LOADER = 0x1024D8C      # recipe offset, translated at use


def selected_features(features):
    require(features and len(features) == len(set(features)) and set(features) <= set(FEATURES),
            'Select prores, precapture, opengate, or any combination, without duplicates')
    require('opengate' not in features or 'precapture' in features,
            'opengate needs precapture: only the precapture loader window (0x40970000) maps the hook code')
    return [f for f in FEATURES if f in features]


def identity(eg):
    require(len(eg) == 81807711 and binascii.crc_hqx(eg, 0) == 0, 'Invalid EG length or CRC')
    text = eg[0x14eaa90:0x14eaa98]
    require(re.fullmatch(rb'[0-9]{2}\.[0-9]{2}\.(?:[a-z]\d|[0-9]{2})', text),  # LOCAL DEVIATION: 03.12 stock tag is numeric
            'Unsupported runtime identity')
    code_at = basemod.at(0xeb29fc)
    require(eg[-11:-3] == text and eg[code_at:code_at + 12] == public_words(text[:5].decode()),
            'Public, runtime and trailer versions disagree')
    return text.decode()


def compatibility(eg, features):
    features = selected_features(features)
    basemod.CURRENT['base'] = basemod.identity_of(eg)   # recipe offsets translate from here on
    old_identity = identity(eg)
    profiles = {}
    if 'prores' in features:
        profiles['prores'], _ = prores_compatibility(eg)
    if 'precapture' in features:
        from z8precapture.patcher import compatibility as raw_compatibility
        profiles['precapture'] = raw_compatibility(eg)
    if 'opengate' in features:
        from z8opengate.patcher import compatibility as og_compatibility
        profiles['opengate'] = og_compatibility(eg)
    if 'menuh' in features:
        from z8menuh.patcher import compatibility as menuh_compatibility
        profiles['menuh'] = menuh_compatibility(eg)
    return profiles, old_identity


def build(eg, version, tag, features, compiler='clang'):
    features = selected_features(features)
    profiles, old_identity = compatibility(eg, features)
    public_words(version)
    require(re.fullmatch(r'[a-z][0-9]', tag), 'Tag must be a lowercase letter and digit')
    require(tuple(map(int, version.split('.'))) >= tuple(map(int, old_identity[:5].split('.'))),  # LOCAL DEVIATION
            'Output version must not be lower than the input version')
    edits = {}
    details = {}

    def add(at, raw, purpose, feature):
        for start, e in edits.items():
            if at < start+len(e['new']) and start < at+len(raw):
                require(at == start == basemod.at(LOADER) and len(raw) == len(e['new']) == 8,
                        'Selected features contain overlapping patch windows')  # LOCAL DEVIATION: loader end may be raised by several features
        edits[at] = dict(offset=at, new=raw, purpose=purpose, feature=feature)

    if 'prores' in features:
        from z8prores.menu import build_main
        image, details['prores'] = build_main(eg[:-2])
        generated = {e['offset']: e for e in image.edits}
        require(len(generated) == len(profiles['prores']['patches']), 'Unexpected ProRes edit count')
        for row in profiles['prores']['patches']:
            at = int(row['offset'], 16)   # base-absolute
            e = generated[at]
            require(len(e['new']) == row['bytes'] and sha(e['old']) == row['old_sha256'] and
                    sha(e['new']) == row['new_sha256'], 'ProRes differs from the reviewed recipe')
            add(at, e['new'], row['purpose'], 'prores')
    if 'precapture' in features:
        from z8precapture.patcher import compile_code, edits as raw_edits
        code, details['precapture'] = compile_code(compiler)
        for e in raw_edits(code):
            add(e['offset'], e['new'], e['purpose'], 'precapture')
    if 'opengate' in features:
        from z8opengate.patcher import build_edits as og_edits
        for e in og_edits(compiler):
            add(e['offset'], e['new'], e['purpose'], 'opengate')
        details['opengate'] = 'opengate option: 3:2 experimental tiers, Z8OG.CFG gate'
    if 'menuh' in features:
        from z8menuh.patcher import edits as menuh_edits, compatibility as menuh_compat
        rows = menuh_edits(eg[:-2])
        locked = menuh_compat(eg[:-2])
        if isinstance(locked, dict) and 'patches' in locked:
            require(len(rows) == len(locked['patches']), 'Unexpected menuh edit count')
            for e, row in zip(rows, locked['patches']):
                require(len(e['new']) == row['bytes'] and sha(e['old']) == row['old_sha256'] and
                        sha(e['new']) == row['new_sha256'], 'menuh differs from the reviewed recipe')
        for e in rows:
            add(e['offset'], e['new'], e['purpose'], 'menuh')
        details['menuh'] = 'P2-A DS-table relocation + h group shell (menuh)'
    text = f'{version}.{tag}'.encode()
    for at, raw, purpose in [(basemod.at(0xeb29fc), public_words(version), 'public version instructions'),
                             (0x14eaa90, text, 'runtime identity'), (len(eg)-11, text, 'trailer identity')]:
        add(at, raw, purpose, 'identity')
    out = bytearray(eg)
    for e in edits.values():
        out[e['offset']:e['offset']+len(e['new'])] = e['new']
    add(len(eg)-2, binascii.crc_hqx(out[:-2], 0).to_bytes(2, 'big'), 'EG CRC16', 'integrity')
    out[-2:] = edits[len(eg)-2]['new']
    end, rows, preserved = 0, [], []
    for at, e in sorted(edits.items()):
        require(end <= at and eg[end:at] == out[end:at], 'Unexpected modification outside patch windows')
        if end < at:
            preserved.append(dict(start=end, end=at, sha256=sha(eg[end:at])))
        rows.append(dict(offset=at, bytes=len(e['new']), purpose=e['purpose'], feature=e['feature'],
                         before_sha256=sha(eg[at:at+len(e['new'])]), after_sha256=sha(e['new'])))
        end = at+len(e['new'])
    require(eg[end:] == out[end:] and binascii.crc_hqx(out, 0) == 0, 'Invalid final payload')
    return bytes(out), dict(features=features, input_identity=old_identity, output_identity=text.decode(),
                            profiles={f: p['id'] for f,p in profiles.items()}, edits=rows,
                            preserved_ranges=preserved, all_bytes_outside_edits_preserved=True, details=details)
