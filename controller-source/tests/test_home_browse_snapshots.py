"""Lower Home reuse stays account-owned and uses existing refresh workers."""
import json,sys,tempfile,unittest
from pathlib import Path
from urllib.parse import urlencode
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from home_rows import HomeRowSnapshots,home_path
from test_public_row_snapshots import ITEM
import test_snapshot_controller as controller_fixture
ROUTES=[('trakt_recommendations','tv'),('trakt_recommendations','movie'),('trakt_trending','tv'),('trakt_trending','movie'),('trakt_ondeck','tv'),('trakt_inprogress','movie'),('trakt_nextepisodes','tv'),('trending_week','tv'),('trending_week','movie')]
BASE='plugin://plugin.video.themoviedb.helper/?'
def route(info,kind):return BASE+urlencode(dict(info=info,tmdb_type=kind,nextpage='true',widget='true'))
PATHS=[route(*pair) for pair in ROUTES]
def cards(kind):
 return [dict(ITEM,art=dict(ITEM['art']),file=BASE+urlencode(dict(info='details',tmdb_type=kind,tmdb_id=str(i+1))),title='Title '+str(i+1),plot='Display plot. '*120,lastplayed='private-last-played',watched=True,watchedepisodes=5,resume_point=90,resumetime=90) for i in range(20)]
class HomeBrowseSnapshots(unittest.TestCase):
 def store(self,folder,scope='account',now=1000):return HomeRowSnapshots(Path(folder)/'home.json',scope,clock=lambda:now)
 def test_all_nine_home_rows_survive_restart_without_status_or_extra_fetch(self):
  with tempfile.TemporaryDirectory() as folder:
   s=self.store(folder)
   for path,(_,kind) in zip(PATHS,ROUTES):self.assertTrue(s.put(path,cards(kind)),path)
   restored=self.store(folder,now=1000+12*3600)
   for path in PATHS:
    self.assertEqual(len(restored.get(path)),20,path)
    self.assertNotIn('playcount',restored.get(path)[0]);self.assertNotIn('resume',restored.get(path)[0])
   raw=s.path.read_text()
   for private in ('private-last-played','lastplayed','watchedepisodes','resume_point','resumetime','watched','secret'):self.assertNotIn(private,raw)
   self.assertLessEqual(s.path.stat().st_size,1024*1024)
   self.assertIsNone(self.store(folder,'other-account').get(PATHS[4]));self.assertIsNone(self.store(folder,now=1000+86401).get(PATHS[4]))
 def test_lower_routes_do_not_expand_startup_model_validation(self):
  for path in PATHS[2:]:self.assertFalse(home_path(path))
 def test_only_exact_routes_safe_actions_and_bounded_paging_persist(self):
  with tempfile.TemporaryDirectory() as folder:
   s=self.store(folder);path=PATHS[4]
   for bad in [route('trakt_history','tv'),route('trakt_watchlist','movie'),route('trakt_ondeck','movie'),route('trakt_inprogress','tv'),route('trakt_nextepisodes','movie'),route('search','tv'),route('popular','tv'),path+'&user=me',path+'&query=private',path+'&token=secret',path+'&page=2',path+'&info=trakt_ondeck',path+'&reload=true',path+'#fragment',' '+path,path+'&page=10001',path+'&'*600]:
    self.assertFalse(s.put(bad,[ITEM]),bad)
   for info,kind in ROUTES:
    path=route(info,kind);params=dict(info=info,tmdb_type=kind,nextpage='true',widget='true',page='2',cacheonly='FALSE',plugin_category='private breadcrumb',reload='$INFO[Window(Home).Property(TMDbHelper.Widgets.Reload)]');paging=BASE+urlencode(params)
    self.assertTrue(s.put(path,[ITEM,{'file':paging,'label':'Next page','filetype':'directory'}]),path)
    self.assertIn('cacheonly=false',self.store(folder).get(path)[-1]['file']);self.assertNotIn('breadcrumb',s.path.read_text())
    for bad in (paging+'&token=secret',paging.replace('page=2','page=10001'),paging.replace('page=2','page=0'),paging.replace('page=2','page=2%7C3'),route('trakt_watchlist',kind)+'&page=2','https://private.example/?token=secret',route('trakt_ondeck','tv')):
     self.assertFalse(s.put(path,[dict(ITEM,file=bad)]),bad)
 def test_reload_rejects_malformed_future_oversize_and_mutable_results(self):
  with tempfile.TemporaryDirectory() as folder:
   s=self.store(folder);path=PATHS[4];original=cards('tv');self.assertTrue(s.put(path,original));original[0]['art']['poster']='changed'
   fetched=s.get(path);fetched[0]['title']='changed';fetched[0]['art']['poster']='changed'
   self.assertEqual(s.get(path)[0]['title'],'Title 1');self.assertNotEqual(s.get(path)[0]['art']['poster'],'changed');self.assertIsNone(self.store(folder,now=999).get(path))
   self.assertFalse(s.put(path,[dict(ITEM,plot='x'*300000)]));self.assertFalse(s.put(path,[ITEM]*41))
   for value in ('bad','[]','x'*(1024*1024+1),json.dumps({'version':2,'scope':'account','rows':[{'path':path,'time':1000,'items':[dict(ITEM,title=[])]}]})):
    s.path.write_text(value);self.assertIsNone(self.store(folder).get(path))
 def test_row_and_aggregate_budgets_evict_old_display_without_growth(self):
  with tempfile.TemporaryDirectory() as folder:
   s=self.store(folder)
   paths=PATHS+[path.replace('widget=true','widget=false') for path in PATHS]
   for path in paths:self.assertTrue(s.put(path,[ITEM]))
   self.assertIsNone(self.store(folder).get(paths[0]));self.assertIsNotNone(self.store(folder).get(paths[-1]));self.assertLessEqual(len(json.loads(s.path.read_text())['rows']),12)
   for path in paths:
    self.assertTrue(s.put(path,[dict(ITEM,plot='x'*120000)]));self.assertLessEqual(s.path.stat().st_size,1024*1024)
   self.assertIsNone(self.store(folder).get(paths[0]));self.assertIsNotNone(self.store(folder).get(paths[-1]))
 def test_clear_during_sanitization_rejects_late_writer(self):
  with tempfile.TemporaryDirectory() as folder:
   s=self.store(folder);path=PATHS[4];self.assertTrue(s.put(path,[ITEM]));revision=s.revision;sanitize=s.sanitize_items
   def invalidated(files):s.clear();return sanitize(files)
   s.sanitize_items=invalidated;self.assertFalse(s.put(path,[ITEM],revision=revision));self.assertIsNone(self.store(folder).get(path))
