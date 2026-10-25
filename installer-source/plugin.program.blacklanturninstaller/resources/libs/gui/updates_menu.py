"""Updates page over the existing build catalog, transaction and curated notices."""
import json
import os
from pathlib import Path
import tempfile
import time

from resources.libs import release_notice_state as releases
from resources.libs import update_notes_state as notices
from resources.libs.common.config import CONFIG
from resources.libs.gui.navigation_model import entry

BUILDS = {'apple': 'BlackLanturn Apple TV & Mac', 'general': 'BlackLanturn General'}
PRESERVE = 'Keep all saved data, accounts, settings, playback history and other add-ons automatically. No Keep choices are needed for an update.'


def _read(path, limit=releases.MAX_BYTES):
    path = Path(path)
    if path.is_symlink() or path.stat().st_size > limit:
        raise ValueError('Invalid update information')
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('Invalid update information')
    return value


def _write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name+'.', dir=str(path.parent))
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _paths(home):
    home = Path(home)
    profile = home/'userdata/addon_data/script.blacklanturn.preview'
    return profile/'release-notices.json', profile/'update-notes.json', profile/'release-catalog-cache.json'


def _status_path(home):
    return Path(home)/'userdata/addon_data/plugin.program.blacklanturninstaller/update-check.json'


def _installed(home):
    marker = _read(Path(home)/'userdata/blacklanturn-build.json', 16384)
    if marker.get('schema') != 3:
        raise ValueError('Unsupported installed build')
    return releases.identity(marker)


def _catalog(home):
    # Use exactly the bundled/catalog-cache sources used by Home release notices.
    entries = {}
    for path in (Path(home)/'userdata/blacklanturn-releases.json', _paths(home)[2]):
        try:
            raw = _read(path, releases.MAX_BYTES+2048)
            if path.name == 'release-catalog-cache.json':
                if raw.get('source') != releases.FEED:
                    continue
                raw = raw['catalog']
            catalog = releases.validate_catalog(raw)
            entries.update((e['id'], e) for e in catalog['releases'])
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return {'schema': 1, 'releases': sorted(entries.values(), key=releases.order)[-30:]}


def _status(home, installed):
    try:
        status = _read(_status_path(home), 4096)
        if (status.get('schema') != 1 or status.get('edition') != installed['edition']
                or type(status.get('checked')) not in (int, float)
                or not 0 < status['checked'] <= 4102444800
                or type(status.get('ok')) is not bool):
            return None
        if status.get('latest') is not None:
            releases.version(status['latest'])
        return status
    except (OSError, ValueError, KeyError, TypeError):
        return None


def check_now(home=None, now=None):
    """Check availability only. Never downloads or applies a build archive."""
    from resources.libs import check
    home = Path(home or CONFIG.HOME)
    now = time.time() if now is None else now
    try:
        installed = _installed(home)
    except (OSError, ValueError, KeyError, TypeError):
        return
    previous = _status(home, installed) or {}
    status = {'schema': 1, 'edition': installed['edition'], 'checked': now,
              'ok': False, 'latest': previous.get('latest'), 'notes_ok': False}
    try:
        latest = check.check_build(BUILDS[installed['edition']], 'version')
        releases.version(latest)
        status.update(ok=True, latest=latest)
    except (OSError, ValueError, KeyError, TypeError):
        pass
    try:
        catalog = releases.fetch_catalog()
        _write(_paths(home)[2], {'source': releases.FEED, 'fetched': now, 'catalog': catalog})
        status['notes_ok'] = True
    except (OSError, ValueError, KeyError, TypeError):
        pass
    _write(_status_path(home), status)
    # Keep Home's notes available after dismissal, without changing acknowledgements.
    refresh_notes(home, now)


def refresh_notes(home=None, now=None):
    """Prepare real saved notes without acknowledging a notice or fetching data."""
    home = Path(home or CONFIG.HOME)
    installed = _installed(home)
    state, legacy, _ = _paths(home)
    catalog = _catalog(home)
    return notices.transact(state, lambda old: releases.refresh(old, installed, catalog, now or time.time(), home),
                            reader=lambda p: releases.read_state(p, legacy), writer=releases.write_state)


def toggle_preference(home=None):
    state, legacy, _ = _paths(home or CONFIG.HOME)
    return notices.transact(state, lambda old: dict(old, enabled=not old['enabled']),
                            reader=lambda p: releases.read_state(p, legacy), writer=releases.write_state)


def rows(home=None):
    home = Path(home or CONFIG.HOME)
    result = []
    def add(label, params=None, description=''):
        result.append(entry(label, params, description, False))
    try:
        installed = _installed(home)
    except (OSError, ValueError, KeyError, TypeError):
        add('No supported BlackLanturn build installed', description='Choose your device edition in Builds before checking for updates.')
        return result
    status = _status(home, installed)
    catalog = _catalog(home)
    same_edition = [e for e in catalog['releases'] if e['edition'] == installed['edition']]
    latest_note = max(same_edition, key=releases.order) if same_edition else None
    latest = status.get('latest') if status else None
    known = latest or (latest_note['version'] if latest_note else None)
    add('Installed: v'+installed['version'], description=BUILDS[installed['edition']])
    add('Latest '+('checked' if status and status['ok'] else 'known')+': '+('v'+known if known else 'Not checked'),
        description='Use Check now to refresh the build catalog for your installed edition.')
    if status and status['ok'] and latest and releases.version(latest) > releases.version(installed['version']):
        add('Update BlackLanturn', {'mode': 'install', 'action': 'update', 'name': BUILDS[installed['edition']]}, PRESERVE)
    elif status and status['ok']:
        add('BlackLanturn is up to date', description=PRESERVE)
    else:
        add('Check now to confirm update availability', description=PRESERVE)
    add('What’s new', {'mode': 'updatenotes'}, latest_note['summary'] if latest_note else 'Read curated BlackLanturn release notes. Notes remain available after dismissal.')
    try:
        state, legacy, _ = _paths(home)
        enabled = releases.read_state(state, legacy)['enabled']
        add('Update notices: '+('ON' if enabled else 'OFF'), {'mode': 'updatespref'},
            'Show curated BlackLanturn release notices on Home. This changes only this notice preference.')
    except (OSError, ValueError, KeyError, TypeError):
        add('Update notice preference unavailable', description='Existing notice history has been kept. Retry after closing other dialogs.')
    add('Check now', {'mode': 'updatescheck'}, 'Check your edition’s build catalog and curated release notes. This does not install anything.')
    if status:
        stamp = time.strftime('%Y-%m-%d %H:%M', time.localtime(status['checked']))
        label = 'Last check: '+stamp+(' — successful' if status['ok'] else ' — failed; retry Check now')
        add(label, description='Release notes '+('refreshed.' if status.get('notes_ok') else 'could not be refreshed; saved notes remain available.'))
    else:
        add('Last check: Not checked here', description='Opening Updates reads saved release information. Check now refreshes it.')
    add('Updates keep your entire setup', description=PRESERVE+' Install or reinstall from Builds uses the Save Data Keep choices.')
    return result


def get_listing():
    from resources.libs.common import directory
    for row in rows():
        directory.add_file(row['label'], row['params'], description=row['description'], themeit=CONFIG.THEME1)
