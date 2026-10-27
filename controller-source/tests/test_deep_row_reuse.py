"""Many small lower rows should share the existing byte budget, not thrash at12."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from row_feedback import RowResultCache
from public_rows import PublicRowSnapshots
from test_public_row_snapshots import P,ITEM
class DeepRows(unittest.TestCase):
 def test_session_lower_rows_survive_full_movies_and_shows_visit_with_same_byte_limit(self):
  cache=RowResultCache(clock=lambda:1000)
  for n in range(38):self.assertTrue(cache.put(str(n),[dict(ITEM,title=str(n))]))
  self.assertEqual(cache.max_bytes,2*1024*1024)
  self.assertIsNotNone(cache.get('0'));self.assertIsNotNone(cache.get('37'))
 def test_public_lower_rows_survive_restart_without_watch_state_or_more_disk_bytes(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'rows.json';s=PublicRowSnapshots(path,'account',clock=lambda:1000)
   for n in range(38):self.assertTrue(s.put(P+'&page='+str(n+1),[ITEM]))
   restored=PublicRowSnapshots(path,'account',clock=lambda:1001)
   self.assertIsNotNone(restored.get(P+'&page=1'));self.assertIsNotNone(restored.get(P+'&page=38'))
   self.assertLessEqual(path.stat().st_size,2*1024*1024)
   self.assertNotIn('playcount',restored.get(P+'&page=1')[0])

 def test_batched_refresh_enforces_byte_limit_before_flush(self):
  with tempfile.TemporaryDirectory() as folder:
   s=PublicRowSnapshots(Path(folder)/'rows.json','account',clock=lambda:1000)
   with s.batch():
    for n in range(38):
     s.put(P+'&page='+str(n+1),[dict(ITEM,plot='x'*1000)]*80)
     self.assertLessEqual(len(s._encode(s.rows)),2*1024*1024)
