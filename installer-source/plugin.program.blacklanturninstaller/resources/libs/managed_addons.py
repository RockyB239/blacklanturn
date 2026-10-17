"""Verified BlackLanturn Helper payloads and Kodi 21 per-addon update protection.

Normal Helper updates are supplied by reviewed BlackLanturn build releases.
Never copy an old patch over an unknown newer Helper implementation.
"""
import hashlib
import json
from pathlib import Path
import sqlite3

HELPER = 'plugin.video.themoviedb.helper'
PREFIX = 'addons/' + HELPER + '/'
USER_DISABLED_AUTO_UPDATE = 1  # Kodi 21 AddonInfo.h AddonUpdateRule

class ProtectionError(Exception):
    pass

def verify_archive(archive):
    """Verify the complete Helper tree against the installer's reviewed manifest."""
    expected = json.loads((Path(__file__).parents[1] / 'managed-helper.json').read_text())['files']
    actual = {n[len(PREFIX):]: hashlib.sha256(archive.read(n)).hexdigest()
              for n in archive.namelist() if n.startswith(PREFIX) and not n.endswith('/')}
    if actual != expected:
        raise ProtectionError('The Helper package has not passed BlackLanturn compatibility checks. Update BlackLanturn Installer and retry. Your current build has been kept.')
    return HELPER

def protect(db_path):
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
            connection.execute('INSERT INTO update_rules (addonID,updateRule) SELECT ?,? WHERE NOT EXISTS (SELECT 1 FROM update_rules WHERE addonID=? AND updateRule=?)',
                               (HELPER, USER_DISABLED_AUTO_UPDATE, HELPER, USER_DISABLED_AUTO_UPDATE))
            if not connection.execute('SELECT 1 FROM update_rules WHERE addonID=? AND updateRule=?',(HELPER, USER_DISABLED_AUTO_UPDATE)).fetchone():
                raise ProtectionError('Helper update protection could not be verified.')
    except sqlite3.Error as exc:
        raise ProtectionError('Helper update protection could not be saved. Please restart Kodi and retry.') from exc
    finally:
        if connection is not None:
            connection.close()