class LowerHomeController(unittest.TestCase):
 def state(self,folder,provider):
  s,calls,controls,queue=controller_fixture.SnapshotController().state(folder,provider);s.section='Home';s.home_snapshot_cache=HomeRowSnapshots(Path(folder)/'home.json','account');return s,calls,controls,queue
 def test_lower_saved_row_paints_then_refreshes_watch_metadata_in_place(self):
  for path in PATHS[2:]:
   with self.subTest(path=path),tempfile.TemporaryDirectory() as folder:
    fresh=dict(ITEM,playcount=2,resume={'position':40,'total':100});s,calls,controls,queue=self.state(folder,lambda p:[fresh]);self.assertTrue(s.home_snapshot_cache.put(path,[ITEM]));s.set_rows([{'label':'Lower row','path':path}]);card=controls[900].items[0]
    self.assertEqual(calls,[]);self.assertEqual(card.properties['watchState'],'unknown');s.focus=105;s.update=lambda item:None;mutations=[]
    for name in ('reset','addItems','selectItem'):setattr(controls[900],name,lambda *a,n=name:mutations.append(n))
    queue.pop(0)();self.assertEqual(calls,[path]);self.assertEqual(mutations,[]);self.assertEqual(s.focus,105);self.assertIs(controls[900].items[0],card);self.assertEqual(card.properties['watchState'],'progress');self.assertEqual(card.resume,(40.,100.))
 def test_empty_refresh_removes_disk_stale_row_and_full_reload_uses_empty(self):
  with tempfile.TemporaryDirectory() as folder:
   path=PATHS[4];s,calls,controls,queue=self.state(folder,lambda p:[]);self.assertTrue(s.home_snapshot_cache.put(path,[ITEM]));definitions=[{'label':'Continue','path':path},{'label':'Local','path':'','local_items':[ITEM]}];s.set_rows(definitions);queue.pop(0)()
   self.assertIsNone(HomeRowSnapshots(s.home_snapshot_cache.path,'account').get(path));s.set_rows(definitions);self.assertEqual(s.rows[0],[]);self.assertEqual(calls,[path])
 def test_full_controller_recreation_keeps_nine_rows_and_saved_order(self):
  with tempfile.TemporaryDirectory() as folder:
   s,_,_,_=self.state(folder,lambda p:[ITEM])
   for path in PATHS:self.assertTrue(s.home_snapshot_cache.put(path,[ITEM]))
   new,calls,controls,queue=self.state(folder,lambda p:[ITEM]);definitions=[{'label':str(i),'path':path} for i,path in reversed(list(enumerate(PATHS)))];new.set_rows(definitions)
   self.assertEqual(new.page_definitions,definitions);self.assertEqual(new.paths[:2],list(reversed(PATHS))[:2]);self.assertEqual(calls,[])
   for path in PATHS:self.assertIsNotNone(new.home_snapshot_cache.get(path))
 def test_invalidation_rejects_refresh_before_and_during_provider(self):
  for running in (False,True):
   with self.subTest(running=running),tempfile.TemporaryDirectory() as folder:
    def provider(path):s.invalidate_row_results();return [dict(ITEM,title='Late')]
    path=PATHS[4];s,calls,controls,queue=self.state(folder,provider);self.assertTrue(s.home_snapshot_cache.put(path,[ITEM]));s.set_rows([{'label':'Continue','path':path}])
    if not running:s.invalidate_row_results()
    queue.pop(0)();self.assertEqual(calls,[path] if running else []);self.assertIsNone(s.home_snapshot_cache.get(path));self.assertIsNone(s.result_cache.get(path));self.assertEqual(s.rows[0][0]['title'],ITEM['title'])
if __name__=='__main__':unittest.main()
