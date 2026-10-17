import sys,unittest,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from search_ui import route,load_best_matches
from row_feedback import RowResultCache

def item(k,n):return {'file':route('discover' if k=='company' else 'details',k,**({'with_companies':n} if k=='company' else {'tmdb_id':n})),'title':str(n),'cast':[{'name':'Actor'}],'art':{'poster':'https://test/poster'},'resume':{'position':4},'playcount':1}
def marker(a,b,c):return {'file':f'blacklanturn://search-status?version=1&both={a}&company={b}&collection={c}'}
class SearchBatch(unittest.TestCase):
 def test_one_run_preserves_full_independent_components_before_global_limit(self):
  a=[item('movie',n) for n in range(1,81)];b=[item('company',n) for n in range(81,101)];c=[item('collection',101)];nxt={'file':route('search','company',query='q',page=2)};raw=a+b+[nxt]+c+[marker(80,21,1)];before=copy.deepcopy(raw);calls=[];cache=RowResultCache()
  result=load_best_matches('q',lambda p:self.fail('unnecessary fallback'),batch_provider=lambda p:calls.append(p) or raw,cache=cache,revision=cache.revision)
  self.assertEqual(len(calls),1);self.assertEqual(len(result),40);self.assertEqual(raw,before)
  self.assertEqual(cache.get(route('search','company',query='q')),b+[nxt]);self.assertEqual(cache.get(route('search','collection',query='q')),c)
  self.assertEqual(result[0]['cast'],[{'name':'Actor'}])
 def test_missing_or_malformed_status_falls_back_without_caching_components(self):
  for status in ([],[marker(8,0,0)],[marker(0,0,0),marker(0,0,0)],[{'file':'blacklanturn://search-status?version=2&both=0&company=0&collection=0'}]):
   calls=[];cache=RowResultCache();result=load_best_matches('q',lambda p:calls.append(p) or [],batch_provider=lambda p:status,cache=cache,revision=cache.revision)
   self.assertEqual(len(calls),3);self.assertEqual(result,[]);self.assertIsNone(cache.get(route('search','company',query='q')))
 def test_failed_part_never_cached_as_empty_success(self):
  cache=RowResultCache();a=item('movie',1);r=load_best_matches('q',lambda p:self.fail('fallback'),batch_provider=lambda p:[a,marker(1,-1,0)],cache=cache,revision=cache.revision)
  self.assertEqual(r,[a]);self.assertIsNone(cache.get(route('search','company',query='q')));self.assertEqual(cache.get(route('search','collection',query='q')),[])  # Verified empty success has a short TTL.
 def test_no_results_with_failed_part_remains_error(self):
  with self.assertRaises(ValueError):load_best_matches('q',lambda p:[],batch_provider=lambda p:[marker(0,-1,0)])
 def test_navigation_cancellation_does_not_publish_any_component(self):
  cache=RowResultCache();active=[True]
  def fetch(p):active[0]=False;return [marker(0,0,0)]
  with self.assertRaises(ValueError):load_best_matches('q',lambda p:[],lambda:active[0],batch_provider=fetch,cache=cache,revision=cache.revision)
  self.assertEqual(cache.stats()['entries'],0)
class SearchBatchInitialRows(unittest.TestCase):
 def test_movie_row_is_reused_but_does_not_change_all_ranking(self):
  all_item=item('person',1);movie=item('movie',2);nxt={'file':route('search','movie',query='q',page=2)}
  raw=[all_item,movie,nxt,{'file':'blacklanturn://search-status?version=2&both=1&company=0&collection=0&movie=2'}]
  cache=RowResultCache()
  result=load_best_matches('q',lambda p:self.fail('unexpected fallback'),batch_provider=lambda p:raw,cache=cache,revision=cache.revision)
  self.assertEqual(result,[all_item]);self.assertEqual(cache.get(route('search','movie',query='q')),[movie,nxt])
 def test_failed_movie_row_does_not_turn_successful_empty_all_into_error(self):
  cache=RowResultCache();raw=[{'file':'blacklanturn://search-status?version=2&both=0&company=0&collection=0&movie=-1'}]
  self.assertEqual(load_best_matches('q',lambda p:self.fail('fallback'),batch_provider=lambda p:raw,cache=cache,revision=cache.revision),[])
  self.assertIsNone(cache.get(route('search','movie',query='q')))
 def test_wrong_entity_in_movie_partition_rejects_batch(self):
  from search_ui import batch_components
  self.assertIsNone(batch_components([item('company',2),{'file':'blacklanturn://search-status?version=2&both=0&company=0&collection=0&movie=1'}]))
if __name__=='__main__':unittest.main()
