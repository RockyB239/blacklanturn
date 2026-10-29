"""Series state must be reliable metadata, never a guessed ending."""
import tempfile,sqlite3,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
try:from series_status import SeriesStatus,status_label
except ImportError:SeriesStatus=None;status_label=None
from live_core import title_presentation

def show(i=1,**kw):return dict({'label':'Show','file':'plugin://plugin.video.themoviedb.helper/?info=seasons&tmdb_type=tv&tmdb_id='+str(i),'filetype':'directory','type':'tvshow','year':2026},**kw)
class SeriesTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(SeriesStatus,'Series status support is missing')
 def test_normalized_known_states_and_unknown_blank(self):
  for raw,label in [('Returning Series','Returning series'),('ended','Ended'),('Canceled','Canceled'),('cancelled','Canceled'),('In Production','In production'),('Planned','Planned'),('Pilot','Pilot'),('??',''),(None,'')]:self.assertEqual(status_label(raw),label)
 def test_movies_episodes_and_people_do_not_get_series_labels(self):
  with tempfile.TemporaryDirectory() as f:
   s=SeriesStatus(f);items=[dict(show(),type='movie',file='plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=movie&tmdb_id=1',status='Ended'),dict(show(),type='episode',season=1,episode=1,file=show()['file']+'&season=1&episode=1',status='Ended')];self.assertTrue(all(not x.get('_series_status') for x in s.enrich(items)))
 def test_reads_known_rows_in_one_readonly_batch_and_caches(self):
  with tempfile.TemporaryDirectory() as f:
   folder=Path(f)/'database_01';folder.mkdir();db=folder/'ItemDetails.db'
   with sqlite3.connect(db) as c:c.executescript("CREATE TABLE tvshow(tmdb_id INTEGER,status TEXT);INSERT INTO tvshow VALUES(1,'Ended'),(2,'Returning Series')")
   before=db.read_bytes();s=SeriesStatus(f);items=[show(1),show(2),show(3)];out=s.enrich(items);self.assertEqual([x.get('_series_status','') for x in out],['Ended','Returning series','']);self.assertNotIn('_series_status',items[0]);self.assertEqual(s.enrich(items),out);self.assertEqual(s.reads,1);self.assertEqual(db.read_bytes(),before)
 def test_missing_cache_is_unknown_and_never_creates_database(self):
  with tempfile.TemporaryDirectory() as f:
   s=SeriesStatus(f);self.assertEqual(s.enrich([show()]),[show()]);self.assertEqual(list(Path(f).iterdir()),[])
 def test_provider_status_and_watch_state_are_separate(self):
  with tempfile.TemporaryDirectory() as f:
   item=SeriesStatus(f).enrich([show(status='Canceled',runtime=3600,mpaa='TV-MA',playcount=3)])[0];p=title_presentation(item);self.assertIn('Canceled',p['technical']);self.assertIn('60 min',p['technical']);self.assertEqual(p['watch'],'Watched')
 def test_status_is_not_inferred_from_release_year_or_episode_count(self):
  with tempfile.TemporaryDirectory() as f:self.assertNotIn('_series_status',SeriesStatus(f).enrich([show(year=1990,episode=99)])[0])
 def test_corrupt_database_does_not_break_details(self):
  with tempfile.TemporaryDirectory() as f:
   folder=Path(f)/'database_01';folder.mkdir();(folder/'ItemDetails.db').write_bytes(b'bad');self.assertEqual(SeriesStatus(f).enrich([show()]),[show()])
