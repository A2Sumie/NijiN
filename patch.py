#!/usr/bin/env python3
"""Build selected experimental Nikon Z8 features from a user-supplied update package."""
import argparse
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from z8prores.package import Package, PACKAGE_BYTES, RESOURCES, require, sha
from features import build, compatibility
from z8precapture.config import CONFIG_NAME, build_config


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('firmware', type=Path, help='User-supplied complete Z8 firmware .bin')
    ap.add_argument('--check', action='store_true', help='Read-only input compatibility and integrity check')
    ap.add_argument('--version', help='Output version NN.NN, e.g. 04.03 (choose higher than the installed camera)')
    ap.add_argument('--tag', default='p0', help='Internal revision suffix: lowercase letter plus digit; default p0')
    group = ap.add_mutually_exclusive_group()
    group.add_argument('--features', nargs='+', choices=['prores', 'precapture', 'opengate', 'menuh'], help='Any combination of the features; default prores')
    group.add_argument('--interactive', action='store_true', help='Choose ProRes, menu-controlled RAW capture, or both')
    ap.add_argument('--compiler', default='clang', help='Clang executable for pre-capture; output must match the reviewed recipe')
    ap.add_argument('--output', type=Path, help='New output directory; must not already exist')
    a = ap.parse_args()
    if not a.check and (not a.version or not a.output):
        ap.error('Building requires --version and --output; use --check for read-only inspection')
    if a.check and (a.output or a.version or a.tag != 'p0' or a.interactive):
        ap.error('--check cannot be combined with output options')
    if a.interactive:
        print('1: ProRes quality / ProRes 画质\n2: HE RAW capture / HE RAW 连拍与预拍\n3: Both / 两项同时启用')
        choice = input('Select / 选择 [1/2/3]: ').strip()
        require(choice in ('1', '2', '3'), 'Select 1, 2 or 3')
        a.features = {'1': ['prores'], '2': ['precapture'], '3': ['prores', 'precapture', 'opengate']}[choice]
    selected = a.features or ['prores']
    require(a.firmware.is_file(), 'Input must be a regular firmware file')
    require(a.firmware.stat().st_size == PACKAGE_BYTES, 'Unsupported firmware length')
    if not a.check:
        require(not a.output.exists(), 'Output directory already exists; use a new directory')
    data = a.firmware.read_bytes()
    package = Package(data)
    profiles, identity = compatibility(package.eg, selected)
    if a.check:
        print(json.dumps(dict(status='COMPATIBLE', input_sha256=package.sha256,
                              identity=identity, features=selected,
                              profiles={f:p['id'] for f,p in profiles.items()}, modules=package.modules), indent=2))
        return
    eg, report = build(package.eg, a.version, a.tag, selected, a.compiler)
    module_name = 'eg2070_' + a.version.replace('.', '') + a.tag + '.bi'
    packet, checked = package.replace_eg(eg, module_name)
    name = 'Z_8_' + a.version.replace('.', '') + '.bin'
    from verify import verify_pair
    independent = verify_pair(data, packet, selected)
    report.update(status='BUILT_AND_LOCALLY_VERIFIED', input_sha256=package.sha256,
                  input_filename=a.firmware.name, input_bytes=len(data), output_sha256=sha(packet),
                  output_bytes=len(packet), output_filename=name, output_eg_sha256=sha(eg),
                  input_modules=package.modules, output_modules=checked.modules,
                  source_hashes={str(p.relative_to(Path(__file__).resolve().parent)): sha(p.read_bytes())
                                 for p in sorted([*Path(__file__).resolve().parent.glob('*.py'),
                                                  *Path(__file__).resolve().parent.glob('z8prores/*.py'),
                                                  *Path(__file__).resolve().parent.glob('z8precapture/*') ,
                                                  *RESOURCES.glob('*.json')]) if p.is_file() and p.suffix in ('.py','.c','.inc','.json')},
                  independent_verification=independent,
                  scope='Only selected patch windows, version fields and checksums changed; no camera test of this new output')
    config = build_config() if 'precapture' in selected else None
    if config is not None:
        report['configuration'] = dict(filename=CONFIG_NAME, sha256=sha(config), history_ceiling=30,
                                       control='camera-menu', format=3, c15=True, c30=True, diagnostic_footer=False, budget_us=1500000)
    # Create only after validation. Exclusive creation never replaces input or an earlier build.
    # On I/O failure the directory is kept, without a successful manifest, for inspection.
    a.output.mkdir(parents=True, exist_ok=False)
    with (a.output / name).open('xb') as f:
        f.write(packet)
        f.flush()
        os.fsync(f.fileno())
    require(sha((a.output / name).read_bytes()) == report['output_sha256'], 'Output readback mismatch')
    require(sha(a.firmware.read_bytes()) == package.sha256, 'Input changed during build')
    if config is not None:
        with (a.output / CONFIG_NAME).open('xb') as f:
            f.write(config)
        require((a.output / CONFIG_NAME).read_bytes() == config, 'Configuration readback mismatch')
    with (a.output / 'SHA256SUMS.txt').open('x') as f:
        f.write(report['output_sha256'] + '  ' + name + '\n')
        if config is not None:
            f.write(sha(config) + '  ' + CONFIG_NAME + '\n')
    with (a.output / 'manifest.json').open('x') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps(dict(status=report['status'], output=str(a.output / name), sha256=report['output_sha256'],
                          features=selected, input_identity=identity, output_identity=report['output_identity']), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, ImportError, EOFError) as e:
        raise SystemExit('ERROR: ' + str(e))
