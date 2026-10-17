"""Filtered discovery pages fill shelves without losing overflow titles."""
import importlib.util,unittest,sys
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
ROOT=Path(__file__).parents[1]/'addon';sys.path.insert(0,str(ROOT))
from browse_controls import is_next_page,page_cards
from live_core import PageHistory
ORIGIN='plugin://plugin.video.themoviedb.helper/?info=discover&tmdb_type=tv'
def title(n,anime=False):return {'file':'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id='+str(n),'label':str(n),'anime':anime}
def more(page):return {'file':ORIGIN+'&page='+str(page),'filetype':'directory','label':'Next page'}
def keep(files):return [x for x in files if not x.get('anime')]
class FilteredPages(unittest.TestCase):
 def module(self):
  path=ROOT/'filtered_pages.py';self.assertTrue(path.exists(),'Filtered discovery lacks page filling and an overflow cursor')
  spec=importlib.util.spec_from_file_location('filtered_pages',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 def test_two_eligible_titles_fill_from_following_page_without_discarding_overflow(self):
  m=self.module();pages={ORIGIN:[title(n,n>2) for n in range(1,21)]+[more(2)],ORIGIN+'&page=2':[title(n) for n in range(21,41)]+[more(3)],ORIGIN+'&page=3':[title(n) for n in range(41,51)]};calls=[]
  def fetch(path):calls.append(path);return pages[path]
  first=m.fill_page(ORIGIN,pages[ORIGIN],fetch,keep)
  self.assertEqual([x['label'] for x in first if not is_next_page(x,ORIGIN)],['1','2']+[str(n) for n in range(21,39)])
  cursor=first[-1]['file'];self.assertTrue(is_next_page(first[-1],ORIGIN));second=m.fill_page(cursor,fetch(m.provider_path(cursor)),fetch,keep)
  self.assertEqual([x['label'] for x in second],[str(n) for n in range(39,51)]);self.assertFalse(any(is_next_page(x,cursor) for x in second))
  self.assertEqual(calls.count(ORIGIN+'&page=2'),2,'A supplied first page must not be refetched inside fill_page')
 def test_cursor_can_continue_inside_the_same_provider_page(self):
  m=self.module();path=ORIGIN+'&page=4';files=[title(n) for n in range(1,31)];out=m.fill_page(path,files,lambda p:self.fail('Unnecessary provider request'),keep)
  self.assertEqual(len(out),21);self.assertTrue(is_next_page(out[-1],path));cursor=out[-1]['file']
  self.assertEqual([x['label'] for x in m.fill_page(cursor,files,None,keep)],[str(n) for n in range(21,31)])
  rendered,_=page_cards(out,PageHistory(),path);self.assertEqual(rendered[-1]['_page_control'],'next')
 def test_all_anime_page_is_skipped_and_a_final_short_page_has_no_next(self):
  m=self.module();first=[title(n,True) for n in range(20)]+[more(2)];last=[title(30),title(31)]
  self.assertEqual(m.fill_page(ORIGIN,first,lambda p:last,keep),last)
 def test_complete_page_does_not_eagerly_fetch_the_next_page(self):
  m=self.module();files=[title(n) for n in range(20)]+[more(2)]
  out=m.fill_page(ORIGIN,files,lambda p:self.fail('Full row must not prefetch'),keep)
  self.assertEqual(len(out),21);self.assertEqual(out[-1]['file'],more(2)['file'])
 def test_raw_provider_result_is_not_mutated(self):
  import copy
  m=self.module();files=[title(n,n>1) for n in range(20)]+[more(2)];original=copy.deepcopy(files)
  m.fill_page(ORIGIN,files,lambda p:[title(100+n) for n in range(20)],keep);self.assertEqual(files,original)
 def test_cancellation_stops_following_provider_requests(self):
  m=self.module();alive=[True];calls=[]
  def fetch(p):calls.append(p);alive[0]=False;return [title(30)]+[more(3)]
  with self.assertRaises(m.PageCancelled):m.fill_page(ORIGIN,[more(2)],fetch,keep,current=lambda:alive[0])
  self.assertEqual(len(calls),1)
 def test_failed_refill_never_becomes_a_successful_partial_page(self):
  m=self.module()
  def fail(p):raise RuntimeError('offline')
  with self.assertRaisesRegex(RuntimeError,'offline'):m.fill_page(ORIGIN,[title(1),more(2)],fail,keep)
 def test_repeated_routes_or_request_limit_fail_recoverably(self):
  m=self.module()
  with self.assertRaises(ValueError):m.fill_page(ORIGIN,[more(2)],lambda p:[more(2)],keep)
  def fetch(p):return [more(int(parse_qs(urlsplit(p).query)['page'][0])+1)]
  with self.assertRaises(RuntimeError):m.fill_page(ORIGIN,[more(2)],fetch,keep,max_pages=3)
 def test_cursor_is_stripped_before_the_provider_and_shortness_is_detected(self):
  m=self.module();files=[title(n,n>1) for n in range(20)]+[more(2)]
  self.assertTrue(m.needs_fill(ORIGIN,files,keep));self.assertFalse(m.needs_fill(ORIGIN,[title(n) for n in range(20)]+[more(2)],keep))
  self.assertEqual(m.provider_path(ORIGIN+'&bl_start=3'),ORIGIN)
 def test_same_provider_page_cursor_retains_the_row_heading(self):
  from row_feedback import provider_page_label
  self.assertEqual(provider_page_label(ORIGIN+'&page=2',ORIGIN+'&page=2&bl_start=18','Japanese picks','Next'),'Japanese picks')
 def test_japan_only_discover_can_exclude_animation_upstream_without_affecting_other_countries(self):
  m=self.module();self.assertTrue(hasattr(m,'upstream_path'),'Japan-only rows still fetch and discard large anime pages')
  jp=ORIGIN+'&with_origin_country=JP';p=m.upstream_path(jp+'&without_genres=99');self.assertEqual(parse_qs(urlsplit(p).query)['without_genres'],['99,16'])
  for path in (ORIGIN,ORIGIN+'&with_origin_country=JP|US',ORIGIN.replace('discover','search')+'&with_origin_country=JP'):self.assertEqual(m.upstream_path(path),path)
 def test_upstream_page_links_return_to_the_logical_route(self):
  m=self.module();self.assertTrue(hasattr(m,'logical_files'))
  jp=ORIGIN+'&with_origin_country=JP';up=jp+'&without_genres=16';files=[title(1),{'file':up+'&page=2','filetype':'directory','label':'Next page'}]
  fixed=m.logical_files(files,up,jp);self.assertTrue(is_next_page(fixed[-1],jp));self.assertNotIn('without_genres',parse_qs(urlsplit(fixed[-1]['file']).query));self.assertIn('without_genres',files[-1]['file'])
if __name__=='__main__':unittest.main()

class ControllerFilteredPages(unittest.TestCase):
 def bind_pages(self,s,calls,pages,provider=None):
  from types import MethodType,SimpleNamespace
  from test_discovery_controller import methods,SyncThread
  from row_feedback import provider_page_label,row_message
  from live_core import valid_source
  ns=methods(['load_path'],dict(threading=SimpleNamespace(Thread=SyncThread),valid_source=valid_source,provider_page_label=provider_page_label,row_message=row_message,TMDB='plugin://plugin.video.themoviedb.helper/',get_list=provider or (lambda p:calls.append(p) or pages[p]),event=lambda *a,**kw:None))
  s.load_path=MethodType(ns['load_path'],s)
 def state(self):
  import tempfile
  from browse_controls import AnimeMetadata
  from test_discovery_controller import DiscoveryController
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  pages={ORIGIN:[dict(title(n),genre=['Drama'] if n<3 else ['Animation'],country=['JP']) for n in range(1,21)]+[more(2)],ORIGIN+'&page=2':[dict(title(n),genre=['Drama'],country=['JP']) for n in range(21,41)]+[more(3)],ORIGIN+'&page=3':[dict(title(n),genre=['Drama'],country=['JP']) for n in range(41,51)]}
  s,calls,controls=DiscoveryController().state(provider=lambda p:pages[p]);s.section='Shows';s.search_state=None;s.person_context=None;s.discovery_stack=[];s.config={};s.anime_metadata=AnimeMetadata(self.tmp.name)
  return s,calls,controls,pages
 def test_actual_worker_fills_short_rows_and_keeps_shared_raw_cache_intact(self):
  s,calls,_,pages=self.state();s.set_rows([{'label':'Japanese picks','path':ORIGIN}])
  self.assertEqual(len([x for x in s.rows[0] if not x.get('_page_control')]),20)
  self.assertEqual(s.result_cache.get(ORIGIN),pages[ORIGIN]);self.assertEqual(s.rows[0][-1]['_page_control'],'next')
  calls.clear();s.set_rows([{'label':'Japanese picks','path':ORIGIN}]);self.assertEqual(calls,[],'Filled rows should be retained within the existing bounded session cache')
 def test_retained_sparse_snapshot_is_not_presented_as_a_complete_short_row(self):
  s,_,_,pages=self.state();s.search_state={'query':'anime'};s.set_rows([{'label':'Search','path':ORIGIN}]);s.search_state=None;s.result_cache.clear();s.result_cache.put(ORIGIN,pages[ORIGIN])
  retained,_=s.retained_row_items({'path':ORIGIN});self.assertIsNone(retained,'Raw short filtered cache needs asynchronous filling before display')
 def test_unfiltered_search_keeps_anime_and_original_provider_pagination(self):
  s,calls,_,pages=self.state();s.search_state={'query':'anime'};s.set_rows([{'label':'Search','path':ORIGIN}])
  self.assertEqual(calls,[ORIGIN]);self.assertEqual(len([x for x in s.rows[0] if not x.get('_page_control')]),20)
  self.assertEqual(s.rows[0][-1]['file'],more(2)['file'])
 def test_actual_next_and_previous_restore_the_filled_page_and_selected_next_card(self):
  from types import MethodType,SimpleNamespace
  import threading
  from test_discovery_controller import methods,SyncThread
  from row_feedback import provider_page_label,row_message
  from live_core import valid_source
  s,calls,controls,pages=self.state();s.set_rows([{'label':'Japanese picks','path':ORIGIN}])
  ns=methods(['load_path'],dict(threading=SimpleNamespace(Thread=SyncThread),valid_source=valid_source,provider_page_label=provider_page_label,row_message=row_message,TMDB='plugin://plugin.video.themoviedb.helper/',get_list=lambda p:calls.append(p) or pages[p],event=lambda *a,**kw:None))
  s.load_path=MethodType(ns['load_path'],s);controls[900].selectItem(20);cursor=s.rows[0][-1]['file'];s.load_path(0,cursor,'Next')
  self.assertEqual(s.rows[0][0]['_page_control'],'previous');self.assertEqual([x['label'] for x in s.rows[0][1:]],[str(n) for n in range(39,51)])
  self.assertEqual(s.getProperty('row0'),'Japanese picks');previous,position=s.histories[0].pop();s.load_path(0,previous,back=True,position=position)
  self.assertEqual(len(s.rows[0]),21);self.assertEqual(controls[900].getSelectedPosition(),20);self.assertEqual(s.rows[0][20]['_page_control'],'next')
 def test_page_response_cannot_repopulate_cache_after_invalidation(self):
  s,calls,controls,pages=self.state();s.set_rows([{'label':'Japanese picks','path':ORIGIN}]);old=list(s.rows[0]);s.result_cache.clear()
  def provider(p):s.invalidate_row_results();return pages[p]
  self.bind_pages(s,calls,pages,provider);s.load_path(0,ORIGIN+'&page=2','Next')
  self.assertEqual(s.rows[0],old);self.assertIsNone(s.result_cache.get('filtered-v1:'+ORIGIN+'&page=2'))
 def test_refill_stops_when_same_row_navigation_token_changes(self):
  from browse_controls import AnimeMetadata
  from test_discovery_controller import DiscoveryController
  import tempfile
  with tempfile.TemporaryDirectory() as folder:
   def provider(p):
    if p==ORIGIN:return [more(2)]
    if p==ORIGIN+'&page=2':s.path_tokens[0]=1;s.rows[0]=[title(99)];return [more(3)]
    return [title(100+n) for n in range(20)]
   s,calls,_=DiscoveryController().state(provider=provider);s.section='Shows';s.search_state=None;s.config={};s.person_context=None;s.discovery_stack=[];s.anime_metadata=AnimeMetadata(folder)
   s.set_rows([{'label':'Japanese picks','path':ORIGIN}])
   self.assertEqual(calls,[ORIGIN,ORIGIN+'&page=2']);self.assertEqual(s.rows[0],[title(99)])
 def test_watch_refresh_preserves_cursor_and_fills_the_same_logical_page(self):
  import copy,time,threading
  from types import MethodType,SimpleNamespace
  from test_window_lifecycle import extract
  from test_discovery_controller import SyncThread
  from playback_core import restored_position,refreshed_watch_item,item_key
  s,calls,controls,pages=self.state();s.set_rows([{'label':'Japanese picks','path':ORIGIN}]);self.bind_pages(s,calls,pages)
  controls[900].selectItem(20);s.load_path(0,s.rows[0][-1]['file'],'Next');old=[x['file'] for x in s.rows[0]];s.selected=s.rows[0][1];s.actions_open=False
  ns=dict(copy=copy,time=time,threading=SimpleNamespace(Thread=SyncThread),get_list=lambda p:calls.append(p) or pages[p],provider_path=__import__('filtered_pages').provider_path,restored_position=restored_position,refreshed_watch_item=refreshed_watch_item,item_key=item_key,trakt_command=lambda x:None,event=lambda *a,**kw:None)
  refresh=extract(ROOT/'live_review.py','refresh_watch_status',ns,'LiveReview');refresh(s)
  self.assertEqual([x['file'] for x in s.rows[0]],old);self.assertNotIn('could not refresh',s.getProperty('notice'))
 def test_newly_available_anime_metadata_refills_a_cached_page(self):
  s,calls,controls,pages=self.state();s.set_rows([{'label':'Japanese picks','path':ORIGIN}]);original=s.anime_metadata.without_anime
  s.anime_metadata.without_anime=lambda files:[x for x in original(files) if x.get('label')!='1']
  s.set_rows([{'label':'Japanese picks','path':ORIGIN}])
  titles=[x['label'] for x in s.rows[0] if not x.get('_page_control')];self.assertEqual(len(titles),20);self.assertNotIn('1',titles);self.assertIn('39',titles)
 def test_japan_pushdown_uses_one_fetch_and_does_not_poison_intentional_search(self):
  import tempfile
  from browse_controls import AnimeMetadata
  from test_discovery_controller import DiscoveryController
  path=ORIGIN+'&with_origin_country=JP'
  def provider(p):
   q=parse_qs(urlsplit(p).query);filtered=q.get('without_genres')==['16']
   return [dict(title(n+(100 if filtered else 0)),genre=['Drama' if filtered else 'Animation'],country=['JP']) for n in range(20)]+[{'file':p+'&page=2','filetype':'directory','label':'Next page'}]
  with tempfile.TemporaryDirectory() as folder:
   s,calls,_=DiscoveryController().state(provider=provider);s.section='Shows';s.search_state=None;s.config={};s.person_context=None;s.discovery_stack=[];s.anime_metadata=AnimeMetadata(folder)
   s.set_rows([{'label':'Japanese picks','path':path}]);self.assertEqual(len(calls),1);self.assertEqual(parse_qs(urlsplit(calls[0]).query)['without_genres'],['16'])
   self.assertEqual(len(s.rows[0]),21);self.assertEqual(s.rows[0][0]['label'],'100');self.assertNotIn('without_genres',s.rows[0][-1]['file']);self.assertIsNone(s.result_cache.get(path))
   s.search_state={'query':'anime'};s.set_rows([{'label':'Search','path':path}]);self.assertEqual(calls[-1],path);self.assertEqual(s.rows[0][0]['label'],'0');self.assertEqual(len(s.rows[0]),21)
