import ast,copy,unittest
from pathlib import Path
from functools import partial
ROOT=Path(__file__).resolve().parents[2]
def cache_run():
 path=ROOT/'compatibility/youtube-refresh/candidate/function_cache.py'
 cls=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='FunctionCache')
 fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='run');ns={'partial':partial}
 exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(path),'exec'),ns);return ns['run']
class Cache:
 SCOPE_ALL=2;_enabled=True
 def __init__(self):self.now=1;self.row=None;self.stamp=0;self.calls=0;self.writes=0
 def _create_id_from_func(self,*a):return 'home'
 def _get(self,*a,**k):return {'age':self.now-self.stamp,'value':copy.deepcopy(self.row)} if self.row is not None else None
 def _set(self,k,value):self.row=copy.deepcopy(value);self.stamp=self.now;self.writes+=1
 def _remove(self,*a):self.row=None
 def provider(self):self.calls+=1;return {'revision':self.calls}
 def call(self,**kw):return cache_run()(self,self.provider,3600,**kw)
class Freshness(unittest.TestCase):
 def test_visits_cannot_extend_fetched_lifetime(self):
  c=Cache();c.call()
  for _ in range(144):c.now+=1800;c.call()
  self.assertGreater(c.calls,24);self.assertEqual(c.writes,c.calls)
 def test_pure_cache_hit_does_not_write_sqlite_or_renew_timestamp(self):
  c=Cache();c.call();c.now+=60;c.call();self.assertEqual((c.stamp,c.calls,c.writes),(1,1,1))
 def test_explicit_refresh_replaces_cached_revision_immediately(self):
  c=Cache();c.call();c.now+=1;self.assertEqual(c.call(_refresh=True),{'revision':2});self.assertEqual(c.stamp,c.now)
 def test_same_value_actual_refetch_still_advances_fetched_time(self):
  c=Cache();c.provider=lambda:{'same':'value'};c.call();c.now+=4000;c.call();self.assertEqual(c.stamp,c.now)
 def test_process_merging_and_oneshot_miss_remain_supported(self):
  c=Cache();c.call();c.now+=20;c.call(_process=lambda new,old:dict(old,merged=True));self.assertTrue(c.row['merged']);self.assertEqual(c.stamp,c.now)
  c.provider=lambda:None;c.call(_refresh=True,_oneshot=True);self.assertIsNone(c.row)
 def test_disabled_cache_does_not_write(self):
  c=Cache();c._enabled=False;c.call();self.assertEqual((c.calls,c.writes),(1,0))
class CompletionOrdering(unittest.TestCase):
 def test_first_recommendation_page_orders_completed_last_but_history_and_subscriptions_keep_provider_order(self):
  from youtube_rows import YouTubeRows
  from types import SimpleNamespace
  a={'file':'plugin://plugin.video.youtube/play/?video_id=00000000001','playcount':1};b={'file':'plugin://plugin.video.youtube/play/?video_id=00000000002','playcount':0}
  for route in ('/special/recommendations','/special/recommendations?bl_shelf=music','/special/my_subscriptions','/special/playback_history'):
   w=SimpleNamespace(section='YouTube',paths=['plugin://plugin.video.youtube'+route],page_definitions=[],youtube_pages={})
   result=YouTubeRows.prepare_youtube_row(w,0,[a,b]);want=[b,a] if route.startswith('/special/recommendations') else [a,b]
   self.assertEqual(result,want)
   # Return/watch-state updates must not rebind an existing row into a new order.
   stable=YouTubeRows.prepare_youtube_row(w,0,[b,a]);self.assertEqual(stable,[b,a])
 def test_only_completed_videos_move_down_and_metadata_objects_survive(self):
  import youtube_core as m
  fn=getattr(m,'recommendation_order',None);self.assertTrue(callable(fn),'Recommendation completion ordering missing')
  def v(n,playcount=0,position=0):return {'file':'plugin://plugin.video.youtube/play/?video_id='+str(n).zfill(11),'playcount':playcount,'resume':{'position':position,'total':100},'art':{'thumb':str(n)+'.jpg'}}
  folder={'file':'plugin://plugin.video.youtube/playlist/PL_test/','filetype':'directory'};watched=v(1,1);partial=v(2,0,65);fresh=v(3);files=[watched,folder,partial,fresh];before=copy.deepcopy(files)
  result=fn(files);self.assertEqual(result,[partial,folder,fresh,watched]);self.assertEqual(files,before)
  self.assertIs(result[0],partial);self.assertIs(result[1],folder);self.assertIs(result[-1],watched)
 def test_all_watched_or_missing_watch_state_keeps_every_candidate_stable(self):
  import youtube_core as m
  fn=getattr(m,'recommendation_order',None);self.assertTrue(callable(fn))
  files=[{'file':'plugin://plugin.video.youtube/play/?video_id='+str(n).zfill(11),'playcount':1} for n in range(5)]
  self.assertEqual(fn(files),files);self.assertEqual(fn([dict(files[0],playcount='unknown')]),[dict(files[0],playcount='unknown')])

