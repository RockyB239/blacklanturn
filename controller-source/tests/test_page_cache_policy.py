import unittest
from types import SimpleNamespace
from urllib.parse import parse_qs,urlsplit
from test_window_lifecycle import ROOT,extract
from row_feedback import RowResultCache
from filtered_pages import PageCancelled
class Policy(unittest.TestCase):
 def test_public_trakt_keeps_thirty_second_ttl(self):
  clock=[0];cache=RowResultCache(clock=lambda:clock[0]);calls=[]
  method=extract(ROOT/'live_review.py','cached_provider_list',{'PageCancelled':PageCancelled,'parse_qs':parse_qs,'urlsplit':urlsplit,'get_list':lambda p:calls.append(p) or [{'file':'x'}]},'LiveReview')
  s=SimpleNamespace(result_cache=cache)
  p='plugin://plugin.video.themoviedb.helper/?info=trakt_trending&tmdb_type=tv&page=2'
  method(s,p,cache.revision,lambda:True);clock[0]=29;method(s,p,cache.revision,lambda:True);self.assertEqual(len(calls),1)
  clock[0]=31;method(s,p,cache.revision,lambda:True);self.assertEqual(len(calls),2)
 def test_cancelled_fetch_never_enters_cache(self):
  cache=RowResultCache();active=[True]
  def fetch(p):active[0]=False;return [{'file':'x'}]
  method=extract(ROOT/'live_review.py','cached_provider_list',{'PageCancelled':PageCancelled,'parse_qs':parse_qs,'urlsplit':urlsplit,'get_list':fetch},'LiveReview')
  with self.assertRaises(PageCancelled):method(SimpleNamespace(result_cache=cache),'route',cache.revision,lambda:active[0])
  self.assertEqual(cache.stats()['entries'],0)
if __name__=='__main__':unittest.main()
