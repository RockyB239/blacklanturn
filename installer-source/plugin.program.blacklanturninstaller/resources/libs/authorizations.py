"""Preserve selected account credentials, without copying addon preferences or caches.

Explicit keys follow the settings schemas shipped in BlackLanturn. Never infer a
credential from a substring: unrelated Trakt/cache/quality options stay clean.
"""
import json
import os
from pathlib import Path
import xml.etree.ElementTree as E

MAX_BYTES = 4 * 1024 * 1024
class AuthorizationError(Exception):
    pass

KEYS = {
 'plugin.video.umbrella': {
  'trakt': 'trakt.isauthed traktuserkey.customenabled trakt.clientid trakt.clientsecret trakt.user.token trakt.authed.clientid trakt.user.name trakt.token.expires trakt.refreshtoken',
  'debrid': 'alldebrid.enable alldebridtoken alldebridusername premiumize.enable premiumizetoken premiumizeusername realdebrid.enable realdebridtoken realdebridusername realdebrid.clientid realdebridrefresh realdebridsecret torboxtoken torbox.username torbox.enable offcloudtoken offcloud.username offcloud.enable',
  'login': 'simkltoken simklusername mdblist.token mdblist.refresh.token custom.user.token custom.token.expires custom.refreshtoken custom.isauthed custom.clientid custom.clientsecret custom.user.name floppy.token floppy.user.name floppy.isauthed scrob.accesstoken scrob.refreshtoken scrob.tokenexpiry scrob.isauthed scrob.apikey punchplay.username punchplay.accesstoken punchplay.refreshtoken punchplay.tokenexpiry punchplay.isauthed plexsharetoken plex.client_id plexshare.accessToken easynews.user easynews.password filepursuittoken gdrivetoken fanart_tv.api_key tmdb.apikey tmdbusername tmdbpassword tmdb.sessionid tmdb.v4.readtoken tmdb.v4.accesstoken tmdb.v4.accountid opensubsusername opensubspassword opensubstoken'},
 'plugin.video.themoviedb.helper': {
  'trakt': 'trakt_token trakt_token_access trakt.token trakt.management',
  'login': 'tmdb_user_token tmdb_user_token_access tvdb_token tvdb_token_access omdb_apikey omdb_apikey_access mdblist_apikey mdblist_apikey_access ratingposterdb_apikey gemini_apikey fanarttv_clientkey fanarttv_clientkey_access tmdb_apikey'},
 'script.trakt': {'trakt': 'authorization user'},
 'plugin.video.youtube': {'login': 'youtube.api.enable youtube.api.key youtube.api.id youtube.api.secret'},
 'script.module.resolveurl': {'debrid': 'AllDebridResolver_token AllDebridResolver_login AllDebridResolver_enabled PremiumizeMeResolver_token PremiumizeMeResolver_enabled RealDebridResolver_token RealDebridResolver_refresh RealDebridResolver_client_id RealDebridResolver_client_secret RealDebridResolver_login RealDebridResolver_enabled TorBoxResolver_apikey TorBoxResolver_enabled DebridLinkResolver_token DebridLinkResolver_refresh DebridLinkResolver_client_id DebridLinkResolver_enabled OffCloudResolver_apikey OffCloudResolver_user OffCloudResolver_enabled'}
}
FILES = {'addon_data/plugin.video.youtube/'+n for n in ('access_manager.json','api_keys.json')}

def _read(path):
    if path.is_symlink() or path.stat().st_size > MAX_BYTES:
        raise AuthorizationError('Account data could not be read safely. Your current build has been kept.')
    return path.read_text(encoding='utf-8')

def _allowed(aid, categories):
    return {k for category, keys in KEYS.get(aid, {}).items() if category in categories for k in keys.split()}

def capture(home, addon_ids, categories):
    snapshot = {'schema': 1, 'addon_ids': sorted(set(addon_ids)), 'categories': sorted(categories), 'settings': {}, 'files': {}}
    try:
        profile = Path(home) / 'userdata'
        for aid in sorted(set(addon_ids) & set(KEYS)):
            allowed = _allowed(aid, categories)
            path = profile / 'addon_data' / aid / 'settings.xml'
            if allowed and path.exists():
                root = E.fromstring(_read(path))
                values = {e.get('id'): e.text if e.text is not None else e.get('value', '') for e in root if e.get('id') in allowed}
                if values:
                    snapshot['settings'][aid] = values
        if 'login' in categories and 'plugin.video.youtube' in addon_ids:
            for name in sorted(FILES):
                path = profile / name
                if path.exists():
                    raw = _read(path)
                    if not isinstance(json.loads(raw), dict):
                        raise ValueError('Invalid account JSON')
                    snapshot['files'][name] = raw
        if len(json.dumps(snapshot).encode('utf-8')) > MAX_BYTES:
            raise ValueError('Account snapshot too large')
        return snapshot
    except (OSError, ValueError, E.ParseError) as exc:
        raise AuthorizationError('Account data could not be preserved. Your current build has been kept.') from exc

