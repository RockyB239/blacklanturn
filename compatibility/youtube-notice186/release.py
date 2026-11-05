"""Build the Fire TV Preview Check correction from the published 1.1.63 editions."""
import argparse
import json
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def previous_pipeline():
    import importlib.util
    path = ROOT / 'compatibility/controller-maintenance185/release.py'
    spec = importlib.util.spec_from_file_location('release185_baseline', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


previous = previous_pipeline()
prior = previous.prior
require = previous.require
BASE = '1.1.63'
VERSION = '1.1.64'
VERSIONS = {**previous.VERSIONS, 'build': VERSION}
EDITIONS = {
    'general': ('General', '3626dd49d9de695e48b1849965d6bdfe9bf12cfd276e0727158f016755da72e9'),
    'apple': ('Apple-TV-Mac', '301ae34d45f936bfdfd7418e7abfaf06389bab7754a52feb96508f76617bfa8d'),
}
MARKER, NOTICES = previous.MARKER, previous.NOTICES
GUARD = 'addons/service.blacklanturn.previewcheck/'
YOUTUBE = 'addons/plugin.video.youtube/'
CLIENT = YOUTUBE + 'resources/lib/youtube_plugin/youtube/client/player_client.py'
DOWNLOAD = f'https://github.com/RockyB239/blacklanturn/releases/download/v{VERSION}/'
NOTES = {
    'title': f'BlackLanturn Build {VERSION}',
    'summary': 'Corrects a YouTube compatibility warning on Fire TV.',
    'sections': [{'heading': 'YouTube previews', 'bullets': [
        'The Fire TV startup check now recognizes the tested YouTube patch already in the build.',
        'Warnings still appear if the tested files are replaced or preview playback settings are disabled.',
    ]}],
}


def expected_payload(label):
    return {GUARD + name for name in ('addon.xml', 'check.py')} if label == 'general' else set()


def stage_hosted(out, report, entries):
    hosted = ROOT / 'hosted-files'
    staged = out / 'draft-hosted/hosted-files'
    staged.mkdir(parents=True)
    catalog = json.loads((hosted / 'releases-v1.json').read_bytes())['releases']
    require(all(entry['version'] != VERSION for entry in catalog), 'Version already in release catalog')
    (staged / 'releases-v1.json').write_bytes(prior.validated_feed(previous.validator, entries + catalog))
    (staged / f'release-notes-{VERSION}.json').write_bytes(prior.encoded(NOTES))
    (staged / f'setup-{VERSION}.txt').write_text((hosted / f'setup-{BASE}.txt').read_text().replace(BASE, VERSION))
    blocks = (hosted / 'builds-v2.txt').read_text().strip().split('\n\n')
    require(len(blocks) == 3 and 'version="1.0.54"' in blocks[0], 'Catalog layout differs')
    for i, label in enumerate(EDITIONS, 1):
        row = report[label]
        require(f'version="{BASE}"' in blocks[i], 'Catalog base differs')
        fields = {
            'version': VERSION, 'url': DOWNLOAD + row['full']['file'],
            'info': previous.PAGES + f'setup-{VERSION}.txt',
            'description': NOTES['summary'] + ' Requires BlackLanturn Installer 1.0.54.',
            'updatebase': row['components']['base'],
            'updateurl': DOWNLOAD + row['components']['file'], 'updatesha256': row['components']['sha256'],
        }
        for key, value in fields.items():
            blocks[i], count = re.subn(rf'^{key}="[^"\n]*"$', lambda _: f'{key}="{value}"', blocks[i], flags=re.M)
            require(count == 1, 'Unexpected catalog field ' + key)
    (staged / 'builds-v2.txt').write_text('\n\n'.join(blocks) + '\n\n')
    return {p.relative_to(staged.parent).as_posix(): prior.asset(p) for p in sorted(staged.iterdir())}


def build(baselines, output):
    require(not output.exists(), 'Choose an unused output directory')
    installer = baselines / previous.INSTALLER_NAME
    require(prior.file_sha(installer) == previous.INSTALLER_PIN, 'Published installer differs')
    require(prior.file_sha(ROOT / 'repository.blacklanturn.zip') == prior.REPOSITORY_PIN, 'Repository differs')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.notice186-', dir=output.parent) as folder:
        out = Path(folder) / 'candidate'
        out.mkdir()
        shutil.copyfile(installer, out / installer.name)
        manifest = {
            'schema': 1, 'versions': VERSIONS,
            'baselines': {label: pin for label, (_, pin) in EDITIONS.items()},
            'installer_sha256': previous.INSTALLER_PIN,
            'guard': json.loads((ROOT / 'compatibility/managed-updates/previewcheck/provenance.json').read_bytes()),
            'pipeline_sha256': prior.file_sha(Path(__file__)),
        }
        (out / 'source-manifest.json').write_bytes(prior.encoded(manifest))
        report = {'schema': 1, 'versions': VERSIONS, 'installer': prior.asset(out / installer.name)}
        entries = []
        for label, (edition, pin) in EDITIONS.items():
            base = baselines / f'BlackLanturn-{edition}-Kodi21-{BASE}.zip'
            require(prior.file_sha(base) == pin, 'Unexpected baseline ' + edition)
            before = previous.read_zip(base)
            data = dict(before)
            previous.legacy.apply_preview_check(data)
            expected = expected_payload(label)
            require({name for name in data.keys() | before.keys() if data.get(name) != before.get(name)} == expected,
                    'Unreviewed package delta ' + edition)
            marker = json.loads(data[MARKER])
            base_id = f'blacklanturn-{label}-{BASE}-r0'
            require(marker['release_id'] == base_id and marker['build_version'] == BASE, 'Unexpected build marker')
            marker.update(build_version=VERSION, release_id=f'blacklanturn-{label}-{VERSION}-r0')
            proof = expected | {CLIENT, YOUTUBE + 'addon.xml', previous.PREFIX + 'addon.xml'}
            entry = dict(id=marker['release_id'], edition=label, version=VERSION, revision=0,
                         **NOTES, files={name: prior.sha(data[name]) for name in sorted(proof)})
            entries.append(entry)
            data[MARKER] = prior.encoded(marker)
            history = json.loads(before[NOTICES])['releases']
            require(history[0]['id'] == base_id, 'Unexpected bundled release notes')
            data[NOTICES] = prior.validated_feed(previous.validator, [entry, *history])
            full = out / f'BlackLanturn-{edition}-Kodi21-{VERSION}.zip'
            previous.legacy.zipwrite(full, data)
            with zipfile.ZipFile(full) as archive:
                previous.managed.verify_archive(archive, umbrella=True, network=True, youtube=True)
            delta = out / f'BlackLanturn-{edition}-Update-{BASE}-to-{VERSION}.zip'
            change = previous.component_update.build(base, full, delta)
            require(change['base'] == base_id, 'Unexpected component base')
            report[label] = {'edition': label, 'baseline_sha256': pin, 'full': prior.asset(full),
                             'components': dict(prior.asset(delta), base=base_id),
                             'changed_files': sorted(expected | {MARKER, NOTICES})}
            print('Built', edition, VERSION, flush=True)
        report['draft_hosted'] = stage_hosted(out, report, entries)
        (out / 'candidate-packages.json').write_bytes(prior.encoded(report))
        hashes = prior.record(prior.inventory(out))
        (out / 'SHA256SUMS').write_text(''.join(f'{value}  {name}\n' for name, value in hashes.items()))
        out.rename(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baselines', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.baselines.resolve(), args.output.resolve())
