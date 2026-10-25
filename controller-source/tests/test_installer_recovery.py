"""Recover the update entrypoint even when the Installer directory is missing."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'controller-source/addon/installer_recovery.py'
LIB=ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/libs'
SELF='plugin.program.blacklanturninstaller'
META=('blacklanturn-build.json','blacklanturn-releases.json','blacklanturn-install-complete.json')

class Recovery(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)/'home';(self.home/'addons').mkdir(parents=True)
        (self.home/'userdata').mkdir();self.work=self.home/'addons/.blacklanturn-update'
        self.target=self.home/'addons'/SELF;self.old=self.work/'old'/SELF
        self.saved=self.home/'userdata/private-settings.json';self.saved.write_bytes(b'preserve preferences and authorizations')
        self.unrelated=self.home/'addons/plugin.user/custom.py';self.unrelated.parent.mkdir();self.unrelated.write_bytes(b'custom add-on')
        self.assertTrue(SOURCE.is_file(),'Independent Installer recovery entrypoint is missing')
        spec=importlib.util.spec_from_file_location('recover_entry_test',SOURCE);self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
    def core(self,where,version='1.0.32'):
        where.mkdir(parents=True,exist_ok=True)
        (where/'addon.xml').write_text('<addon id="'+SELF+'" version="'+version+'"/>')
        lib=where/'resources/libs';lib.mkdir(parents=True)
        for name in ('inplace_update.py','standard_addons.py','archive_paths.py'):shutil.copyfile(LIB/name,lib/name)
    def journal(self,status='applying'):
        self.work.mkdir(parents=True,exist_ok=True)
        state={'schema':1,'status':status,'addons':{SELF:{'before':{'old':'a'*64},'after':{'new':'b'*64},'started':True,'enabled_before':True}},'metadata':{k:{'started':False,'existed':False} for k in META}}
        (self.work/'journal.json').write_text(json.dumps(state,sort_keys=True))
    def preserved(self):
        self.assertEqual(self.saved.read_bytes(),b'preserve preferences and authorizations')
        self.assertEqual(self.unrelated.read_bytes(),b'custom add-on')
    def test_normal_startup_performs_no_module_import_or_writes(self):
        self.assertFalse(self.m.recover_installer(self.home));self.assertFalse(self.work.exists());self.preserved()
    def test_missing_installer_restored_from_real_backup_core(self):
        self.core(self.old);self.journal();self.assertFalse(self.target.exists())
        self.assertTrue(self.m.recover_installer(self.home))
        self.assertTrue((self.target/'resources/libs/inplace_update.py').is_file());self.assertFalse(self.work.exists());self.preserved()
    def test_incomplete_update_replaces_new_installer_with_backup(self):
        self.core(self.old);self.core(self.target,'1.0.33');self.journal()
        self.assertTrue(self.m.recover_installer(self.home));self.assertIn('1.0.32',(self.target/'addon.xml').read_text());self.preserved()
    def test_committed_update_keeps_new_installer(self):
        self.core(self.old);self.core(self.target,'1.0.33');self.journal('committed')
        self.assertTrue(self.m.recover_installer(self.home));self.assertIn('1.0.33',(self.target/'addon.xml').read_text());self.assertFalse(self.work.exists());self.preserved()
    def test_active_writer_is_never_rolled_back(self):
        import fcntl
        self.core(self.old);self.journal()
        with (self.home/'addons/.blacklanturn-update.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.assertFalse(self.m.recover_installer(self.home));self.assertTrue(self.old.exists());self.assertFalse(self.target.exists())
        self.preserved()
    def test_ordinary_addon_update_does_not_load_installer_core(self):
        self.journal();p=self.work/'journal.json';s=json.loads(p.read_text());s['addons']={'plugin.other':s['addons'][SELF]};p.write_text(json.dumps(s))
        self.assertFalse(self.m.recover_installer(self.home));self.assertTrue(p.exists());self.preserved()
    def test_linked_backup_is_refused_without_executing_it(self):
        external=self.home/'external';self.core(external);self.old.parent.mkdir(parents=True);self.old.symlink_to(external,target_is_directory=True);self.journal()
        with self.assertRaises(self.m.RecoveryError):self.m.recover_installer(self.home)
        self.assertTrue(self.old.is_symlink());self.preserved()
    def test_corrupt_journal_is_preserved_and_reports_recovery_failure(self):
        self.work.mkdir();(self.work/'journal.json').write_text('{bad')
        with self.assertRaises(self.m.RecoveryError):self.m.recover_installer(self.home)
        self.assertTrue((self.work/'journal.json').exists());self.preserved()
    def test_missing_both_entrypoints_retains_recovery_data(self):
        self.journal()
        with self.assertRaises(self.m.RecoveryError):self.m.recover_installer(self.home)
        self.assertTrue((self.work/'journal.json').exists());self.preserved()

    def kodi(self,version='1.0.32',enabled=False,fail=False):
        import types
        state={'version':version,'enabled':enabled,'fail':fail}
        def rpc(raw):
            req=json.loads(raw)
            if req['method']=='Addons.SetAddonEnabled':
                if state['fail']:return json.dumps({'error':{'code':-1,'message':'registration failed'}})
                state['enabled']=req['params']['enabled'];return json.dumps({'result':'OK'})
            return json.dumps({'result':{'addon':{'addonid':SELF,'version':state['version'],'enabled':state['enabled']}}})
        kodi=types.SimpleNamespace(executeJSONRPC=rpc,executebuiltin=lambda *a,**k:None)
        def factory(aid):
            if aid!=SELF or not state['enabled']:raise RuntimeError('Unknown addon id')
            return types.SimpleNamespace(getAddonInfo=lambda key:state['version'])
        return kodi,factory,state
    def test_recovery_restores_registration_and_native_addon_usability(self):
        self.core(self.old);self.journal();k,factory,state=self.kodi()
        self.assertTrue(self.m.recover_installer(self.home,k,factory));self.assertTrue(state['enabled'])
        self.assertFalse((self.home/'addons/.blacklanturn-installer-registration.json').exists());self.preserved()
    def test_failed_registration_is_durable_and_retried_without_journal(self):
        self.core(self.old);self.journal();k,factory,state=self.kodi(fail=True)
        with self.assertRaises(self.m.RecoveryError):self.m.recover_installer(self.home,k,factory)
        pending=self.home/'addons/.blacklanturn-installer-registration.json'
        self.assertTrue(pending.is_file());self.assertFalse(self.work.exists());self.assertTrue(self.target.is_dir())
        state['fail']=False
        self.assertTrue(self.m.recover_installer(self.home,k,factory));self.assertTrue(state['enabled']);self.assertFalse(pending.exists());self.preserved()
    def test_prior_disabled_preference_is_preserved(self):
        self.core(self.old);self.journal();p=self.work/'journal.json';s=json.loads(p.read_text());s['addons'][SELF]['enabled_before']=False;p.write_text(json.dumps(s))
        k,factory,state=self.kodi(enabled=True)
        self.assertTrue(self.m.recover_installer(self.home,k,factory));self.assertFalse(state['enabled']);self.preserved()
