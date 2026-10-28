"""Prevent a BlackLanturn release from retaining the known outdated targets."""
from pathlib import Path
import json,unittest
ROOT=Path(__file__).resolve().parents[1]
class CurrentAddonTargets(unittest.TestCase):
 def test_managed_targets_include_current_reviewed_upstream_versions(self):
  policy=json.loads((ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/managed-versions.json').read_text())
  for aid,version in [('plugin.video.umbrella','6.7.98'),('plugin.video.themoviedb.helper','6.19.2')]:
   with self.subTest(addon=aid):self.assertEqual(policy['addons'][aid][0]['upstream_version'],version)
 def test_release_inputs_include_current_upnext_and_complete_provider_trees(self):
  p=ROOT/'compatibility/addons134/manifest.json';self.assertTrue(p.is_file(),'No reviewed complete current-source release inputs')
  x=json.loads(p.read_text())
  for aid,version in [('plugin.video.umbrella','1:6.7.98+blacklanturn.1'),('plugin.video.themoviedb.helper','1:6.19.2+blacklanturn.1'),('service.upnext','1.3.0')]:
   with self.subTest(addon=aid):self.assertEqual(x['addons'][aid]['version'],version)

 def test_preceding_managed97_tree_remains_migratable(self):
  import importlib.util,tempfile,zipfile
  lib=ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/libs'
  spec=importlib.util.spec_from_file_location('migration134',lib/'managed_addons.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  with tempfile.TemporaryDirectory() as tmp:
   home=Path(tmp)
   with zipfile.ZipFile(ROOT/'compatibility/current-addons/plugin.video.umbrella.zip') as z:z.extractall(home/'addons')
   self.assertEqual(m.verify_installed(home),'plugin.video.umbrella')
