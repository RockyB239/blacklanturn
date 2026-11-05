"""Freeze and build local 1.1.62 artifacts; never publish or touch live profiles."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

VERSIONS = {'build': '1.1.62', 'controller': '0.1.126', 'installer': '1.0.54'}
BASE_VERSION = '1.1.61'
BASELINES = {
    'general': ('General', 'abe0beb95868e07fde1ef276e7e9adb72e79728eb063bcac5849178a9a78c7a4'),
    'apple': ('Apple-TV-Mac', 'e41855a60c24e19299002b593a529d0e6dc91e6ebee73497883bfae9f874e8fc'),
}
CONTROLLER = 'script.blacklanturn.preview'
INSTALLER = 'plugin.program.blacklanturninstaller'
MANAGED = {'plugin.video.themoviedb.helper': 'helper', 'plugin.video.youtube': 'youtube'}
MARKER = 'userdata/blacklanturn-build.json'
NOTICES = 'userdata/blacklanturn-releases.json'
PAGES = 'https://rockyb239.github.io/blacklanturn'
RELEASES = 'https://github.com/RockyB239/blacklanturn/releases/download'
PACKAGING_TOOLS = ('build_release.py', 'verify_release165.py')
HOSTED_INPUTS = ('addons.xml', 'hosted-files/builds.txt', 'hosted-files/builds-v2.txt',
                 'hosted-files/releases-v1.json', 'hosted-files/setup-1.1.61.txt',
                 'repository.blacklanturn.zip', 'index.html')
REPOSITORY_PIN = 'b7307d60bbfb507848ece7dc039eb20a0501a16e7d8a5f47a9c176c5aeb576be'
FEED_TARGET_BYTES = 220 * 1024


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('Linked source is forbidden: ' + str(path))
        if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.pyc', '.pyo') and path.name != '.DS_Store':
            result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def record(files):
    return {name: sha(raw) for name, raw in sorted(files.items())}


def asset(path):
    return {'file': path.name, 'sha256': file_sha(path), 'bytes': path.stat().st_size}


def baseline(path, label):
    edition, pin = BASELINES[label]
    if file_sha(path) != pin:
        raise ValueError('Public 61-r1 baseline hash differs: ' + edition)
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or archive.testzip():
            raise ValueError('Public baseline ZIP integrity differs')
        data = {n: archive.read(n) for n in names if not n.endswith('/')}
    marker = json.loads(data[MARKER])
    if (marker['edition'], marker['build_version'], marker['release_id']) != (
            label, BASE_VERSION, f'blacklanturn-{label}-{BASE_VERSION}-r1'):
        raise ValueError('Public baseline identity differs')
    active = json.loads(data[NOTICES])['releases'][0]
    if active['id'] != marker['release_id'] or any(sha(data[n]) != pin for n, pin in active['files'].items()):
        raise ValueError('Public baseline active source proof differs')
    return data


def read_overlays(items, before, config_root, label=None):
    """Only exact reviewed Helper/YouTube source deltas, no profile mutations."""
    result = {}
    for item in items:
        required = {'target', 'source', 'before_sha256', 'sha256'}
        if not required <= item.keys() or item.keys() - required - {'editions'}:
            raise ValueError('Overlay must name exact source and baseline hashes')
        editions = item.get('editions', list(BASELINES))
        if not isinstance(editions, list) or not editions or len(editions) != len(set(editions)) or set(editions) - BASELINES.keys():
            raise ValueError('Invalid overlay editions')
        if label is not None and label not in editions:
            continue
        name = item['target']
        parts = PurePosixPath(name).parts
        if (len(parts) < 3 or parts[0] != 'addons' or parts[1] not in MANAGED or
                '..' in parts or '\\' in name or name != '/'.join(parts) or parts[-1] == 'addon.xml'):
            raise ValueError('Forbidden overlay path: ' + name)
        if name in result:
            raise ValueError('Duplicate overlay path: ' + name)
        path = config_root / item['source']
        if path.is_symlink():
            raise ValueError('Linked candidate source')
        raw = path.read_bytes()
        if sha(raw) != item['sha256']:
            raise ValueError('Reviewed candidate hash differs: ' + name)
        expected = item['before_sha256']
        if (expected is None and name in before) or (expected is not None and (name not in before or sha(before[name]) != expected)):
            raise ValueError('Reviewed baseline hash differs: ' + name)
        if raw == before.get(name):
            raise ValueError('Overlay has no change: ' + name)
        result[name] = raw
    return result


def next_metadata(aid, raw, policy):
    variants = policy['addons'][aid]
    match = next((v for v in variants if sha(raw) == v['managed_sha256']), None)
    if match is None:
        raise ValueError('Unreviewed managed metadata: ' + aid)
    token = ('version="' + match['managed_version'] + '"').encode()
    if raw.count(token) != 1:
        raise ValueError('Ambiguous managed metadata')
    upstream = raw.replace(token, ('version="' + match['upstream_version'] + '"').encode(), 1)
    if sha(upstream) != match['upstream_sha256']:
        raise ValueError('Managed metadata provenance differs')
    revision = int(match['managed_version'].rsplit('.', 1)[1]) + 1
    version = '1:' + match['upstream_version'] + '+blacklanturn.' + str(revision)
    new = raw.replace(token, ('version="' + version + '"').encode(), 1)
    existing = next((v for v in variants if v['managed_version'] == version), None)
    candidate = dict(match, managed_version=version, managed_sha256=sha(new))
    if existing is not None and existing != candidate:
        raise ValueError('Existing managed revision provenance differs')
    if existing is None:
        variants.insert(0, candidate)
    return new


def write_tree(root, files):
    for name, raw in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)


def update_support(installer, data_by_edition, changed_addons):
    policy_path = 'resources/managed-versions.json'
    policy = json.loads(installer[policy_path])
    for aid in sorted(changed_addons):
        key = 'addons/' + aid + '/addon.xml'
        replacements = {old: next_metadata(aid, old, policy)
                        for old in sorted({data[key] for data in data_by_edition.values()})}
        for data in data_by_edition.values():
            data[key] = replacements[data[key]]
    installer[policy_path] = encoded(policy)
    # Hash exactly the normalized trees accepted by managed_addons._digest.
    metadata_hashes = {v['managed_sha256']: v['upstream_sha256'] for variants in policy['addons'].values() for v in variants}
    adapters = policy.get('source_adapters', {})
    for aid in sorted(changed_addons):
        trees = {}
        for label, data in data_by_edition.items():
            prefix = 'addons/' + aid + '/'
            tree = {n[len(prefix):]: sha(raw) for n, raw in data.items() if n.startswith(prefix)}
            tree['addon.xml'] = metadata_hashes[tree['addon.xml']]
            for key, variant in adapters.items():
                if not key.startswith(aid + '/'):
                    continue
                name = key[len(aid) + 1:]
                for reviewed in (variant, *variant.get('legacy_variants', ())):
                    if tree.get(name) == reviewed['managed_sha256']:
                        tree[name] = reviewed['upstream_sha256']
            trees[label] = tree
        resource = 'resources/managed-' + MANAGED[aid] + '.json'
        manifest = json.loads(installer[resource])
        if aid == 'plugin.video.themoviedb.helper':
            if trees['general'] != trees['apple']:
                raise ValueError('Unexpected edition-specific Helper tree')
            manifest.setdefault('archive_variants', {})['responsiveness179'] = trees['general']
            version = policy['addons'][aid][0]['upstream_version']
            hashes = manifest['installed_tree_sha256'].setdefault(version, [])
            digest = sha(json.dumps(trees['general'], sort_keys=True, separators=(',', ':')).encode())
            if digest not in hashes:
                hashes.append(digest)
        else:
            for label, tree in trees.items():
                manifest['variants']['responsiveness179-' + label] = {'files': tree}
                digest = sha(json.dumps(tree, sort_keys=True, separators=(',', ':')).encode())
                if digest not in manifest['installed_tree_sha256']:
                    manifest['installed_tree_sha256'].append(digest)
        installer[resource] = encoded(manifest)
    target = 'resources/libs/managed_versions.py'
    old = (b"def browse_minimum(marker, minimum):\n"
           b"    browse = marker.get('browse_patch')\n"
           b"    if browse is None:\n"
           b"        return minimum\n"
           b"    if browse == 'shelf-tools-1' and minimum == '1.0.52':\n"
           b"        return '1.0.53'\n"
           b"    raise ValueError('Update BlackLanturn Installer before installing this build.')\n")
    new = old.replace(b"    if browse is None:\n", (
        b"    responsiveness = marker.get('responsiveness_patch')\n"
        b"    if responsiveness is not None:\n"
        b"        if responsiveness != 'preview-services-1' or browse != 'shelf-tools-1' or minimum != '1.0.52':\n"
        b"            raise ValueError('Update BlackLanturn Installer before installing this build.')\n"
        b"        return '1.0.54'\n"
        b"    if browse is None:\n"))
    prior_inline = (b"    responsiveness = marker.get('responsiveness_patch')\n"
                    b"    if responsiveness is not None:\n"
                    b"        if responsiveness != 'preview-services-1' or minimum != '1.0.53':\n"
                    b"            raise ValueError('Update BlackLanturn Installer before installing this build.')\n"
                    b"        minimum = '1.0.54'\n")
    raw = installer[target]
    if prior_inline in raw:
        raw = raw.replace(prior_inline, b'', 1)
    if old in raw:
        raw = raw.replace(old, new, 1)
    elif raw.count(new) != 1:
        raise ValueError('Installer support source changed; review shared minimum gate')
    installer[target] = raw
    return installer


def bump_addon(files, aid, old, new):
    raw = files['addon.xml']
    root = ET.fromstring(raw)
    if root.get('id') == aid and root.get('version') == new:
        return
    token = ('version="' + old + '"').encode()
    if root.get('id') != aid or root.get('version') != old or raw.count(token) != 1:
        raise ValueError('Source version identity changed: ' + aid)
    files['addon.xml'] = raw.replace(token, ('version="' + new + '"').encode(), 1)


def freeze(source, baselines, config_path, output):
    if output.exists():
        raise FileExistsError('Use a new snapshot output directory')
    config = json.loads(config_path.read_bytes())
    if set(config) != {'schema', 'notes', 'overlays', 'native_acceptance_required'} or config['schema'] != 1:
        raise ValueError('Unexpected release configuration')
    if config['native_acceptance_required'] != ['mac', 'fire', 'apple']:
        raise ValueError('Native acceptance must cover all three platforms')
    data = {label: baseline(baselines / full_name(edition, BASE_VERSION), label)
            for label, (edition, _) in BASELINES.items()}
    overlays = {label: read_overlays(config['overlays'], before, config_path.parent, label) for label, before in data.items()}
    changed_addons = {name.split('/')[1] for items in overlays.values() for name in items}
    if changed_addons != MANAGED.keys():
        raise ValueError('The final release must include reviewed Helper and YouTube fixes')
    controller = inventory(source / 'controller-source/addon')
    installer = inventory(source / 'installer-source' / INSTALLER)
    bump_addon(controller, CONTROLLER, '0.1.125', VERSIONS['controller'])
    bump_addon(installer, INSTALLER, '1.0.53', VERSIONS['installer'])
    installer['addon.xml'] = re.sub(rb'<news>.*?</news>', b'<news>1.0.54: Compatibility support for BlackLanturn 1.1.62.</news>',
                                    installer['addon.xml'], flags=re.S)
    for label, items in overlays.items():
        data[label].update(items)
    installer = update_support(installer, data, changed_addons)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.freeze179-', dir=output.parent) as directory:
        staging = Path(directory) / 'snapshot'
        write_tree(staging / 'source/controller-source/addon', controller)
        write_tree(staging / 'source/installer-source' / INSTALLER, installer)
        for label, items in overlays.items():
            # Metadata is generated from exact baseline provenance, then frozen too.
            items.update({'addons/' + aid + '/addon.xml': data[label]['addons/' + aid + '/addon.xml'] for aid in changed_addons})
            write_tree(staging / 'overlays' / label, items)
        for name in HOSTED_INPUTS:
            target = staging / 'source' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, target)
        for name in PACKAGING_TOOLS:
            target = staging / 'source/tools' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / 'tools' / name, target)
        write_tree(staging / 'source/tests', inventory(source / 'tests'))
        write_tree(staging / 'source/controller-source/tests', inventory(source / 'controller-source/tests'))
        write_tree(staging / 'pipeline', {name: Path(__file__).with_name(name).read_bytes()
                                         for name in ('release179.py', 'verify179.py')})
        (staging / 'release-config.json').write_bytes(encoded(config))
        manifest = {'schema': 1, 'versions': VERSIONS,
                    'baseline_sha256': {label: pin for label, (_, pin) in BASELINES.items()},
                    'files': record(inventory(staging)), 'state': 'FROZEN_LOCAL_SOURCE'}
        (staging / 'source-manifest.json').write_bytes(encoded(manifest))
        staging.rename(output)
    return manifest


def full_name(edition, version):
    return f'BlackLanturn-{edition}-Kodi21-{version}.zip'


def verify_snapshot(snapshot):
    manifest = json.loads((snapshot / 'source-manifest.json').read_bytes())
    files = inventory(snapshot)
    files.pop('source-manifest.json')
    if manifest['versions'] != VERSIONS or manifest['files'] != record(files):
        raise ValueError('Frozen snapshot has drifted')
    if (snapshot / 'pipeline/release179.py').read_bytes() != Path(__file__).read_bytes():
        raise ValueError('Invoke the exact frozen pipeline implementation')
    return manifest


def validated_feed(validator, entries):
    # Bound the active notice index, retaining complete edition groups. Full
    # historical records remain in immutable source commits/release archives.
    groups = {}
    for entry in entries:
        groups.setdefault((entry['version'], entry['revision']), []).append(entry)
    retained = list(groups.values())[:10]
    limit = min(FEED_TARGET_BYTES, validator.MAX_BYTES)
    while retained:
        feed = {'schema': 1, 'releases': [entry for group in retained for entry in group]}
        raw = encoded(feed)
        if len(raw) <= limit:
            validator.validate_catalog(feed)
            return raw
        if len(retained) == 1:
            break
        retained.pop()
    raise ValueError('Current release proof exceeds the bounded notice reader limit')


def stage_hosted(snapshot, out, report, entries, validator, notes):
    source = snapshot / 'source'
    hosted = out / 'draft-hosted'
    target = hosted / 'hosted-files'
    target.mkdir(parents=True)
    prior = json.loads((source / 'hosted-files/releases-v1.json').read_bytes())['releases']
    (target / 'releases-v1.json').write_bytes(validated_feed(validator, entries + prior))
    (target / 'release-notes-1.1.62.json').write_bytes(encoded(notes))
    setup = (source / 'hosted-files/setup-1.1.61.txt').read_text()
    (target / 'setup-1.1.62.txt').write_text(setup.replace('1.1.61', '1.1.62').replace('1.0.53', '1.0.54'))
    legacy = (source / 'hosted-files/builds.txt').read_text()
    (target / 'builds.txt').write_text(legacy.replace('1.0.53', '1.0.54'))
    blocks = (source / 'hosted-files/builds-v2.txt').read_text().strip().split('\n\n')
    if len(blocks) != 3:
        raise ValueError('Unexpected catalog structure')
    blocks[0] = blocks[0].replace('1.0.53', '1.0.54')
    for index, label in enumerate(BASELINES, 1):
        row = report[label]
        replacements = {'version': '1.1.62', 'url': f'{RELEASES}/v1.1.62/' + row['full']['file'],
                        'info': f'{PAGES}/hosted-files/setup-1.1.62.txt',
                        'description': notes['summary'] + ' Requires BlackLanturn Installer 1.0.54.',
                        'updatebase': row['components']['base'],
                        'updateurl': f'{RELEASES}/v1.1.62/' + row['components']['file'],
                        'updatesha256': row['components']['sha256']}
        for field, value in replacements.items():
            blocks[index], count = re.subn(rf'^{field}="[^"\n]*"$', lambda _: f'{field}="{value}"', blocks[index], flags=re.M)
            if count != 1:
                raise ValueError('Missing catalog field: ' + field)
    (target / 'builds-v2.txt').write_text('\n\n'.join(blocks) + '\n\n')
    root = ET.parse(source / 'addons.xml').getroot()
    current = next(node for node in root if node.get('id') == INSTALLER)
    position = list(root).index(current)
    root.remove(current)
    root.insert(position, ET.fromstring((snapshot / 'source/installer-source' / INSTALLER / 'addon.xml').read_bytes()))
    metadata = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    (hosted / 'addons.xml').write_bytes(metadata)
    (hosted / 'addons.xml.md5').write_text(hashlib.md5(metadata).hexdigest())
    installer_target = hosted / INSTALLER / report['installer']['file']
    installer_target.parent.mkdir()
    shutil.copyfile(out / report['installer']['file'], installer_target)
    index = (source / 'index.html').read_text()
    index, count = re.subn(r'plugin\.program\.blacklanturninstaller-1\.0\.[0-9]+\.zip',
                           report['installer']['file'], index)
    if count != 2:
        raise ValueError('Repository download page installer link is ambiguous')
    (hosted / 'index.html').write_text(index)
    return {path.relative_to(hosted).as_posix(): asset(path) for path in sorted(hosted.rglob('*')) if path.is_file()}


def build(snapshot, baselines, output):
    manifest = verify_snapshot(snapshot)
    if output.exists():
        raise FileExistsError('Use a new build output directory')
    source = snapshot / 'source'
    installer_root = source / 'installer-source' / INSTALLER
    sys.path.insert(0, str(installer_root))
    legacy = load('release179_legacy', source / 'tools/build_release.py')
    components = load('release179_components', installer_root / 'resources/libs/component_update.py')
    managed = load('release179_managed', installer_root / 'resources/libs/managed_addons.py')
    validator = load('release179_notices', source / 'controller-source/addon/release_updates.py')
    config = json.loads((snapshot / 'release-config.json').read_bytes())
    controller = inventory(source / 'controller-source/addon')
    installer = inventory(installer_root)
    if file_sha(source / 'repository.blacklanturn.zip') != REPOSITORY_PIN:
        raise ValueError('Repository ZIP changed')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.build179-', dir=output.parent) as directory:
        out = Path(directory) / 'candidate'
        out.mkdir()
        installer_zip = out / f'{INSTALLER}-1.0.54.zip'
        legacy.zipwrite(installer_zip, {INSTALLER + '/' + n: raw for n, raw in installer.items()})
        report = {'schema': 1, 'state': 'LOCAL_CANDIDATE', 'versions': VERSIONS,
                  'source_manifest_sha256': file_sha(snapshot / 'source-manifest.json'), 'installer': asset(installer_zip)}
        entries = []
        for label, (edition, pin) in BASELINES.items():
            base = baselines / full_name(edition, BASE_VERSION)
            before = baseline(base, label)
            data = dict(before)
            data.update(inventory(snapshot / 'overlays' / label))
            for aid, files in ((CONTROLLER, controller), (INSTALLER, installer)):
                prefix = 'addons/' + aid + '/'
                original_names = {n[len(prefix):] for n in before if n.startswith(prefix)}
                if original_names - files.keys():
                    raise ValueError('Source removes baseline add-on files: ' + aid)
                data.update({prefix + n: raw for n, raw in files.items()})
            changed = {n for n in data.keys() | before.keys() if data.get(n) != before.get(n)}
            if any(not n.startswith('addons/') for n in changed):
                raise ValueError('Payload source unexpectedly changes profile data')
            marker = json.loads(before[MARKER])
            marker.update(build_version='1.1.62', controller_version='0.1.126', installer_min_version='1.0.54',
                          responsiveness_patch='preview-services-1', release_id=f'blacklanturn-{label}-1.1.62-r0',
                          release_revision=0)
            data[MARKER] = encoded(marker)
            entry = dict(id=marker['release_id'], edition=label, version='1.1.62', revision=0,
                         **config['notes'], files={n: sha(data[n]) for n in sorted(changed)})
            entries.append(entry)
            history = json.loads(before[NOTICES])['releases']
            data[NOTICES] = validated_feed(validator, [entry, *history])
            exact_delta = {n for n in data.keys() | before.keys() if data.get(n) != before.get(n)}
            if exact_delta != changed | {MARKER, NOTICES}:
                raise ValueError('Unexpected payload delta')
            private = ('addons/plugin.video.blacklanturn.fights/', 'addons/resource.images.blacklanturn.personal/',
                       'addons/script.module.slyguy/', 'addons/slyguy.paramount.plus/', 'userdata/Database/', 'userdata/profiles/')
            for name in data:
                if name.startswith(private) or Path(name).name in ('access_manager.json', 'authorizations.json', 'oauth.json', 'tokens.json'):
                    raise ValueError('Private data in public payload: ' + name)
            legacy.verify_dependency_closure(data)
            full = out / full_name(edition, '1.1.62')
            legacy.zipwrite(full, data)
            with zipfile.ZipFile(full) as archive:
                managed.verify_archive(archive, umbrella=True, network=True, youtube=True)
            component = out / f'BlackLanturn-{edition}-Update-1.1.61-to-1.1.62.zip'
            doc = components.build(base, full, component)
            report[label] = {'edition': label, 'baseline_sha256': pin, 'full': asset(full),
                             'components': dict(asset(component), base=doc['base']), 'proof_files': len(changed),
                             'changed_files': sorted(exact_delta), 'unchanged_other_files': len(before) - len(exact_delta & before.keys()),
                             'userdata_unchanged_except_release_metadata': True}
            print(edition + ' 1.1.62 ready', flush=True)
        report['draft_hosted'] = stage_hosted(snapshot, out, report, entries, validator, config['notes'])
        shutil.copyfile(snapshot / 'source-manifest.json', out / 'source-manifest.json')
        (out / 'candidate-packages.json').write_bytes(encoded(report))
        hashes = record(inventory(out))
        (out / 'SHA256SUMS').write_text(''.join(f'{pin}  {name}\n' for name, pin in hashes.items()))
        out.rename(output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    freeze_parser = sub.add_parser('freeze')
    freeze_parser.add_argument('--source', type=Path)
    freeze_parser.add_argument('--config', type=Path, default=Path(__file__).with_name('release-config.json'))
    for name in ('baselines', 'output'):
        freeze_parser.add_argument('--' + name, type=Path, required=True)
    build_parser = sub.add_parser('build')
    for name in ('snapshot', 'baselines', 'output'):
        build_parser.add_argument('--' + name, type=Path, required=True)
    check_parser = sub.add_parser('check-snapshot')
    check_parser.add_argument('--snapshot', type=Path, required=True)
    args = parser.parse_args()
    if args.operation == 'freeze':
        if args.source is None:
            args.source = next((p for p in Path(__file__).resolve().parents
                                if (p / 'controller-source/addon').is_dir()
                                and (p / 'installer-source' / INSTALLER).is_dir()), None)
            if args.source is None:
                parser.error('Could not discover the source root; provide --source')
        freeze(args.source, args.baselines, args.config, args.output)
    elif args.operation == 'build':
        build(args.snapshot, args.baselines, args.output)
    else:
        verify_snapshot(args.snapshot)


if __name__ == '__main__':
    main()
