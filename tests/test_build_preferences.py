"""Clean defaults and explicit preference preservation use the real installer code."""
import copy,importlib.util,io,json,tempfile,types,unittest,xml.etree.ElementTree as E,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/libs'
EXPECTED={'guisettings.xml':{'locale.audiolanguage':'default','locale.subtitlelanguage':'forced_only'},'addon_data/plugin.video.themoviedb.helper/settings.xml':{'trakt_watchedindicators':'true','sync_source_watched':'Trakt','trakt_scrobbling':'true'},'addon_data/plugin.video.umbrella/settings.xml':{'indicators.alt':'1','indicators':'Trakt','scrobble.source':'1','scrobble':'Trakt'}}
EXPECTED['addon_data/plugin.video.youtube/settings.xml']={'kodion.mpd.quality.selection':'6','kodion.mpd.stream.select':'1','kodion.mpd.stream.features':'avc1,mp4a,vtt,filter,alt_sort,vp9','kodion.video.quality.isa':'true','kodion.mpd.videos':'true','kodion.video.stream.select':'1'}
IDS=['plugin.video.themoviedb.helper','plugin.video.umbrella','plugin.video.youtube']
import sys
sys.path.insert(0,str(ROOT.parents[1]) if ROOT.name=='libs' else str(LIB.parents[1]))

