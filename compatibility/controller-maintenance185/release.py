"""Reproduce the Controller-only BlackLanturn 1.1.63 release from pinned public inputs."""
import argparse
from collections import OrderedDict
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTROLLER = 'script.blacklanturn.preview'
INSTALLER = 'plugin.program.blacklanturninstaller'
INSTALLER_NAME = INSTALLER + '-1.0.54.zip'
INSTALLER_PIN = 'b7c83dce792e85d765641724325fcbce380cf53fa2b3fcc6ada741d0a0d897d2'
VERSIONS = {'build': '1.1.63', 'controller': '0.1.127', 'installer': '1.0.54'}
BASELINES = OrderedDict((
    ('general', ('General', 'bf2296fefbfdcf7ff8b4d0a5d87da2c7fd48e45abfd8dbad69db616f83259824')),
    ('apple', ('Apple-TV-Mac', '25c288c09460854099571cdf918e4add2dad4a4f93445774b5e3f1a34841db8c')),
))
MARKER = 'userdata/blacklanturn-build.json'
NOTICES = 'userdata/blacklanturn-releases.json'
PREFIX = 'addons/' + CONTROLLER + '/'
RELEASE = 'https://github.com/RockyB239/blacklanturn/releases/download/v1.1.63/'
PAGES = 'https://rockyb239.github.io/blacklanturn/hosted-files/'
NOTES = {
    'title': 'BlackLanturn Build 1.1.63',
    'summary': 'Browsing maintenance for local database connections and discovery sorting.',
    'sections': [
        {'heading': 'Browsing', 'bullets': [
            'Release local database connections promptly during browsing.',
            'Reuse title IDs during discovery sorting while keeping the same row order.',
        ]},
        {'heading': 'Update your build', 'bullets': [
            'Use Update BlackLanturn in Installer 1.0.54 to keep your settings, sign-ins and history.',
        ]},
    ],
}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prior = load('release179_reference', ROOT / 'compatibility/responsiveness179/release179.py')
installer_root = ROOT / 'installer-source' / INSTALLER
sys.path.insert(0, str(installer_root))
component_update = load('release185_components', installer_root / 'resources/libs/component_update.py')
managed = load('release185_managed', installer_root / 'resources/libs/managed_addons.py')
legacy = load('release185_legacy', ROOT / 'tools/build_release.py')
validator = load('release185_notices', ROOT / 'controller-source/addon/release_updates.py')


def require(value, message):
    if not value:
        raise ValueError(message)


def read_zip(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) and archive.testzip() is None, 'Invalid ZIP ' + path.name)
        return {name: archive.read(name) for name in names if not name.endswith('/')}


def stage_hosted(out, report, entries):
    source = ROOT / 'hosted-files'
    target = out / 'draft-hosted/hosted-files'
    target.mkdir(parents=True)
    prior_entries = json.loads((source / 'releases-v1.json').read_bytes())['releases']
    require(not any(entry['version'] == VERSIONS['build'] for entry in prior_entries),
            'Build identity already occurs in the feed')
    (target / 'releases-v1.json').write_bytes(prior.validated_feed(validator, entries + prior_entries))
    (target / 'release-notes-1.1.63.json').write_bytes(prior.encoded(NOTES))
    setup = (source / 'setup-1.1.62.txt').read_text().replace('1.1.62', VERSIONS['build'])
    (target / 'setup-1.1.63.txt').write_text(setup)
    blocks = (source / 'builds-v2.txt').read_text().strip().split('\n\n')
    require(len(blocks) == 3 and 'version="1.0.54"' in blocks[0], 'Catalog layout differs')
    for index, label in enumerate(BASELINES, 1):
        row = report[label]
        require('version="1.1.62"' in blocks[index], 'Catalog base differs')
        values = {
            'version': VERSIONS['build'],
            'url': RELEASE + row['full']['file'],
            'info': PAGES + 'setup-1.1.63.txt',
            'description': NOTES['summary'] + ' Requires BlackLanturn Installer 1.0.54.',
            'updatebase': row['components']['base'],
            'updateurl': RELEASE + row['components']['file'],
            'updatesha256': row['components']['sha256'],
        }
        for name, value in values.items():
            blocks[index], count = re.subn(rf'^{name}="[^"\n]*"$', lambda _: f'{name}="{value}"',
                                           blocks[index], flags=re.M)
            require(count == 1, 'Invalid catalog field ' + name)
    (target / 'builds-v2.txt').write_text('\n\n'.join(blocks) + '\n\n')
    hosted = target.parent
    return {path.relative_to(hosted).as_posix(): prior.asset(path) for path in sorted(target.iterdir())}


