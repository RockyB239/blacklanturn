"""A published YouTube controller must match its native Mac acceptance."""
import copy,json,unittest
from pathlib import Path
from tools.verify_release import verify_youtube_acceptance
ROOT=Path(__file__).resolve().parents[1]
class YouTubeRelease(unittest.TestCase):
 def setUp(self):
  self.receipt=json.loads((ROOT/'controller-source/youtube-native-verification.json').read_text())
  self.manifest=json.loads((ROOT/'controller-source/manifest75.json').read_text())
 def test_exact_native_controller_passes(self):
  verify_youtube_acceptance(self.receipt,self.manifest)
 def test_source_drift_or_missing_native_check_blocks_release(self):
  for change in ('source','sidebar','preview','settings','adaptive','thumbnail','watch'):
   with self.subTest(change=change):
    r=copy.deepcopy(self.receipt)
    if change=='source':r['files']['youtube_core.py']='changed'
    elif change=='sidebar':r['acceptance']['disconnected_sidebar_hidden_with_simulated_account_state']=False
    elif change=='preview':r['acceptance']['automatic_preview']['remote_history_reporting']=True
    elif change=='adaptive':r['acceptance']['adaptive_home']['labels_match_provider']=False
    elif change=='thumbnail':r['visual_verification']['forced_missing_primary_thumbnail_visible']=False
    elif change=='watch':r['acceptance']['youtube_watch_refresh_preserves_category_art_and_order']=False
    else:r['settings_and_authorizations']['authorization_grants_and_selected_accounts_preserved']=False
    with self.assertRaises(AssertionError):verify_youtube_acceptance(r,self.manifest)