def save(path, snapshot):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.pending')
    try:
        with temp.open('w', encoding='utf-8') as stream:
            os.chmod(temp, 0o600)
            json.dump(snapshot, stream)
        temp.replace(path)
        if load(path) != snapshot:
            raise ValueError('Account snapshot verification failed')
    except (OSError, ValueError) as exc:
        raise AuthorizationError('Account backup failed. Your current build has been kept.') from exc

def load(path):
    try:
        data = json.loads(_read(Path(path)))
        if not isinstance(data, dict) or data.get('schema') != 1:
            raise ValueError('Invalid account snapshot')
        return data
    except (OSError, ValueError) as exc:
        raise AuthorizationError('Account backup is unreadable. Reinstall has stopped.') from exc

def restore(home, snapshot, addon_ids):
    try:
        _validate(snapshot, addon_ids)
        profile = Path(home) / 'userdata'
        for aid, values in snapshot['settings'].items():
            path = profile / 'addon_data' / aid / 'settings.xml'
            root = E.fromstring(_read(path)) if path.exists() else E.Element('settings', version='2')
            for key, value in sorted(values.items()):
                entry = next((e for e in root if e.get('id') == key), None)
                if entry is None:
                    entry = E.SubElement(root, 'setting', id=key)
                entry.attrib.pop('default', None)
                entry.attrib.pop('value', None)
                entry.text = value
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_suffix('.pending')
            E.ElementTree(root).write(temp, encoding='utf-8', xml_declaration=True)
            os.chmod(temp, 0o600)
            temp.replace(path)
            actual = {e.get('id'): e.text or '' for e in E.fromstring(_read(path))}
            if any(actual.get(k) != v for k, v in values.items()):
                raise ValueError('Account verification failed')
        for name, raw in snapshot['files'].items():
            path = profile / name
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_suffix('.pending')
            temp.write_text(raw, encoding='utf-8')
            os.chmod(temp, 0o600)
            temp.replace(path)
            if _read(path) != raw:
                raise ValueError('Account file verification failed')
    except (OSError, ValueError, TypeError, E.ParseError) as exc:
        raise AuthorizationError('Account restoration needs attention. Keep the account backup and reinstall this build.') from exc


def prepare(home, addon_ids, categories, pending):
    """Reuse the original account snapshot after any interrupted installation."""
    if Path(pending).exists():
        snapshot = load(pending)
        if snapshot.get('addon_ids') != sorted(set(addon_ids)) or snapshot.get('categories') != sorted(categories):
            raise AuthorizationError('An unfinished account recovery belongs to another install selection. Keep the account backup and finish that installation first.')
        try:
            _validate(snapshot, addon_ids)
        except (ValueError, TypeError, AttributeError) as exc:
            raise AuthorizationError('The pending account backup is invalid. Your current build has been kept.') from exc
        return snapshot
    snapshot = capture(home, addon_ids, categories)
    save(pending, snapshot)
    return snapshot


def commit(pending, last_success):
    """Retain a private recovery copy, but allow the next install to capture fresh accounts."""
    try:
        Path(pending).replace(Path(last_success))
    except OSError as exc:
        raise AuthorizationError('Account recovery could not be finalized. Keep the pending backup and retry.') from exc


def _validate(snapshot, addon_ids):
    if snapshot.get('schema') != 1 or not isinstance(snapshot.get('settings'), dict) or not isinstance(snapshot.get('files'), dict):
        raise ValueError('Invalid account snapshot')
    # Validate every path/key before the first write.
    for aid, values in snapshot['settings'].items():
        if aid not in addon_ids or aid not in KEYS or not isinstance(values, dict) or not set(values) <= _allowed(aid, {'trakt', 'debrid', 'login'}) or not all(isinstance(v, str) for v in values.values()):
            raise ValueError('Unexpected account settings')
    for name, raw in snapshot['files'].items():
        if name not in FILES or 'plugin.video.youtube' not in addon_ids or not isinstance(raw, str) or not isinstance(json.loads(raw), dict):
            raise ValueError('Unexpected account file')
