"""All-search subrequests must be reusable by the corresponding category."""
import unittest,copy
from urllib.parse import parse_qs,urlsplit
import test_discovery_controller as fixture
from search_ui import route,search_sources

def result(kind,n):
 info='discover' if kind=='company' else 'collection' if kind=='collection' else 'details'
 extra={'with_companies':str(n)} if kind=='company' else {'tmdb_id':str(n)}
 return {'file':route(info,kind,**extra),'label':kind+' result','title':kind+' result'}

class SearchResultReuse(unittest.TestCase):
 def state(self,provider=None):
  s,calls,controls=fixture.DiscoveryController().state(provider=provider or (lambda p:[result(parse_qs(urlsplit(p).query)['tmdb_type'][0],1)]))
  s.search_state={'query':'A24','kind':'all'};return s,calls,controls
 def all(self,s,query='A24'):
  path=search_sources(query)[0]['rows'][0]['path'];s.set_rows([{'label':'Best matches','path':path}]);return path
 def test_all_search_reuses_exact_studio_and_collection_results_without_refetch(self):
  s,calls,_=self.state();self.all(s);first=list(s.rows[0]);self.assertEqual(len(calls),3)
  for kind in ('company','collection'):
   path=route('search',kind,query='A24');s.set_rows([{'label':kind,'path':path}])
   self.assertEqual(len(calls),3,'All already fetched this exact category')
   self.assertEqual(s.rows[0],[result(kind,1)])
  self.all(s);self.assertEqual(len(calls),3);self.assertEqual(s.rows[0],first)
 def test_subresult_cache_retains_owned_copy_and_existing_memory_bounds(self):
  shared=[result('company',1)];s,calls,_=self.state(lambda p:shared if parse_qs(urlsplit(p).query)['tmdb_type']==['company'] else [result('movie',2)])
  self.all(s);path=route('search','company',query='A24');before=copy.deepcopy(shared);shared[0]['label']='later mutation'
  self.assertEqual(s.result_cache.get(path),before);self.assertLessEqual(s.result_cache.stats()['bytes'],2*1024*1024);self.assertEqual(s.result_cache.max_rows,48)
 def test_different_query_and_exact_movie_category_are_not_substituted_by_multi_search(self):
  s,calls,_=self.state();self.all(s)
  for kind,query in (('movie','A24'),('company','Pixar')):
   path=route('search',kind,query=query);s.set_rows([{'label':kind,'path':path}]);self.assertEqual(calls[-1],path)
  self.assertEqual(len(calls),5)
 def test_failed_subrequest_is_retried_instead_of_cached_as_success(self):
  attempts=[0]
  def provider(path):
   kind=parse_qs(urlsplit(path).query)['tmdb_type'][0]
   if kind=='company':
    attempts[0]+=1
    if attempts[0]==1:raise ValueError('Provider unavailable')
   return [result(kind,1)]
  s,calls,_=self.state(provider);self.all(s);path=route('search','company',query='A24');self.assertIsNone(s.result_cache.get(path))
  s.set_rows([{'label':'Studios','path':path}]);self.assertEqual(attempts[0],2);self.assertEqual(s.rows[0],[result('company',1)])
 def test_invalidation_during_subrequest_rejects_old_cache_and_stops_further_requests(self):
  def provider(path):
   if parse_qs(urlsplit(path).query)['tmdb_type']==['company']:s.invalidate_row_results()
   return [result('movie',1)]
  s,calls,_=self.state(provider);self.all(s);self.assertGreaterEqual(len(calls),1);self.assertLessEqual(len(calls),2)
  for kind in ('both','company','collection'):self.assertIsNone(s.result_cache.get(route('search',kind,query='A24')))

class QueryPersistence(unittest.TestCase):
 def test_query_only_save_persists_without_invalidating_or_restarting_browsing(self):
  import json,tempfile
  from pathlib import Path
  from types import SimpleNamespace
  from test_window_lifecycle import ROOT
  with tempfile.TemporaryDirectory() as folder:
   calls=[];s=SimpleNamespace(config={'SearchQuery':'A24'},alive=True,invalidate_row_results=lambda:calls.append('invalidate'),restart_pending_rows=lambda:calls.append('restart'))
   save=fixture.methods(['save'],{'json':json,'STORE':Path(folder)})['save'];save(s,invalidate=False)
   self.assertEqual(json.loads((Path(folder)/'rows.json').read_text()),s.config);self.assertEqual(calls,[])
   save(s);self.assertEqual(calls,['invalidate','restart'],'Normal configuration saves must keep full invalidation')
 def test_recent_search_text_does_not_change_public_snapshot_scope(self):
  from public_rows import snapshot_scope
  base={'Home':[{'path':route('popular','movie')}],'SearchQuery':'A24'}
  self.assertEqual(snapshot_scope(base,b'account'),snapshot_scope(dict(base,SearchQuery='Alien'),b'account'))
  self.assertNotEqual(snapshot_scope(base,b'account'),snapshot_scope(base,b'new-account'))
  self.assertNotEqual(snapshot_scope(base,b'account'),snapshot_scope(dict(base,Home=[]),b'account'))
 def test_opening_search_cancels_old_row_owner_and_requests_query_only_persistence(self):
  from types import SimpleNamespace
  from test_window_lifecycle import extract,ROOT
  calls=[];s=SimpleNamespace(search_state=None,config={'SearchQuery':'old'},generation=3,capture_browse=lambda:{'origin':True},stop_preview=lambda:None,setProperty=lambda *a:None,getControl=lambda cid:SimpleNamespace(setHeight=lambda h:None),save=lambda **kw:calls.append(kw),select_search=lambda n:None)
  extract(ROOT/'live_review.py','open_search',{},'LiveReview')(s,'A24')
  self.assertEqual(calls,[{'invalidate':False}]);self.assertGreater(s.generation,3)
if __name__=='__main__':unittest.main()
