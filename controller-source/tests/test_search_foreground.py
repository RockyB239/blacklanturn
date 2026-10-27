import ast,threading,unittest,time,sys
from pathlib import Path
from types import SimpleNamespace
P=Path(__file__).parents[1]/'addon/live_review.py'
sys.path.insert(0,str(P.parent))
def method(name):
 tree=ast.parse(P.read_text());cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='LiveReview');node=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name==name);ns={'submit_latest':__import__('provider_work').submit_latest,'threading':threading,'event':lambda *a,**k:None};exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(P),'exec'),ns);return ns[name]
class ForegroundSearch(unittest.TestCase):
 def test_serial_search_starts_after_home_and_old_result_is_not_published(self):
  home=threading.Event();release=threading.Event();search=threading.Event();published=[]
  s=SimpleNamespace(alive=True,generation=1,result_cache=SimpleNamespace(revision=0),paths=['home',''],path_tokens={},preview_dispatch_lock=threading.RLock(),list_lock=threading.Lock(),search_list_lock=threading.Lock(),search_state=None,startup_idle=True,rows=[[],[]])
  def load(d,**kw):
   if d['path']=='home':home.set();release.wait(3)
   else:search.set()
   return [{'label':d['path']}]
  s.cached_row_items=load;s.apply_row=lambda n,files,*a,**k:published.append(files[0]['label']);f=method('request_row_loads')
  try:
   f(s,[(0,{'path':'home','label':'Home'})]);self.assertTrue(home.wait(1));s.generation=2;s.paths[0]='search';s.search_state={'query':'q'}
   f(s,[(0,{'path':'search','label':'Search'})]);self.assertFalse(search.wait(.1));release.set();self.assertTrue(search.wait(1))
  finally:release.set();time.sleep(.1)
  self.assertEqual(published,['search'])
if __name__=='__main__':unittest.main()

class StaleRowCompletion(unittest.TestCase):
 def state(self,fetch):
  from cache_fixture import bind
  s=SimpleNamespace(alive=True,generation=1,config={},preview_dispatch_lock=threading.RLock())
  bind(s,{'get_list':lambda p:fetch(s),'row_items':lambda *a:[]})
  s.effects=[];s.configure_row_snapshots=lambda:s.effects.append('configure') or False
  s.restart_pending_rows=lambda:s.effects.append('restart');s.publish_cache_stats=lambda:None
  return s
 def test_obsolete_provider_completion_cannot_configure_restart_or_cache(self):
  from filtered_pages import PageCancelled
  def fetch(s):s.generation+=1;return [{'file':'old'}]
  s=self.state(fetch);path='plugin://plugin.video.themoviedb.helper/?info=popular'
  with self.assertRaises(PageCancelled):s.cached_row_items({'path':path})
  self.assertEqual(s.effects,[]);self.assertIsNone(s.result_cache.get(path))
 def test_snapshot_reconfiguration_restarts_but_rejects_old_response(self):
  from filtered_pages import PageCancelled
  s=self.state(lambda s:[{'file':'old'}]);path='plugin://plugin.video.themoviedb.helper/?info=popular'
  def changed():s.result_cache.clear();return True
  s.configure_row_snapshots=changed
  with self.assertRaises(PageCancelled):s.cached_row_items({'path':path})
  self.assertEqual(s.effects,['restart']);self.assertIsNone(s.result_cache.get(path))
