"""Exact reviewed Coco concurrency payload, retained source and update protection."""
import hashlib,importlib.util,json,sqlite3,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];I=ROOT/'installer-source/plugin.program.blacklanturninstaller';LIB=I/'resources/libs';sys.path.insert(0,str(I));AID='script.module.cocoscrapers'
def load(name):
 s=importlib.util.spec_from_file_location('policy152_'+name,LIB/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class CocoPolicy(unittest.TestCase):
 def coco(self):
  self.assertTrue((LIB/'cocoscrapers_policy.py').is_file(),'Coco concurrency source is not protected by an exact-source policy')
  return load('cocoscrapers_policy')
 def archive(self):return ROOT/'compatibility/addons152/script.module.cocoscrapers.zip'
 def marker(self):return {'managed_update_policy':'kodi-version-epoch-1','inplace_update_policy':'bundled-code-1','bundle_registration_policy':'new-bundles-1','youtube_refresh_patch':'youtube-freshness-2','installer_min_version':'1.0.48','helper_sync_policy':'providers-1','cocoscrapers_policy':'parallel-airdate-1'}
 def test_floor48_is_required_only_for_the_exact_new_coco_policy(self):
  m=load('managed_versions')
  with patch.object(m,'verify_archive_metadata'):
   try:actual=m.prepare_policy(self.marker(),None)
   except ValueError:actual='new policy rejected'
   self.assertEqual(actual,'1.0.48')
   with self.assertRaises(ValueError):m.prepare_policy(dict(self.marker(),cocoscrapers_policy='unknown'),None)
   with self.assertRaises(ValueError):m.prepare_policy(dict(self.marker(),installer_min_version='1.0.47'),None)
   old=self.marker();old.pop('cocoscrapers_policy');old['installer_min_version']='1.0.47';self.assertEqual(m.prepare_policy(old,None),'1.0.47')
 def test_exact_archive_unknown_change_and_missing_policy_fail_closed(self):
  m=self.coco()
  with zipfile.ZipFile(self.archive()) as source,tempfile.TemporaryDirectory() as td:
   # The native build prefix is applied without altering archive source bytes.
   data={'addons/'+n:source.read(n) for n in source.namelist()}
   def archive(values):
    p=Path(td)/'build.zip'
    with zipfile.ZipFile(p,'w') as z:
     for n,raw in values.items():z.writestr(n,raw)
    return zipfile.ZipFile(p)
   with archive(data) as z:m.prepare(self.marker(),z,td)
   marker=self.marker();marker.pop('cocoscrapers_policy')
   with archive(data) as z,self.assertRaises(m.managed.ProtectionError):m.prepare(marker,z,td)
   target='addons/'+AID+'/lib/cocoscrapers/modules/source_utils.py';data[target]+=b'\n# unreviewed\n'
   with archive(data) as z,self.assertRaises(m.managed.ProtectionError):m.prepare(self.marker(),z,td)
 def test_legacy_target_without_coco_is_accepted_but_new_policy_requires_it(self):
  m=self.coco()
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'empty.zip'
   with zipfile.ZipFile(p,'w'):pass
   with zipfile.ZipFile(p) as z:
    self.assertIsNone(m.prepare({},z,td))
    with self.assertRaises(m.managed.ProtectionError):m.prepare(self.marker(),z,td)
 def test_unknown_installed_and_whitelist_source_fail_before_mutation(self):
  m=self.coco()
  with tempfile.TemporaryDirectory() as td,zipfile.ZipFile(self.archive()) as z:
   home=Path(td);z.extractall(home/'addons');m.verify_installed(home);m.verify_kept(home,{AID})
   p=home/'addons'/AID/'lib/cocoscrapers/modules/source_utils.py';p.write_bytes(p.read_bytes()+b'\n# foreign\n');before=p.read_bytes()
   with self.assertRaises(m.managed.ProtectionError):m.verify_installed(home)
   with self.assertRaises(m.managed.ProtectionError):m.verify_kept(home,{AID})
   self.assertEqual(p.read_bytes(),before)
 def test_epoch_beats_ordinary_upgrade_and_registry_keeps_unrelated_rule(self):
  m=self.coco();v=load('managed_versions');ordinary=load('standard_addons');updater=load('inplace_update')
  with zipfile.ZipFile(self.archive()) as z:
   raw=z.read(AID+'/addon.xml');self.assertNotEqual(v.normalize_metadata(AID,raw),raw)
   import xml.etree.ElementTree as E
   self.assertGreater(ordinary.compare(E.fromstring(raw).get('version'),'99.0.0'),0)
  self.assertIn(AID,ordinary.MANAGED);self.assertIn(AID,updater.MANAGED)
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'Addons33.db'
   with sqlite3.connect(p) as db:db.execute('CREATE TABLE update_rules(id integer primary key,addonID text,updateRule integer)');db.execute('INSERT INTO update_rules(addonID,updateRule) VALUES("unrelated",7)')
   m.protect(p);m.protect(p)
   with sqlite3.connect(p) as db:
    self.assertEqual(db.execute('SELECT updateRule FROM update_rules WHERE addonID=?',(AID,)).fetchall(),[(1,)])
    self.assertEqual(db.execute('SELECT updateRule FROM update_rules WHERE addonID="unrelated"').fetchall(),[(7,)])
if __name__=='__main__':unittest.main()
