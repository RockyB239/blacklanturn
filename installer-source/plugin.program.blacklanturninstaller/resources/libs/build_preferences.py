"""Versioned playback/Trakt preferences for managed build installs, without accounts.

Clean installs receive explicit defaults. Standard updates retain stored choices,
including entries Kodi marks as upstream defaults. No startup loop
or account token is used. Pending account recovery carries this bounded snapshot.
"""
import copy,json
from pathlib import Path
import xml.etree.ElementTree as E
from resources.libs import settings_store as store
DEFAULTS=json.loads((Path(__file__).parents[1]/'playback-defaults.json').read_text(encoding='utf-8'))
MAX_BYTES=4*1024*1024
PROVIDERS={'0':'Local','1':'Trakt','2':'Simkl','3':'MDBList','4':'Custom','5':'Floppy','6':'Scrob','7':'PunchPlay'}
class PreferenceError(Exception):pass

def _paths(home,addon_ids):
 return {name:fields for name,fields in DEFAULTS.items() if name=='guisettings.xml' or name.split('/')[1] in addon_ids}
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
 if not isinstance(value,str) or (not value and key not in ('indicators','scrobble')) or len(value)>128 or any(ord(c)<32 for c in value):raise PreferenceError('Invalid playback preference. Installation stopped.')
 if key in ('trakt_watchedindicators','trakt_scrobbling','trakt.scrobble') and value not in ('true','false'):raise PreferenceError('Invalid Trakt preference. Installation stopped.')
 if key.startswith('sync_source_') and value not in ('Trakt','MDbList'):raise PreferenceError('Invalid sync preference. Installation stopped.')
 if key in ('indicators.alt','scrobble.source') and value not in PROVIDERS:raise PreferenceError('Unsupported tracking provider. Installation stopped.')
 return value

def _validate(snapshot,addon_ids,auth_only=None):
 if not isinstance(snapshot,dict) or snapshot.get('schema')!=1 or type(snapshot.get('auth_only')) is not bool or not isinstance(snapshot.get('values'),dict):raise PreferenceError('Invalid preference recovery. Installation stopped.')
 if auth_only is not None and snapshot['auth_only']!=auth_only:raise PreferenceError('Finish the pending installation using its original clean/update mode.')
 allowed=_paths(None,addon_ids)
 for name,values in snapshot['values'].items():
  if name not in allowed or not isinstance(values,dict) or not set(values)<=set(allowed[name]):raise PreferenceError('Unexpected preference recovery. Installation stopped.')
  for key,value in values.items():_value(key,value)
 if snapshot['auth_only'] and snapshot['values']:raise PreferenceError('Clean recovery contains preferences. Installation stopped.')
 return snapshot

def prepare(home,accounts,addon_ids,auth_only=False):
 """Capture once before cleanup; retries reuse original choices and install mode."""
 try:
  result=copy.deepcopy(accounts)
  if 'build_preferences' in result:
   _validate(result['build_preferences'],addon_ids,auth_only);return result
  values={}
  if not auth_only:
   for name,fields in _paths(home,addon_ids).items():
    root=_root(_read(home,name));explicit={}
    for node in root:
     key=node.get('id')
     if key in fields:explicit[key]=_value(key,node.text if node.text is not None else node.get('value',''))
    if explicit:values[name]=explicit
  result['build_preferences']={'schema':1,'auth_only':auth_only,'values':values}
  return result
 except (OSError,ValueError,TypeError,E.ParseError) as exc:raise PreferenceError('Playback preferences could not be saved. Your current build has been kept.') from exc

def _write(home,name,raw):
 store.write(_path(home,name),raw)

def restore(home,accounts,addon_ids):
 """Restore only approved choices over extracted defaults; retain unrelated XML."""
 try:
  snapshot=_validate(accounts.get('build_preferences'),addon_ids)
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
  for name,raw in prepared:_write(home,name,raw)
 except (OSError,ValueError,TypeError,E.ParseError) as exc:raise PreferenceError('Playback preference restoration needs attention. Keep the pending backup and reinstall.') from exc

def verify_archive(archive):
 """Reject missing/implicit defaults before any profile cleanup."""
 try:
  for name,fields in DEFAULTS.items():
   root=_root(archive.read('userdata/'+name));nodes={n.get('id'):n for n in root}
   if name.startswith('addon_data/'):
    aid=name.split('/')[1];schema=E.fromstring(archive.read('addons/'+aid+'/resources/settings.xml'))
    known={n.get('id') for n in schema.iter('setting')}
    if not set(fields)<=known:raise PreferenceError('The tracking add-on settings changed. This build requires compatibility review before installation.')
   for key,value in fields.items():
    if key not in nodes or nodes[key].get('default')=='true' or nodes[key].text!=value:raise PreferenceError('Build playback/Trakt defaults are incomplete. Update Installer and retry; your current build has been kept.')
 except (KeyError,OSError,ValueError,E.ParseError) as exc:raise PreferenceError('Build playback preferences are missing or invalid. Your current build has been kept.') from exc
