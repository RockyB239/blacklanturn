"""Real OpenWizard cleanup/extraction and account/preference restoration."""
import importlib.util,json,sqlite3,sys,types,unittest,xml.etree.ElementTree as E,zipfile
from pathlib import Path
from unittest.mock import patch
from test_compatibility import CompatibilityTests,Kodi,ROOT as LIB
from test_managed_helper import ManagedTests
from test_build_preferences import EXPECTED,IDS
class PreferenceInstallFlow(CompatibilityTests):
 def packaged(self,change=None):
  fixture=ManagedTests();fixture.root=self.root
  with zipfile.ZipFile(fixture.archive()) as z:data={n:z.read(n) for n in z.namelist()}
  data['addons/plugin.video.umbrella/addon.xml']=b'<addon id="plugin.video.umbrella" version="1.0"/>'
  data['addons/plugin.video.youtube/addon.xml']=b'<addon id="plugin.video.youtube" version="7.3.0"/>'
  for name,fields in EXPECTED.items():data['userdata/'+name]=('<settings>'+''.join('<setting id="'+k+'">'+v+'</setting>' for k,v in fields.items())+'</settings>').encode()
  data['addons/plugin.video.umbrella/resources/settings.xml']=('<settings>'+''.join('<setting id="'+key+'"/>' for key in EXPECTED['addon_data/plugin.video.umbrella/settings.xml'])+'</settings>').encode()
  data['addons/plugin.video.youtube/resources/settings.xml']=('<settings>'+''.join('<setting id="'+key+'"/>' for key in EXPECTED['addon_data/plugin.video.youtube/settings.xml'])+'</settings>').encode()
  if change:change(data)
  return self.archive({'schema':3,'edition':'apple','kodi_major':21,'helper_patch':'empty-cache-1','preferences_policy':'playback-trakt-youtube-1','installer_min_version':'1.0.17'},data)
 def run_install(self,auth_only=False,gui_keep=False,youtube_choices=None,compatibility_choices=False):
  k=Kodi();cfg,mods=self.install_environment(k);self.packaged();cfg.KEEPTRAKT='true';cfg.KEEPLOGIN='true';cfg.KEEPGUISETTINGS='true' if gui_keep else 'false';cfg.get_setting=lambda key:'true' if key=='authonlyclean' and auth_only else 'false'
  db=Path(cfg.DATABASE)/'Addons33.db';db.parent.mkdir(parents=True)
  with sqlite3.connect(db) as c:c.execute('CREATE TABLE update_rules(id integer primary key,addonID text,updateRule integer)')
  h=Path(cfg.HOME);g=h/'userdata/guisettings.xml';g.write_text('<settings><setting id="locale.audiolanguage">English</setting><setting id="locale.subtitlelanguage">forced_only</setting><setting id="videoplayer.usemediacodec">false</setting></settings>')
  p=h/'userdata/addon_data/plugin.video.themoviedb.helper/settings.xml';p.parent.mkdir(parents=True);p.write_text('<settings><setting id="trakt_token">private-token</setting><setting id="trakt_watchedindicators">true</setting></settings>')
  if compatibility_choices:
   root=E.parse(g).getroot()
   for key,value in {'videoplayer.usemediacodecsurface':'false','videoplayer.usemediacodec':'true'}.items():
    node=next((n for n in root if n.get('id')==key),None)
    if node is None:node=E.SubElement(root,'setting',id=key)
    node.set('default','true');node.text=value
   g.write_bytes(E.tostring(root));p=h/'userdata/addon_data/plugin.video.umbrella/settings.xml';p.parent.mkdir(parents=True);p.write_text('<settings><setting id="remove.hdr" default="true">true</setting><setting id="remove.dolby.vision" default="true">true</setting><setting id="remove.hevc" default="true">true</setting></settings>')
  if youtube_choices is not None:
   p=h/'userdata/addon_data/plugin.video.youtube/settings.xml';p.parent.mkdir(parents=True);root=E.Element('settings',version='2')
   for key,value in dict(youtube_choices,**{'youtube.api.key':'private-youtube-key'}).items():E.SubElement(root,'setting',id=key,default='true').text=value
   p.write_bytes(E.tostring(root));(p.parent/'access_manager.json').write_text('{"access_manager":{"users":{"fixture":{"refresh_token":"private-refresh"}}}}')
  mods['resources.libs.whitelist']=types.SimpleNamespace(whitelist=lambda mode:[]);mods['resources.libs.common.tools'].convert_size=lambda v:str(v);mods['resources.libs.common.tools'].kodi_version=lambda:21.3
  with patch.dict(sys.modules,mods):
   s=importlib.util.spec_from_file_location('real_extract',LIB/'extract.py');ex=importlib.util.module_from_spec(s);s.loader.exec_module(ex);mods['resources.libs.extract'].all=ex.all
   s=importlib.util.spec_from_file_location('wizard_prefs',LIB/'wizard.py');w=importlib.util.module_from_spec(s);s.loader.exec_module(w);w.Wizard().build('Apple TV and Mac')
  return h
 def test_standard_real_cleanup_and_extraction_preserve_youtube_choices_and_account(self):
  choices={'kodion.mpd.quality.selection':'3','kodion.mpd.stream.select':'4','kodion.mpd.stream.features':'avc1,hdr,hfr','kodion.video.quality.isa':'false','kodion.video.quality':'2','kodion.audio_only':'true'}
  h=self.run_install(youtube_choices=choices);p=h/'userdata/addon_data/plugin.video.youtube';values={n.get('id'):n.text for n in E.parse(p/'settings.xml').getroot()}
  for key,value in choices.items():self.assertEqual(values[key],value)
  self.assertEqual(values['youtube.api.key'],'private-youtube-key');self.assertEqual(json.loads((p/'access_manager.json').read_text())['access_manager']['users']['fixture']['refresh_token'],'private-refresh')
 def test_clean_real_cleanup_applies_youtube_defaults_and_retains_selected_account(self):
  h=self.run_install(auth_only=True,youtube_choices={'kodion.mpd.quality.selection':'3','kodion.mpd.stream.features':'avc1,hdr'});p=h/'userdata/addon_data/plugin.video.youtube';values={n.get('id'):n.text for n in E.parse(p/'settings.xml').getroot()}
  for key,value in EXPECTED['addon_data/plugin.video.youtube/settings.xml'].items():self.assertEqual(values[key],value)
  self.assertEqual(values['youtube.api.key'],'private-youtube-key');self.assertTrue((p/'access_manager.json').is_file())
 def test_standard_real_install_preserves_live_formats_and_external_player_routing(self):
  choices={'kodion.live_stream.selection.1':'3','kodion.live_stream.selection.2':'0','kodion.support.alternative_player':'true','kodion.alternative_player.web_urls':'true','kodion.alternative_player.mpd':'false','kodion.default_player.web_urls':'false','kodion.default_player.fallback_video':'true'}
  h=self.run_install(youtube_choices=choices);p=h/'userdata/addon_data/plugin.video.youtube';values={n.get('id'):n.text for n in E.parse(p/'settings.xml').getroot()}
  for key,value in choices.items():
   with self.subTest(key=key):self.assertEqual(values.get(key),value)
  self.assertEqual(values['youtube.api.key'],'private-youtube-key');self.assertTrue((p/'access_manager.json').is_file())
 def test_standard_without_keep_gui_preserves_decoder_and_sdr_compatibility_choices(self):
  h=self.run_install(gui_keep=False,compatibility_choices=True)
  for name,choices in {'guisettings.xml':{'videoplayer.usemediacodecsurface':'false','videoplayer.usemediacodec':'true'},'addon_data/plugin.video.umbrella/settings.xml':{'remove.hdr':'true','remove.dolby.vision':'true','remove.hevc':'true'}}.items():
   values={n.get('id'):n.text for n in E.parse(h/'userdata'/name).getroot()}
   for key,value in choices.items():
    with self.subTest(key=key):self.assertEqual(values.get(key),value)
 def test_account_only_clean_does_not_carry_old_decoder_or_sdr_compatibility_choices(self):
  h=self.run_install(auth_only=True,gui_keep=False,compatibility_choices=True)
  for name,keys in {'guisettings.xml':['videoplayer.usemediacodecsurface','videoplayer.usemediacodec'],'addon_data/plugin.video.umbrella/settings.xml':['remove.hdr','remove.dolby.vision','remove.hevc']}.items():
   values={n.get('id'):n.text for n in E.parse(h/'userdata'/name).getroot()}
   for key in keys:
    with self.subTest(key=key):self.assertNotIn(key,values)
 def test_standard_update_retains_english_without_requiring_keep_whole_gui(self):
  h=self.run_install();d={n.get('id'):n.text for n in E.parse(h/'userdata/guisettings.xml').getroot()};self.assertEqual(d['locale.audiolanguage'],'English');self.assertEqual(d['locale.subtitlelanguage'],'forced_only');self.assertTrue((h/'userdata/addon_data/plugin.program.blacklanturninstaller/authorizations.json').is_file())
 def test_keep_gui_retains_hardware_fields_and_language(self):
  h=self.run_install(gui_keep=True);d={n.get('id'):n.text for n in E.parse(h/'userdata/guisettings.xml').getroot()};self.assertEqual(d['videoplayer.usemediacodec'],'false');self.assertEqual(d['locale.audiolanguage'],'English')
 def test_account_only_clean_keeps_token_and_uses_all_explicit_defaults(self):
  h=self.run_install(auth_only=True)
  for name,fields in EXPECTED.items():
   values={n.get('id'):n.text for n in E.parse(h/'userdata'/name).getroot()}
   for k,v in fields.items():self.assertEqual(values[k],v)
  self.assertEqual({n.get('id'):n.text for n in E.parse(h/'userdata/addon_data/plugin.video.themoviedb.helper/settings.xml').getroot()}['trakt_token'],'private-token')
 def test_old_installer_rejects_new_payload_before_device_setup(self):
  s=importlib.util.spec_from_file_location('old',LIB.parents[3]/'tests/fixtures/platform_compatibility_1_0_12.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);k=Kodi()
  with self.assertRaises(m.CompatibilityError):m.prepare(self.packaged(),k)
  self.assertEqual(k.requests,[])
 def test_missing_policy_defaults_rejected_before_device_setup(self):
  k=Kodi();cfg,mods=self.install_environment(k);p=self.packaged(lambda d:d.pop('userdata/addon_data/plugin.video.umbrella/settings.xml'));m=self.module()
  with patch.dict(sys.modules,mods),self.assertRaises(m.CompatibilityError):m.prepare(p,k)
  self.assertEqual(k.requests,[])

 def test_native_xml_extraction_replaces_virtual_values_and_honors_keep_gui(self):
  cfg,mods=self.install_environment(Kodi());mods['resources.libs.whitelist']=types.SimpleNamespace(whitelist=lambda mode:[]);mods['resources.libs.common.tools'].convert_size=lambda v:str(v)
  archive=self.archive(None,{'userdata/guisettings.xml':'<settings/>','userdata/addon_data/plugin.video.umbrella/settings.xml':'<settings version="2"/>','addons/skin.extra/addon.xml':'<addon/>'})
  writes={}
  store=types.SimpleNamespace(virtual_xml=lambda p:Path(p).suffix=='.xml',write=lambda p,b:writes.__setitem__(Path(p).relative_to(cfg.HOME).as_posix(),b))
  mods['resources.libs.settings_store']=store
  import resources.libs
  with patch.dict(sys.modules,mods),patch.object(resources.libs,'settings_store',store,create=True):
   spec=importlib.util.spec_from_file_location('native_extract',LIB/'extract.py');ex=importlib.util.module_from_spec(spec);spec.loader.exec_module(ex)
   cfg.KEEPGUISETTINGS='true';result=ex.all(str(archive),cfg.HOME)
   self.assertEqual(result[:2],(100,0));self.assertNotIn('userdata/guisettings.xml',writes);self.assertEqual(writes['userdata/addon_data/plugin.video.umbrella/settings.xml'],b'<settings version="2"/>');self.assertTrue((Path(cfg.HOME)/'addons/skin.extra/addon.xml').is_file())
   cfg.KEEPGUISETTINGS='false';ex.all(str(archive),cfg.HOME);self.assertEqual(writes['userdata/guisettings.xml'],b'<settings/>')

 def test_tvos_wipe_removes_native_only_xml_and_preserves_selected_gui(self):
  cfg,mods=self.install_environment(Kodi());h=Path(cfg.HOME);u=h/'userdata';paths=[u/'guisettings.xml',u/'addon_data/inputstream.adaptive/settings.xml',u/'addon_data/old.plugin/settings.xml',u/'addon_data'/cfg.ADDON_ID/'settings.xml'];removed=[]
  store=types.SimpleNamespace(native_userdata_xml=lambda home:paths,delete=lambda path:removed.append(path))
  mods['resources.libs.settings_store']=store
  import resources.libs
  with patch.dict(sys.modules,mods),patch.object(resources.libs,'settings_store',store,create=True):
   cfg.KEEPGUISETTINGS='true';mods['resources.libs.install'].wipe(accounts_prepared=True)
   self.assertNotIn(paths[0],removed);self.assertIn(paths[2],removed);self.assertNotIn(paths[3],removed)
   removed.clear();cfg.KEEPGUISETTINGS='false';mods['resources.libs.install'].wipe(accounts_prepared=True,auth_only=True)
   self.assertIn(paths[0],removed);self.assertIn(paths[1],removed);self.assertIn(paths[2],removed);self.assertNotIn(paths[3],removed)
