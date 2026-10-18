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

class StallRelease(unittest.TestCase):
 def setUp(self):
  self.fire=json.loads((ROOT/'controller-source/youtube-stall-native-verification.json').read_text())
  self.manifest=json.loads((ROOT/'controller-source/manifest76.json').read_text())
  self.mac=copy.deepcopy(json.loads((ROOT/'controller-source/youtube-native-verification.json').read_text()))
  self.mac.update(controller='0.1.76',files=self.manifest['files'],ordinary_restart={'passed':True,'source_exact':True,'home_ready':True,'active_players':[]})
  self.mac['visual_basis']={'controller':'0.1.75','files':json.loads((ROOT/'controller-source/manifest75.json').read_text())['files']}
 def check(self,mac=None,fire=None,manifest=None):
  from tools import verify_release
  self.assertTrue(callable(getattr(verify_release,'verify_stall_acceptance',None)),'Release has no gate for the tested YouTube stall repair')
  verify_release.verify_stall_acceptance(mac or self.mac,fire or self.fire,manifest or self.manifest)
 def test_exact_fire_and_mac_proof_passes(self):self.check()
 def test_missing_or_stale_preview_and_preservation_proof_blocks_release(self):
  for change in ('source','phase','restore','hardware','history','profile','restart','mac_preview','mac_profile','mac_restart','visual_layout'):
   with self.subTest(change=change):
    f=copy.deepcopy(self.fire);m=copy.deepcopy(self.mac)
    if change=='source':f['source']['files']['youtube_provider.py']='wrong'
    elif change=='phase':f['native']['cancel_moments']=f['native']['cancel_moments'][:2]
    elif change=='restore':f['native']['cancel_moments'][0]['normal_core_restored']=False
    elif change=='hardware':f['native']['normal_clip_decoder']='ff-h264'
    elif change=='history':f['native']['youtube_history_preserved']=False
    elif change=='profile':f['native']['protected_files_preserved']=0
    elif change=='restart':f['native']['normal_restart']=False
    elif change=='mac_preview':m['acceptance']['preview_navigation_cancels_playback']=False
    elif change=='mac_profile':m['settings_and_authorizations']['authorization_grants_and_selected_accounts_preserved']=False
    elif change=='mac_restart':m['ordinary_restart']['home_ready']=False
    else:m['visual_basis']['files']['resources/skins/Default/1080i/LiveReview.xml']='wrong'
    with self.assertRaises(AssertionError):self.check(m,f)
