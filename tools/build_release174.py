"""Build BlackLanturn 1.1.61 from the exact public 1.1.60 archives."""
import argparse
from functools import lru_cache
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

from build_release import verify_dependency_closure, zipwrite
from build_release165 import file_sha, inventory, load, sha
from build_release170 import (
    CONTROLLER, CONTROLLER_ID, INSTALLER, INSTALLER_ID, MARKER, NOTICES, PAGES, RELEASES, ROOT,
    asset_record, ensure_portable, files_record, full_name, json_bytes, overlay_tree, release_id,
    validated_feed,
)

VERSIONS = {'build': '1.1.61', 'controller': '0.1.125', 'installer': '1.0.53'}
BASE_VERSION = '1.1.60'
BASELINES = {
    'general': ('General', 'b249c1754a743cd93677916411319abf831cf62e119fd7dfe670b406bb369c14'),
    'apple': ('Apple-TV-Mac', 'c814d03091e36b4f5b834b68b50d538d603304b699747b0931c165cb674683b9'),
}
CONTROLLER_FILES = frozenset({
    'addon.xml', 'live_review.py', 'provider_work.py', 'search_ui.py', 'shelf_tools.py',
    'streaming_cache.py', 'streaming_services.py', 'streaming_services_ui.py', 'streaming_shelves.py',
    'resources/skins/Default/1080i/LiveReview.xml',
    'resources/skins/Default/1080i/StreamingServicesGrid.xml',
})
INSTALLER_ZIP = f'{INSTALLER_ID}-{VERSIONS["installer"]}.zip'
INSTALLER_PIN = 'bd6d26ea6d644633eb451f0c49c3f9b0225826a8cb787be0bda967a11e3d767a'
HOSTED_BASELINE_COMMIT = 'ab112fd5d91352fd8b3a1a124123cae4c7c1d698'
HOSTED_INPUTS = (
    'hosted-files/builds-v2.txt', 'hosted-files/releases-v1.json',
    f'hosted-files/setup-{BASE_VERSION}.txt', f'{INSTALLER_ID}/{INSTALLER_ZIP}',
)
NOTES = {
    'title': 'BlackLanturn Build 1.1.61',
    'summary': 'Browse streaming services in a logo grid, then explore Popular, Recent Releases and genres.',
    'sections': [
        {'heading': 'Browse streaming services',
         'bullets': ['Find pinned and featured services in the streaming-services grid.',
                     'Browse Popular, Recent Releases and genre shelves for a service.',
                     'Lists you open take priority over background streaming refreshes.']},
        {'heading': 'Keep your setup',
         'bullets': ['Use Update BlackLanturn to preserve settings, sign-ins, history and other installed add-ons.']},
    ],
}


@lru_cache(maxsize=1)
def hosted_inputs():
    raw = subprocess.check_output(
        ['git', 'archive', '--format=zip', HOSTED_BASELINE_COMMIT, *HOSTED_INPUTS], cwd=ROOT,
    )
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        return {name: archive.read(name) for name in HOSTED_INPUTS}


def source_inputs():
    controller, installer = inventory(CONTROLLER), inventory(INSTALLER)
    for files, aid, version in ((controller, CONTROLLER_ID, VERSIONS['controller']),
                                (installer, INSTALLER_ID, VERSIONS['installer'])):
        addon = ET.fromstring(files['addon.xml'])
        if (addon.get('id'), addon.get('version')) != (aid, version):
            raise ValueError('Unexpected add-on identity ' + aid)
    return controller, installer


def source_record(controller, installer):
    dependencies = ('tools/build_release.py', 'tools/build_release165.py', 'tools/build_release170.py')
    return {'schema': 1, 'versions': VERSIONS, 'controller': files_record(controller),
            'installer': files_record(installer), 'builder': file_sha(Path(__file__)),
            'packaging_inputs': {**files_record(hosted_inputs()),
                                 **{name: file_sha(ROOT / name) for name in dependencies}}}


