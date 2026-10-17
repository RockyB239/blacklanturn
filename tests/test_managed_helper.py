"""Catch unprotected installs, changed helper code, and loss of unrelated update rules."""
import importlib.util,json,sqlite3,tempfile,unittest,zipfile,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/libs'
BASE=ROOT/'compatibility/helper-empty-cache/upstream-6.17.9.zip'
PATCH=ROOT/'compatibility/helper-empty-cache/candidate'
ID='plugin.video.themoviedb.helper'
class ManagedTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def module(self):
  p=LIB/'managed_addons.py';self.assertTrue(p.exists(),'Installer does not protect the patched Helper')
  s=importlib.util.spec_from_file_location('managed_addons',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
 def archive(self,change=None):
  p=self.root/'helper.zip'
  with zipfile.ZipFile(BASE) as z:data={n:z.read(n) for n in z.namelist() if n.startswith('addons/'+ID+'/')}
  for name,rel in [('lists_default.py','lists_default.py'),('lists_trakt.py','trakt/lists_standard.py'),('lists_search.py','tmdb/lists_search.py')]:data['addons/'+ID+'/resources/tmdbhelper/lib/items/directories/'+rel]=(PATCH/name).read_bytes()
  if change:change(data)
  with zipfile.ZipFile(p,'w') as z:
   for n,d in data.items():z.writestr(n,d)
  return p
 def db(self,valid=True):
  p=self.root/'Addons33.db'
  with sqlite3.connect(p) as c:
   c.execute('CREATE TABLE update_rules (id integer primary key, addonID text, updateRule integer)' if valid else 'CREATE TABLE unrelated (value text)')
   if valid:c.execute('INSERT INTO update_rules VALUES (1,?,2)',('repository.keep',))
  return p
 def test_verified_payload_accepted(self):
  m=self.module()
  with zipfile.ZipFile(self.archive()) as z:self.assertEqual(m.verify_archive(z),ID)
 def test_reverted_cache_fix_rejected(self):
  m=self.module()
  with zipfile.ZipFile(self.archive(lambda d:d.__setitem__('addons/'+ID+'/resources/tmdbhelper/lib/items/directories/lists_default.py',b'old code'))) as z:
   with self.assertRaises(m.ProtectionError):m.verify_archive(z)
 def test_unknown_future_helper_rejected(self):
  m=self.module()
  with zipfile.ZipFile(self.archive(lambda d:d.__setitem__('addons/'+ID+'/addon.xml',d['addons/'+ID+'/addon.xml'].replace(b'6.17.9',b'6.18.0')))) as z:
   with self.assertRaises(m.ProtectionError):m.verify_archive(z)
 def test_added_python_code_rejected(self):
  m=self.module()
  with zipfile.ZipFile(self.archive(lambda d:d.__setitem__('addons/'+ID+'/unexpected.py',b'pass'))) as z:
   with self.assertRaises(m.ProtectionError):m.verify_archive(z)
 def test_pin_persists_without_changing_other_addons(self):
  m=self.module();p=self.db();m.protect(p);m.protect(p)
  with sqlite3.connect(p) as c:
   self.assertEqual(c.execute('SELECT addonID,updateRule FROM update_rules ORDER BY id').fetchall(),[('repository.keep',2),(ID,1)])
 def test_missing_registry_not_created(self):
  m=self.module();p=self.root/'missing.db'
  with self.assertRaises(m.ProtectionError):m.protect(p)
  self.assertFalse(p.exists())
 def test_unsupported_registry_is_not_modified(self):
  m=self.module();p=self.db(False);before=p.read_bytes()
  with self.assertRaises(m.ProtectionError):m.protect(p)
  self.assertEqual(p.read_bytes(),before)
 def test_existing_helper_rule_retained(self):
  m=self.module();p=self.db()
  with sqlite3.connect(p) as c:c.execute('INSERT INTO update_rules VALUES (2,?,3)',(ID,))
  m.protect(p)
  with sqlite3.connect(p) as c:self.assertEqual(c.execute('SELECT updateRule FROM update_rules WHERE addonID=? ORDER BY updateRule',(ID,)).fetchall(),[(1,),(3,)])
if __name__=='__main__':unittest.main()

from test_compatibility import CompatibilityTests,Kodi
from unittest.mock import patch
import sys,types,shutil
class ManagedInstallTests(CompatibilityTests):
 def protected_archive(self,changes=None):
  fixture=ManagedTests();fixture.root=self.root
  with zipfile.ZipFile(fixture.archive(changes)) as z:extras={n:z.read(n) for n in z.namelist()}
  return self.archive({'schema':2,'edition':'apple','kodi_major':21,'helper_patch':'empty-cache-1'},extras)
 def test_schema2_missing_patch_is_rejected_before_cleanup(self):
  cfg,mods=self.install_environment(Kodi());self.archive({'schema':2,'edition':'apple','kodi_major':21})
  old=Path(cfg.HOME)/'userdata/keep.txt';old.parent.mkdir(parents=True);old.write_text('keep')
  with patch.dict(sys.modules,mods):
   spec=importlib.util.spec_from_file_location('wizard',LIB/'wizard.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w);w.Wizard().build('Apple TV and Mac')
  self.assertEqual(old.read_text(),'keep')
 def test_unavailable_update_registry_stops_before_wipe(self):
  cfg,mods=self.install_environment(Kodi());self.protected_archive()
  old=Path(cfg.HOME)/'userdata/keep.txt';old.parent.mkdir(parents=True);old.write_text('keep')
  with patch.dict(sys.modules,mods):
   spec=importlib.util.spec_from_file_location('wizard',LIB/'wizard.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w);w.Wizard().build('Apple TV and Mac')
  self.assertEqual(old.read_text(),'keep')
 def test_full_install_protects_and_keeps_native_preferences(self):
  k=Kodi();cfg,mods=self.install_environment(k);cfg.DATABASE=str(Path(cfg.HOME)/'userdata/Database');self.protected_archive();db=Path(cfg.DATABASE)/'Addons33.db';db.parent.mkdir(parents=True)
  with sqlite3.connect(db) as c:c.execute('CREATE TABLE update_rules(id integer primary key,addonID text,updateRule integer)');c.execute("INSERT INTO update_rules VALUES (1,'repository.keep',2)")
  prefs=Path(cfg.HOME)/'userdata/addon_data/inputstream.adaptive/settings.xml';prefs.parent.mkdir(parents=True);prefs.write_text('preserve native prefs')
  mods['resources.libs.whitelist']=types.SimpleNamespace(whitelist=lambda mode:[]);mods['resources.libs.common.tools'].convert_size=lambda value:str(value);mods['resources.libs.common.tools'].kodi_version=lambda:21.3
  with patch.dict(sys.modules,mods):
   spec=importlib.util.spec_from_file_location('real_extract',LIB/'extract.py');ex=importlib.util.module_from_spec(spec);spec.loader.exec_module(ex);mods['resources.libs.extract'].all=ex.all
   spec=importlib.util.spec_from_file_location('wizard',LIB/'wizard.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w);w.Wizard().build('Apple TV and Mac')
  self.assertEqual(prefs.read_text(),'preserve native prefs')
  with sqlite3.connect(db) as c:self.assertEqual(c.execute('SELECT addonID,updateRule FROM update_rules ORDER BY id').fetchall(),[('repository.keep',2),(ID,1)])
  installed=Path(cfg.HOME)/'addons'/ID/'resources/tmdbhelper/lib/items/directories/lists_default.py'
  self.assertEqual(hashlib.sha256(installed.read_bytes()).hexdigest(),'f2b0ae2a7165499177147aa5d13150271460ea3331c83e471ad453a38682c02a')
  self.assertIn('UpdateLocalAddons',k.commands)

class OldInstallerTests(ManagedInstallTests):
 def test_old_installer_rejects_before_any_device_setup(self):
  source=ROOT/'tests/fixtures/platform_compatibility_1_0_9.py'
  spec=importlib.util.spec_from_file_location('old_compat',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  k=Kodi()
  with self.assertRaises(m.CompatibilityError):m.prepare(self.protected_archive(),k)
  self.assertEqual(k.requests,[])
