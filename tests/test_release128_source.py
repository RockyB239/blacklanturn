"""Release128 must only change the accepted update and title-menu paths."""
import importlib.util,json,unittest
from pathlib import Path
from unittest.mock import patch
from historical_release_fixture import published129
ROOT=published129()
class Release128Source(unittest.TestCase):
 def gate(self):
  spec=importlib.util.spec_from_file_location('release128_gate',ROOT/'tools/verify_release128.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g);g.ROOT=ROOT;return g
 def test_exact_reviewed_source_and_unchanged_method_scopes(self):
  g=self.gate();original=g.inventory;baseline=__import__('tools.verify_release129',fromlist=['baseline_installer']).baseline_installer()
  with patch.object(g,'inventory',side_effect=lambda p:baseline if p==ROOT/'installer-source/plugin.program.blacklanturninstaller' else original(p)):
   self.assertTrue(g.verify_source(json.loads((ROOT/'controller-source/manifest95.json').read_text()),baseline))
 def test_unrelated_controller_or_installer_change_is_rejected(self):
  g=self.gate();controller=g.inventory(ROOT/'controller-source/addon');installer=g.inventory(ROOT/'installer-source/plugin.program.blacklanturninstaller')
  for path,side in [('preview_fallback.py','controller'),('resources/libs/inplace_update.py','installer'),('resources/libs/managed_versions.py','installer')]:
   c=dict(controller);i=dict(installer);(c if side=='controller'else i)[path]='f'*64
   with self.subTest(path=path),patch.object(g,'inventory',side_effect=lambda p:c if p==ROOT/'controller-source/addon'else i),self.assertRaises(AssertionError):g.verify_source({'controller':'0.1.95','files':c},i)
 def test_wizard_normalization_allows_only_final_focus_keyword(self):
  g=self.gate();old=g.baseline_installer(raw=True)['resources/libs/wizard.py'];current=(ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/libs/wizard.py').read_bytes()
  self.assertEqual(g.normalized_wizard(old),g.normalized_wizard(current,True))
  self.assertNotEqual(g.normalized_wizard(old),g.normalized_wizard(current.replace(b"xbmc.executebuiltin('Quit')",b"xbmc.executebuiltin('Other')"),True))
  with self.assertRaises(AssertionError):g.normalized_wizard(current.replace(b'xbmcgui.DLG_YESNO_YES_BTN',b'xbmcgui.DLG_YESNO_NO_BTN'),True)
