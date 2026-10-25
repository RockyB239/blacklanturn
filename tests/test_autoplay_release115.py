"""Mac-only natural acceptance cannot be substituted by old multi-device proof."""
import copy,importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('release115',ROOT/'tools/verify_release.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class AutoplayRelease(unittest.TestCase):
 def setUp(self):
  self.receipt=json.loads((ROOT/'compatibility/autoplay-size/natural-verification.json').read_text())
  self.controller=json.loads((ROOT/'controller-source/manifest84.json').read_text())
  self.umbrella=json.loads((ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/managed-umbrella.json').read_text())
  # Natural Mac receipt tested complete Umbrella92, retained as historical input.
  self.umbrella=dict(self.umbrella,version='6.7.92',files=self.umbrella['legacy_files']['6.7.92'])
 def verify(self):
  fn=getattr(module,'verify_autoplay_acceptance',None);self.assertTrue(callable(fn),'Missing source-bound natural playback acceptance gate')
  fn(self.receipt,self.controller,self.umbrella)
 def test_actual_receipt_is_accepted_as_mac_only(self):self.verify()
 def test_missing_natural_lifecycle_proofs_are_rejected(self):
  for field in ('sequence_without_seeking','season_transition','manual_service_and_ceiling_retained','stillwatching_pause_confirmed','trakt_completed_watched_partial_unwatched'):
   with self.subTest(field=field):
    self.receipt[field]=False
    with self.assertRaises(AssertionError):self.verify()
    self.receipt[field]=True
 def test_changed_player_source_or_controller_is_rejected(self):
  for container,key in ((self.controller['files'],'live_review.py'),(self.umbrella['files'],'resources/lib/modules/player.py'),(self.umbrella['files'],'resources/lib/modules/source_preferences.py')):
   with self.subTest(key=key):
    old=container[key];container[key]='0'*64
    with self.assertRaises(AssertionError):self.verify()
    container[key]=old
 def test_simulated_counts_and_missing_prepared_sources_are_rejected(self):
  self.receipt['simulated_viewing_count']=True
  with self.assertRaises(AssertionError):self.verify()
  self.receipt['simulated_viewing_count']=False;self.receipt['prepared_source_matches']=3
  with self.assertRaises(AssertionError):self.verify()
 def test_bad_resume_and_unpreserved_settings_are_rejected(self):
  self.receipt['resume_seconds']=100
  with self.assertRaises(AssertionError):self.verify()
  self.receipt['resume_seconds']=self.receipt['stop_seconds'];self.receipt['preservation']['passed']=False
  with self.assertRaises(AssertionError):self.verify()

class CurrentAutoplayComponentScope(unittest.TestCase):
 def test_only_unchanged_session_component_inherits_natural_playback_evidence(self):
  import hashlib,tempfile
  from unittest.mock import patch
  fn=getattr(module,'verify_inherited_autoplay_component',None)
  self.assertTrue(callable(fn),'Missing narrow current autoplay component gate')
  receipt=json.loads((ROOT/'compatibility/autoplay-size/natural-verification.json').read_text())
  self.assertTrue(fn(receipt))
  with tempfile.TemporaryDirectory()as folder:
   root=Path(folder);target=root/'controller-source/addon';target.mkdir(parents=True);(target/'autoplay_session.py').write_text('changed implementation')
   with patch.object(module,'ROOT',root),self.assertRaises(AssertionError):fn(receipt)