def build(baselines, output):
    require(not output.exists(), 'Choose an unused output directory')
    controller = prior.inventory(ROOT / 'controller-source/addon')
    pins = json.loads((HERE / 'controller-delta.json').read_bytes())
    require(len(pins) == 8 and all(prior.sha(controller[name]) == pin for name, pin in pins.items()),
            'Reviewed Controller delta changed')
    installer_zip = baselines / INSTALLER_NAME
    require(prior.file_sha(installer_zip) == INSTALLER_PIN, 'Published Installer differs')
    installer = read_zip(installer_zip)
    require(installer == {INSTALLER + '/' + name: raw for name, raw in prior.inventory(installer_root).items()},
            'Source no longer matches the published Installer')
    require(prior.file_sha(ROOT / 'repository.blacklanturn.zip') == prior.REPOSITORY_PIN,
            'Repository ZIP differs')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.maintenance185-', dir=output.parent) as tmp:
        out = Path(tmp) / 'candidate'
        out.mkdir()
        shutil.copyfile(installer_zip, out / INSTALLER_NAME)
        source = {
            'schema': 1, 'versions': VERSIONS,
            'baselines': {key: pin for key, (_, pin) in BASELINES.items()},
            'installer_sha256': INSTALLER_PIN, 'controller_sha256': prior.record(controller),
            'pipeline_sha256': prior.file_sha(Path(__file__)),
            'catalog_inputs': {name: prior.file_sha(ROOT / 'hosted-files' / name)
                               for name in ('builds-v2.txt', 'releases-v1.json', 'setup-1.1.62.txt')},
        }
        (out / 'source-manifest.json').write_bytes(prior.encoded(source))
        report = {'schema': 1, 'state': 'LOCAL_CANDIDATE', 'versions': VERSIONS,
                  'source_manifest_sha256': prior.file_sha(out / 'source-manifest.json'),
                  'installer': prior.asset(out / INSTALLER_NAME)}
        entries = []
        for label, (edition, pin) in BASELINES.items():
            base_path = baselines / f'BlackLanturn-{edition}-Kodi21-1.1.62.zip'
            require(prior.file_sha(base_path) == pin, 'Published baseline differs: ' + label)
            before = read_zip(base_path)
            marker = json.loads(before[MARKER])
            base_id = f'blacklanturn-{label}-1.1.62-r0'
            require(marker['release_id'] == base_id and marker['build_version'] == '1.1.62', 'Baseline marker differs')
            data = {**before, **{PREFIX + name: raw for name, raw in controller.items()}}
            require({name[len(PREFIX):] for name in before if name.startswith(PREFIX)} == controller.keys(),
                    'Controller source adds or removes files')
            changed = {name for name in data if data[name] != before[name]}
            require(changed == {PREFIX + name for name in pins}, 'Unexpected change outside reviewed Controller files')
            marker.update(build_version=VERSIONS['build'], controller_version=VERSIONS['controller'],
                          release_id=f'blacklanturn-{label}-1.1.63-r0', release_revision=0)
            entry = dict(id=marker['release_id'], edition=label, version=VERSIONS['build'], revision=0,
                         **NOTES, files={PREFIX + name: value for name, value in pins.items()})
            entries.append(entry)
            data[MARKER] = prior.encoded(marker)
            history = json.loads(before[NOTICES])['releases']
            require(history[0]['id'] == base_id and all(prior.sha(before[n]) == v for n, v in history[0]['files'].items()),
                    'Published active proof differs')
            data[NOTICES] = prior.validated_feed(validator, [entry, *history])
            legacy.verify_dependency_closure(data)
            full = out / f'BlackLanturn-{edition}-Kodi21-1.1.63.zip'
            legacy.zipwrite(full, data)
            with zipfile.ZipFile(full) as archive:
                managed.verify_archive(archive, umbrella=True, network=True, youtube=True)
            delta = out / f'BlackLanturn-{edition}-Update-1.1.62-to-1.1.63.zip'
            change = component_update.build(base_path, full, delta)
            require(change['base'] == base_id, 'Component package base differs')
            report[label] = {'edition': label, 'baseline_sha256': pin, 'full': prior.asset(full),
                             'components': dict(prior.asset(delta), base=base_id),
                             'changed_files': sorted(changed | {MARKER, NOTICES})}
            print(edition, '1.1.63 built', flush=True)
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
