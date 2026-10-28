"""Versioned playback/Trakt preferences for managed build installs, without accounts.

Clean installs receive explicit defaults. Standard updates retain stored choices,
including entries Kodi marks as upstream defaults. No startup loop
or account token is used. Pending account recovery carries this bounded snapshot.
"""
import copy,json,math
from pathlib import Path
import xml.etree.ElementTree as E
from resources.libs import settings_store as store
from resources.libs import update_notes_state as update_notes
from resources.libs import release_notice_state as releases
from resources.libs.discovery_defaults import upgrade as discovery_upgrade
DEFAULTS=json.loads((Path(__file__).parents[1]/'playback-defaults.json').read_text(encoding='utf-8'))
YOUTUBE='addon_data/plugin.video.youtube/settings.xml'
YOUTUBE_CHOICES={'kodion.history.remote','kodion.history.local','kodion.video.quality','kodion.video.quality.ask','kodion.subtitle.languages.num','kodion.subtitle.download','kodion.audio_only',
 'kodion.live_stream.selection.1','kodion.live_stream.selection.2','kodion.support.alternative_player',
 'kodion.alternative_player.web_urls','kodion.alternative_player.mpd','kodion.default_player.web_urls','kodion.default_player.fallback_video'}
CAPTURE_CHOICES={YOUTUBE:YOUTUBE_CHOICES,
 'addon_data/plugin.video.themoviedb.helper/settings.xml':{'sync_source_playback'},
 'guisettings.xml':{'videoplayer.usemediacodecsurface','videoplayer.usemediacodec'},
 'addon_data/plugin.video.umbrella/settings.xml':{'remove.hdr','remove.dolby.vision','remove.hevc'}}
MAX_BYTES=4*1024*1024
CONTROLLER='script.blacklanturn.preview'
CONTROLLER_CONFIG='addon_data/script.blacklanturn.preview/rows.json'
TITLE_PREFERENCES='addon_data/script.blacklanturn.preview/title-preferences.json'
MAX_TITLE_BYTES=256*1024
PROVIDERS={'0':'Local','1':'Trakt','2':'Simkl','3':'MDBList','4':'Custom','5':'Floppy','6':'Scrob','7':'PunchPlay'}
class PreferenceError(Exception):pass

def _paths(home,addon_ids):
 return {name:fields for name,fields in DEFAULTS.items() if name=='guisettings.xml' or name.split('/')[1] in addon_ids}
def _keys(name,fields):return set(fields)|CAPTURE_CHOICES.get(name,set())
def _path(home,name):
 base=Path(home).resolve();path=base/'userdata'/name
 for item in [path]+list(path.parents):
  if item==base:break
  if item.is_symlink():raise PreferenceError('A settings path is a symbolic link. Your current build has been kept.')
 return path

def _read(home,name):
 path=_path(home,name)
 return store.read(path) if store.exists(path) else None

def _root(raw):
 root=E.fromstring(raw) if raw is not None else E.Element('settings',version='2')
 if root.tag!='settings':raise PreferenceError('Invalid playback settings. Installation stopped.')
 ids=[n.get('id') for n in root if n.get('id')]
 if len(ids)!=len(set(ids)):raise PreferenceError('Duplicate playback settings. Installation stopped.')
 return root

def _value(key,value):
 if not isinstance(value,str) or (not value and key not in ('indicators','scrobble','kodion.mpd.stream.features')) or len(value)>(1024 if key=='kodion.mpd.stream.features' else 128) or any(ord(c)<32 for c in value):raise PreferenceError('Invalid playback preference. Installation stopped.')
 if key in ('trakt_watchedindicators','trakt_scrobbling','trakt.scrobble') and value not in ('true','false'):raise PreferenceError('Invalid Trakt preference. Installation stopped.')
 if key.startswith('sync_source_') and value not in ('Trakt','MDbList'):raise PreferenceError('Invalid sync preference. Installation stopped.')
 if key in ('indicators.alt','scrobble.source') and value not in PROVIDERS:raise PreferenceError('Unsupported tracking provider. Installation stopped.')
 return value

def _json_object(pairs):
 result={}
 for key,value in pairs:
  if key in result:raise ValueError('Duplicate controller setting')
  result[key]=value
 return result

def _reject_constant(value):
 raise ValueError('Nonfinite controller setting')

def _controller_text(raw):
 """Validate a bounded object without changing its original UTF-8 representation."""
 try:
  if not isinstance(raw,str) or len(raw.encode('utf-8'))>MAX_BYTES:raise ValueError('Controller settings exceed limit')
  value=json.loads(raw,object_pairs_hook=_json_object,parse_constant=_reject_constant)
  if not isinstance(value,dict):raise ValueError('Controller settings must be an object')
  pending=[value]
  while pending:
   item=pending.pop()
   if isinstance(item,dict):pending.extend(item.values())
   elif isinstance(item,list):pending.extend(item)
   elif isinstance(item,float) and not math.isfinite(item):raise ValueError('Nonfinite controller setting')
  return raw
 except (ValueError,TypeError,RecursionError) as exc:
  raise PreferenceError('Controller settings are invalid. Your current build has been kept.') from exc

