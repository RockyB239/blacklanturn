"""Bound All search concurrency without changing metadata or result ordering."""
import unittest,sys,threading
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from search_ui import load_best_matches,route

class ParallelSearch(unittest.TestCase):
 def test_two_requests_overlap_and_preserve_full_metadata_and_ranking(self):
  entered=threading.Barrier(2);lock=threading.Lock();active=0;maximum=0;calls=[]
  def provider(path):
   nonlocal active,maximum
   kind=parse_qs(urlsplit(path).query)['tmdb_type'][0]
   with lock:active+=1;maximum=max(maximum,active);calls.append(kind)
   try:
    if kind in ('both','company'):entered.wait(timeout=2)
    return [{'file':route('details','movie',tmdb_id={'both':1,'company':2,'collection':3}[kind]),'label':kind,'plot':'full plot','runtime':123,'cast':[{'name':'Actor'}],'resume':{'position':50}}]
   finally:
    with lock:active-=1
  result=load_best_matches('query',provider,workers=2)
  self.assertEqual(maximum,2);self.assertCountEqual(calls,['both','company','collection'])
  self.assertEqual([x['label'] for x in result],['both','company','collection'])
  self.assertTrue(all(x['runtime']==123 and x['resume']['position']==50 and x['cast'] for x in result))
 def test_cancellation_in_side_lookup_retires_whole_search_before_collection(self):
  active=threading.Event();active.set();both_started=threading.Event();cancelled=threading.Event();calls=[]
  def provider(path):
   kind=parse_qs(urlsplit(path).query)['tmdb_type'][0];calls.append(kind)
   if kind=='both':both_started.set();self.assertTrue(cancelled.wait(2))
   if kind=='company':self.assertTrue(both_started.wait(2));active.clear();cancelled.set()
   return []
  with self.assertRaises(ValueError):load_best_matches('query',provider,active.is_set,workers=2)
  self.assertNotIn('collection',calls)
 def test_all_failures_remain_errors_and_partial_results_remain_usable(self):
  def failed(path):raise ValueError('offline')
  with self.assertRaises(ValueError):load_best_matches('query',failed,workers=2)
  item={'file':route('details','movie',tmdb_id=7),'label':'result'}
  def partial(path):
   if parse_qs(urlsplit(path).query)['tmdb_type']==['both']:return [item]
   raise ValueError('offline')
  self.assertEqual(load_best_matches('query',partial,workers=2),[item])

if __name__=='__main__':unittest.main()
