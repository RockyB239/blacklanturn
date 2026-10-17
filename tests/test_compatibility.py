import ast
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1] / 'installer-source/plugin.program.blacklanturninstaller/resources/libs'
POLICY = {'schema': 1, 'edition': 'apple', 'kodi_major': 21}

class Kodi:
    def __init__(self, present=True, installed=True, disabled=False, repo_mode=0):
        self.present = present
        self.installed = installed
        self.disabled = disabled
        self.repo_mode = repo_mode
        self.requests = []
        self.commands = []
    def executeJSONRPC(self, raw):
        req = json.loads(raw); self.requests.append(req)
        method, p = req['method'], req.get('params', {})
        if method == 'Addons.GetAddonDetails':
            aid = p['addonid']
            if aid == 'repository.xbmc.org' or self.present:
                return json.dumps({'jsonrpc':'2.0','id':1,'result':{'addon':{'addonid':aid,'version':'21.5.25' if aid=='inputstream.adaptive' else '5.1.0','enabled':not self.disabled,'path':'/native/'+aid}}})
            return json.dumps({'jsonrpc':'2.0','id':1,'error':{'code':-32602,'message':'Invalid params.'}})
        if method == 'Addons.SetAddonEnabled':
            self.disabled = False
            return json.dumps({'jsonrpc':'2.0','id':1,'result':'OK'})
        if method == 'Settings.GetSettingValue':
            assert p['setting']=='addons.updatemode', 'Wrong Kodi repository policy setting'
            return json.dumps({'jsonrpc':'2.0','id':1,'result':{'value':self.repo_mode}})
        raise AssertionError(method)
    def executebuiltin(self, command, wait=False):
        self.commands.append(command)
        if command.startswith('InstallAddon(') and self.installed:
            self.present = True
    def getInfoLabel(self, label):
        return '21.3' if label == 'System.BuildVersion' else ''
    def getCondVisibility(self, condition):
        return condition in ('System.Platform.OSX','System.Platform.Darwin')
    def Monitor(self):
        return types.SimpleNamespace(abortRequested=lambda:False)

class CompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def archive(self, policy=POLICY, extras=None):
        path = self.root/'build.zip'
        with zipfile.ZipFile(path,'w') as z:
            z.writestr('addons/skin.test/addon.xml','<addon id="skin.test" version="1.0.0"/>')
            if policy is not None: z.writestr('userdata/blacklanturn-build.json',json.dumps(policy))
            for name, data in (extras or {}).items(): z.writestr(name,data)
        return path
    def module(self):
        p=ROOT/'platform_compatibility.py'
        if not p.exists(): self.fail('Approved platform safeguard is missing')
        spec=importlib.util.spec_from_file_location('platform_compatibility',p)
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    def test_existing_components_are_kept_without_install_or_settings_changes(self):
        m=self.module(); k=Kodi(); result=m.prepare(self.archive(),k)
        self.assertEqual(result['addon_ids'],['skin.test'])
        self.assertEqual(k.commands,[])
        self.assertTrue(all(r['method']=='Addons.GetAddonDetails' for r in k.requests))
    def test_missing_component_uses_kodi_install_then_rechecks(self):
        m=self.module(); k=Kodi(present=False)
        m.prepare(self.archive(),k)
        self.assertIn('InstallAddon(inputstream.adaptive)',k.commands)
        self.assertTrue(k.present)
    def test_cancelled_dependency_install_blocks_the_build(self):
        m=self.module(); k=Kodi(present=False,installed=False)
        with self.assertRaises(m.CompatibilityError):m.prepare(self.archive(),k)
    def test_disabled_component_is_enabled_without_replacing_it(self):
        m=self.module(); k=Kodi(disabled=True)
        m.prepare(self.archive(),k)
        self.assertFalse(k.disabled);self.assertEqual(k.commands,[])
    def test_unknown_repository_policy_blocks_automatic_download(self):
        m=self.module(); k=Kodi(present=False,repo_mode=1)
        with self.assertRaises(m.CompatibilityError):m.prepare(self.archive(),k)
        self.assertEqual(k.commands,[])
    def test_wrong_edition_stops_without_installing_anything(self):
        m=self.module(); k=Kodi()
        with self.assertRaises(m.CompatibilityError):m.prepare(self.archive(dict(POLICY,edition='general')),k)
        self.assertEqual(k.commands,[])
    def test_wrong_kodi_major_stops_before_setup(self):
        m=self.module();k=Kodi();k.getInfoLabel=lambda label:'22.0'
        with self.assertRaises(m.CompatibilityError):m.prepare(self.archive(),k)
        self.assertEqual(k.requests,[])
    def test_payload_cannot_overwrite_native_components(self):
        m=self.module();k=Kodi()
        with self.assertRaises(m.CompatibilityError):m.prepare(self.archive(extras={'addons/inputstream.adaptive/addon.xml':'<addon/>'}),k)
        self.assertEqual(k.requests,[])
    def test_payload_cannot_replace_device_addon_registry(self):
        m=self.module();k=Kodi()
        with self.assertRaises(m.CompatibilityError):m.prepare(self.archive(extras={'userdata/Database/Addons33.db':b'old database'}),k)
        self.assertEqual(k.requests,[])
    def test_traversal_archive_stops_before_setup(self):
        m=self.module();k=Kodi()
        with self.assertRaises(m.CompatibilityError):m.prepare(self.archive(extras={'../outside.txt':'bad'}),k)
        self.assertEqual(k.requests,[])
    def test_html_download_stops_before_setup(self):
        m=self.module(); k=Kodi();p=self.root/'build.zip';p.write_text('<html>Download failed</html>')
        with self.assertRaises(m.CompatibilityError):m.prepare(p,k)
        self.assertEqual(k.requests,[])
    def test_kodi_21_legacy_archive_still_installs_without_new_policy(self):
        m=self.module();k=Kodi()
        self.assertEqual(m.prepare(self.archive(None),k)['addon_ids'],['skin.test'])
        self.assertEqual(k.commands,[])

    def install_environment(self, kodi):
        cfg=types.SimpleNamespace(ADDON_ID='plugin.program.blacklanturninstaller',ADDONTITLE='BlackLanturn',KODIV=21.3,COLOR1='white',COLOR2='cyan',MYBUILDS=str(self.root/'My_Builds'),HOME=str(self.root/'profile'),EXCLUDES=['plugin.program.blacklanturninstaller'],clear_setting=lambda *a:None,set_setting=lambda *a:None,UPDATECHECK=7)
        for key in ('KEEPTRAKT','KEEPDEBRID','KEEPLOGIN','KEEPREPOS','KEEPSUPER','KEEPWHITELIST','KEEPSOURCES','KEEPFAVS','KEEPPROFILES','KEEPPLAYERCORE','KEEPGUISETTINGS','KEEPADVANCED'):setattr(cfg,key,'false')
        cfg.ADDON_PATH=str(ROOT.parent.parent);cfg.LOGFILES=[];cfg.USERDATA=str(Path(cfg.HOME)/'userdata');cfg.ADDONS=str(Path(cfg.HOME)/'addons');cfg.DATABASE=str(Path(cfg.USERDATA)/'Database')
        modules={}
        for n in ('resources','resources.libs','resources.libs.common','resources.libs.gui'):
            modules[n]=types.ModuleType(n);modules[n].__path__=[str(ROOT.parent if n=='resources' else ROOT)]
        log=types.SimpleNamespace(log=lambda *a,**k:None,log_notify=lambda *a,**k:None)
        tools=types.SimpleNamespace(ensure_folders=lambda p:Path(p).mkdir(parents=True,exist_ok=True),percentage=lambda a,b:a/max(b,1)*100,get_date=lambda **kw:'2026-10-15',kill_kodi=lambda **kw:None)
        skin=types.SimpleNamespace(skin_to_default=lambda *a:None,look_and_feel_data=lambda *a:None)
        progress=types.SimpleNamespace(create=lambda *a:None,update=lambda *a:None,close=lambda:None,iscanceled=lambda:False)
        dialog=types.SimpleNamespace(yesno=lambda *a,**k:True,ok=lambda *a:None)
        for n,obj in [('resources.libs.common.logging',log),('resources.libs.common.tools',tools),('resources.libs.skin',skin),('resources.libs.update',types.SimpleNamespace(addon_updates=lambda *a:None)),('resources.libs.db',types.SimpleNamespace(latest_db=lambda *a:'Addons33.db',fix_metas=lambda:None,addon_database=lambda *a,**k:None,force_check_updates=lambda **k:None)),('resources.libs.check',types.SimpleNamespace(check_build=lambda name,key:{'kodi':'21.3','version':'1.0','url':'https://example.invalid/build.zip','theme':'http://'}[key])),('resources.libs.extract',types.SimpleNamespace(all=lambda *a,**kw:(100,0,''))),('resources.libs.common.config',types.SimpleNamespace(CONFIG=cfg)),('resources.libs.gui.build_menu',types.SimpleNamespace(BuildMenu=lambda:types.SimpleNamespace(theme_count=lambda name:0)))]:modules[n]=obj
        modules['xbmc']=kodi;modules['xbmcgui']=types.SimpleNamespace(Dialog=lambda:dialog,DialogProgress=lambda:progress)
        kodi.sleep=lambda t:None
        # Use the real path/config initialization and real wipe in a disposable filesystem.
        tree=ast.parse((ROOT/'common/config.py').read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef))
        init=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='init_paths')
        env={'os':os,'xbmcvfs':types.SimpleNamespace(translatePath=lambda p:str(Path(cfg.HOME)/p.removeprefix('special://').strip('/')))}
        exec(compile(ast.Module(body=[init],type_ignores=[]),'config.py','exec'),env);env['init_paths'](cfg)
        cfg.HOME=str(self.root/'profile');cfg.ADDONS=str(Path(cfg.HOME)/'addons')
        cfg.USERDATA=str(Path(cfg.HOME)/'userdata');cfg.ADDON_DATA=str(Path(cfg.USERDATA)/'addon_data');cfg.PLUGIN_DATA=str(Path(cfg.ADDON_DATA)/cfg.ADDON_ID);cfg.DATABASE=str(Path(cfg.USERDATA)/'Database')
        cfg.get_setting=lambda key:'false'
        def typed_set_setting(key,value):
            if not isinstance(value,str):raise TypeError('Kodi setSetting requires text')
        cfg.set_setting=typed_set_setting
        wt=ast.parse((ROOT/'install.py').read_text());fn=next(n for n in wt.body if isinstance(n,ast.FunctionDef) and n.name=='wipe')
        wipe_env={'CONFIG':cfg,'xbmcgui':modules['xbmcgui'],'os':os,'glob':__import__('glob'),'shutil':shutil}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'install.py','exec'),wipe_env)
        modules['resources.libs.install']=types.SimpleNamespace(wipe=wipe_env['wipe'])
        Path(cfg.MYBUILDS).mkdir(parents=True,exist_ok=True)
        source=self.archive();modules['resources.libs.downloader']=types.SimpleNamespace(Downloader=lambda:types.SimpleNamespace(download=lambda url,dest:shutil.copy2(source,dest)))
        return cfg,modules
    def test_failed_dependency_check_never_wipes_existing_profile(self):
        cfg,modules=self.install_environment(Kodi(present=False,installed=False))
        protected=Path(cfg.HOME)/'userdata/existing.txt';protected.parent.mkdir(parents=True);protected.write_text('keep existing setup')
        with patch.dict(sys.modules,modules):
            spec=importlib.util.spec_from_file_location('wizard_under_test',ROOT/'wizard.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
            w.Wizard().build('Apple TV and Mac')
        self.assertTrue(protected.exists(),'The existing profile was wiped before playback setup succeeded')
        self.assertEqual(protected.read_text(),'keep existing setup')
    def test_real_cleanup_keeps_native_binaries_and_preferences(self):
        cfg,modules=self.install_environment(Kodi())
        native=Path(cfg.HOME)/'addons/inputstream.adaptive/component.dylib';prefs=Path(cfg.HOME)/'userdata/addon_data/inputstream.adaptive/settings.xml';old=Path(cfg.HOME)/'addons/obsolete/file.txt'
        for p in (native,prefs,old):p.parent.mkdir(parents=True,exist_ok=True);p.write_text('original bytes')
        with patch.dict(sys.modules,modules):modules['resources.libs.install'].wipe()
        self.assertTrue(native.exists(),'Cleanup removed the platform-specific playback binary')
        self.assertTrue(prefs.exists(),'Cleanup removed existing playback preferences')
        self.assertFalse(old.exists())

if __name__=='__main__': unittest.main()

class ReleaseRegressionTests(unittest.TestCase):
    setUp=CompatibilityTests.setUp
    tearDown=CompatibilityTests.tearDown
    archive=CompatibilityTests.archive
    module=CompatibilityTests.module
    install_environment=CompatibilityTests.install_environment
    def test_native_preferences_survive_full_wipe_and_real_extraction(self):
        cfg,mods=self.install_environment(Kodi())
        prefs=Path(cfg.HOME)/'userdata/addon_data/inputstream.adaptive/settings.xml';prefs.parent.mkdir(parents=True);prefs.write_text('device-specific preferences')
        source=self.archive(None,{'userdata/addon_data/inputstream.adaptive/settings.xml':'payload preferences'})
        mods['resources.libs.whitelist']=types.SimpleNamespace(whitelist=lambda mode:[])
        mods['resources.libs.common.tools'].convert_size=lambda value:str(value)
        with patch.dict(sys.modules,mods):
            mods['resources.libs.install'].wipe()
            spec=importlib.util.spec_from_file_location('extract_under_test',ROOT/'extract.py');ex=importlib.util.module_from_spec(spec);spec.loader.exec_module(ex)
            result=ex.all(str(source),cfg.HOME)
        self.assertEqual(result[:2],(100,0));self.assertEqual(prefs.read_text(),'device-specific preferences')
        self.assertTrue((Path(cfg.HOME)/'addons/skin.test/addon.xml').is_file())
    def test_cancelled_real_download_never_reaches_profile_cleanup(self):
        cfg,mods=self.install_environment(Kodi())
        old=Path(cfg.HOME)/'userdata/existing.txt';old.parent.mkdir(parents=True);old.write_text('keep existing setup')
        body=self.archive().read_bytes()
        mods['resources.libs.common.tools'].open_url=lambda *a,**k:types.SimpleNamespace(headers={'content-length':str(len(body))},iter_content=lambda **kw:iter([body]),close=lambda:None)
        class Progress:
            def __init__(self): self.kind=''
            def create(self,title,text):self.kind=text
            def update(self,*args):pass
            def close(self):pass
            def iscanceled(self):return self.kind=='Downloading Content'
        mods['xbmcgui'].DialogProgress=Progress
        with patch.dict(sys.modules,mods):
            spec=importlib.util.spec_from_file_location('real_download',ROOT/'downloader.py');dl=importlib.util.module_from_spec(spec);spec.loader.exec_module(dl)
            mods['resources.libs.downloader'].Downloader=dl.Downloader
            spec=importlib.util.spec_from_file_location('wizard_cancel_test',ROOT/'wizard.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
            w.Wizard().build('Apple TV and Mac')
        self.assertTrue(old.exists(),'Cancel still reached cleanup')
    def test_kodi_21_2_is_rejected_before_component_setup(self):
        m=self.module();k=Kodi();k.getInfoLabel=lambda label:'21.2'
        with self.assertRaises(m.CompatibilityError):m.prepare(self.archive(),k)
        self.assertEqual(k.requests,[])

class LegacyNativeRegression(unittest.TestCase):
    setUp=CompatibilityTests.setUp
    tearDown=CompatibilityTests.tearDown
    archive=CompatibilityTests.archive
    module=CompatibilityTests.module
    def test_legacy_native_requirement_is_checked_before_cleanup(self):
        m=self.module();k=Kodi(present=False,installed=False)
        p=self.archive(None,{'addons/plugin.video.test/addon.xml':'<addon id="plugin.video.test" version="1"><requires><import addon="inputstream.adaptive" version="21.0.0"/></requires></addon>'})
        with self.assertRaises(m.CompatibilityError):m.prepare(p,k)
