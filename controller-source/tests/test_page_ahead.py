import sys,threading,unittest,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from page_ahead import PageAhead
class Ahead(unittest.TestCase):
 def test_only_one_job_and_matching_foreground_waits(self):
  a=PageAhead();entered=threading.Event();release=threading.Event();calls=[]
  def fetch():calls.append('fetch');entered.set();release.wait(1)
  self.assertTrue(a.start('next',fetch,lambda:True));self.assertTrue(entered.wait(1));self.assertFalse(a.start('other',fetch,lambda:True))
  joined=threading.Event();t=threading.Thread(target=lambda:(a.wait('next',lambda:True),joined.set()));t.start();self.assertFalse(joined.wait(.02));release.set();t.join(1);self.assertTrue(joined.is_set());self.assertEqual(calls,['fetch'])
 def test_obsolete_job_does_not_start_and_cancelled_wait_returns_promptly(self):
  a=PageAhead();calls=[];a.start('next',lambda:calls.append(1),lambda:False);a.wait('next',lambda:True);self.assertEqual(calls,[])
  release=threading.Event();a.start('other',lambda:release.wait(1),lambda:True);t=time.monotonic();a.wait('other',lambda:False);self.assertLess(time.monotonic()-t,.1);release.set()
 def test_failed_background_job_does_not_wedge_worker_or_repeat_forever(self):
  a=PageAhead()
  def fail():raise RuntimeError('offline')
  a.start('next',fail,lambda:True);a.wait('next',lambda:True);self.assertFalse(a.start('next',fail,lambda:True));self.assertTrue(a.start('other',lambda:None,lambda:True));a.wait('other',lambda:True)
if __name__=='__main__':unittest.main()

class Eligibility(unittest.TestCase):
 def test_native_breadcrumb_and_logical_cursor_are_supported(self):
  from page_ahead import eligible
  for path in ('plugin://plugin.video.themoviedb.helper/?info=trakt_trending&tmdb_type=tv&page=2&cacheonly=false','plugin://plugin.video.themoviedb.helper/?info=trakt_popular&tmdb_type=movie&page=2','plugin://plugin.video.themoviedb.helper/?info=trending_day&tmdb_type=tv&page=2&cacheonly=False&plugin_category=Trending+shows','plugin://plugin.video.themoviedb.helper/?info=discover&tmdb_type=movie&page=2&bl_start=4&with_origin_country=JP','plugin://plugin.video.themoviedb.helper/?info=search&tmdb_type=company&page=2&query=A24'):self.assertTrue(eligible(path))
 def test_actions_personal_lists_and_malformed_cursors_are_rejected(self):
  from page_ahead import eligible
  for path in ('plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=movie&page=2','plugin://plugin.video.themoviedb.helper/?info=trakt_watchlist&tmdb_type=movie&page=2','plugin://other/?info=discover&page=2','plugin://plugin.video.themoviedb.helper/?info=discover&page=-1','plugin://plugin.video.themoviedb.helper/?info=discover&page=2&bl_start=999999','plugin://plugin.video.themoviedb.helper/?info=discover&page=2&info=play'):self.assertFalse(eligible(path))
