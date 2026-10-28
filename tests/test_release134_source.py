"""The new release recipe must distribute complete reviewed sources without defaults drift."""
from pathlib import Path
import importlib.util,unittest
ROOT=Path(__file__).resolve().parents[1]
class Release134Recipe(unittest.TestCase):
 def test_builder_uses_new_complete_sources_and_sha_pinned_baselines(self):
  path=ROOT/'tools/build_release134.py';self.assertTrue(path.is_file())
  spec=importlib.util.spec_from_file_location('release134_builder',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  data={'userdata/account.xml':b'untouched','addons/unrelated/addon.xml':b'keep','addons/plugin.video.themoviedb.helper/obsolete.py':b'remove'}
  m.apply_current(data)
  self.assertEqual(data['userdata/account.xml'],b'untouched');self.assertEqual(data['addons/unrelated/addon.xml'],b'keep')
  self.assertNotIn('addons/plugin.video.themoviedb.helper/obsolete.py',data)
  self.assertIn(b'version="1:6.19.2+blacklanturn.1"',data['addons/plugin.video.themoviedb.helper/addon.xml'])
  self.assertIn(b'version="1:6.7.98+blacklanturn.1"',data['addons/plugin.video.umbrella/addon.xml'])
  self.assertIn(b'version="1.3.0"',data['addons/service.upnext/addon.xml'])
  self.assertEqual(len(m.PINS),2)
