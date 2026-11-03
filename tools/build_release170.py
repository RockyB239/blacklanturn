"""Build local BlackLanturn 1.1.59 artifacts from the exact public 1.1.58 archives."""
import argparse
from functools import lru_cache
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

from build_release165 import file_sha, inventory, load, sha
from build_release import verify_dependency_closure, zipwrite

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / 'controller-source/addon'
INSTALLER_ID = 'plugin.program.blacklanturninstaller'
CONTROLLER_ID = 'script.blacklanturn.preview'
INSTALLER = ROOT / 'installer-source' / INSTALLER_ID
VERSIONS = {'build': '1.1.59', 'controller': '0.1.123', 'installer': '1.0.53'}
BASE_VERSION = '1.1.58'
BASELINES = {
    'general': ('General', '5865e1b9d21fb3ca0bcf840f9bee7d68dae669c84f50924df98960671edd4d65'),
    'apple': ('Apple-TV-Mac', 'f12ca1a42fb87bd22e02eff134b5d2fe3fcd6ecf881cee4b5d3b2641d41c49ff'),
}
MARKER = 'userdata/blacklanturn-build.json'
NOTICES = 'userdata/blacklanturn-releases.json'
PAGES = 'https://rockyb239.github.io/blacklanturn'
RELEASES = 'https://github.com/RockyB239/blacklanturn/releases/download'
OLD_FEED_SHA256 = 'ad306444dd879ee46b1cae53b8b4e083c8be0f9e7c0e46c8ee61a51f72369ce4'
HOSTED_BASELINE_COMMIT = 'a550661740cbc8c407dea95c55d8dd06526ad2b3'
HOSTED_INPUTS = (
    'addons.xml', 'hosted-files/builds.txt', 'hosted-files/builds-v2.txt',
    'hosted-files/releases-v1.json', 'hosted-files/setup-1.1.58.txt', 'repository.blacklanturn.zip',
)
PRIVATE_PREFIXES = (
    'addons/plugin.video.blacklanturn.fights/', 'addons/resource.images.blacklanturn.personal/',
    'addons/script.module.slyguy/', 'addons/slyguy.paramount.plus/', 'userdata/Database/',
    'userdata/profiles/', 'userdata/addon_data/plugin.video.blacklanturn.fights/',
)
CHANGED_CONTROLLER = frozenset({
    'action_panel_model.py', 'addon.xml', 'backend_core.py', 'backend_ui.py', 'coming_up.py',
    'genre_lookahead.py', 'genre_picker.py', 'library_ui.py', 'live_core.py', 'live_review.py',
    'page_ahead.py', 'search_ui.py', 'shelf_tools.py', 'shelf_visits.py', 'title_feedback_ui.py',
    'title_preferences.py', 'update_notes_ui.py', 'watch_tonight.py',
    'resources/skins/Default/1080i/LiveReview.xml',
})
CHANGED_INSTALLER = frozenset({
    'addon.xml', 'resources/libs/cocoscrapers_policy.py', 'resources/libs/helper_providers.py',
    'resources/libs/managed_versions.py',
})
RETRY_MODULES = frozenset('addons/plugin.video.umbrella/resources/lib/modules/' + name
                          for name in ('player.py', 'sources.py', 'source_retry.py'))


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def files_record(files):
    return {name: sha(raw) for name, raw in sorted(files.items())}


@lru_cache(maxsize=1)
def hosted_inputs():
    # Rebuilding after catalog activation still uses the untouched prior feed.
    raw = subprocess.check_output(['git', 'archive', '--format=zip', HOSTED_BASELINE_COMMIT, *HOSTED_INPUTS],
                                  cwd=ROOT)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        return {name: archive.read(name) for name in HOSTED_INPUTS}


def source_inputs():
    controller = inventory(CONTROLLER)
    installer = inventory(INSTALLER)
    for files, aid, version in ((controller, CONTROLLER_ID, VERSIONS['controller']),
                                (installer, INSTALLER_ID, VERSIONS['installer'])):
        addon = ET.fromstring(files['addon.xml'])
        if (addon.get('id'), addon.get('version')) != (aid, version):
            raise ValueError('Unexpected add-on identity ' + aid)
    return controller, installer


def source_record(controller, installer):
    return {'schema': 1, 'versions': VERSIONS, 'controller': files_record(controller),
            'installer': files_record(installer),
            'builder': file_sha(Path(__file__)),
            'packaging_inputs': {
                **files_record(hosted_inputs()),
                **{name: file_sha(ROOT / name) for name in ('tools/build_release.py', 'tools/build_release165.py')},
            }}


