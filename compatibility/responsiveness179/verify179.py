"""Run real candidate installation paths and verify exact immutable release deltas."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import release179 as release


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(snapshot, artifacts, baselines, output):
    manifest = release.verify_snapshot(snapshot)
    require((snapshot / 'pipeline/verify179.py').read_bytes() == Path(__file__).read_bytes(),
            'Invoke the exact frozen verification implementation')
    report_path = artifacts / 'candidate-packages.json'
    report = json.loads(report_path.read_bytes())
    require(report['versions'] == release.VERSIONS and report['source_manifest_sha256'] == release.file_sha(snapshot / 'source-manifest.json'),
            'Candidate versions or snapshot identity differ')
    exact_assets = []
    for label, (edition, pin) in release.BASELINES.items():
        row = report[label]
        base = baselines / release.full_name(edition, release.BASE_VERSION)
        before = release.baseline(base, label)
        require(row['baseline_sha256'] == pin, 'Unexpected baseline pin')
        for role in ('full', 'components'):
            entry = row[role]
            path = artifacts / entry['file']
            require(release.asset(path) == entry if role == 'full' else
                    release.asset(path) == {k: v for k, v in entry.items() if k != 'base'}, 'Artifact hash differs')
            with zipfile.ZipFile(path) as archive:
                require(archive.testzip() is None, 'Artifact CRC differs')
            exact_assets.append(entry['file'])
        with zipfile.ZipFile(artifacts / row['full']['file']) as archive:
            after = {name: archive.read(name) for name in archive.namelist() if not name.endswith('/')}
        changed = {name for name in before.keys() | after.keys() if before.get(name) != after.get(name)}
        require(changed == set(row['changed_files']), 'Unreported payload delta')
        require(before.keys() <= after.keys(), 'Payload unexpectedly removes files')
        require({n for n in changed if not n.startswith('addons/')} == {release.MARKER, release.NOTICES},
                'Arbitrary defaults or other userdata changed')
        allowed_addons = {release.CONTROLLER, release.INSTALLER, *release.MANAGED}
        require(all(n.split('/')[1] in allowed_addons for n in changed if n.startswith('addons/')),
                'Unrelated add-on changed')
        require(not any('source_retry.py' in n for n in changed), 'Unpublished retry experiment included')
        require(json.loads(after[release.MARKER])['release_id'] == f'blacklanturn-{label}-1.1.62-r0',
                'Incorrect release target')
        for aid, directory in ((release.CONTROLLER, 'controller-source/addon'),
                               (release.INSTALLER, 'installer-source/' + release.INSTALLER)):
            expected = release.inventory(snapshot / 'source' / directory)
            prefix = 'addons/' + aid + '/'
            require({n[len(prefix):]: raw for n, raw in after.items() if n.startswith(prefix)} == expected,
                    'Bundled source differs from snapshot: ' + aid)
    installer = report['installer']
    require(release.asset(artifacts / installer['file']) == installer, 'Installer asset hash differs')
    exact_assets.append(installer['file'])
    for name, entry in report['draft_hosted'].items():
        require(release.asset(artifacts / 'draft-hosted' / name) == entry, 'Staged Pages hash differs')
    metadata = (artifacts / 'draft-hosted/addons.xml').read_bytes()
    require((artifacts / 'draft-hosted/addons.xml.md5').read_text() == release.hashlib.md5(metadata).hexdigest(),
            'Repository metadata checksum differs')
    matrix_output = output.with_name(output.stem + '-matrix.json')
    subprocess.run([sys.executable, str(snapshot / 'source/tools/verify_release165.py'),
                    '--artifacts', str(artifacts), '--baselines', str(baselines),
                    '--baseline-version', '1.1.61', '--installer-version', '1.0.54',
                    '--output', str(matrix_output)], check=True)
    matrix = json.loads(matrix_output.read_bytes())
    expected_checks = {label + ' ' + case for label in release.BASELINES
                       for case in ('in-place full', 'in-place components', 'Standard install', 'clean install')}
    require(matrix['passed'] is True and set(matrix['checks']) == expected_checks and
            matrix['package_report_sha256'] == release.file_sha(report_path), 'Exact eight-case matrix did not pass')
    receipt = {'schema': 1, 'passed': True, 'source_manifest_sha256': release.file_sha(snapshot / 'source-manifest.json'),
               'package_report_sha256': release.file_sha(report_path), 'matrix_sha256': release.file_sha(matrix_output),
               'artifacts_sha256': {name: release.file_sha(artifacts / name) for name in exact_assets},
               'checks': sorted(expected_checks), 'public_changed': False,
               'scope': 'Real packaged Installer paths in disposable synthetic profiles; no physical-device acceptance claim'}
    output.write_bytes(release.encoded(receipt))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('snapshot', 'artifacts', 'baselines', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.snapshot.resolve(), args.artifacts.resolve(), args.baselines.resolve(), args.output.resolve()), indent=2))


if __name__ == '__main__':
    main()
