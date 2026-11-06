"""Package BlackLanturn 1.1.65 against the two exact public 1.1.64 builds."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

# Reuse the archive, hashing and release-feed helpers from the prior pipeline.
spec = importlib.util.spec_from_file_location('release186', ROOT / 'compatibility/youtube-notice186/release.py')
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)
previous, prior, require = baseline.previous, baseline.prior, baseline.require

BASE, VERSION = '1.1.64', '1.1.65'
OLD_INSTALLER, INSTALLER_VERSION = '1.0.54', '1.0.55'
CONTROLLER_VERSION = '0.1.128'
INSTALLER = previous.INSTALLER
INSTALLER_NAME = f'{INSTALLER}-{INSTALLER_VERSION}.zip'
HELPER = 'addons/plugin.video.themoviedb.helper/'
HELPER_MEMBER = HELPER + 'resources/tmdbhelper/lib/items/directories/tmdb/lists_discover.py'
HELPER_BEFORE = 'b4c53a8ea4067a208ae77db27bfe00b615dcfba9903a649c516706a3eccc2c2a'
HELPER_AFTER = '69827a8895cc54866e88df763a46ce90ecae20fbfb4158a72627fc09fba755ba'
EDITIONS = {
    'general': ('General', '20315930173ee7ca7779b6596eb7213941ddd0147f92177d4323eab3ea586da8'),
    'apple': ('Apple-TV-Mac', 'dc485f159b691e6413aef54f8b3afb9cc3b773b6efcfb15755c4ed10d61eb6d8'),
}
CONTROLLER_DELTA = {
    'addon.xml', 'live_review.py', 'preview_fallback.py', 'preview_identity.py',
    'resources/skins/Default/1080i/LiveReview.xml', 'row_feedback.py',
}
INSTALLER_DELTA = {'addon.xml', 'resources/managed-helper.json', 'resources/managed-versions.json',
                   'resources/libs/managed_versions.py'}
DOWNLOAD = f'https://github.com/RockyB239/blacklanturn/releases/download/v{VERSION}/'
NOTES = {
    'title': f'BlackLanturn Build {VERSION}',
    'summary': 'Improves trailer matching and fixes empty streaming-service shelves.',
    'sections': [
        {'heading': 'Previews', 'bullets': [
            'Use release years and verified season titles to distinguish similar movies and shows.',
            'Keep credible trailer matches when their titles omit the year.',
        ]},
        {'heading': 'Streaming services', 'bullets': [
            'Skip shelves when the service has no matching titles in your region.',
            'Keep the previous row visible during loading and offer Retry for failed requests.',
        ]},
    ],
}


def addon_delta(before, after, prefix, names):
    staged = {prefix + name: raw for name, raw in after.items()}
    original = {name: raw for name, raw in before.items() if name.startswith(prefix)}
    require(staged.keys() == original.keys(), f'Unexpected file set for {prefix}')
    require({name for name in staged if staged[name] != original[name]} == {prefix + n for n in names},
            f'Unexpected changed files for {prefix}')
    return staged


def stage_hosted(out, report, entries, installer):
    hosted = ROOT / 'hosted-files'
    draft = out / 'draft-hosted'
    target = draft / 'hosted-files'
    target.mkdir(parents=True)
    feed = json.loads((hosted / 'releases-v1.json').read_bytes())['releases']
    require(all(entry['version'] != VERSION for entry in feed), 'Version already in release catalog')
    (target / 'releases-v1.json').write_bytes(prior.validated_feed(previous.validator, entries + feed))
    (target / f'release-notes-{VERSION}.json').write_bytes(prior.encoded(NOTES))
    for src, dst in ((f'setup-{BASE}.txt', f'setup-{VERSION}.txt'), ('builds.txt', 'builds.txt')):
        text = (hosted / src).read_text().replace(OLD_INSTALLER, INSTALLER_VERSION)
        (target / dst).write_text(text.replace(BASE, VERSION) if src != dst else text)
    blocks = (hosted / 'builds-v2.txt').read_text().strip().split('\n\n')
    require(len(blocks) == 3 and f'version="{OLD_INSTALLER}"' in blocks[0], 'Unexpected installer catalog')
    blocks[0] = blocks[0].replace(OLD_INSTALLER, INSTALLER_VERSION)
    for index, label in enumerate(EDITIONS, 1):
        require(f'version="{BASE}"' in blocks[index], 'Unexpected build catalog')
        row = report[label]
        fields = {
            'version': VERSION,
            'url': DOWNLOAD + row['full']['file'],
            'info': previous.PAGES + f'setup-{VERSION}.txt',
            'description': f'{NOTES["summary"]} Requires BlackLanturn Installer {INSTALLER_VERSION}.',
            'updatebase': row['components']['base'],
            'updateurl': DOWNLOAD + row['components']['file'],
            'updatesha256': row['components']['sha256'],
        }
        for key, value in fields.items():
            blocks[index], count = re.subn(rf'^{key}="[^"\n]*"$', lambda _: f'{key}="{value}"',
                                           blocks[index], flags=re.M)
            require(count == 1, 'Unexpected catalog field ' + key)
    (target / 'builds-v2.txt').write_text('\n\n'.join(blocks) + '\n\n')

    old_xml = (ROOT / 'addons.xml').read_bytes()
    pattern = rb'<addon id="plugin.program.blacklanturninstaller"[\s\S]*?</addon>'
    addon_xml = installer['addon.xml'].split(b'\n', 1)[1].strip()
    catalog, count = re.subn(pattern, lambda _: addon_xml, old_xml)
    require(count == 1, 'Unexpected repository installer entry')
    listed = ET.fromstring(catalog).find(f"addon[@id='{INSTALLER}']")
    require(listed is not None and listed.get('version') == INSTALLER_VERSION and addon_xml in catalog,
            'Repository Installer metadata differs')
    (draft / 'addons.xml').write_bytes(catalog)
    (draft / 'addons.xml.md5').write_text(hashlib.md5(catalog).hexdigest())
    old_index = (ROOT / 'index.html').read_text()
    require(old_index.count(f'{INSTALLER}-{OLD_INSTALLER}.zip') == 2, 'Unexpected Installer download link')
    (draft / 'index.html').write_text(old_index.replace(f'{INSTALLER}-{OLD_INSTALLER}.zip', INSTALLER_NAME))
    return {p.relative_to(draft).as_posix(): prior.asset(p) for p in sorted(draft.rglob('*')) if p.is_file()}


def build(baselines, output):
    require(not output.exists(), 'Choose an unused output directory')
    controller = prior.inventory(ROOT / 'controller-source/addon')
    installer = prior.inventory(previous.installer_root)
    require(ET.fromstring(controller['addon.xml']).get('version') == CONTROLLER_VERSION, 'Controller version differs')
    require(ET.fromstring(installer['addon.xml']).get('version') == INSTALLER_VERSION, 'Installer version differs')
    helper = (HERE / 'helper/lists_discover.py').read_bytes()
    require(prior.sha(helper) == HELPER_AFTER, 'Reviewed Helper overlay differs')
    require(prior.file_sha(ROOT / 'repository.blacklanturn.zip') == prior.REPOSITORY_PIN, 'Repository ZIP differs')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.shelves189-', dir=output.parent) as folder:
        out = Path(folder) / 'candidate'
        out.mkdir()
        previous.legacy.zipwrite(out / INSTALLER_NAME, {f'{INSTALLER}/{n}': r for n, r in installer.items()})
        versions = {'build': VERSION, 'controller': CONTROLLER_VERSION, 'installer': INSTALLER_VERSION}
        manifest = {'schema': 1, 'versions': versions,
                    'baselines': {label: pin for label, (_, pin) in EDITIONS.items()},
                    'controller_sha256': prior.record(controller), 'installer_sha256': prior.record(installer),
                    'helper_overlay_sha256': HELPER_AFTER, 'pipeline_sha256': prior.file_sha(Path(__file__))}
        (out / 'source-manifest.json').write_bytes(prior.encoded(manifest))
        report = {'schema': 1, 'versions': versions, 'installer': prior.asset(out / INSTALLER_NAME)}
        entries = []
        for label, (edition, pin) in EDITIONS.items():
            base = baselines / f'BlackLanturn-{edition}-Kodi21-{BASE}.zip'
            require(prior.file_sha(base) == pin, 'Unexpected baseline ' + edition)
            before = previous.read_zip(base)
            data = dict(before)
            data.update(addon_delta(before, controller, previous.PREFIX, CONTROLLER_DELTA))
            data.update(addon_delta(before, installer, f'addons/{INSTALLER}/', INSTALLER_DELTA))
            require(prior.sha(before[HELPER_MEMBER]) == HELPER_BEFORE, 'Original Helper file differs')
            data[HELPER_MEMBER] = helper
            old = data[HELPER + 'addon.xml']
            token = b'version="1:6.19.6+blacklanturn.2"'
            require(old.count(token) == 1, 'Original managed Helper version differs')
            data[HELPER + 'addon.xml'] = old.replace(token, b'version="1:6.19.6+blacklanturn.3"', 1)
            changes = {n for n in data if data[n] != before[n]}
            marker = json.loads(before[previous.MARKER])
            base_id = f'blacklanturn-{label}-{BASE}-r0'
            require(marker['release_id'] == base_id, 'Unexpected baseline marker')
            marker.update(build_version=VERSION, controller_version=CONTROLLER_VERSION,
                          installer_min_version=INSTALLER_VERSION, streaming_shelves_patch='verified-empty-1',
                          release_id=f'blacklanturn-{label}-{VERSION}-r0')
            entry = dict(id=marker['release_id'], edition=label, version=VERSION, revision=0, **NOTES,
                         files={n: prior.sha(data[n]) for n in sorted(changes)})
            entries.append(entry)
            history = json.loads(before[previous.NOTICES])['releases']
            require(history[0]['id'] == base_id, 'Unexpected baseline release proof')
            data[previous.MARKER] = prior.encoded(marker)
            data[previous.NOTICES] = prior.validated_feed(previous.validator, [entry, *history])
            previous.legacy.verify_dependency_closure(data)
            full = out / f'BlackLanturn-{edition}-Kodi21-{VERSION}.zip'
            previous.legacy.zipwrite(full, data)
            with ZipFile(full) as archive:
                previous.managed.verify_archive(archive, umbrella=True, network=True, youtube=True)
            delta = out / f'BlackLanturn-{edition}-Update-{BASE}-to-{VERSION}.zip'
            change = previous.component_update.build(base, full, delta)
            require(change['base'] == base_id, 'Unexpected component base')
            report[label] = {'edition': label, 'baseline_sha256': pin, 'full': prior.asset(full),
                             'components': dict(prior.asset(delta), base=base_id),
                             'changed_files': sorted(changes | {previous.MARKER, previous.NOTICES})}
            print('Built', edition, VERSION, flush=True)
        report['draft_hosted'] = stage_hosted(out, report, entries, installer)
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