def baseline_files(path, edition, pin, components):
    if file_sha(path) != pin:
        raise ValueError('Public baseline SHA-256 mismatch for ' + edition)
    with zipfile.ZipFile(path) as archive:
        components.validate(archive)
        if archive.testzip() is not None:
            raise ValueError('Public baseline CRC mismatch for ' + edition)
        files = {name: archive.read(name) for name in archive.namelist() if not name.endswith('/')}
    marker = json.loads(files[MARKER])
    if (marker.get('edition'), marker.get('build_version'), marker.get('release_id')) != (
            edition, BASE_VERSION, release_id(edition, BASE_VERSION)):
        raise ValueError('Public baseline identity mismatch for ' + edition)
    return files


def release_id(edition, version):
    return f'blacklanturn-{edition}-{version}-r0'


def overlay_tree(data, baseline, addon_id, files, allowed):
    prefix = f'addons/{addon_id}/'
    original = {name[len(prefix):]: raw for name, raw in baseline.items() if name.startswith(prefix)}
    if original.keys() - files.keys():
        raise ValueError('Release would remove baseline add-on files for ' + addon_id)
    changed = {name for name, raw in files.items() if original.get(name) != raw}
    if changed - allowed:
        raise ValueError('Unreviewed files changed for ' + addon_id + ': ' + repr(sorted(changed - allowed)))
    if 'addon.xml' not in changed:
        raise ValueError('Version update missing for ' + addon_id)
    data.update({prefix + name: raw for name, raw in files.items() if name in changed})
    return {prefix + name for name in changed}


def retry_inputs(baselines, receipt, receipt_sha):
    if receipt is None and receipt_sha is None:
        return {}, None
    if receipt is None or receipt_sha is None or file_sha(receipt) != receipt_sha:
        raise ValueError('Playback retry requires the exact approved native receipt')
    proof = json.loads(receipt.read_bytes())
    if proof.get('passed') is not True or proof.get('scope') != 'native-playback-retry':
        raise ValueError('Playback retry native acceptance is absent')
    stage = load('release170_retry', ROOT / 'compatibility/playback-retry170/stage.py')
    overlays = {}
    for label, (edition, _) in BASELINES.items():
        files = {path.as_posix(): raw for path, raw in stage.overlays(baselines / full_name(edition, BASE_VERSION)).items()}
        if files.keys() != RETRY_MODULES or files_record(files) != proof.get('overlay_sha256'):
            raise ValueError('Approved playback retry overlay differs for ' + label)
        overlays[label] = files
    return overlays, receipt_sha


def add_retry_variant(installer, data, managed):
    path = 'resources/managed-umbrella.json'
    manifest = json.loads(installer[path])
    prefix = 'addons/' + managed.UMBRELLA + '/'
    tree = {name[len(prefix):]: managed._digest(managed.UMBRELLA, name[len(prefix):], raw)
            for name, raw in data.items() if name.startswith(prefix)}
    manifest.setdefault('archive_variants', {})['playback-retry-1'] = tree
    manifest['installed_tree_sha256'][manifest['version']] = sorted({
        *manifest['installed_tree_sha256'][manifest['version']], managed._tree_digest(tree)})
    installer[path] = json_bytes(manifest)


def notes_for(retry):
    sections = [
        {'heading': 'Browse your way',
         'bullets': ['Filter a movie shelf by runtime, see titles new since your last visit, or use Pick Three.',
                     'Browse movies and shows by streaming service in your TMDb Helper region.',
                     'Use More like this to help shape recommendations.']},
        {'heading': 'Plan what to watch',
         'bullets': ['Keep a short Watch Tonight queue in My Stuff.']},
        {'heading': 'Keep your setup',
         'bullets': ['Use Update BlackLanturn to preserve settings, sign-ins, history and other installed add-ons.']},
    ]
    if retry:
        sections.insert(2, {'heading': 'Playback recovery',
                            'bullets': ['Automatic Umbrella playback can try another eligible source after a confirmed early failure.']})
    return {'title': 'BlackLanturn Build 1.1.59',
            'summary': 'Shelf filters, Pick Three, streaming-service discovery and the Watch Tonight queue.',
            'sections': sections}


def full_name(edition, version):
    return f'BlackLanturn-{edition}-Kodi21-{version}.zip'


def asset_record(path):
    return {'file': path.name, 'sha256': file_sha(path), 'bytes': path.stat().st_size}


def validated_feed(validator, entries):
    feed = {'schema': 1, 'releases': entries}
    validator.validate_catalog(feed)
    encoded = json_bytes(feed)
    if len(encoded) > validator.MAX_BYTES:
        raise ValueError('Release notice feed exceeds the Kodi reader limit')
    return encoded


