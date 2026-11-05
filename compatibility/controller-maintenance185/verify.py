"""Verify exact build bytes with the shipped Installer and the packaged Controller."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

import release


def verify(artifacts, baselines, output):
    report_path = artifacts / 'candidate-packages.json'
    report = json.loads(report_path.read_bytes())
    release.require(report['versions'] == release.VERSIONS, 'Package version mismatch')
    smoke = {}
    with tempfile.TemporaryDirectory(prefix='bl185-packaged-smoke-') as folder:
        for label, (edition, pin) in release.BASELINES.items():
            row = report[label]
            baseline = baselines / f'BlackLanturn-{edition}-Kodi21-1.1.62.zip'
            release.require(release.prior.file_sha(baseline) == pin, 'Public baseline mismatch')
            before = release.read_zip(baseline)
            full = artifacts / row['full']['file']
            release.require(release.prior.asset(full) == row['full'], 'Full archive mismatch')
            after = release.read_zip(full)
            changed = {n for n in before.keys() | after.keys() if before.get(n) != after.get(n)}
            expected = json.loads((release.HERE / 'controller-delta.json').read_bytes())
            release.require(changed == {release.PREFIX + n for n in expected} | {release.MARKER, release.NOTICES},
                            'Unexpected package payload delta')
            root = Path(folder) / label
            addon = root / 'controller-source/addon'
            tests = root / 'controller-source/tests'
            release.prior.write_tree(addon, {n[len(release.PREFIX):]: raw for n, raw in after.items()
                                             if n.startswith(release.PREFIX)})
            for n, pin in expected.items():
                release.require(release.prior.file_sha(addon / n) == pin, 'Packaged Controller hash mismatch')
            shutil.copytree(release.ROOT / 'controller-source/tests', tests,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            check = '''import sys, unittest
sys.path.insert(0, 'controller-source/addon')
names=['test_discovery_order','test_discovery_order_context','test_first_page_latency',
       'test_discovery_snapshot_routes','test_read_connections180']
sys.path.insert(0, 'controller-source/tests')
result=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromNames(names))
if not result.wasSuccessful() or result.testsRun < 45: sys.exit(1)
print(result.testsRun)
'''
            done = subprocess.run([sys.executable, '-c', check], cwd=root, text=True, check=True, stdout=subprocess.PIPE)
            smoke[label] = int(done.stdout.strip())
    matrix_path = output.with_name(output.stem + '-matrix.json')
    subprocess.run([sys.executable, str(release.ROOT / 'tools/verify_release165.py'),
                    '--artifacts', str(artifacts), '--baselines', str(baselines),
                    '--baseline-version', '1.1.62', '--installer-version', '1.0.54',
                    '--output', str(matrix_path)], check=True)
    matrix = json.loads(matrix_path.read_bytes())
    expected_cases = {label + ' ' + case for label in release.BASELINES
                      for case in ('in-place full', 'in-place components', 'Standard install', 'clean install')}
    release.require(matrix['passed'] and set(matrix['checks']) == expected_cases
                    and matrix['package_report_sha256'] == release.prior.file_sha(report_path),
                    'Package matrix is not bound to the exact candidate')
    result = {'passed': True, 'versions': report['versions'],
              'package_report_sha256': matrix['package_report_sha256'],
              'archive_sha256': matrix['artifacts_sha256'],
              'matrix_sha256': release.prior.file_sha(matrix_path),
              'matrix_checks': sorted(expected_cases), 'packaged_controller_checks': smoke}
    output.write_bytes(release.prior.encoded(result))
    print(json.dumps(result))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('artifacts', 'baselines', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    args = p.parse_args()
    verify(args.artifacts.resolve(), args.baselines.resolve(), args.output.resolve())
