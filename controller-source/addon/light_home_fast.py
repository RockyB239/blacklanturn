"""Account-scoped display cards for the first two Home rows."""
from hashlib import sha256
from hmac import compare_digest, digest as hmac_digest
import json
import os
from pathlib import Path
import time

CACHE = 'home-card-display.json'
VERSION = 1
MAX_BYTES = 768 * 1024
MAX_AGE = 24 * 3600
HELPER = 'plugin.video.themoviedb.helper'
YOUTUBE = 'plugin.video.youtube'


def _read(path, limit=MAX_BYTES):
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('Home cache is too large')
    return raw


def _schema(helper):
    import xbmcvfs
    root = Path(xbmcvfs.translatePath(helper.getAddonInfo('path')))
    return _read(root/'resources/settings.xml', 1024*1024)


def scope_schema():
    import xbmcaddon
    from public_rows import _helper_setting_ids
    raw = _schema(xbmcaddon.Addon(HELPER))
    return {'hash': sha256(raw).hexdigest(), 'keys': list(_helper_setting_ids(raw))}


def fingerprint(store, schema):
    """Hash current settings and account state without writing credentials."""
    import xbmc
    import xbmcaddon
    from youtube_core import connected_account

    helper = xbmcaddon.Addon(HELPER)
    youtube = xbmcaddon.Addon(YOUTUBE)
    keys = schema['keys']
    if (not isinstance(keys,list) or len(keys)>500 or 'trakt_token' not in keys
            or sha256(_schema(helper)).hexdigest()!=schema['hash']):
        return None
    authorization = helper.getSetting('trakt_token')
    token = json.loads(authorization)
    created, expires = token.get('created_at'), token.get('expires_in')
    if (not all(type(value) in (int,float) and 0<=value<=32503680000 for value in (created,expires))
            or not all(isinstance(token.get(key),str) and token[key] for key in ('access_token','refresh_token'))
            or not created<=time.time()<created+expires):
        return None

    digest = sha256()
    def update(raw):
        if isinstance(raw,str):
            raw = raw.encode()
        digest.update(len(raw).to_bytes(8,'big'))
        digest.update(raw)

    def optional(path, limit):
        try:
            return _read(path,limit)
        except FileNotFoundError:
            return b''

    update(str(store.resolve()))
    update(authorization)
    for addon in (helper,youtube,xbmcaddon.Addon('script.blacklanturn.preview')):
        update(addon.getAddonInfo('version'))
    for key in keys:
        update(key)
        update(authorization if key=='trakt_token' else helper.getSetting(key))
    for key in ('youtube.api.key','youtube.api.id','youtube.api.secret'):
        update(youtube.getSetting(key))
    yt_store = store.parent/YOUTUBE
    account = json.loads(optional(yt_store/'access_manager.json',1024*1024) or b'{}')
    manager = account.get('access_manager',{})
    current, users = manager.get('current_user'),manager.get('users',{})
    if current is not None and type(current) not in (str,int):
        return None
    user = users.get(str(current),users.get(current))
    if user is not None and (not isinstance(user,dict) or not isinstance(user.get('refresh_token',''),str)):
        return None
    update(json.dumps(connected_account(account),separators=(',',':')))
    update(optional(yt_store/'api_keys.json',1024*1024))
    update(_read(store/'rows.json',256*1024))
    for name in ('row-layouts.json','title-preferences.json'):
        update(optional(store/name,256*1024))
    request = {'jsonrpc':'2.0','id':1,'method':'Addons.GetAddons','params':{'properties':['enabled','path']}}
    addons = json.loads(xbmc.executeJSONRPC(json.dumps(request)))['result']['addons']
    relevant = sorted((row['addonid'],row['enabled'],row['path']) for row in addons
                      if row['addonid']==YOUTUBE or row['addonid'].startswith('resource.images.'))
    update(json.dumps(relevant,separators=(',',':')))
    return digest.hexdigest()