class BuildPreferences(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.home=Path(self.temp.name).resolve()
  p=LIB/'build_preferences.py';self.assertTrue(p.is_file(),'Installer has no build preference safeguard');s=importlib.util.spec_from_file_location('build_preferences',p);self.m=importlib.util.module_from_spec(s);s.loader.exec_module(self.m)
 def put(self,name,values,default=False):
  p=self.home/'userdata'/name;p.parent.mkdir(parents=True,exist_ok=True);root=E.Element('settings',version='2')
  for k,v in values.items():E.SubElement(root,'setting',id=k,**({'default':'true'} if default else {})).text=v
  E.ElementTree(root).write(p,encoding='utf-8');return p
 def get(self,name):return {n.get('id'):n.text or '' for n in E.parse(self.home/'userdata'/name).getroot()}
 def accounts(self):return {'schema':1,'settings':{},'files':{},'addon_ids':IDS,'categories':[]}
 def archive(self,change=None):
  d={'userdata/'+n:E.tostring(E.fromstring('<settings>'+''.join('<setting id="'+k+'">'+v+'</setting>' for k,v in fields.items())+'</settings>')) for n,fields in EXPECTED.items()}
  for aid in IDS:
   fields=EXPECTED['addon_data/'+aid+'/settings.xml'];d['addons/'+aid+'/resources/settings.xml']=('<settings>'+''.join('<setting id="'+key+'"/>' for key in fields)+'</settings>').encode()
  if change:change(d)
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w') as z:
   for n,v in d.items():z.writestr(n,v)
  return zipfile.ZipFile(b)
 def test_policy_has_all_explicit_noncredential_defaults(self):self.assertEqual(self.m.DEFAULTS,EXPECTED)
 def test_clean_install_fills_all_defaults(self):
  accounts=self.m.prepare(self.home,self.accounts(),IDS,auth_only=True);self.m.restore(self.home,accounts,IDS)
  for n,v in EXPECTED.items():self.assertEqual(self.get(n),v)
 def test_standard_update_preserves_explicit_choices_and_unrelated_settings(self):
  self.put('guisettings.xml',{'locale.audiolanguage':'English','locale.subtitlelanguage':'forced_only','videoplayer.usemediacodec':'false'})
  self.put('addon_data/plugin.video.themoviedb.helper/settings.xml',{'trakt_watchedindicators':'false','sync_source_watched':'MDbList','trakt_token':'private-token'})
  accounts=self.m.prepare(self.home,self.accounts(),IDS,auth_only=False)
  self.put('guisettings.xml',dict(EXPECTED['guisettings.xml'],**{'videoplayer.usemediacodec':'false'}));self.put('addon_data/plugin.video.themoviedb.helper/settings.xml',dict(EXPECTED['addon_data/plugin.video.themoviedb.helper/settings.xml'],trakt_token='private-token'))
  self.m.restore(self.home,accounts,IDS)
  self.assertEqual(self.get('guisettings.xml')['locale.audiolanguage'],'English');h=self.get('addon_data/plugin.video.themoviedb.helper/settings.xml');self.assertEqual(h['trakt_watchedindicators'],'false');self.assertEqual(h['sync_source_watched'],'MDbList');self.assertEqual(h['trakt_token'],'private-token');self.assertEqual(self.get('guisettings.xml')['videoplayer.usemediacodec'],'false')
 def test_standard_update_preserves_stored_choices_even_when_kodi_marks_them_default(self):
  self.put('guisettings.xml',{'locale.audiolanguage':'mediadefault','locale.subtitlelanguage':'original'},default=True);self.put('addon_data/plugin.video.themoviedb.helper/settings.xml',{'trakt_watchedindicators':'false'},default=True)
  accounts=self.m.prepare(self.home,self.accounts(),IDS,False);self.m.restore(self.home,accounts,IDS)
  self.assertEqual(self.get('guisettings.xml'),{'locale.audiolanguage':'mediadefault','locale.subtitlelanguage':'original'})
  self.assertEqual(self.get('addon_data/plugin.video.themoviedb.helper/settings.xml')['trakt_watchedindicators'],'false')
 def test_account_only_clean_does_not_restore_old_preference_overrides(self):
  self.put('guisettings.xml',{'locale.audiolanguage':'English','locale.subtitlelanguage':'original'});a=self.m.prepare(self.home,self.accounts(),IDS,True);self.m.restore(self.home,a,IDS);self.assertEqual(self.get('guisettings.xml'),EXPECTED['guisettings.xml'])
 def test_retry_keeps_original_preferences_after_partial_extraction(self):
  self.put('guisettings.xml',{'locale.audiolanguage':'French'});first=self.m.prepare(self.home,self.accounts(),IDS,False);self.put('guisettings.xml',EXPECTED['guisettings.xml']);again=self.m.prepare(self.home,copy.deepcopy(first),IDS,False);self.m.restore(self.home,again,IDS);self.assertEqual(self.get('guisettings.xml')['locale.audiolanguage'],'French')
 def test_retry_cannot_change_clean_mode(self):
  first=self.m.prepare(self.home,self.accounts(),IDS,False)
  with self.assertRaises(self.m.PreferenceError):self.m.prepare(self.home,first,IDS,True)
 def test_preferences_never_capture_credentials_or_unknown_addons(self):
  self.put('addon_data/plugin.video.themoviedb.helper/settings.xml',{'trakt_token':'secret','trakt_watchedindicators':'true'});a=self.m.prepare(self.home,self.accounts(),[],False);self.assertNotIn('secret',json.dumps(a));self.m.restore(self.home,a,[]);self.assertNotIn('addon_data/plugin.video.themoviedb.helper/settings.xml',a['build_preferences']['values'])
 def test_invalid_restore_rejected_before_any_write(self):
  a=self.m.prepare(self.home,self.accounts(),IDS,False)
  for name,key,value in [('../escape','test','x'),('guisettings.xml','services.webserverpassword','secret'),('addon_data/plugin.video.themoviedb.helper/settings.xml','trakt_watchedindicators','invalid')]:
   with self.subTest(key=key):
    broken=copy.deepcopy(a);broken['build_preferences']['values']={name:{key:value}}
    with self.assertRaises(self.m.PreferenceError):self.m.restore(self.home,broken,IDS)
    self.assertFalse((self.home/'userdata/guisettings.xml').exists())
 def test_malformed_existing_or_symlink_stops_before_cleanup(self):
  p=self.put('guisettings.xml',{});p.write_text('<broken')
  with self.assertRaises(self.m.PreferenceError):self.m.prepare(self.home,self.accounts(),IDS,False)
  p.unlink();target=self.home/'other.xml';target.write_text('<settings/>');p.symlink_to(target)
  with self.assertRaises(self.m.PreferenceError):self.m.prepare(self.home,self.accounts(),IDS,False)
 def test_default_attribute_removed_so_upstream_default_change_cannot_reset_choice(self):
  self.put('guisettings.xml',EXPECTED['guisettings.xml'],default=True);a=self.m.prepare(self.home,self.accounts(),IDS,False);self.m.restore(self.home,a,IDS)
  for n in E.parse(self.home/'userdata/guisettings.xml').getroot():self.assertNotIn('default',n.attrib)
 def test_archive_gate_accepts_exact_clean_policy(self):
  with self.archive() as z:self.m.verify_archive(z)
 def test_archive_gate_rejects_missing_or_wrong_sync_defaults(self):
  for name,fields in EXPECTED.items():
   for key in fields:
    def change(d):
     root=E.fromstring(d['userdata/'+name]);root.remove(next(n for n in root if n.get('id')==key));d['userdata/'+name]=E.tostring(root)
    with self.subTest(key=key),self.archive(change) as z:
     with self.assertRaises(self.m.PreferenceError):self.m.verify_archive(z)

 def test_native_virtual_settings_roundtrip_and_explicit_choices(self):
  store={str(self.home/'userdata/guisettings.xml'):b'<settings><setting id="locale.audiolanguage">English</setting></settings>'}
  class File:
   def __init__(self,path,mode=None):self.path=path
   def readBytes(self):return store[self.path]
   def size(self):return len(store[self.path])
   def write(self,text):store[self.path]=text.encode();return True
   def close(self):pass
  previous_vfs=self.m.store.xbmcvfs;self.addCleanup(setattr,self.m.store,'xbmcvfs',previous_vfs);self.m.store.xbmcvfs=types.SimpleNamespace(translatePath=lambda p:str(self.home),exists=lambda p:p in store,File=File,mkdirs=lambda p:True)
  a=self.m.prepare(self.home,self.accounts(),IDS,False);self.m.restore(self.home,a,IDS)
  root=E.fromstring(store[str(self.home/'userdata/guisettings.xml')]);self.assertEqual({n.get('id'):n.text for n in root},{'locale.audiolanguage':'English','locale.subtitlelanguage':'forced_only'})
 def test_provider_labels_follow_preserved_selector(self):
  self.put('addon_data/plugin.video.umbrella/settings.xml',{'scrobble.source':'0','scrobble':'Trakt','indicators.alt':'2'})
  a=self.m.prepare(self.home,self.accounts(),IDS,False);self.m.restore(self.home,a,IDS);d=self.get('addon_data/plugin.video.umbrella/settings.xml');self.assertEqual(d['scrobble'],'Local');self.assertEqual(d['indicators'],'Simkl')
 def test_unknown_addon_setting_schema_rejected_before_cleanup(self):
  with self.archive(lambda d:d.__setitem__('addons/plugin.video.umbrella/resources/settings.xml',b'<settings/>')) as z:
   with self.assertRaises(self.m.PreferenceError):self.m.verify_archive(z)

 def test_existing_temporary_symlink_cannot_overwrite_an_unrelated_file(self):
  p=self.put('guisettings.xml',EXPECTED['guisettings.xml']);victim=self.home/'unrelated.txt';victim.write_text('keep');p.with_suffix('.preferences-pending').symlink_to(victim)
  a=self.m.prepare(self.home,self.accounts(),IDS,False);self.m.restore(self.home,a,IDS);self.assertEqual(victim.read_text(),'keep')
 def test_schema_valid_empty_provider_display_labels_are_normalized(self):
  self.put('addon_data/plugin.video.umbrella/settings.xml',{'indicators':'','scrobble':'','indicators.alt':'1','scrobble.source':'1'});a=self.m.prepare(self.home,self.accounts(),IDS,False);self.m.restore(self.home,a,IDS);d=self.get('addon_data/plugin.video.umbrella/settings.xml');self.assertEqual(d['indicators'],'Trakt');self.assertEqual(d['scrobble'],'Trakt')
 def test_failed_native_vfs_readback_restores_original_xml(self):
  original=b'<settings><setting id="locale.audiolanguage">English</setting></settings>';key=str(self.home/'userdata/guisettings.xml');store={key:original};writes=[]
  class File:
   def __init__(self,path,mode=None):self.path=path
   def readBytes(self):return store[self.path]
   def size(self):return len(store[self.path])
   def write(self,text):
    writes.append(text);store[self.path]=b'corrupt' if len(writes)==1 else text.encode();return True
   def close(self):pass
  previous_vfs=self.m.store.xbmcvfs;self.addCleanup(setattr,self.m.store,'xbmcvfs',previous_vfs);self.m.store.xbmcvfs=types.SimpleNamespace(translatePath=lambda p:str(self.home),exists=lambda p:p in store,File=File,mkdirs=lambda p:True)
  a=self.m.prepare(self.home,self.accounts(),IDS,False)
  with self.assertRaises(self.m.PreferenceError):self.m.restore(self.home,a,IDS)
  self.assertEqual(store[key],original)

 def test_update_note_preferences_survive_standard_cleanup(self):
  from resources.libs.update_notes_state import empty_state
  ids=IDS+['script.blacklanturn.preview'];state=empty_state();state['enabled']=False
  p=self.home/'userdata/addon_data/script.blacklanturn.preview/update-notes.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(state))
  a=self.m.prepare(self.home,self.accounts(),ids,False);p.unlink();self.m.restore(self.home,a,ids)
  self.assertEqual(json.loads(p.read_text()),state)
 def test_account_only_clean_does_not_restore_update_history(self):
  from resources.libs.update_notes_state import empty_state
  ids=IDS+['script.blacklanturn.preview'];p=self.home/'userdata/addon_data/script.blacklanturn.preview/update-notes.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(empty_state()))
  a=self.m.prepare(self.home,self.accounts(),ids,True);p.unlink();self.m.restore(self.home,a,ids);self.assertFalse(p.exists())
