import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
import public_rows
from test_public_row_snapshots import ITEM,P
NOW=4_000_000
EARLIEST=NOW-public_rows.MAX_AGE
class SnapshotEfficiency(unittest.TestCase):
 def test_ineligible_timestamp_never_inspects_card_contents(self):
  for stamp in (EARLIEST-1,NOW+1,-1,None,"bad",float('inf'),True):
   with self.subTest(stamp=stamp),tempfile.TemporaryDirectory() as folder:
    path=Path(folder)/'rows';path.write_text(json.dumps({'version':2,'scope':'s','rows':[{'path':P,'time':stamp,'items':[ITEM]}]}))
    with patch.object(public_rows.PublicRowSnapshots,'sanitize_items',return_value=None) as inspect:store=public_rows.PublicRowSnapshots(path,'s',clock=lambda:NOW)
    self.assertEqual(inspect.call_count,0);self.assertIsNone(store.get(P))
 def test_exact_age_boundaries_keep_artwork_without_watch_state(self):
  for stamp,kept in ((EARLIEST,True),(NOW,True),(EARLIEST-1,False),(NOW+1,False)):
   with self.subTest(stamp=stamp),tempfile.TemporaryDirectory() as folder:
    path=Path(folder)/'rows';path.write_text(json.dumps({'version':2,'scope':'s','rows':[{'path':P,'time':stamp,'items':[ITEM]}]}))
    value=public_rows.PublicRowSnapshots(path,'s',clock=lambda:NOW).get(P);self.assertEqual(value is not None,kept)
    if kept:self.assertEqual(value[0]['art'],ITEM['art']);self.assertNotIn('playcount',value[0])
 def test_shared_artwork_validated_once_per_batch(self):
  image='image://https%3a%2f%2fimage.tmdb.org%2ft%2fp%2fw500%2fposter.jpg/';files=[dict(ITEM,art={key:image for key in ('thumb','poster','fanart','landscape','tvshow.poster')},thumbnail=image) for _ in range(40)]
  with patch.object(public_rows,'_art',wraps=public_rows._art) as validate:result=public_rows._items(files)
  self.assertEqual(result[0]['art'],files[0]['art']);self.assertEqual(result[0]['thumbnail'],image);self.assertEqual(len(result),40);self.assertLessEqual(validate.call_count,1)
  result[0]['art']['poster']='changed';self.assertEqual(files[0]['art']['poster'],image)
 def test_bad_art_remains_rejected_and_memo_does_not_cross_batches(self):
  bad=['https://image.tmdb.org/a?token=secret','image://image%3a%2f%2fanything/','https://evil.invalid/a',[],{},None,42,'https://image.tmdb.org/a\n.jpg'];result=public_rows._items([dict(ITEM,art={str(i):v for i,v in enumerate(bad)},thumbnail=[])])
  self.assertEqual(result[0]['art'],{});self.assertNotIn('thumbnail',result[0])
  with patch.object(public_rows,'_art',wraps=public_rows._art) as validate:
   for _ in range(2):public_rows._items([dict(ITEM,art={'poster':'https://image.tmdb.org/a.jpg'})])
  self.assertGreaterEqual(validate.call_count,2)
