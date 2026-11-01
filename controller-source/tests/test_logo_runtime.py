import sys,tempfile,unittest,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from test_logo_readability import png
class RuntimeContracts(unittest.TestCase):
 def runtime(self,folder):
  import logo_readability_runtime as m
  return m.LogoDecisions(Path(folder)/'decisions.json')
 def test_cached_dark_logo_uses_text_without_mutating_art_and_survives_restart(self):
  with tempfile.TemporaryDirectory() as f:
   store=self.runtime(f);path=Path(f)/'dark.png';path.write_bytes(png(2,1,rows=b'\0'+bytes([0,0,0,255])*2))
   url='https://image.tmdb.org/t/p/w500/black.png';calls=[]
   self.assertEqual(store.visible(url),url)
   self.assertFalse(store.inspect(url,lambda u:(calls.append(u) or path)))
   self.assertEqual(store.visible(url),'');self.assertEqual(calls,[url]);self.assertEqual(self.runtime(f).visible(url),'')
 def test_missing_local_texture_does_not_download_or_cache_a_false_decision(self):
  with tempfile.TemporaryDirectory() as f:
   store=self.runtime(f);url='logo.png';self.assertIsNone(store.inspect(url,lambda u:None));self.assertEqual(store.visible(url),url);self.assertFalse(store.path.exists())
 def test_known_result_is_not_decoded_or_looked_up_again(self):
  with tempfile.TemporaryDirectory() as f:
   store=self.runtime(f);p=Path(f)/'white.png';p.write_bytes(png(1,1,rows=b'\0'+bytes([255,255,255,255])))
   self.assertTrue(store.inspect('logo',lambda u:p));self.assertTrue(store.inspect('logo',lambda u:self.fail('already cached')));self.assertEqual(store.visible('logo'),'logo')
 def test_store_rejects_oversize_or_invalid_decisions_and_is_bounded(self):
  with tempfile.TemporaryDirectory() as f:
   p=Path(f)/'decisions.json';p.write_text('x'*40000);store=self.runtime(f);self.assertEqual(store.visible('a'),'a')
   p.write_text(json.dumps({'version':1,'entries':{'bad':False}}));self.assertEqual(self.runtime(f).visible('bad'),'bad')

 def test_persisted_decisions_are_bounded_and_do_not_store_artwork_urls(self):
  with tempfile.TemporaryDirectory() as f:
   store=self.runtime(f);p=Path(f)/'dark.png';p.write_bytes(png(1,1,rows=b'\0'+bytes([0,0,0,255])))
   for n in range(260):store.inspect('https://example.com/logo'+str(n)+'.png',lambda u:p)
   raw=store.path.read_bytes();self.assertLessEqual(len(raw),32768);self.assertNotIn(b'example.com',raw);self.assertEqual(len(json.loads(raw)['entries']),256)
