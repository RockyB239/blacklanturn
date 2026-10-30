from pathlib import Path
import hashlib,json,unittest
ROOT=Path(__file__).parents[1]
class PersonalLibraryRelease(unittest.TestCase):
 def test_new_release_proof_covers_all_personal_library_runtime_files(self):
  p=ROOT/'controller-source/manifest104.json';self.assertTrue(p.is_file(),'New personal-library source requires a new manifest')
  m=json.loads(p.read_text());self.assertEqual(m['controller'],'0.1.104')
  for n in ('personal_library.py','library_ui.py','local_watch.py','movie_series.py','series_end.py','series_end_core.py','series_metadata.py','series_end_ui.py','resources/skins/Default/1080i/SeriesEnd.xml'):
   self.assertEqual(m['files'][n],hashlib.sha256((ROOT/'controller-source/addon'/n).read_bytes()).hexdigest())
  builder=(ROOT/'tools/build_release140.py').read_text()
  for n in ('personal_library.py','library_ui.py','local_watch.py','movie_series.py','series_end.py','series_end_core.py','series_metadata.py','series_end_ui.py','resources/skins/Default/1080i/SeriesEnd.xml'):self.assertIn(repr(n),builder,'New runtime file must be covered by installed-release proof')
 def test_release_notes_overflow_is_rejected_by_the_packaging_gate(self):
  import importlib.util
  spec=importlib.util.spec_from_file_location('release138_validation',ROOT/'tools/build_release140.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
  entry={'id':'blacklanturn-general-1.1.39-r0','edition':'general','version':'1.1.39','revision':0,'title':'Release test','summary':'Summary','sections':[{'heading':'Test','bullets':['x'*241]}],'files':{'addons/script.blacklanturn.preview/default.py':'a'*64}}
  with self.assertRaises(ValueError):builder.validate_release_entry(entry)
