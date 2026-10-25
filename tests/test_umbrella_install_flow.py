"""Real Standard/account-only cleanup/extraction with current Umbrella97 with legacy preference marker18; fullrelease29 gate tested separately."""
import importlib.util,json,shutil,sqlite3,sys,types,unittest,xml.etree.ElementTree as E,zipfile
from pathlib import Path
from unittest.mock import patch
import test_compatibility as compatibility
Kodi=compatibility.Kodi;LIB=compatibility.ROOT
import test_managed_helper as helper_fixture
from test_build_preferences import EXPECTED
ROOT=LIB.parents[3];PROGRESS=ROOT/'compatibility/umbrella-progress'
ID='plugin.video.umbrella';PLAYER='resources/lib/modules/player.py'
POLICY={'schema':3,'edition':'apple','kodi_major':21,'helper_patch':'empty-cache-1',
 'preferences_policy':'playback-trakt-youtube-umbrella-1','installer_min_version':'1.0.18',
 'umbrella_patch':'event-progress-3','umbrella_version':'6.7.97'}

class UmbrellaInstallFlow(unittest.TestCase):
 setUp=compatibility.CompatibilityTests.setUp;tearDown=compatibility.CompatibilityTests.tearDown
 archive=compatibility.CompatibilityTests.archive;install_environment=compatibility.CompatibilityTests.install_environment;module=compatibility.CompatibilityTests.module
 def provider(self,patched=True):
  with zipfile.ZipFile(PROGRESS/'upstream-6.7.92.zip')as z:data={n.split('/',1)[1]:z.read(n)for n in z.namelist()if not n.endswith('/')}
  if patched:
   spec=importlib.util.spec_from_file_location('current_install_builder',ROOT/'tools/build_release.py');build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
   record=build.current_addon_manifest()[ID]
   data=build.current_addon_files(ID,record)
  return data
 def packaged(self,change=None,policy=None):
  h=helper_fixture.ManagedTests();h.root=self.root
  with zipfile.ZipFile(h.archive())as z:data={n:z.read(n)for n in z.namelist()}
  spec=importlib.util.spec_from_file_location('current_helper_install_builder',ROOT/'tools/build_release.py');build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
  build.apply_current_addons(data,('plugin.video.themoviedb.helper','script.module.infotagger'))
  data.update({'addons/'+ID+'/'+n:b for n,b in self.provider().items()})
  data['addons/plugin.video.youtube/addon.xml']=b'<addon id="plugin.video.youtube" version="7.3.0"/>'
  for name,fields in EXPECTED.items():data['userdata/'+name]=('<settings>'+''.join('<setting id="'+k+'">'+v+'</setting>'for k,v in fields.items())+'</settings>').encode()
  data['addons/plugin.video.youtube/resources/settings.xml']=('<settings>'+''.join('<setting id="'+k+'"/>'for k in EXPECTED['addon_data/plugin.video.youtube/settings.xml'])+'</settings>').encode()
  if change:change(data)
  return self.archive(policy or POLICY,data)
 def environment(self,auth_only=False,foreign=None,transaction_failure=False):
  k=Kodi();cfg,mods=self.install_environment(k);self.packaged()
  cfg.KEEPTRAKT=cfg.KEEPDEBRID=cfg.KEEPLOGIN='true';cfg.KEEPFAVS=cfg.KEEPSOURCES='true'
  cfg.get_setting=lambda key:'true'if key=='authonlyclean'and auth_only else'false'
  h=Path(cfg.HOME)
  for n,b in self.provider(False).items():
   p=h/'addons'/ID/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
  if foreign=='future':
   p=h/'addons'/ID/'addon.xml';p.write_bytes(p.read_bytes().replace(b'6.7.92',b'6.8.0'))
  elif foreign:
   p=h/'addons'/ID/foreign;p.write_bytes(b'foreign unreviewed source')
  db=h/'userdata/Database/Addons33.db';db.parent.mkdir(parents=True)
  with sqlite3.connect(db)as c:
   c.execute('CREATE TABLE update_rules(id INTEGER PRIMARY KEY,addonID TEXT,updateRule INTEGER)')
   c.executemany('INSERT INTO update_rules VALUES(?,?,?)',[(1,'repository.keep',2),(2,'plugin.video.themoviedb.helper',3),(3,ID,2)])
   if transaction_failure:c.execute("CREATE TRIGGER reject_umbrella BEFORE INSERT ON update_rules WHEN NEW.addonID='plugin.video.umbrella' AND NEW.updateRule=1 BEGIN SELECT RAISE(ABORT,'fixture failure'); END")
  def put(name,raw):
   p=h/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);return p
  put('userdata/guisettings.xml',b'<settings><setting id="locale.audiolanguage" default="true">English</setting></settings>')
  put('userdata/addon_data/plugin.video.themoviedb.helper/settings.xml',b'<settings><setting id="trakt_token">private-helper</setting></settings>')
  self.credentials={'torboxtoken':'private-torbox','torbox.username':'fixture','torbox.enable':'true','trakt.user.token':'private-trakt','trakt.refreshtoken':'private-trakt-refresh','realdebridtoken':'private-rd','premiumizetoken':'private-pm','alldebridtoken':'private-ad','simkltoken':'private-simkl','mdblist.token':'private-mdb','custom.user.token':'private-custom','floppy.token':'private-floppy','scrob.accesstoken':'private-scrob','punchplay.accesstoken':'private-punch'}
  vals=dict(self.credentials,**{'scrobble.source':'0','scrobble':'Local','indicators.alt':'2','indicators':'Simkl','remove.hdr':'true'})
  put('userdata/addon_data/'+ID+'/settings.xml',('<settings>'+''.join('<setting id="'+k+'" default="true">'+v+'</setting>'for k,v in vals.items())+'</settings>').encode())
  put('userdata/addon_data/plugin.video.youtube/settings.xml',b'<settings><setting id="youtube.api.key">private-youtube</setting><setting id="kodion.mpd.quality.selection">3</setting></settings>')
  put('userdata/addon_data/plugin.video.youtube/access_manager.json',b'{"fixture":{"refresh_token":"private-refresh"}}')
  put('userdata/favourites.xml',b'<favourites><favourite name="Fixture">fixture</favourite></favourites>')
  put('userdata/sources.xml',b'<sources/>');put('userdata/keep-before-preflight.txt',b'keep until verified')
  put('addons/inputstream.adaptive/component.native',b'owned native binary');put('userdata/addon_data/inputstream.adaptive/settings.xml',b'<settings><setting id="device">native</setting></settings>')
  mods['resources.libs.whitelist']=types.SimpleNamespace(whitelist=lambda mode:[])
  mods['resources.libs.db'].depends_list=lambda addon:[]
  mods['resources.libs.common.tools'].convert_size=lambda value:str(value);mods['resources.libs.common.tools'].kodi_version=lambda:21.3
  return k,cfg,mods
 def install(self,cfg,mods):
  with patch.dict(sys.modules,mods):
   s=importlib.util.spec_from_file_location('real_umbrella_extract',LIB/'extract.py');ex=importlib.util.module_from_spec(s);s.loader.exec_module(ex);mods['resources.libs.extract'].all=ex.all
   s=importlib.util.spec_from_file_location('umbrella_wizard',LIB/'wizard.py');w=importlib.util.module_from_spec(s);s.loader.exec_module(w);w.Wizard().build('Apple TV and Mac')
 def values(self,path):return {n.get('id'):n.text or''for n in E.parse(path).getroot()}
 def test_standard_and_account_only_use_real_cleanup_extract_and_selected_accounts(self):
  for auth_only in (False,True):
   with self.subTest(auth_only=auth_only):
    if (self.root/'profile').exists():shutil.rmtree(self.root/'profile')
    k,cfg,mods=self.environment(auth_only);h=Path(cfg.HOME);self.install(cfg,mods)
    self.assertFalse((h/'userdata/keep-before-preflight.txt').exists(),'No real cleanup occurred')
    self.assertEqual((h/'addons'/ID/PLAYER).read_bytes(),self.provider()[PLAYER])
    self.assertEqual((h/'addons/inputstream.adaptive/component.native').read_bytes(),b'owned native binary')
    vals=self.values(h/'userdata/addon_data'/ID/'settings.xml')
    for key,value in self.credentials.items():self.assertEqual(vals[key],value)
    self.assertEqual(vals['scrobble.source'],'1'if auth_only else'0')
    self.assertEqual(vals['indicators.alt'],'1'if auth_only else'2')
    self.assertEqual(self.values(h/'userdata/guisettings.xml')['locale.audiolanguage'],'default'if auth_only else'English')
    self.assertEqual(self.values(h/'userdata/addon_data/plugin.video.youtube/settings.xml')['youtube.api.key'],'private-youtube')
    self.assertEqual((h/'userdata/addon_data/plugin.video.youtube/access_manager.json').read_bytes(),b'{"fixture":{"refresh_token":"private-refresh"}}')
    self.assertEqual((h/'userdata/favourites.xml').exists(),not auth_only)
    self.assertEqual((h/'userdata/sources.xml').exists(),not auth_only)
    if not auth_only:self.assertTrue((h/'userdata/addon_data/inputstream.adaptive/settings.xml').is_file())
    with sqlite3.connect(h/'userdata/Database/Addons33.db')as c:self.assertEqual(c.execute('SELECT addonID,updateRule FROM update_rules ORDER BY id').fetchall(),[('repository.keep',2),('plugin.video.themoviedb.helper',3),(ID,2),('plugin.video.themoviedb.helper',1),(ID,1)])
    self.assertEqual(k.commands.count('UpdateLocalAddons'),2)
 def test_future_and_foreign_source_fail_before_cleanup_or_any_native_rpc(self):
  for foreign in ('future',PLAYER,'resources/lib/modules/trakt.py','foreign.py'):
   with self.subTest(foreign=foreign):
    if (self.root/'profile').exists():shutil.rmtree(self.root/'profile')
    k,cfg,mods=self.environment(foreign=foreign);h=Path(cfg.HOME)
    before={p.relative_to(h):p.read_bytes()for p in h.rglob('*')if p.is_file()}
    self.install(cfg,mods)
    self.assertTrue(before=={p.relative_to(h):p.read_bytes()for p in h.rglob('*')if p.is_file()},'Profile changed before preflight succeeded')
    self.assertEqual(k.requests,[]);self.assertEqual(k.commands,[])
 def test_zip_destination_aliases_fail_before_native_rpc_rule_writes_or_cleanup(self):
  for alias in ('addons/./'+ID+'/'+PLAYER,'addons//'+ID+'/'+PLAYER,
                'addons/'+ID.upper()+'/'+PLAYER,'addons/'+ID.upper()+'/unreviewed.py'):
   with self.subTest(alias=alias):
    if (self.root/'profile').exists():shutil.rmtree(self.root/'profile')
    k,cfg,mods=self.environment();self.packaged(lambda data:data.__setitem__(alias,b'unreviewed alias'))
    h=Path(cfg.HOME);before={p.relative_to(h):p.read_bytes()for p in h.rglob('*')if p.is_file()}
    # Avoid displaying whole source bodies if the expected preflight fails.
    self.install(cfg,mods)
    self.assertTrue(before=={p.relative_to(h):p.read_bytes()for p in h.rglob('*')if p.is_file()},'Alias package reached cleanup or changed rules')
    self.assertEqual(k.requests,[]);self.assertEqual(k.commands,[])

 def test_rule_transaction_failure_keeps_all_existing_rules_and_profile(self):
  k,cfg,mods=self.environment(transaction_failure=True);h=Path(cfg.HOME)
  before={p.relative_to(h):p.read_bytes()for p in h.rglob('*')if p.is_file()}
  self.install(cfg,mods)
  self.assertTrue(before=={p.relative_to(h):p.read_bytes()for p in h.rglob('*')if p.is_file()},'Profile changed before preflight succeeded')
 def test_conflicting_managed_whitelist_stops_before_rule_changes_or_cleanup(self):
  for addon in (ID,'plugin.video.themoviedb.helper','dependency-umbrella'):
   with self.subTest(addon=addon):
    if (self.root/'profile').exists():shutil.rmtree(self.root/'profile')
    k,cfg,mods=self.environment();cfg.KEEPWHITELIST='true'
    mods['resources.libs.whitelist'].whitelist=lambda mode:[('Fixture',addon,addon)]
    if addon=='dependency-umbrella':mods['resources.libs.db'].depends_list=lambda fold:[ID]if fold=='dependency-umbrella'else[]
    messages=[];mods['xbmcgui'].Dialog().ok=lambda *args:messages.append(args)
    h=Path(cfg.HOME);before={p.relative_to(h):p.read_bytes()for p in h.rglob('*')if p.is_file()}
    self.install(cfg,mods)
    self.assertTrue(before=={p.relative_to(h):p.read_bytes()for p in h.rglob('*')if p.is_file()},'Profile changed before preflight succeeded')
    self.assertTrue(any('Edit My Whitelist'in str(args)for args in messages),messages)
    self.assertNotIn('UpdateLocalAddons',k.commands)
 def test_exact_managed_whitelist_target_is_allowed_and_keeps_its_userdata(self):
  k,cfg,mods=self.environment();cfg.KEEPWHITELIST='true';h=Path(cfg.HOME)
  shutil.rmtree(h/'addons'/ID)
  for n,b in self.provider().items():
   p=h/'addons'/ID/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
  mods['resources.libs.whitelist'].whitelist=lambda mode:[('Umbrella',ID,ID)]
  messages=[];mods['xbmcgui'].Dialog().ok=lambda *args:messages.append(args)
  self.install(cfg,mods)
  self.assertFalse((h/'userdata/keep-before-preflight.txt').exists(),messages)
  self.assertEqual((h/'addons'/ID/PLAYER).read_bytes(),self.provider()[PLAYER])
  self.assertEqual(self.values(h/'userdata/addon_data'/ID/'settings.xml')['remove.hdr'],'true')

 def test_frozen17_rejects_new_policy_before_native_setup(self):
  fixture=ROOT/'tests/fixtures/platform_compatibility_1_0_17.py'
  with zipfile.ZipFile(ROOT/'plugin.program.blacklanturninstaller/plugin.program.blacklanturninstaller-1.0.17.zip')as archive:self.assertEqual(fixture.read_bytes(),archive.read('plugin.program.blacklanturninstaller/resources/libs/platform_compatibility.py'))
  s=importlib.util.spec_from_file_location('frozen17',fixture);old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
  k,cfg,mods=self.environment()
  with patch.dict(sys.modules,mods),self.assertRaisesRegex(old.CompatibilityError,'Update BlackLanturn Installer'):old.prepare(self.packaged(),k)
  self.assertEqual(k.requests,[]);self.assertEqual(k.commands,[])
 def test_wrong_patch_minimum_or_payload_rejected_before_native_setup(self):
  k,cfg,mods=self.environment();m=self.module()
  for change in ({'installer_min_version':'1.0.17'},{'umbrella_patch':'unknown'},{'umbrella_version':'6.8.0'}):
   with patch.dict(sys.modules,mods),self.subTest(change=change),self.assertRaises(m.CompatibilityError):m.prepare(self.packaged(policy=dict(POLICY,**change)),k,home=cfg.HOME)
  self.assertEqual(k.requests,[]);self.assertEqual(k.commands,[])

if __name__=='__main__':unittest.main()