def ensure_portable(data):
    for name in data:
        if (name.startswith(PRIVATE_PREFIXES) or Path(name).name in
                ('access_manager.json', 'authorizations.json', 'oauth.json', 'tokens.json')
                or name.endswith(('.so', '.dll', '.dylib'))
                or name.startswith('userdata/') and name.endswith(('.db', '.sqlite', '.sqlite3'))):
            raise ValueError('Private or device-specific file is present: ' + name)


def stage_hosted(out, report, installer, entries, notes, validator):
    hosted = out / 'draft-hosted'
    target = hosted / 'hosted-files'
    target.mkdir(parents=True)
    prior = hosted_inputs()
    metadata = ET.fromstring(prior['addons.xml'])
    existing = metadata.find(f"./addon[@id='{INSTALLER_ID}']")
    if existing is None or existing.get('version') != '1.0.52':
        raise ValueError('Unexpected public repository installer metadata')
    metadata.remove(existing)
    metadata.append(ET.fromstring(installer['addon.xml']))
    raw = ET.tostring(metadata, encoding='utf-8', xml_declaration=True) + b'\n'
    (hosted / 'addons.xml').write_bytes(raw)
    (hosted / 'addons.xml.md5').write_text(hashlib.md5(raw).hexdigest(), encoding='ascii')
    installer_zip = hosted / INSTALLER_ID / report['installer']['file']
    installer_zip.parent.mkdir()
    shutil.copyfile(out / installer_zip.name, installer_zip)
    repository = prior['repository.blacklanturn.zip']
    if sha(repository) != 'b7307d60bbfb507848ece7dc039eb20a0501a16e7d8a5f47a9c176c5aeb576be':
        raise ValueError('Public repository archive differs')
    (hosted / 'repository.blacklanturn.zip').write_bytes(repository)
    history = prior['hosted-files/releases-v1.json']
    if sha(history) != OLD_FEED_SHA256:
        raise ValueError('Previous hosted notices have changed')
    (target / 'releases-v1.json').write_bytes(validated_feed(
        validator, entries + json.loads(history)['releases']))
    (target / 'release-notes-1.1.59.json').write_bytes(json_bytes(notes))
    legacy = prior['hosted-files/builds.txt'].decode('utf-8')
    (target / 'builds.txt').write_text(legacy.replace('1.0.52', VERSIONS['installer']), encoding='utf-8')
    setup = prior['hosted-files/setup-1.1.58.txt'].decode('utf-8')
    (target / 'setup-1.1.59.txt').write_text(
        setup.replace(BASE_VERSION, VERSIONS['build']).replace('1.0.52', VERSIONS['installer']),
        encoding='utf-8')
    blocks = prior['hosted-files/builds-v2.txt'].decode('utf-8').strip().split('\n\n')
    if len(blocks) != 3:
        raise ValueError('Unexpected public build catalog structure')
    blocks[0] = blocks[0].replace('1.0.52', VERSIONS['installer'])
    for index, label in enumerate(BASELINES, 1):
        edition = report[label]
        prefix = f'{RELEASES}/v{VERSIONS["build"]}'
        replacements = {
            'version': VERSIONS['build'], 'url': prefix + '/' + edition['full']['file'],
            'info': f'{PAGES}/hosted-files/setup-1.1.59.txt',
            'description': notes['summary'] + ' Install BlackLanturn Installer 1.0.53 and restart Kodi before updating.',
            'updatebase': edition['components']['base'], 'updateurl': prefix + '/' + edition['components']['file'],
            'updatesha256': edition['components']['sha256'],
        }
        for field, value in replacements.items():
            blocks[index], count = re.subn(rf'^{field}="[^"\n]*"$', f'{field}="{value}"', blocks[index], flags=re.M)
            if count != 1:
                raise ValueError('Build catalog field is missing or duplicated: ' + field)
    (target / 'builds-v2.txt').write_text('\n\n'.join(blocks) + '\n\n', encoding='utf-8')
    return {path.relative_to(hosted).as_posix(): asset_record(path)
            for path in sorted(hosted.rglob('*')) if path.is_file()}