def verified_installer(installer):
    raw = hosted_inputs()[f'{INSTALLER_ID}/{INSTALLER_ZIP}']
    if sha(raw) != INSTALLER_PIN:
        raise ValueError('Public Installer SHA-256 differs')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        expected = {f'{INSTALLER_ID}/{name}' for name in installer}
        if len(archive.namelist()) != len(expected) or set(archive.namelist()) != expected or archive.testzip():
            raise ValueError('Public Installer ZIP structure differs')
        if any(archive.read(f'{INSTALLER_ID}/{name}') != data for name, data in installer.items()):
            raise ValueError('Installer source differs from the public ZIP')
    return raw


def baseline_files(path, label, pin, components):
    if file_sha(path) != pin:
        raise ValueError('Public baseline SHA-256 mismatch for ' + label)
    with zipfile.ZipFile(path) as archive:
        components.validate(archive)
        if archive.testzip() is not None:
            raise ValueError('Public baseline CRC mismatch for ' + label)
        files = {name: archive.read(name) for name in archive.namelist() if not name.endswith('/')}
    marker = json.loads(files[MARKER])
    if (marker.get('edition'), marker.get('build_version'), marker.get('release_id')) != (
            label, BASE_VERSION, release_id(label, BASE_VERSION)):
        raise ValueError('Public baseline identity mismatch for ' + label)
    return files


def stage_hosted(out, report, entries, validator):
    prior = hosted_inputs()
    hosted = out / 'draft-hosted'
    target = hosted / 'hosted-files'
    target.mkdir(parents=True)
    history = json.loads(prior['hosted-files/releases-v1.json'])['releases']
    (target / 'releases-v1.json').write_bytes(validated_feed(validator, entries + history))
    version = VERSIONS['build']
    (target / f'release-notes-{version}.json').write_bytes(json_bytes(NOTES))
    setup = prior[f'hosted-files/setup-{BASE_VERSION}.txt'].decode('utf-8')
    (target / f'setup-{version}.txt').write_text(setup.replace(BASE_VERSION, version), encoding='utf-8')
    blocks = prior['hosted-files/builds-v2.txt'].decode('utf-8').strip().split('\n\n')
    if len(blocks) != 1 + len(BASELINES):
        raise ValueError('Unexpected public build catalog structure')
    for index, label in enumerate(BASELINES, 1):
        edition = report[label]
        prefix = f'{RELEASES}/v{version}'
        replacements = {
            'version': version, 'url': prefix + '/' + edition['full']['file'],
            'info': f'{PAGES}/hosted-files/setup-{version}.txt',
            'description': NOTES['summary'] + ' Requires BlackLanturn Installer 1.0.53.',
            'updatebase': edition['components']['base'], 'updateurl': prefix + '/' + edition['components']['file'],
            'updatesha256': edition['components']['sha256'],
        }
        for field, value in replacements.items():
            blocks[index], count = re.subn(
                rf'^{field}="[^"\n]*"$', f'{field}="{value}"', blocks[index], flags=re.M,
            )
            if count != 1:
                raise ValueError('Build catalog field is missing or duplicated: ' + field)
    (target / 'builds-v2.txt').write_text('\n\n'.join(blocks) + '\n\n', encoding='utf-8')
    return {path.relative_to(hosted).as_posix(): asset_record(path) for path in sorted(target.iterdir())}


