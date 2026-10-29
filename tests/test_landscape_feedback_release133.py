from pathlib import Path
import hashlib,json,unittest,xml.etree.ElementTree as E
ROOT=Path(__file__).parents[1]
class Release133(unittest.TestCase):
 def test_release_has_exact_source_manifest_and_both_packaging_recipes(self):
  p=ROOT/'controller-source/manifest100.json';self.assertTrue(p.is_file(),'The accepted landscape and feedback source needs its release99 manifest')
  manifest=json.loads(p.read_text());self.assertEqual(manifest['controller'],'0.1.100')
  source=ROOT/'controller-source/addon'
  self.assertEqual(manifest['files'],{p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo') and p.name!='.DS_Store'})
  for rel in ('title_preferences.py','title_feedback_ui.py','resources/skins/Default/1080i/FeedbackUndo.xml','live_core.py'):self.assertIn(rel,manifest['files'])
  for name in ('build_release133.py','verify_release133.py'):self.assertTrue((ROOT/'tools'/name).is_file())
 def test_release_notes_describe_local_title_controls_and_stable_landscape_cards(self):
  p=ROOT/'hosted-files/release-notes-1.1.33.json';self.assertTrue(p.is_file(),'Release33 needs its own user-facing update notes')
  notes=json.loads(p.read_text());self.assertEqual(notes['title'],'BlackLanturn 1.1.33');text=json.dumps(notes).lower()
  for term in ('landscape','hide','undo','settings'):self.assertIn(term,text)
