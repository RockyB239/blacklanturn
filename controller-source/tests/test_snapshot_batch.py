import sys,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from public_rows import PublicRowSnapshots
P='plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=movie'
ITEM={'file':'plugin://plugin.video.themoviedb.helper/?info=details&tmdb_type=movie&tmdb_id=1','label':'One'}
class SnapshotBatch(unittest.TestCase):
 def test_batch_paints_memory_before_one_atomic_disk_write(self):
  with tempfile.TemporaryDirectory() as t:
   cache=PublicRowSnapshots(Path(t)/'rows','scope')
   with patch.object(cache,'_write',wraps=cache._write) as write:
    with cache.batch():
     cache.put(P,[ITEM]);self.assertEqual(cache.get(P),[ITEM]);self.assertEqual(write.call_count,0)
     cache.put(P+'&page=2',[ITEM]);self.assertEqual(write.call_count,0)
    self.assertEqual(write.call_count,1)
   self.assertEqual(PublicRowSnapshots(cache.path,'scope').get(P),[ITEM])
 def test_clear_during_batch_never_resurrects_private_scope(self):
  with tempfile.TemporaryDirectory() as t:
   cache=PublicRowSnapshots(Path(t)/'rows','scope')
   with cache.batch():cache.put(P,[ITEM]);cache.clear()
   self.assertIsNone(PublicRowSnapshots(cache.path,'scope').get(P))
