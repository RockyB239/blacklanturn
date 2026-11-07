"""Restarted sections paint owned displays, then use the existing visible worker."""
import sys,tempfile,time,unittest
from pathlib import Path
from types import MethodType
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from browse_controls import AnimeMetadata
from filtered_pages import PageCancelled,upstream_path
from home_rows import HomeRowSnapshots
from public_rows import PublicRowSnapshots
from title_preferences import TitlePreferences,discovery_scope
import test_snapshot_controller as fixture
from test_window_lifecycle import extract

BASE='plugin://plugin.video.themoviedb.helper/?'
def route(info,kind='tv',extra=''):
 return BASE+'info='+info+'&tmdb_type='+kind+'&nextpage=true&widget=true'+extra
def title(n,kind='tv',anime=False):
 return {'file':BASE+'info='+('seasons' if kind=='tv' else 'play')+'&tmdb_type='+kind+'&tmdb_id='+str(n),'filetype':'directory' if kind=='tv' else 'file','type':'tvshow' if kind=='tv' else 'movie','label':str(n),'title':str(n),'genre':['Animation' if anime else 'Drama'],'country':['JP'],'playcount':2,'resume':{'position':40,'total':100}}
def page_data(path):
 return {path:[title(n,anime=n>2) for n in range(1,21)]+[{'file':path+'&page=2','filetype':'directory','label':'Next page'}],path+'&page=2':[title(n) for n in range(21,41)]+[{'file':path+'&page=3','filetype':'directory','label':'Next page'}]}
def labels(files):return [x['label'] for x in files]
FILLED=['1','2']+[str(n) for n in range(21,39)]+['Next']

