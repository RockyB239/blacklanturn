"""Verified BlackLanturn managed payloads and Kodi 21 per-addon update protection.

Normal managed-addon updates are supplied by reviewed BlackLanturn build releases.
Never copy an old patch over an unknown newer managed implementation.
"""
import importlib.util
import hashlib
import json
from pathlib import Path
import sqlite3
import xml.etree.ElementTree as E

# These modules are also loaded directly by the offline builder/tests, without
# Kodi's resources package on sys.path. Keep shared path validation standalone.
_path_spec = importlib.util.spec_from_file_location('_blacklanturn_archive_paths', Path(__file__).with_name('archive_paths.py'))
_archive_paths = importlib.util.module_from_spec(_path_spec)
_path_spec.loader.exec_module(_archive_paths)
_version_spec = importlib.util.spec_from_file_location('_blacklanturn_managed_versions', Path(__file__).with_name('managed_versions.py'))
_versions = importlib.util.module_from_spec(_version_spec)
_version_spec.loader.exec_module(_versions)

def _digest(addon, name, raw):
    if name == 'addon.xml':
        raw = _versions.normalize_metadata(addon, raw)
    return _versions.source_digest(addon, name, raw)


HELPER = 'plugin.video.themoviedb.helper'
PREFIX = 'addons/' + HELPER + '/'
UMBRELLA = 'plugin.video.umbrella'
NETWORK = 'script.module.jurialmunkey'
YOUTUBE = 'plugin.video.youtube'
USER_DISABLED_AUTO_UPDATE = 1  # Kodi 21 AddonInfo.h AddonUpdateRule

class ProtectionError(Exception):
    pass

def _umbrella_manifest():
    return json.loads((Path(__file__).parents[1] / 'managed-umbrella.json').read_text())

def verify_archive(archive, umbrella=False, network=False, youtube=False):
    """Verify Helper and selected managed dependencies against reviewed manifests."""
    try:
        _archive_paths.validate(archive)
    except _archive_paths.PathError as exc:
        raise ProtectionError(str(exc)) from exc
    try:
        _versions.verify_archive_adapters(archive)
    except (OSError, ValueError) as exc:
        raise ProtectionError(str(exc)) from exc
    expected = json.loads((Path(__file__).parents[1] / 'managed-helper.json').read_text())['files']
    actual = {n[len(PREFIX):]: _digest(HELPER, n[len(PREFIX):], archive.read(n))
              for n in archive.namelist() if n.startswith(PREFIX) and not n.endswith('/')}
    if actual != expected:
        raise ProtectionError('The Helper package has not passed BlackLanturn compatibility checks. Update BlackLanturn Installer and retry. Your current build has been kept.')
    if umbrella:
        prefix = 'addons/' + UMBRELLA + '/'
        expected = _umbrella_manifest()['files']
        actual = {n[len(prefix):]: _digest(UMBRELLA, n[len(prefix):], archive.read(n))
                  for n in archive.namelist() if n.startswith(prefix) and not n.endswith('/')}
        if actual != expected:
            raise ProtectionError('The Umbrella package has not passed BlackLanturn compatibility checks. Update BlackLanturn Installer and retry. Your current build has been kept.')
    if network:
        prefix = 'addons/' + NETWORK + '/'
        expected = json.loads((Path(__file__).parents[1] / 'managed-network.json').read_text())['files']
        actual = {n[len(prefix):]: _digest(NETWORK, n[len(prefix):], archive.read(n))
                  for n in archive.namelist() if n.startswith(prefix) and not n.endswith('/')}
        if actual != expected:
            raise ProtectionError('The shared network package has not passed BlackLanturn compatibility checks. Update BlackLanturn Installer and retry. Your current build has been kept.')
    if youtube:
        prefix = 'addons/' + YOUTUBE + '/'
        actual = {n[len(prefix):]: _digest(YOUTUBE, n[len(prefix):], archive.read(n))
                  for n in archive.namelist() if n.startswith(prefix) and not n.endswith('/')}
        if not any(actual == variant['files'] for variant in _youtube_manifest()['variants'].values()):
            raise ProtectionError('The YouTube package has not passed BlackLanturn compatibility checks. Update BlackLanturn Installer and retry. Your current build has been kept.')
    return HELPER

