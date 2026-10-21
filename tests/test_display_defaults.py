"""A clean build must not silently restore TMDb as a fifth rating."""
import importlib.util,io,json,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class DisplayDefaults(unittest.TestCase):
 def test_sanitized_five_rating_config_gets_four_without_losing_other_build_choices(self):
  m=load('build_display',ROOT/'tools/build_release.py');key='userdata/addon_data/script.blacklanturn.preview/rows.json'
  data={key:json.dumps({'RatingSources':['rottentomatoes','metacritic','imdb','popcorn','themoviedatabase'],'PreviewMode':'manual','Saved':[],'YouTubeEndSuggestions':True,'YouTubeEndAutoplay':False}).encode(),'userdata/other.txt':b'keep'}
  self.assertTrue(callable(getattr(m,"apply_display_defaults",None)),"Build lacks an explicit four-rating default step")
  m.apply_display_defaults(data)
  self.assertEqual(json.loads(data[key]),{'RatingSources':['rottentomatoes','metacritic','imdb','popcorn'],'PreviewMode':'manual','Saved':[],'YouTubeEndSuggestions':True,'YouTubeEndAutoplay':False})
  self.assertEqual(data['userdata/other.txt'],b'keep')
 def archive(self,ratings):
  stream=io.BytesIO()
  with zipfile.ZipFile(stream,'w') as z:z.writestr('userdata/addon_data/script.blacklanturn.preview/rows.json',json.dumps({'RatingSources':ratings}))
  stream.seek(0);return zipfile.ZipFile(stream)
 def test_verifier_accepts_four_and_rejects_fifth_or_missing_rating_defaults(self):
  m=load('verify_display',ROOT/'tools/verify_release.py')
  self.assertTrue(callable(getattr(m,"verify_display_defaults",None)),"Release verification does not reject a fifth default rating")
  with self.archive(['rottentomatoes','metacritic','imdb','popcorn']) as z:m.verify_display_defaults(z)
  for bad in [None,[],['rottentomatoes','metacritic','imdb','popcorn','themoviedatabase']]:
   with self.subTest(ratings=bad),self.archive(bad) as z:
    with self.assertRaises(AssertionError):m.verify_display_defaults(z)
if __name__=='__main__':unittest.main()
