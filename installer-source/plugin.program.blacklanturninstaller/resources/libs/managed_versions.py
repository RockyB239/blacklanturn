"""Kodi-native version epochs for exact reviewed managed add-on metadata.

No runtime repatching: epoch-zero upstream packages remain ordinary upgrades
for ordinary addons, but cannot replace these epoch-one managed variants.
Umbrella's two exact source adapters keep its internal migrations numeric.
"""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as E


@lru_cache(maxsize=1)
def policy():
    return json.loads((Path(__file__).parents[1] / 'managed-versions.json').read_text())


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _replace(raw, old, new):
    token = ('version="' + old + '"').encode()
    if raw.count(token) != 1:
        raise ValueError('Managed metadata version is ambiguous')
    return raw.replace(token, ('version="' + new + '"').encode(), 1)


def normalize_metadata(addon_id, raw):
    """Normalize only an exact reviewed metadata hash, never arbitrary XML."""
    for variant in policy()['addons'].get(addon_id, ()):
        if _sha(raw) == variant['managed_sha256']:
            original = _replace(raw, variant['managed_version'], variant['upstream_version'])
            if _sha(original) != variant['upstream_sha256']:
                raise ValueError('Managed metadata provenance differs')
            return original
    return raw


def _adapter_variants(variant):
    return (variant, *variant.get('legacy_variants', ()))


def _adapter_for_metadata(data, key, variant):
    addon_id = key.split('/', 1)[0]
    metadata = data.get('addons/' + addon_id + '/addon.xml')
    if metadata is None:
        raise ValueError('Missing managed source adapter metadata: ' + addon_id)
    reviewed_metadata = {v[field] for v in policy()['addons'].get(addon_id, ())
                         for field in ('upstream_sha256', 'managed_sha256')}
    if _sha(metadata) not in reviewed_metadata:
        raise ValueError('Unreviewed managed source adapter metadata: ' + addon_id)
    try:
        version = upstream_version(addon_id, metadata)
    except E.ParseError as exc:
        raise ValueError('Invalid managed source adapter metadata') from exc
    for reviewed in _adapter_variants(variant):
        if reviewed.get('upstream_version') == version:
            return reviewed
    raise ValueError('Unreviewed managed source adapter version: ' + addon_id)


def source_digest(addon_id, name, raw):
    """Validate the new overlay independently while retaining historical gates."""
    digest = _sha(raw)
    variant = policy().get('source_adapters', {}).get(addon_id + '/' + name)
    for reviewed in _adapter_variants(variant) if variant else ():
        if digest == reviewed['managed_sha256']:
            return reviewed['upstream_sha256']
    return digest


def apply_source_adapters(data, candidates):
    changes = {}
    for key, variant in policy()['source_adapters'].items():
        variant = _adapter_for_metadata(data, key, variant)
        target = 'addons/' + key
        raw = data.get(target)
        candidate = candidates.get(key)
        if (raw is None or candidate is None or _sha(raw) not in (variant['upstream_sha256'], variant['managed_sha256'])
                or _sha(candidate) != variant['managed_sha256']):
            raise ValueError('Unreviewed managed version source adapter: ' + key)
        changes[target] = candidate
    data.update(changes)


def verify_source_adapters(data, addon_id=None):
    for key, variant in policy()['source_adapters'].items():
        if addon_id is not None and key.split('/', 1)[0] != addon_id:
            continue
        variant = _adapter_for_metadata(data, key, variant)
        raw = data.get('addons/' + key)
        if raw is None or _sha(raw) != variant['managed_sha256']:
            raise ValueError('The managed version source adapter is missing or unreviewed: ' + key)


def verify_adapter_sets(data):
    """A coupled adapter pair is atomic even with legacy numeric metadata."""
    addons = {key.split('/', 1)[0] for key in policy()['source_adapters']}
    for addon_id in addons:
        metadata = data.get('addons/' + addon_id + '/addon.xml')
        protected = metadata is not None and normalize_metadata(addon_id, metadata) != metadata
        adapted = any(data.get('addons/' + key) is not None
                      and _sha(data['addons/' + key]) in {v['managed_sha256'] for v in _adapter_variants(variant)}
                      for key, variant in policy()['source_adapters'].items() if key.split('/', 1)[0] == addon_id)
        if protected or adapted:
            verify_source_adapters(data, addon_id)


