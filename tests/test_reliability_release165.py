import importlib.util,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
class Release165Gate(unittest.TestCase):
 def gate(self):
  s=importlib.util.spec_from_file_location('reliability165_versions',R/'installer-source/plugin.program.blacklanturninstaller/resources/libs/managed_versions.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.verify_archive_metadata=lambda _:None;return m
 def marker(self):return dict(managed_update_policy='kodi-version-epoch-1',inplace_update_policy='bundled-code-1',bundle_registration_policy='new-bundles-1',helper_sync_policy='providers-1',cocoscrapers_policy='parallel-airdate-1',shutdown_patch='retained-monitor-1',youtube_refresh_patch='youtube-freshness-2',installer_min_version='1.0.52',reliability_patch='navigation-focus-1')
 def test_known_reliability_payload_requires52(self):self.assertEqual(self.gate().prepare_policy(self.marker(),None),'1.0.52')
 def test_reliability_payload_cannot_downgrade_minimum(self):
  m=self.marker();m['installer_min_version']='1.0.51'
  with self.assertRaises(ValueError):self.gate().prepare_policy(m,None)
 def test_unknown_reliability_revision_rejected(self):
  m=self.marker();m['reliability_patch']='future'
  with self.assertRaises(ValueError):self.gate().prepare_policy(m,None)
 def test_previous_shutdown_payload_remains51(self):
  m=self.marker();m.pop('reliability_patch');m['installer_min_version']='1.0.51';self.assertEqual(self.gate().prepare_policy(m,None),'1.0.51')

class ProviderRelease165Gate(Release165Gate):
 def test_group_policy_minimum_matches_release_gate(self):
  import ast,types
  for name in ('helper_providers','cocoscrapers_policy'):
   path=R/'installer-source/plugin.program.blacklanturninstaller/resources/libs'/(name+'.py');fn=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='prepare');calls=[]
   class Rejected(Exception):pass
   managed=types.SimpleNamespace(ProtectionError=Rejected,HELPER='helper',PREFIX='prefix/',_versions=types.SimpleNamespace(upstream_version=lambda *x:'6.19.3',normalize_metadata=lambda *x:b'upstream'))
   ns={'managed':managed,'POLICY':'parallel-airdate-1','ID':'script.module.cocoscrapers','verify_archive':lambda _:calls.append('archive'),'verify_installed':lambda _:calls.append('installed')};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(path),'exec'),ns);archive=types.SimpleNamespace(read=lambda _:b'managed',namelist=lambda:['addons/script.module.cocoscrapers/addon.xml'])
   with self.subTest(provider=name):
    ns['prepare'](self.marker(),archive,'profile');self.assertEqual(calls,['archive','installed'])
    for changes in ({'installer_min_version':'1.0.51'},{'reliability_patch':'future'},{'shutdown_patch':None}):
     with self.subTest(changes=changes),self.assertRaises(Rejected):ns['prepare'](dict(self.marker(),**changes),archive,'profile')
