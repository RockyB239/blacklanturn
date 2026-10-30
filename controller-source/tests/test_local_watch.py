import unittest,tempfile,sqlite3
from pathlib import Path
from local_watch import hydrate_local
from test_personal_library import title
class LocalWatch(unittest.TestCase):
 def test_cached_status_clears_watched_resume_and_hydrates_progress_without_provider_calls(self):
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d)/'database_1';folder.mkdir()
   with sqlite3.connect(folder/'ItemDetails.db') as c:
    c.executescript('CREATE TABLE simplecache(id TEXT,plays INTEGER,aired_episodes INTEGER,watched_episodes INTEGER,playback_progress REAL);')
    c.executemany('INSERT INTO simplecache VALUES (?,?,?,?,?)',[('movie.1',1,None,None,30),('movie.2',0,None,None,50),('tv.3',0,10,10,None)])
   a=dict(title(),resume={'position':5,'total':100},runtime=100);b=dict(title(2),playcount=0,runtime=200);tv=dict(title(3,'tv'),playcount=0)
   result=hydrate_local(d,[a,b,tv]);self.assertEqual(result[0]['resume'],{'position':0,'total':0});self.assertEqual(result[1]['resume'],{'position':100,'total':200});self.assertEqual(result[2]['playcount'],1);self.assertEqual(a['resume']['position'],5)
 def test_missing_cache_keeps_previous_metadata(self):
  with tempfile.TemporaryDirectory() as d:self.assertEqual(hydrate_local(d,[title()]),[title()])