class SectionDisplaySnapshots(unittest.TestCase):
 def state(self,folder,section,provider,scope='account'):
  s,calls,controls,queue=fixture.SnapshotController().state(folder,provider)
  s.section=section;s.mode='home';s.search_state=None;s.person_context=None;s.discovery_stack=[]
  s.anime_metadata=AnimeMetadata(folder)
  s.home_snapshot_cache=HomeRowSnapshots(Path(folder)/'home.json',scope)
  return s,calls,controls,queue

 def test_shows_and_movies_share_both_home_routes_before_provider_and_hydrate_without_rebinding(self):
  for section,kind in (('Shows','tv'),('Movies','movie')):
   with self.subTest(section=section),tempfile.TemporaryDirectory() as folder:
    paths=[route('trakt_recommendations',kind),route('trending_week',kind)]
    store=HomeRowSnapshots(Path(folder)/'home.json','account')
    for path in paths:self.assertTrue(store.put(path,[title(1,kind)]))
    s,calls,controls,queue=self.state(folder,section,lambda path:[title(1,kind),title(2,kind)])
    s.set_rows([{'path':path,'label':str(n)} for n,path in enumerate(paths)])
    self.assertEqual([labels(row) for row in s.rows],[['1'],['1']]);self.assertEqual(calls,[])
    self.assertEqual(s.snapshot_rows,{0:True,1:True});self.assertEqual(len(queue),1)
    cards=[controls[900+n].items[0] for n in range(2)];s.focus=105
    queue.pop(0)()
    self.assertEqual(calls,paths);self.assertEqual(s.focus,105)
    for n,card in enumerate(cards):
     self.assertIs(controls[900+n].items[0],card);self.assertEqual(card.properties['watchState'],'progress');self.assertEqual(card.resume,(40.,100.));self.assertEqual(labels(s.rows[n]),['1'])

 def test_fresh_section_recommendations_persist_for_home_and_other_section(self):
  for section,kind in (('Shows','tv'),('Movies','movie')):
   with self.subTest(section=section),tempfile.TemporaryDirectory() as folder:
    path=route('trakt_recommendations',kind)
    s,calls,_,_=self.state(folder,section,lambda p:[title(1,kind)])
    self.assertEqual(labels(s.cached_row_items({'path':path,'label':'Recommended'})),['1']);self.assertEqual(calls,[path])
    self.assertIsNone(s.snapshot_cache.get(path),'Private recommendations never enter the public store')
    saved=HomeRowSnapshots(s.home_snapshot_cache.path,'account').get(path);self.assertIsNotNone(saved);self.assertEqual(labels(saved),['1'])
    for destination in ('Home','Shows','Movies'):
     fresh,new_calls,_,_=self.state(folder,destination,lambda p:self.fail('Saved display paints before refresh'))
     fresh.set_rows([{'path':path,'label':'Recommended'}]);self.assertEqual(labels(fresh.rows[0]),['1']);self.assertEqual(new_calls,[])

 def test_shared_private_progress_cards_keep_play_guard_but_other_sections_do_not_read_home(self):
  with tempfile.TemporaryDirectory() as folder:
   path=route('trakt_ondeck');store=HomeRowSnapshots(Path(folder)/'home.json','account');store.put(path,[title(1)])
   for section in ('Shows','Movies'):
    s,calls,_,_=self.state(folder,section,lambda p:[]);s.set_rows([{'path':path,'label':'Continue'}]);self.assertEqual(labels(s.rows[0]),['1']);self.assertEqual(s.rows[0][0]['_home_progress_scope'],'account');self.assertEqual(calls,[])
   s,calls,_,_=self.state(folder,'My Stuff',lambda p:[]);s.set_rows([{'path':path,'label':'Continue'}]);self.assertEqual(s.rows[0],[])

 def test_wrong_account_expired_home_and_private_routes_still_require_provider(self):
  for boundary in ('account','expired','watchlist','search','user'):
   with self.subTest(boundary=boundary),tempfile.TemporaryDirectory() as folder:
    path=route('trakt_recommendations');store=HomeRowSnapshots(Path(folder)/'home.json','account',clock=lambda:1000 if boundary=='expired' else time.time());store.put(path,[title(1)])
    if boundary=='watchlist':path=route('trakt_watchlist')
    elif boundary=='search':path=route('search',extra='&query=private')
    elif boundary=='user':path+='&user=private'
    s,calls,_,queue=self.state(folder,'Shows',lambda p:[title(2)],scope='different' if boundary=='account' else 'account')
    s.set_rows([{'path':path,'label':'Private'}]);self.assertEqual(s.rows[0],[]);self.assertEqual(calls,[])
    queue.pop(0)();self.assertEqual(calls,[path]);self.assertEqual(labels(s.rows[0]),['2']);self.assertIsNone(s.snapshot_cache.get(path))
    if boundary not in ('account','expired'):self.assertIsNone(s.home_snapshot_cache.get(path))

 def test_public_display_survives_thirty_days_but_refreshes_and_expires_after_bound(self):
  for age,visible in ((901,True),(86401,True),(30*86400,True),(30*86400+1,False),(-1,False)):
   with self.subTest(age=age),tempfile.TemporaryDirectory() as folder:
    path=route('discover',extra='&with_genres=18');s,calls,controls,queue=self.state(folder,'Shows',lambda p:[title(1)])
    cache=PublicRowSnapshots(Path(folder)/'snapshot.json','scope',clock=lambda:1000);cache.put(path,[title(1)])
    s.snapshot_cache=PublicRowSnapshots(cache.path,'scope',clock=lambda:1000+age)
    s.set_rows([{'path':path,'label':'Drama'}]);self.assertEqual(bool(s.rows[0]),visible);self.assertEqual(calls,[])
    if visible:self.assertEqual(controls[900].items[0].properties['watchState'],'unknown')
    queue.pop(0)();self.assertEqual(calls,[path]);self.assertEqual(s.rows[0][0]['playcount'],2)

 def test_completed_filtered_genre_persists_exact_order_next_cursor_and_raw_session_page(self):
  with tempfile.TemporaryDirectory() as folder:
   path=route('discover',extra='&with_genres=18');data=page_data(path)
   s,calls,_,_=self.state(folder,'Shows',lambda p:data[p]);filled=s.cached_row_items({'path':path,'label':'Drama'})
   self.assertEqual(labels(filled),FILLED);self.assertEqual(calls,[path,path+'&page=2']);self.assertEqual(s.result_cache.get(path),data[path])
   saved=PublicRowSnapshots(s.snapshot_cache.path,'scope').get(path);self.assertEqual(labels(saved),FILLED);self.assertEqual(saved[-1]['file'],path+'&page=2&bl_start=18')
   self.assertTrue(all('playcount' not in item and 'resume' not in item for item in saved))
   fresh,new_calls,_,queue=self.state(folder,'Shows',lambda p:self.fail('Completed display must paint first'));fresh.set_rows([{'path':path,'label':'Drama'}])
   self.assertEqual(labels(fresh.rows[0]),FILLED);self.assertEqual(fresh.rows[0][-1]['_page_control'],'next');self.assertEqual(new_calls,[]);self.assertEqual(len(queue),1)

 def test_filtered_session_hit_persists_completed_public_display_without_more_requests(self):
  with tempfile.TemporaryDirectory() as folder:
   path=route('discover',extra='&with_genres=18')
   filled=[title(1),title(2)]+[title(n) for n in range(21,39)]+[{'file':path+'&page=2&bl_start=18','filetype':'directory','label':'Next'}]
   s,calls,_,_=self.state(folder,'Shows',lambda p:self.fail('No extra fetch'));s.result_cache.put('filtered-v1:'+path,filled);s.snapshot_cache.put(path,[title(999)])
   self.assertEqual(labels(s.cached_row_items({'path':path,'label':'Drama'})),FILLED);self.assertEqual(calls,[])
   self.assertEqual(labels(PublicRowSnapshots(s.snapshot_cache.path,'scope').get(path)),FILLED)

 def test_failed_or_canceled_public_fill_preserves_previous_complete_display(self):
  for boundary in ('failure','cancel'):
   with self.subTest(boundary=boundary),tempfile.TemporaryDirectory() as folder:
    path=route('discover',extra='&with_genres=18');data=page_data(path)
    def provider(p):
     if p!=path:
      if boundary=='cancel':s.generation+=1
      else:raise OSError('offline')
     return data[p]
    s,_,_,_=self.state(folder,'Shows',provider);s.snapshot_cache.put(path,[title(999)]);before=s.snapshot_cache.path.read_bytes()
    with self.assertRaises(PageCancelled if boundary=='cancel' else OSError):s.cached_row_items({'path':path,'label':'Drama'})
    self.assertEqual(s.snapshot_cache.path.read_bytes(),before);self.assertEqual(labels(PublicRowSnapshots(s.snapshot_cache.path,'scope').get(path)),['999'])

 def test_configuration_change_during_public_fill_rejects_old_work(self):
  with tempfile.TemporaryDirectory() as folder:
   path=route('discover',extra='&with_genres=18');data=page_data(path);changed=[False]
   def provider(p):
    if p!=path:changed[0]=True
    return data[p]
   s,_,_,_=self.state(folder,'Shows',provider);old=s.snapshot_cache
   def configure():
    if changed[0]:
     changed[0]=False;s.invalidate_row_results();s.snapshot_cache=PublicRowSnapshots(old.path,'new-account-config');return True
    return False
   s.configure_row_snapshots=configure
   with self.assertRaises(PageCancelled):s.cached_row_items({'path':path,'label':'Drama'})
   self.assertIsNone(s.snapshot_cache.get(path));self.assertIsNone(PublicRowSnapshots(old.path,'scope').get(path))

 def test_successful_filtered_empty_removes_previous_public_display(self):
  with tempfile.TemporaryDirectory() as folder:
   path=route('discover',extra='&with_genres=18');data=page_data(path);data[path]=[title(n,anime=True) for n in range(20)]+[{'file':path+'&page=2','filetype':'directory','label':'Next page'}];data[path+'&page=2']=[]
   s,_,_,_=self.state(folder,'Shows',lambda p:data[p]);s.snapshot_cache.put(path,[title(999)])
   self.assertEqual(s.cached_row_items({'path':path,'label':'Drama'}),[]);self.assertIsNone(PublicRowSnapshots(s.snapshot_cache.path,'scope').get(path))

 def test_upstream_filtered_country_route_saves_completed_logical_public_display(self):
  with tempfile.TemporaryDirectory() as folder:
   path=route('discover',extra='&with_origin_country=JP');actual=upstream_path(path)
   s,calls,_,_=self.state(folder,'Shows',lambda p:[title(1)] if p==actual else self.fail('Unexpected upstream route'))
   self.assertEqual(labels(s.cached_row_items({'path':path,'label':'Japan'})),['1']);self.assertEqual(calls,[actual])
   saved=PublicRowSnapshots(s.snapshot_cache.path,'scope').get(path);self.assertIsNotNone(saved);self.assertEqual(labels(saved),['1'])

 def test_title_preferences_apply_after_shared_retention_and_can_restore_without_fetch(self):
  with tempfile.TemporaryDirectory() as folder:
   path=route('trakt_recommendations');s,_,_,_=self.state(folder,'Shows',lambda p:[title(1),title(2)]);s.cached_row_items({'path':path,'label':'Recommended'})
   prefs=TitlePreferences(Path(folder)/'prefs.json');prefs.set(title(1),'hide')
   fresh,calls,_,_=self.state(folder,'Shows',lambda p:self.fail('No provider before queued refresh'));fresh.title_preferences=prefs
   for name in ('prepare_title_row','raw_title_row','hydrate_title_row'):
    setattr(fresh,name,MethodType(extract(Path(__file__).parents[1]/'addon/title_feedback_ui.py',name,{'discovery_scope':discovery_scope},'TitleFeedback'),fresh))
   fresh.set_rows([{'path':path,'label':'Recommended'}]);self.assertEqual(labels(fresh.rows[0]),['2']);self.assertEqual(calls,[])
   prefs.restore(title(1));fresh.apply_row(0,fresh.raw_title_row(0),'Recommended');self.assertEqual(labels(fresh.rows[0]),['1','2']);self.assertEqual(labels(HomeRowSnapshots(fresh.home_snapshot_cache.path,'account').get(path)),['1','2']);self.assertEqual(calls,[])

 def test_missing_visible_row_loads_before_already_painted_refresh(self):
  with tempfile.TemporaryDirectory() as folder:
   first=route('trakt_recommendations');second=route('discover',extra='&with_genres=18')
   s,calls,_,queue=self.state(folder,'Shows',lambda p:[title(1)]);s.home_snapshot_cache.put(first,[title(1)])
   s.set_rows([{'path':first,'label':'Recommended'},{'path':second,'label':'Drama'}]);queue.pop(0)()
   self.assertEqual(calls,[second,first])

if __name__=='__main__':unittest.main()