def load_cache(store, live_fingerprint, now=None):
    try:
        envelope = json.loads(_read(store/CACHE))
        if envelope['version']!=VERSION:
            return None
        identity = live_fingerprint(envelope['schema'])
        payload = envelope['payload']
        if not identity or not compare_digest(_proof(identity,payload),envelope['proof']):
            return None
        record, rows = json.loads(payload)
        stamp = record['time']
        now = time.time() if now is None else now
        if type(stamp) in (int,float) and 0<=now-stamp<=MAX_AGE and len(record['rows'])==len(rows)==2:
            return record,rows
    except (OSError,ValueError,TypeError,AttributeError,KeyError,RuntimeError,OverflowError):
        pass
    return None


def _proof(identity, payload):
    # The key incorporates the current account credential and is never stored.
    return hmac_digest(identity.encode(),payload.encode(),'sha256').hex()


def save_cache(store, schema, identity, record, rows):
    from tempfile import NamedTemporaryFile
    if not identity:
        return False
    payload = json.dumps([record,rows],separators=(',',':'),ensure_ascii=False)
    encoded = json.dumps({'version':VERSION,'schema':schema,
                          'proof':_proof(identity,payload),'payload':payload},
                         separators=(',',':'),ensure_ascii=False).encode()
    if len(encoded)>MAX_BYTES:
        return False
    scratch = None
    try:
        with NamedTemporaryFile(prefix='home-card-',suffix='.pending',dir=store,delete=False) as stream:
            scratch = Path(stream.name)
            stream.write(encoded)
        os.replace(scratch,store/CACHE)
        return True
    finally:
        if scratch is not None:
            scratch.unlink(missing_ok=True)


class CardCapture:
    """Capture the existing renderer's data without creating GUI objects."""
    def __init__(self,**kwargs):
        self.payload = {'item':kwargs}
    def setArt(self,value):
        self.payload['art'] = value
    def setInfo(self,kind,value):
        self.payload['info'] = value
    def setProperties(self,value):
        self.payload['properties'] = value
    def getVideoInfoTag(self):
        return self
    def setResumePoint(self,position,total):
        self.payload['resume'] = (position,total)


def replay_card(payload):
    from xbmcgui import ListItem
    item = ListItem(**payload['item'])
    item.setArt(payload['art'])
    item.setInfo('video',payload['info'])
    item.setProperties(payload['properties'])
    if 'resume' in payload:
        item.getVideoInfoTag().setResumePoint(*payload['resume'])
    return item


def capture_rows(record):
    from browse_controls import page_cards
    from light_home_cards import media_item
    from live_core import PageHistory

    rows = []
    for row in record['rows']:
        captured = []
        for original in row['items']:
            files,_ = page_cards([original],PageHistory(),row['path'])
            model = files[0]
            captured.append([model,media_item(model,factory=CardCapture).payload])
        rows.append(captured)
    return rows


def projected_rows(record, cached, preferences):
    rows = []
    for row, cards in zip(record['rows'],cached):
        original = row['items']
        if len(original)!=len(cards):
            raise ValueError('Home cache row length differs')
        by_identity = {id(item):card for item,card in zip(original,cards)}
        visible = [by_identity[id(item)] for item in preferences.apply(original)]
        visible.sort(key=lambda entry: entry[0].get('_page_control')=='next')
        if not visible:
            raise ValueError('Home cache has no visible titles')
        rows.append(([model for model,_ in visible],[card for _,card in visible]))
    return rows


def refresh_cache(root, store):
    from light_home_bootstrap import prepare_home
    try:
        schema = scope_schema()
        before = fingerprint(store,schema)
        if not before:
            return False
        prepared = prepare_home(root,store,use_fast=False)
        if prepared:
            record = prepared['record']
            rows = capture_rows(record)
            if fingerprint(store,schema)==before:
                return save_cache(store,schema,before,record,rows)
    except (OSError,ValueError,TypeError,AttributeError,IndexError,KeyError,RuntimeError,OverflowError):
        pass
    return False