def build(baselines, output, manifest):
    controller, installer = source_inputs()
    source_bytes = manifest.read_bytes()
    if source_record(controller, installer) != json.loads(source_bytes):
        raise ValueError('Frozen source manifest differs from the current build inputs')
    if output.exists():
        raise FileExistsError('Use a new candidate output directory')
    installer_bytes = verified_installer(installer)
    sys.path.insert(0, str(INSTALLER))
    components = load('release174_components', INSTALLER / 'resources/libs/component_update.py')
    managed = load('release174_managed', INSTALLER / 'resources/libs/managed_addons.py')
    validator = load('release174_notices', CONTROLLER / 'release_updates.py')
    prior_feed = {entry['id']: entry for entry in json.loads(hosted_inputs()['hosted-files/releases-v1.json'])['releases']}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.blacklanturn174-', dir=output.parent) as scratch:
        out = Path(scratch) / 'candidate'
        out.mkdir()
        packaged = out / INSTALLER_ZIP
        packaged.write_bytes(installer_bytes)
        report = {'schema': 1, 'state': 'LOCAL_CANDIDATE', 'versions': VERSIONS,
                  'source_manifest_sha256': sha(source_bytes), 'installer': asset_record(packaged)}
        entries = []
        for label, (edition, pin) in BASELINES.items():
            base = baselines / full_name(edition, BASE_VERSION)
            before = baseline_files(base, label, pin, components)
            expected_installer = {f'addons/{INSTALLER_ID}/{name}': raw for name, raw in installer.items()}
            if {name: raw for name, raw in before.items() if name.startswith(f'addons/{INSTALLER_ID}/')} != expected_installer:
                raise ValueError('Bundled Installer differs from the public ZIP for ' + label)
            data = dict(before)
            changed = overlay_tree(data, before, CONTROLLER_ID, controller, CONTROLLER_FILES)
            if changed != {f'addons/{CONTROLLER_ID}/{name}' for name in CONTROLLER_FILES}:
                raise ValueError('Approved controller delta is incomplete for ' + label)
            marker = json.loads(before[MARKER])
            history = json.loads(before[NOTICES])['releases']
            # Older entries retain the proof of their own release. Only the
            # active baseline proof can be compared to the current archive.
            current = prior_feed[marker['release_id']]
            if history[0] != current or any(sha(before[name]) != digest for name, digest in current['files'].items()):
                raise ValueError('Active baseline proof differs for ' + label)
            marker.update(build_version=VERSIONS['build'], controller_version=VERSIONS['controller'],
                          release_id=release_id(label, VERSIONS['build']))
            data[MARKER] = json_bytes(marker)
            entry = dict(id=marker['release_id'], edition=label, version=VERSIONS['build'],
                         revision=marker['release_revision'], **NOTES,
                         files={name: sha(data[name]) for name in sorted(changed)})
            entries.append(entry)
            data[NOTICES] = validated_feed(validator, [entry, *history])
            exact_delta = {name for name in data.keys() | before.keys() if data.get(name) != before.get(name)}
            if exact_delta != changed | {MARKER, NOTICES}:
                raise ValueError('Unexpected payload delta for ' + label)
            ensure_portable(data)
            verify_dependency_closure(data)
            full = out / full_name(edition, VERSIONS['build'])
            zipwrite(full, data)
            with zipfile.ZipFile(full) as archive:
                managed.verify_archive(archive, umbrella=True, network=True, youtube=True)
            component = out / f'BlackLanturn-{edition}-Update-{BASE_VERSION}-to-{VERSIONS["build"]}.zip'
            component_doc = components.build(base, full, component)
            with zipfile.ZipFile(component) as archive:
                components.validate(archive)
                if archive.testzip() is not None:
                    raise ValueError('Component CRC differs for ' + label)
            report[label] = {'edition': label, 'baseline_sha256': pin, 'full': asset_record(full),
                             'components': dict(asset_record(component), base=component_doc['base']),
                             'changed_files': sorted(exact_delta), 'proof_files': len(entry['files']),
                             'unchanged_other_files': len(before) - len(exact_delta & before.keys())}
            print(f'{edition} {VERSIONS["build"]} ready', flush=True)
        report['draft_hosted'] = stage_hosted(out, report, entries, validator)
        (out / 'source-manifest.json').write_bytes(source_bytes)
        (out / 'candidate-packages.json').write_bytes(json_bytes(report))
        all_files = {path.relative_to(out).as_posix(): file_sha(path) for path in sorted(out.rglob('*')) if path.is_file()}
        (out / 'SHA256SUMS').write_text(''.join(f'{digest}  {name}\n' for name, digest in all_files.items()), encoding='ascii')
        out.rename(output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', type=Path, help='write an explicit manifest before building')
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--baselines', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.freeze:
        if args.manifest or args.baselines or args.output:
            parser.error('--freeze must be used alone')
        with args.freeze.open('xb') as handle:
            handle.write(json_bytes(source_record(*source_inputs())))
        return
    if not (args.manifest and args.baselines and args.output):
        parser.error('--manifest, --baselines and --output are required for a build')
    build(args.baselines, args.output, args.manifest)


if __name__ == '__main__':
    main()
