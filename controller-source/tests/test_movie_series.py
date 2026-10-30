import unittest,copy
from datetime import date
import movie_series as m

def movie(n,day=None,year=0,watched=0):
 return {'file':f'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=movie&tmdb_id={n}','label':str(n),'filetype':'file','type':'movie','premiered':day or '', 'year':year,'playcount':watched,'resume':{'position':10,'total':100}}
class MovieOrder(unittest.TestCase):
 def test_release_order_keeps_metadata_and_chooses_first_released_unwatched(self):
  rows=[movie(3,'2030-01-01'),movie(2,'2002-05-01'),movie(1,'2001-03-01',watched=1),movie(4),movie(2,'2002-05-01')];before=copy.deepcopy(rows)
  ordered,nxt=m.release_order(rows,date(2026,10,29));self.assertEqual([x['label'] for x in ordered],['1','2','3','4']);self.assertEqual(nxt['label'],'2');self.assertEqual(nxt['resume'],{'position':10,'total':100});self.assertEqual(rows,before)
 def test_future_unknown_invalid_dates_and_provider_controls_never_become_next(self):
  rows=[movie(1,'2030-01-01'),movie(2),movie(3,'bad',2020),{'file':'plugin://plugin.video.themoviedb.helper/?info=collection&page=2','filetype':'directory'}]
  ordered,nxt=m.release_order(rows,date(2026,10,29));self.assertEqual([x['label'] for x in ordered],['3','1','2']);self.assertIsNone(nxt)
 def test_year_only_titles_stay_ordered_but_not_guessed_released(self):
  ordered,nxt=m.release_order([movie(1,year=2020),movie(2,'2021-01-01')],date(2026,10,29));self.assertEqual([x['label'] for x in ordered],['1','2']);self.assertEqual(nxt['label'],'2')
class FranchisePaging(unittest.TestCase):
 def test_all_pages_are_loaded_and_cycle_is_not_silently_truncated(self):
  start='plugin://plugin.video.themoviedb.helper/?info=collection&tmdb_type=collection&tmdb_id=1';nxt=start+'&page=2'
  rows=m.load_series(start,lambda path:[movie(1),{'file':nxt,'filetype':'directory','label':'Next page'}] if path==start else [movie(2)],lambda:True)
  self.assertEqual([x['label'] for x in rows],['1','2'])
  with self.assertRaises(ValueError):m.load_series(start,lambda path:[movie(1),{'file':nxt,'filetype':'directory','label':'Next page'}],lambda:True)
 def test_cancelled_fetch_does_not_start_another_page(self):
  active=[True];calls=[]
  def provider(path):calls.append(path);active[0]=False;return [movie(1)]
  self.assertEqual(m.load_series('plugin://plugin.video.themoviedb.helper/?info=collection&tmdb_type=collection&tmdb_id=1',provider,lambda:active[0]),[]);self.assertEqual(len(calls),1)