def _source_files(addon, message):
    if addon.is_symlink() or addon.parent.is_symlink() or not addon.is_dir():
        raise ProtectionError(message)
    try:
        _versions.verify_installed_adapters(addon)
    except (OSError, ValueError) as exc:
        raise ProtectionError(message) from exc
    actual = {}
    total = entries = 0
    for path in addon.rglob('*'):
        entries += 1
        if entries > 8192 or path.is_symlink():
            raise ProtectionError(message)
        relative = path.relative_to(addon)
        if '__pycache__' in relative.parts or path.suffix in ('.pyc', '.pyo') or path.name == '.DS_Store':
            continue
        if not path.is_file():
            continue
        total += path.stat().st_size
        if len(actual) >= 4096 or total > 32 * 1024 * 1024:
            raise ProtectionError(message)
        actual[relative.as_posix()] = _digest(addon.name, relative.as_posix(), path.read_bytes())
    return actual

def _verify_installed_helper(home):
    addon = Path(home) / 'addons' / HELPER
    if not addon.exists() and not addon.is_symlink():
        return
    message = 'Installed Helper has unreviewed source or version. Your current build has been kept; update compatibility support before installing.'
    try:
        actual = _source_files(addon, message)
        version = _versions.upstream_version(HELPER, (addon / 'addon.xml').read_bytes())
        manifest = json.loads((Path(__file__).parents[1] / 'managed-helper.json').read_text())
        if _tree_digest(actual) not in manifest.get('installed_tree_sha256', {}).get(version, ()):
            raise ProtectionError(message)
    except (OSError, ValueError, KeyError, E.ParseError) as exc:
        raise ProtectionError(message) from exc