def _title_preferences_text(raw):
 if not isinstance(raw,str) or len(raw.encode('utf-8'))>MAX_TITLE_BYTES:raise PreferenceError('Saved title choices exceed the recovery limit. Your current build has been kept.')
 return _controller_text(raw)

def _validate(snapshot,addon_ids,auth_only=None):
 if not isinstance(snapshot,dict) or type(snapshot.get('schema')) is not int or snapshot.get('schema') not in (1,2,3,4,5) or type(snapshot.get('auth_only')) is not bool or not isinstance(snapshot.get('values'),dict):raise PreferenceError('Invalid preference recovery. Installation stopped.')
 expected={'schema','auth_only','values'}|({'controller'} if snapshot['schema']>=2 else set())|({'update_notes'} if snapshot['schema']>=3 else set())|({'release_notices'} if snapshot['schema']>=4 else set())|({'title_preferences'} if snapshot['schema']>=5 else set())
 if set(snapshot)!=expected:raise PreferenceError('Invalid preference recovery. Installation stopped.')
 if auth_only is not None and snapshot['auth_only']!=auth_only:raise PreferenceError('Finish the pending installation using its original clean/update mode.')
 if snapshot['schema']==1 and not snapshot['auth_only'] and CONTROLLER in addon_ids:
  raise PreferenceError('This pending backup is from an older Installer and has no original controller settings. Recover the original settings before continuing; installation has stopped.')
 allowed=_paths(None,addon_ids)
 for name,values in snapshot['values'].items():
  if name not in allowed or not isinstance(values,dict) or not set(values)<=_keys(name,allowed[name]):raise PreferenceError('Unexpected preference recovery. Installation stopped.')
  for key,value in values.items():_value(key,value)
 if snapshot['auth_only'] and snapshot['values']:raise PreferenceError('Clean recovery contains preferences. Installation stopped.')
 controller=snapshot.get('controller')
 if controller is not None:
  if snapshot['auth_only'] or CONTROLLER not in addon_ids:raise PreferenceError('Unexpected controller preference recovery. Installation stopped.')
  _controller_text(controller)
 notes=snapshot.get('update_notes')
 if notes is not None:
  if snapshot['auth_only'] or CONTROLLER not in addon_ids:raise PreferenceError('Unexpected update history recovery. Installation stopped.')
  update_notes.validate(notes)
 release_state=snapshot.get('release_notices')
 if release_state is not None:
  if snapshot['auth_only'] or CONTROLLER not in addon_ids:raise PreferenceError('Unexpected release notice recovery. Installation stopped.')
  releases.validate_state(release_state)
 choices=snapshot.get('title_preferences')
 if choices is not None:
  if snapshot['auth_only'] or CONTROLLER not in addon_ids:raise PreferenceError('Unexpected title choice recovery. Installation stopped.')
  _title_preferences_text(choices)
 return snapshot

def prepare(home,accounts,addon_ids,auth_only=False):
 """Capture once before cleanup; retries reuse original choices and install mode."""
 try:
  result=copy.deepcopy(accounts)
  if CONTROLLER in addon_ids:_path(home,CONTROLLER_CONFIG)
  if 'build_preferences' in result:
   _validate(result['build_preferences'],addon_ids,auth_only);return result
  values={}
  if not auth_only:
   for name,fields in _paths(home,addon_ids).items():
    root=_root(_read(home,name));explicit={}
    for node in root:
     key=node.get('id')
     if key in _keys(name,fields):explicit[key]=_value(key,node.text if node.text is not None else node.get('value',''))
    if explicit:values[name]=explicit
  controller=None
  if not auth_only and CONTROLLER in addon_ids:
   raw=_read(home,CONTROLLER_CONFIG)
   if raw is not None:controller=_controller_text(raw.decode('utf-8'))
  notes=None
  if not auth_only and CONTROLLER in addon_ids:
   raw=_read(home,'addon_data/script.blacklanturn.preview/update-notes.json')
   if raw is not None:
    if len(raw)>1024*1024:raise ValueError('Oversized update history')
    notes=update_notes.validate(json.loads(raw))
  release_state=None
  if not auth_only and CONTROLLER in addon_ids:
   raw=_read(home,'addon_data/script.blacklanturn.preview/release-notices.json')
   if raw is not None:
    if len(raw)>releases.MAX_BYTES:raise ValueError('Oversized release notices')
    release_state=releases.validate_state(json.loads(raw))
   else:
    release_state=releases.empty_state(notes['enabled'] if notes is not None else True)
    marker=_read(home,'blacklanturn-build.json')
    if marker is not None:
     previous=json.loads(marker)
     if isinstance(previous,dict) and {'edition','build_version'}<=set(previous):release_state['installed']=releases.identity(previous)
  title_preferences=None
  if not auth_only and CONTROLLER in addon_ids:
   raw=_read(home,TITLE_PREFERENCES)
   if raw is not None:title_preferences=_title_preferences_text(raw.decode('utf-8'))
  result['build_preferences']={'schema':5,'auth_only':auth_only,'values':values,'controller':controller,'update_notes':notes,'release_notices':release_state,'title_preferences':title_preferences}
  return result
 except (OSError,ValueError,TypeError,E.ParseError) as exc:raise PreferenceError('Playback preferences could not be saved. Your current build has been kept.') from exc