def build(baselines, output, manifest, retry_receipt=None, retry_receipt_sha=None):
    controller, installer = source_inputs()
    source = source_record(controller, installer)
    source_bytes = manifest.read_bytes()
    if source != json.loads(source_bytes):
        raise ValueError('Frozen source manifest differs from the current build inputs')
    if output.exists():
        raise FileExistsError('Use a new candidate output directory')
    sys.path.insert(0, str(INSTALLER))
    components = load('release170_components', INSTALLER / 'resources/libs/component_update.py')
    validator = load('release170_notices', CONTROLLER / 'release_updates.py')
    managed = load('release170_managed', INSTALLER / 'resources/libs/managed_addons.py')
    overlays, retry_sha = retry_inputs(baselines, retry_receipt, retry_receipt_sha)
    notes = notes_for(bool(overlays))
    approved_installer_changes = CHANGED_INSTALLER
    if overlays:
        approved_installer_changes |= {'resources/managed-umbrella.json'}
        # Both pinned editions must have the same exact updated managed tree.
        variants = []
        for label, (edition, pin) in BASELINES.items():
            data = baseline_files(baselines / full_name(edition, BASE_VERSION), label, pin, components)
            variant = dict(installer)
            add_retry_variant(variant, data | overlays[label], managed)
            variants.append(variant)
        if variants[0] != variants[1]:
            raise ValueError('Playback retry managed trees differ across editions')
        installer = variants[0]
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.blacklanturn170-', dir=output.parent) as scratch:
        out = Path(scratch) / 'candidate'
        out.mkdir()
        packaged = out / f'{INSTALLER_ID}-{VERSIONS["installer"]}.zip'
        zipwrite(packaged, {f'{INSTALLER_ID}/{name}': raw for name, raw in installer.items()})
        if overlays:
            # The real verifier loads its exact manifest from disk.
            verifier = Path(scratch) / INSTALLER_ID
            with zipfile.ZipFile(packaged) as archive:
                archive.extractall(verifier.parent)
            managed = load('release170_retry_managed', verifier / 'resources/libs/managed_addons.py')
        report = {'schema': 1, 'state': 'LOCAL_CANDIDATE', 'versions': VERSIONS,
                  'source_manifest_sha256': sha(source_bytes), 'playback_retry_receipt_sha256': retry_sha,
                  'installer': asset_record(packaged)}
        entries = []
        for label, (edition, pin) in BASELINES.items():
            base = baselines / full_name(edition, BASE_VERSION)
            before = baseline_files(base, label, pin, components)
            data = dict(before)
            changed = overlay_tree(data, before, CONTROLLER_ID, controller, CHANGED_CONTROLLER)
            changed |= overlay_tree(data, before, INSTALLER_ID, installer, approved_installer_changes)
            data.update(overlays.get(label, {}))
            changed |= overlays.get(label, {}).keys()
            marker = json.loads(before[MARKER])
            marker.update(build_version=VERSIONS['build'], controller_version=VERSIONS['controller'],
                          installer_min_version=VERSIONS['installer'], browse_patch='shelf-tools-1',
                          release_id=release_id(label, VERSIONS['build']))
            if overlays:
                marker['playback_retry_patch'] = 'confirmed-early-failure-1'
            data[MARKER] = json_bytes(marker)
            history = json.loads(before[NOTICES])['releases']
            for entry in history:
                for name, digest in entry['files'].items():
                    if sha(before[name]) != digest:
                        raise ValueError('Inherited archive release proof differs: ' + name)
            entry = dict(id=marker['release_id'], edition=label, version=VERSIONS['build'],
                         revision=marker['release_revision'], **notes,
                         files={name: sha(data[name]) for name in sorted(changed)})
            entries.append(entry)
            data[NOTICES] = validated_feed(validator, [entry, *history])
            exact_delta = {name for name in data.keys() | before.keys() if data.get(name) != before.get(name)}
            if exact_delta != changed | {MARKER, NOTICES}:
                raise ValueError('Unexpected payload delta: ' + repr(sorted(exact_delta ^ changed)))
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
            print(f'{edition} 1.1.59 ready', flush=True)
        report['draft_hosted'] = stage_hosted(out, report, installer, entries, notes, validator)
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
    parser.add_argument('--retry-receipt', type=Path)
    parser.add_argument('--retry-receipt-sha256')
    args = parser.parse_args()
    if args.freeze:
        if args.manifest or args.baselines or args.output or args.retry_receipt or args.retry_receipt_sha256:
            parser.error('--freeze is a separate source snapshot step')
        args.freeze.parent.mkdir(parents=True, exist_ok=True)
        with args.freeze.open('xb') as stream:
            stream.write(json_bytes(source_record(*source_inputs())))
    elif args.manifest and args.baselines and args.output:
        build(args.baselines, args.output, args.manifest, args.retry_receipt, args.retry_receipt_sha256)
    else:
        parser.error('build requires --manifest, --baselines and --output')


if __name__ == '__main__':
    main()
