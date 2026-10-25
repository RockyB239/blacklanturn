"""Every managed Helper source is checked before destructive install work."""
import hashlib,importlib.util,json,shutil,tempfile,unittest,zipfile
from pathlib import Path
R=Path(__file__).resolve().parents[1];LIB=R/'installer-source/plugin.program.blacklanturninstaller/resources/libs';AID='plugin.video.themoviedb.helper'
class InstalledHelper(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.home=Path(self.t.name);self.addon=self.home/'addons'/AID;self.addon.mkdir(parents=True)
  spec=importlib.util.spec_from_file_location('installed_current_helper',LIB/'managed_addons.py');self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
 def seed(self):
  m=json.loads((R/'compatibility/current-addons/manifest.json').read_text())['addons'][AID]
  with zipfile.ZipFile(R/'compatibility/current-addons'/m['archive']) as z:z.extractall(self.home/'addons')
 def test_unknown_source_refuses_before_cleanup(self):
  (self.addon/'addon.xml').write_text('<addon id="plugin.video.themoviedb.helper" version="999.0"/>');(self.addon/'foreign.py').write_text('pass')
  with self.assertRaises(self.m.ProtectionError):self.m.verify_installed(self.home,network=True,youtube=True)
  self.assertTrue((self.addon/'foreign.py').exists())
 def test_linked_helper_directory_refuses(self):
  self.addon.rmdir();other=self.home/'unrelated';other.mkdir();self.addon.symlink_to(other,target_is_directory=True)
  with self.assertRaises(self.m.ProtectionError):self.m.verify_installed(self.home)
 def test_current_complete_tree_passes(self):
  self.seed();self.m.verify_installed(self.home,network=True,youtube=True)
 def test_extra_file_in_current_tree_refuses(self):
  self.seed();(self.addon/'foreign.py').write_text('pass')
  with self.assertRaises(self.m.ProtectionError):self.m.verify_installed(self.home)

 def test_reviewed_stock_current_helper_is_safe_upgrade_input(self):
  with zipfile.ZipFile(R/'compatibility/current-addons/helper-upstream-6.18.2.zip') as z:z.extractall(self.home/'addons')
  self.m.verify_installed(self.home)
 def test_known_legacy6179_patched_tree_is_safe_upgrade_input(self):
  prefix='addons/'+AID+'/'
  with zipfile.ZipFile(R/'compatibility/helper-empty-cache/upstream-6.17.9.zip') as z:
   for n in z.namelist():
    if n.startswith(prefix) and not n.endswith('/'):
     p=self.home/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
  base=self.addon/'resources/tmdbhelper/lib'
  for src,rel in [('lists_default.py','lists_default.py'),('lists_trakt.py','trakt/lists_standard.py'),('lists_search.py','tmdb/lists_search.py')]:
   (base/'items/directories'/rel).write_bytes((R/'compatibility/helper-empty-cache/candidate'/src).read_bytes())
  for n in ('player.py','scrobbler.py','service.py'):(base/'monitor'/n).write_bytes((R/'compatibility/helper-progress/candidate'/n).read_bytes())
  self.m.verify_installed(self.home)