def verify_installed(home, network=False, youtube=False):
    """Reject unknown installed managed code before cleanup or native setup.

    Only reviewed complete trees and explicit player variants are accepted.
    Runtime bytecode is excluded; foreign files, links and oversized trees fail.
    """
    _verify_installed_helper(home)
    if youtube:
        _verify_installed_youtube(home)
    if network:
        _verify_installed_network(home)
    addon = Path(home) / 'addons' / UMBRELLA
    if not addon.exists() and not addon.is_symlink():
        return None
    message = 'Installed Umbrella has unreviewed source or version. Your current build has been kept; update compatibility support before installing.'
    try:
        actual = _source_files(addon, message)
        version = _versions.upstream_version(UMBRELLA, (addon / 'addon.xml').read_bytes())
        manifest = _umbrella_manifest()
        expected = (manifest['files'] if version == manifest['version']
                    else manifest.get('legacy_files', {}).get(version))
        player = 'resources/lib/modules/player.py'
        if 'installed_tree_sha256' in manifest:
            # Entire reviewed trees, not interchangeable per-file patch sets.
            digest = hashlib.sha256(json.dumps(actual, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            if digest not in manifest['installed_tree_sha256'].get(version, ()):
                raise ProtectionError(message)
        elif (not expected or actual.get(player) not in manifest['installed_player_hashes'].get(version, ())
                or {k:v for k,v in actual.items() if k != player} != {k:v for k,v in expected.items() if k != player}):
            raise ProtectionError(message)
    except (OSError, ValueError, KeyError, E.ParseError) as exc:
        raise ProtectionError(message) from exc
    return UMBRELLA

def _youtube_manifest():
    return json.loads((Path(__file__).parents[1] / 'managed-youtube.json').read_text())

def _tree_digest(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def _verify_installed_youtube(home):
    addon = Path(home) / 'addons' / YOUTUBE
    if not addon.exists() and not addon.is_symlink():
        return
    message = 'Installed YouTube has unreviewed source or version. Your current build has been kept; update compatibility support before installing.'
    try:
        if _tree_digest(_source_files(addon, message)) not in _youtube_manifest()['installed_tree_sha256']:
            raise ProtectionError(message)
    except (OSError, ValueError, KeyError) as exc:
        raise ProtectionError(message) from exc

def _verify_installed_network(home):
    addon = Path(home) / 'addons' / NETWORK
    if not addon.exists() and not addon.is_symlink():
        return
    message = 'Installed shared network dependency has unreviewed source or version. Your current build has been kept; update compatibility support before installing.'
    try:
        manifest = json.loads((Path(__file__).parents[1] / 'managed-network.json').read_text())
        actual = _source_files(addon, message)
        expected = manifest['files']
        target = 'resources/modules/jurialmunkey/reqapi.py'
        if (actual.get(target) not in manifest['installed_request_hashes']
                or {k:v for k,v in actual.items() if k != target} != {k:v for k,v in expected.items() if k != target}):
            raise ProtectionError(message)
    except (OSError, ValueError, KeyError) as exc:
        raise ProtectionError(message) from exc

def verify_kept(home, addon_ids, network=False, youtube=False, metadata_protected=False):
    """Whitelist may retain managed source only when it already matches target."""
    managed = [(HELPER, 'TMDb Helper', 'managed-helper.json'),
               (UMBRELLA, 'Umbrella', 'managed-umbrella.json')]
    if network:
        managed.append((NETWORK, 'Shared network dependency', 'managed-network.json'))
    if youtube:
        managed.append((YOUTUBE, 'YouTube', 'managed-youtube.json'))
    for addon, label, filename in managed:
        if addon not in addon_ids:
            continue
        message = (label + " is in your whitelist but does not match this build. "
                   "In Save Data, open Edit My Whitelist and remove it, or turn off Keep My 'WhiteList', then retry. "
                   "Selected accounts and supported playback preferences can still be preserved. Your current build has been kept.")
        try:
            manifest = json.loads((Path(__file__).parents[1] / filename).read_text())
            if metadata_protected:
                raw = (Path(home) / 'addons' / addon / 'addon.xml').read_bytes()
                if _versions.normalize_metadata(addon, raw) == raw:
                    raise ProtectionError(message)
            candidates = ([v['files'] for v in manifest['variants'].values()] if addon == YOUTUBE else [manifest['files']])
            if _source_files(Path(home) / 'addons' / addon, message) not in candidates:
                raise ProtectionError(message)
        except (OSError, ValueError, KeyError) as exc:
            raise ProtectionError(message) from exc

def protect(db_path, umbrella=False, network=False, youtube=False):
    """Use the existing registry, retaining all unrelated and existing rules.

Caller refreshes Kodi's in-memory rules with UpdateLocalAddons before cleanup
and again after extraction. Never create a replacement addon registry.
"""
    path = Path(db_path)
    if not path.is_file():
        raise ProtectionError('Kodi addon registry is unavailable. Your current build has been kept.')
    connection = None
    try:
        connection = sqlite3.connect(str(path), timeout=10)
        with connection:
            connection.execute('BEGIN IMMEDIATE')
            columns = [r[1] for r in connection.execute('PRAGMA table_info(update_rules)')]
            if columns != ['id', 'addonID', 'updateRule']:
                raise ProtectionError('Kodi update protection is unsupported. Your current build has been kept.')
            managed = [HELPER]
            if umbrella:
                managed.append(UMBRELLA)
            if network:
                managed.append(NETWORK)
            if youtube:
                managed.append(YOUTUBE)
            for addon in managed:
                connection.execute('INSERT INTO update_rules (addonID,updateRule) SELECT ?,? WHERE NOT EXISTS (SELECT 1 FROM update_rules WHERE addonID=? AND updateRule=?)',
                                   (addon, USER_DISABLED_AUTO_UPDATE, addon, USER_DISABLED_AUTO_UPDATE))
                if not connection.execute('SELECT 1 FROM update_rules WHERE addonID=? AND updateRule=?',(addon, USER_DISABLED_AUTO_UPDATE)).fetchone():
                    raise ProtectionError('Addon update protection could not be verified.')
    except sqlite3.Error as exc:
        raise ProtectionError('Managed add-on update protection could not be saved. Please restart Kodi and retry.') from exc
    finally:
        if connection is not None:
            connection.close()