class RendererFreshness(unittest.TestCase):
 def state(self):
  from test_discovery_order_context import RendererIntegration
  from youtube_rows import YouTubeRows
  from types import MethodType
  w,c=RendererIntegration().state();w.section='YouTube'
  w.paths=['plugin://plugin.video.youtube/special/recommendations','plugin://plugin.video.youtube/special/recommendations?bl_shelf=music']
  w.page_definitions=[{'path':p,'label':'Test'} for p in w.paths];w.youtube_pages={}
  w.prepare_youtube_row=MethodType(YouTubeRows.prepare_youtube_row,w)
  if hasattr(YouTubeRows,'fresh_recommendation_row'):w.fresh_recommendation_row=MethodType(YouTubeRows.fresh_recommendation_row,w)
  return w,c
 def videos(self):
  return [{'file':'plugin://plugin.video.youtube/play/?video_id='+str(n).zfill(11),'playcount':int(n==1)} for n in (1,2,3)]
 def test_first_render_focuses_unfinished_head_and_return_retains_explicit_selection(self):
  w,c=self.state();a,b,_=self.videos();w.apply_row(0,[a,b],'Test')
  self.assertEqual(w.rows[0][c[900].getSelectedPosition()]['file'],b['file'])
  w.apply_row(0,[a,b],'Test',0)
  self.assertEqual(w.rows[0][c[900].getSelectedPosition()]['file'],a['file'])
 def test_continuation_order_survives_offscreen_page_eviction(self):
  w,_=self.state();a,b,c=self.videos();w.prepare_youtube_row(0,[a,b])
  definition=w.page_definitions[0];definition['local_items']=[b,a,c];definition['youtube_cursor']=None
  w.youtube_pages.pop(w.paths[0])
  result=w.prepare_youtube_row(0,definition['local_items'])
  self.assertEqual(result,[b,a,c])
 def test_initial_failure_retry_then_eviction_keeps_real_items_cursor_and_order(self):
  w,_=self.state();a,b,_=self.videos();path=w.paths[0];definition=w.page_definitions[0]
  w.apply_row(0,[],'Test')
  self.assertNotIn('local_items',definition)
  more={'file':path+'/?page=2&page_token=next','filetype':'directory','label':'Next page: 2'}
  w.apply_row(0,[a,b,more],'Test')
  self.assertEqual(w.rows[0][0],b);self.assertIsNotNone(w.youtube_pages[path]['cursor'])
  self.assertEqual(w.rows[0][w.getControl(900).getSelectedPosition()],b)
  w.youtube_pages.pop(path)
  self.assertEqual(w.prepare_youtube_row(0,definition['local_items'])[:2],[b,a])
  self.assertIsNotNone(w.youtube_pages[path]['cursor'])
