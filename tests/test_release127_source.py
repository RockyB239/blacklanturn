"""127 startup/transaction changes cannot inherit changed126 feature behavior."""
import copy,importlib.util,json,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
class Release127Source(unittest.TestCase):
 def gate(self):
  spec=importlib.util.spec_from_file_location('release127_gate',ROOT/'tools/verify_release127.py');self.assertTrue(Path(spec.origin).is_file(),'Missing127 scoped source gate')
  gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate);return gate
 def inputs(self,g):
  baseline=json.loads((ROOT/'controller-source/manifest93.json').read_text())['files'];controller=dict(baseline,**{'addon.xml':'a'*64,'default.py':'b'*64,'installer_recovery.py':'c'*64})
  installer=g.baseline_installer();current=dict(installer)
  for n in g.INSTALLER_CHANGED:current[n]='d'*64
  return controller,current
 def test_only_the_declared_recovery_transaction_delta_is_accepted(self):
  g=self.gate();controller,installer=self.inputs(g)
  with patch.object(g,'inventory',side_effect=lambda p:controller if p==ROOT/'controller-source/addon' else installer),patch.object(g,'verify_navigation_methods',return_value=True):
   self.assertTrue(g.verify_source({'controller':'0.1.94','files':controller},installer))
 def test_discovery_preview_notes_or_unrelated_installer_changes_fail(self):
  g=self.gate();controller,installer=self.inputs(g)
  for path,is_installer in [('related_titles.py',False),('preview_fallback.py',False),('update_notes_ui.py',False),('resources/libs/gui/updates_menu.py',True),('resources/libs/managed_versions.py',True)]:
   c,i=copy.deepcopy(controller),copy.deepcopy(installer);(i if is_installer else c)[path]='f'*64
   with self.subTest(path=path),patch.object(g,'inventory',side_effect=lambda p:c if p==ROOT/'controller-source/addon' else i),patch.object(g,'verify_navigation_methods',return_value=True),self.assertRaises(AssertionError):g.verify_source({'controller':'0.1.94','files':c},i)
 def test_method_comparison_rejects_modified_sidebar_or_updates_rendering(self):
  g=self.gate()
  before=b'def stable():\n return "Updates"\ndef transaction():\n return False\n'
  changed=b'def stable():\n return "Other"\ndef transaction():\n return True\n'
  self.assertEqual(g.stable_ast(before,{'transaction'}),g.stable_ast(before.replace(b'False',b'True'),{'transaction'}))
  self.assertNotEqual(g.stable_ast(before,{'transaction'}),g.stable_ast(changed,{'transaction'}))

 def test_unchanged_navigation_imports_cannot_be_replaced_under_ast_scope(self):
  g=self.gate()
  before=b'import re\ndef stable():\n return re.sub("x", "y", "x")\ndef transaction():\n return False\n'
  after=before.replace(b'import re',b'import other as re')
  self.assertNotEqual(g.stable_ast(before,{'transaction'}),g.stable_ast(after,{'transaction'}))
 def test_existing_controller_playback_entrypoint_cannot_hide_in_startup_delta(self):
  g=self.gate();fn=getattr(g,'default_ast',None);self.assertTrue(callable(fn),'Missing exact old startup/entrypoint AST linkage')
  old=(ROOT/'controller-source/historical-default93.py').read_bytes();current=(ROOT/'controller-source/addon/default.py').read_bytes()
  self.assertEqual(fn(old),fn(current,remove_recovery=True))
  self.assertNotEqual(fn(old),fn(current.replace(b'def run_live_review():',b'def changed_playback_entrypoint():'),remove_recovery=True))
