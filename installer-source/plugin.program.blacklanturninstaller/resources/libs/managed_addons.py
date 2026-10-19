"""Verified BlackLanturn Helper payloads and Kodi 21 per-addon update protection.

Normal Helper updates are supplied by reviewed BlackLanturn build releases.
Never copy an old patch over an unknown newer Helper implementation.
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

HELPER = 'plugin.video.themoviedb.helper'
PREFIX = 'addons/' + HELPER + '/'
UMBRELLA = 'plugin.video.umbrella'
USER_DISABLED_AUTO_UPDATE = 1  # Kodi 21 AddonInfo.h AddonUpdateRule

class ProtectionError(Exception):
    pass

def _umbrella_manifest():
    return json.loads((Path(__file__).parents[1] / 'managed-umbrella.json').read_text())

def verify_archive(archive, umbrella=False):
    """Verify the complete Helper tree against the installer's reviewed manifest."""
    try:
        _archive_paths.validate(archive)
    except _archive_paths.PathError as exc:
        raise ProtectionError(str(exc)) from exc
    expected = json.loads((Path(__file__).parents[1] / 'managed-helper.json').read_text())['files']
    actual = {n[len(PREFIX):]: hashlib.sha256(archive.read(n)).hexdigest()
              for n in archive.namelist() if n.startswith(PREFIX) and not n.endswith('/')}
    if actual != expected:
        raise ProtectionError('The Helper package has not passed BlackLanturn compatibility checks. Update BlackLanturn Installer and retry. Your current build has been kept.')
    if umbrella:
        prefix = 'addons/' + UMBRELLA + '/'
        expected = _umbrella_manifest()['files']
        actual = {n[len(prefix):]: hashlib.sha256(archive.read(n)).hexdigest()
                  for n in archive.namelist() if n.startswith(prefix) and not n.endswith('/')}
        if actual != expected:
            raise ProtectionError('The Umbrella package has not passed BlackLanturn compatibility checks. Update BlackLanturn Installer and retry. Your current build has been kept.')
    return HELPER

def _source_files(addon, message):
    if addon.is_symlink() or addon.parent.is_symlink() or not addon.is_dir():
        raise ProtectionError(message)
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
        actual[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return actual

def verify_installed(home):
    """Reject unknown installed Umbrella code before cleanup or native setup.

    Only reviewed complete trees and explicit player variants are accepted.
    Runtime bytecode is excluded; foreign files, links and oversized trees fail.
    """
    addon = Path(home) / 'addons' / UMBRELLA
    if not addon.exists() and not addon.is_symlink():
        return None
    message = 'Installed Umbrella has unreviewed source or version. Your current build has been kept; update compatibility support before installing.'
    try:
        actual = _source_files(addon, message)
        version = E.fromstring((addon / 'addon.xml').read_bytes()).get('version')
        manifest = _umbrella_manifest()
        expected = (manifest['files'] if version == manifest['version']
                    else manifest.get('legacy_files', {}).get(version))
        player = 'resources/lib/modules/player.py'
        if (not expected or actual.get(player) not in manifest['installed_player_hashes'].get(version, ())
                or {k:v for k,v in actual.items() if k != player} != {k:v for k,v in expected.items() if k != player}):
            raise ProtectionError(message)
    except (OSError, ValueError, KeyError, E.ParseError) as exc:
        raise ProtectionError(message) from exc
    return UMBRELLA

def verify_kept(home, addon_ids):
    """Whitelist may retain managed source only when it already matches target."""
    for addon, label, filename in ((HELPER, 'TMDb Helper', 'managed-helper.json'),
                                   (UMBRELLA, 'Umbrella', 'managed-umbrella.json')):
        if addon not in addon_ids:
            continue
        message = (label + " is in your whitelist but does not match this build. "
                   "In Save Data, open Edit My Whitelist and remove it, or turn off Keep My 'WhiteList', then retry. "
                   "Selected accounts and supported playback preferences can still be preserved. Your current build has been kept.")
        try:
            expected = json.loads((Path(__file__).parents[1] / filename).read_text())['files']
            if _source_files(Path(home) / 'addons' / addon, message) != expected:
                raise ProtectionError(message)
        except (OSError, ValueError, KeyError) as exc:
            raise ProtectionError(message) from exc

def protect(db_path, umbrella=False):
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
            for addon in (HELPER, UMBRELLA) if umbrella else (HELPER,):
                connection.execute('INSERT INTO update_rules (addonID,updateRule) SELECT ?,? WHERE NOT EXISTS (SELECT 1 FROM update_rules WHERE addonID=? AND updateRule=?)',
                                   (addon, USER_DISABLED_AUTO_UPDATE, addon, USER_DISABLED_AUTO_UPDATE))
                if not connection.execute('SELECT 1 FROM update_rules WHERE addonID=? AND updateRule=?',(addon, USER_DISABLED_AUTO_UPDATE)).fetchone():
                    raise ProtectionError('Addon update protection could not be verified.')
    except sqlite3.Error as exc:
        raise ProtectionError('Helper update protection could not be saved. Please restart Kodi and retry.') from exc
    finally:
        if connection is not None:
            connection.close()