def verify_installed_adapters(addon):
    metadata = (addon / 'addon.xml').read_bytes()
    data = {'addons/' + addon.name + '/addon.xml': metadata}
    for key in policy()['source_adapters']:
        aid, name = key.split('/', 1)
        if aid != addon.name:
            continue
        path = addon / name
        cursor = path
        while cursor != addon:
            if cursor.is_symlink():
                raise ValueError('Managed version adapter is invalid')
            cursor = cursor.parent
        if not path.exists():
            continue
        if path.stat().st_size > 262144:
            raise ValueError('Managed version adapter is invalid')
        data['addons/' + key] = path.read_bytes()
    verify_adapter_sets(data)


def verify_archive_adapters(archive):
    names = set(archive.namelist())
    keys = {'addons/' + key for key in policy()['source_adapters']}
    keys.update('addons/' + key.split('/', 1)[0] + '/addon.xml' for key in policy()['source_adapters'])
    data = {}
    for name in keys & names:
        if archive.getinfo(name).file_size > 262144:
            raise ValueError('Managed version adapter exceeds limit')
        data[name] = archive.read(name)
    verify_adapter_sets(data)


def upstream_version(addon_id, raw):
    normalized = normalize_metadata(addon_id, raw)
    root = E.fromstring(normalized)
    version = root.get('version', '')
    if ':' in version:
        raise ValueError('Unreviewed managed metadata version')
    return version


def verify_metadata(data):
    for addon_id, variants in policy()['addons'].items():
        raw = data.get('addons/' + addon_id + '/addon.xml')
        if raw is None or _sha(raw) not in {v['managed_sha256'] for v in variants}:
            raise ValueError('The managed add-on bulk-update protection is missing or unreviewed: ' + addon_id)


def apply_metadata(data):
    """Preflight every metadata input before changing any package entry."""
    changes = {}
    for addon_id, variants in policy()['addons'].items():
        key = 'addons/' + addon_id + '/addon.xml'
        raw = data.get(key)
        if raw is None:
            raise ValueError('Missing managed addon metadata: ' + addon_id)
        digest = _sha(raw)
        for variant in variants:
            if digest == variant['managed_sha256']:
                changes[key] = raw
                break
            if digest == variant['upstream_sha256']:
                root = E.fromstring(raw)
                if root.get('id') != addon_id or root.get('version') != variant['upstream_version']:
                    raise ValueError('Managed addon identity differs')
                candidate = _replace(raw, variant['upstream_version'], variant['managed_version'])
                if _sha(candidate) != variant['managed_sha256']:
                    raise ValueError('Managed metadata transform differs')
                changes[key] = candidate
                break
        else:
            raise ValueError('Unreviewed managed addon metadata: ' + addon_id)
    data.update(changes)


def verify_archive_metadata(archive):
    data = {}
    for addon_id in policy()["addons"]:
        key = "addons/" + addon_id + "/addon.xml"
        try:
            if archive.getinfo(key).file_size > 262144:
                raise ValueError("Managed metadata exceeds limit")
            data[key] = archive.read(key)
        except KeyError as exc:
            raise ValueError("Missing managed addon metadata") from exc
    verify_metadata(data)
    for key in policy()['source_adapters']:
        name = 'addons/' + key
        try:
            if archive.getinfo(name).file_size > 262144:
                raise ValueError('Managed version adapter exceeds limit')
            data[name] = archive.read(name)
        except KeyError as exc:
            raise ValueError('Missing managed version source adapter') from exc
    verify_source_adapters(data)


def prepare_policy(marker, archive):
    revision = marker.get('managed_update_policy')
    if revision is None:
        return None
    update_policy = marker.get('inplace_update_policy')
    if update_policy not in (None, 'bundled-code-1'):
        raise ValueError('Update BlackLanturn Installer before installing this build.')
    minimum = '1.0.30' if update_policy else policy()['installer_min_version']
    if (revision != policy()['policy'] or marker.get('installer_min_version') != minimum
            or marker.get('youtube_refresh_patch') != 'youtube-freshness-2'):
        raise ValueError('Update BlackLanturn Installer before installing this build.')
    verify_archive_metadata(archive)
    return minimum