def _write(home,name,raw):
 store.write(_path(home,name),raw)

def restore(home,accounts,addon_ids):
 """Restore only approved choices over extracted defaults; retain unrelated XML."""
 try:
  snapshot=_validate(accounts.get('build_preferences'),addon_ids)
  if CONTROLLER in addon_ids:_path(home,CONTROLLER_CONFIG)
  prepared=[]
  for name,fields in _paths(home,addon_ids).items():
   root=_root(_read(home,name));values=dict(fields,**snapshot['values'].get(name,{}))
   if name=='addon_data/plugin.video.umbrella/settings.xml':
    for selector,label in [('indicators.alt','indicators'),('scrobble.source','scrobble')]:values[label]=PROVIDERS[values[selector]]
   for key,value in values.items():
    node=next((n for n in root if n.get('id')==key),None)
    if node is None:node=E.SubElement(root,'setting',id=key)
    node.attrib.pop('default',None);node.attrib.pop('value',None);node.text=value
   prepared.append((name,E.tostring(root,encoding='utf-8',xml_declaration=True)))
  if snapshot.get('controller') is not None:
   raw=snapshot['controller'];marker_raw=_read(home,'blacklanturn-build.json')
   if marker_raw is not None:
    if len(marker_raw)>32768:raise ValueError('Invalid build policy')
    marker=json.loads(marker_raw)
    if not isinstance(marker,dict):raise ValueError('Invalid build policy')
    if marker.get('discovery_patch')=='discovery-first-page-1':raw=discovery_upgrade(raw)
   prepared.append((CONTROLLER_CONFIG,raw.encode('utf-8')))
  if snapshot.get('update_notes') is not None:
   prepared.append(('addon_data/script.blacklanturn.preview/update-notes.json',json.dumps(snapshot['update_notes'],ensure_ascii=False).encode('utf-8')))
  if snapshot.get('release_notices') is not None:
   prepared.append(('addon_data/script.blacklanturn.preview/release-notices.json',json.dumps(snapshot['release_notices'],ensure_ascii=False).encode('utf-8')))
  if snapshot.get('title_preferences') is not None:
   prepared.append((TITLE_PREFERENCES,snapshot['title_preferences'].encode('utf-8')))
  for name,raw in prepared:_write(home,name,raw)
 except (OSError,ValueError,TypeError,E.ParseError) as exc:raise PreferenceError('Playback preference restoration needs attention. Keep the pending backup and reinstall.') from exc

def complete_install(home):
 """Write success only after extraction and account/preference restoration."""
 try:
  raw=_read(home,'blacklanturn-build.json')
  if raw is None:return
  marker=json.loads(raw)
  if marker.get('release_notices')!='curated-releases-1':return
  ident=releases.identity(marker);key=marker.get('release_id')
  import re
  if not isinstance(key,str) or not re.fullmatch(r'[a-zA-Z0-9._-]{1,100}',key):raise ValueError('Invalid release identity')
  receipt=dict(schema=1,id=key,**ident,complete=True)
  _write(home,'blacklanturn-install-complete.json',json.dumps(receipt,sort_keys=True).encode('utf-8'))
 except (OSError,ValueError,TypeError) as exc:raise PreferenceError('Installation completion could not be saved. Keep recovery data and retry.') from exc

def verify_archive(archive,policy='playback-trakt-youtube-1'):
 """Reject missing/implicit defaults before any profile cleanup."""
 try:
  for name,fields in DEFAULTS.items():
   if name==YOUTUBE and policy=='playback-trakt-1':continue
   root=_root(archive.read('userdata/'+name));nodes={n.get('id'):n for n in root}
   if name.startswith('addon_data/'):
    aid=name.split('/')[1];schema=E.fromstring(archive.read('addons/'+aid+'/resources/settings.xml'))
    known={n.get('id') for n in schema.iter('setting')}
    if not set(fields)<=known:raise PreferenceError('The tracking add-on settings changed. This build requires compatibility review before installation.')
   for key,value in fields.items():
    if key not in nodes or nodes[key].get('default')=='true' or nodes[key].text!=value:raise PreferenceError('Build playback/Trakt defaults are incomplete. Update Installer and retry; your current build has been kept.')
 except (KeyError,OSError,ValueError,E.ParseError) as exc:raise PreferenceError('Build playback preferences are missing or invalid. Your current build has been kept.') from exc
