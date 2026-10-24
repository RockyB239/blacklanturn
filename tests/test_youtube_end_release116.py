"""The new release must bind tested end-screen source and both skin overlays."""
import copy,hashlib,importlib.util,json,unittest,xml.etree.ElementTree as E
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('end_release',ROOT/'tools/verify_release.py');V=importlib.util.module_from_spec(spec);spec.loader.exec_module(V)
spec=importlib.util.spec_from_file_location('end_builder',ROOT/'tools/build_release.py');B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
class YouTubeEndRelease(unittest.TestCase):
 def inputs(self):
  return json.loads((ROOT/'controller-source/youtube-end-native-verification.json').read_text()),json.loads((ROOT/'controller-source/manifest85.json').read_text())
 def test_current_receipt_matches_exact_release_source(self):
  receipt,manifest=self.inputs();V.verify_youtube_end_acceptance(receipt,manifest,historical=True)
  self.assertEqual(E.parse(ROOT/'controller-source/addon/addon.xml').getroot().get('version'),'0.1.87')
 def test_missing_native_behaviors_and_changed_source_fail(self):
  receipt,manifest=self.inputs()
  for key in ('natural_end','autoplay_started','back_hides_and_cancels','second_back_restores_row','disabled_skips_request','pointer_cancels','details_save_channel','settings_authorizations_preserved'):
   with self.subTest(key=key):
    bad=copy.deepcopy(receipt);bad['acceptance'][key]=False
    with self.assertRaises(AssertionError):V.verify_youtube_end_acceptance(bad,manifest,historical=True)
  bad=copy.deepcopy(manifest);bad['files']['youtube_end.py']='0'*64
  with self.assertRaises(AssertionError):V.verify_youtube_end_acceptance(receipt,bad,historical=True)
 def test_false_platform_claims_and_early_countdown_fail(self):
  receipt,manifest=self.inputs();receipt['devices']=['mac','fire']
  with self.assertRaises(AssertionError):V.verify_youtube_end_acceptance(receipt,manifest,historical=True)
  receipt,manifest=self.inputs();receipt['autoplay_delay_seconds']=1
  with self.assertRaises(AssertionError):V.verify_youtube_end_acceptance(receipt,manifest,historical=True)
 def test_skin_overlay_is_pinned_and_rejects_unknown_input(self):
  data={'addons/skin.blacklanturn.preview/xml/Home.xml':b'foreign source','userdata/keep':b'keep'}
  with self.assertRaises(AssertionError):B.apply_youtube_skin(data)
  self.assertEqual(data['userdata/keep'],b'keep')
 def test_clean_suggestion_defaults_are_explicit(self):
  key='userdata/addon_data/script.blacklanturn.preview/rows.json';data={key:b'{"Saved":[],"custom":true}'}
  B.apply_display_defaults(data);values=json.loads(data[key])
  self.assertIs(values['YouTubeEndSuggestions'],True);self.assertIs(values['YouTubeEndAutoplay'],False);self.assertIs(values['custom'],True)
