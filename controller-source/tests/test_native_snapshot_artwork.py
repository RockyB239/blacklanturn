"""Real Kodi image:// wrappers must survive display reuse without widening origins."""
import json,sys,tempfile,unittest
from pathlib import Path
from urllib.parse import quote
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from public_rows import PublicRowSnapshots,_art
from home_rows import HomeRowSnapshots
from test_public_row_snapshots import P,ITEM
from test_home_row_snapshots import H
IMAGE='https://image.tmdb.org/t/p/w1280/native.jpg'
WRAPPED='image://'+quote(IMAGE,safe='')+'/'

class NativeArtwork(unittest.TestCase):
 def test_native_wrapped_cards_hero_and_logo_roundtrip_keep_image_cache_keys(self):
  for cls,path in ((PublicRowSnapshots,P),(HomeRowSnapshots,H)):
   with self.subTest(store=cls.__name__),tempfile.TemporaryDirectory() as folder:
    target=Path(folder)/'rows.json';s=cls(target,'same-account',clock=lambda:1000)
    native=dict(ITEM,art={k:WRAPPED for k in ('landscape','poster','fanart','clearlogo')},thumbnail=WRAPPED)
    self.assertTrue(s.put(path,[native]));saved=cls(target,'same-account',clock=lambda:1000).get(path)[0]
    self.assertEqual(saved['art'],native['art']);self.assertEqual(saved['thumbnail'],WRAPPED)
 def test_wrapped_secrets_foreign_origins_and_transform_parameters_are_rejected(self):
  for inner in ('https://evil.invalid/image.jpg','https://image.tmdb.org/a?token=secret','https://image.tmdb.org/a#secret','https://user:pass@image.tmdb.org/a','http://image.tmdb.org/a','file:///private/user-data','plugin://addon/','image://'+quote(IMAGE,safe='')+'/'):
   self.assertEqual(_art('image://'+quote(inner,safe='')+'/'),'')
  for value in (WRAPPED+'?token=secret',WRAPPED+'#secret',WRAPPED+'transform',WRAPPED.replace('native.jpg','native%0A.jpg'),'image:///'):
   self.assertEqual(_art(value),'')
  self.assertEqual(_art(WRAPPED),WRAPPED);self.assertEqual(_art(IMAGE),IMAGE)
 def test_previous_artless_snapshot_format_is_discarded(self):
  for cls,path in ((PublicRowSnapshots,P),(HomeRowSnapshots,H)):
   with self.subTest(store=cls.__name__),tempfile.TemporaryDirectory() as folder:
    target=Path(folder)/'rows.json';target.write_text(json.dumps({'version':1,'scope':'same-account','rows':[{'path':path,'time':1000,'items':[dict(ITEM,art={})]}]}))
    self.assertIsNone(cls(target,'same-account',clock=lambda:1000).get(path))

if __name__=='__main__':unittest.main()
