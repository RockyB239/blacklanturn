import copy,unittest
from types import SimpleNamespace
from unittest.mock import patch
import test_youtube_row_updates as fixtures
from test_youtube_continuation import video
import youtube_rows as mod
import youtube_provider as provider

class ProgressiveRefresh(unittest.TestCase):
 def setUp(self):
  self.fixture=fixtures.RowUpdates();self.w=self.fixture.window();self.fixture.ready(self.w);self.w.paths[1]=self.w.page_definitions[1]['path']
  self.addCleanup(self.fixture.doCleanups)
  self.focus=[900];self.w.getFocusId=lambda:self.focus[0];self.w.setFocusId=lambda n:self.focus.__setitem__(0,n)
 def drain(self):
  for _ in range(6):
   if not self.w.apply_youtube_updates():break
 def test_first_row_is_usable_before_subscription_and_categories_finish(self):
  w=self.w;original_sub=copy.deepcopy(w.rows[1]);seen=[]
  def feed(path):
   if 'my_subscriptions' in path:
    self.assertTrue(w.apply_youtube_updates());self.assertEqual(w.rows[0][0],video(3));self.assertEqual(w.rows[1],original_sub);self.assertTrue(w.youtube_refreshing);seen.append('main first')
   return [video(3 if 'recommendations' in path else 4)]
  def shelves(*a,**kw):
   self.assertTrue(w.apply_youtube_updates());self.assertEqual(w.rows[1][0],video(4));seen.append('subscriptions next')
   self.assertEqual({x['file'] for x in kw['resolved_items']},{video(3)['file'],video(4)['file']})
   return [{'label':'Recommended'},{'label':'Fresh topic','path':'new-topic','local_items':[video(5)]}]
  with patch.object(mod,'_fetch_feed',feed),patch.object(mod,'load_home_rows',shelves):w.refresh_youtube_recommendations();self.fixture.jobs.pop()()
  self.drain();self.assertEqual(seen,['main first','subscriptions next']);self.assertFalse(w.youtube_refreshing);self.assertIsNone(w.youtube_job)
  self.assertEqual(w.page_definitions[-1]['label'],'Fresh topic')
 def test_late_category_failure_keeps_successful_primary_rows_and_old_categories(self):
  w=self.w;old={'label':'Old topic','path':'old-topic','local_items':[video(8)]};w.page_definitions.append(old)
  with patch.object(mod,'_fetch_feed',side_effect=[[video(3)],[video(4)]]),patch.object(mod,'load_home_rows',side_effect=RuntimeError('offline')):
   w.refresh_youtube_recommendations();self.fixture.jobs.pop()()
  self.drain();self.assertEqual(w.rows[0][0],video(3));self.assertEqual(w.rows[1][0],video(4));self.assertEqual(w.page_definitions[-1],old);self.assertFalse(w.youtube_refreshing)
 def test_row_publication_keeps_selected_title_cursor_metadata_and_focus(self):
  w=self.w;self.fixture.controls[900].position=1;anchor=video(2)
  more={'file':w.paths[0]+'?page=2&page_token=fresh','filetype':'directory','label':'Next page'}
  with patch.object(mod,'_fetch_feed',side_effect=[[video(9),anchor,more],[video(4)]]),patch.object(mod,'load_home_rows',return_value=[{'label':'Recommended'}]):
   w.refresh_youtube_recommendations();self.fixture.jobs.pop()()
  self.drain();self.assertEqual(w.rows[0][self.fixture.controls[900].position],anchor);self.assertEqual(self.focus[0],900);self.assertIsNotNone(w.youtube_pages[w.paths[0]]['cursor'])
 def test_retired_account_cannot_publish_any_queued_stage(self):
  w=self.w;before=copy.deepcopy(w.rows)
  with patch.object(mod,'_fetch_feed',return_value=[video(3)]),patch.object(mod,'load_home_rows',return_value=[{'label':'Recommended'}]):
   w.refresh_youtube_recommendations();self.fixture.jobs.pop()()
  w.youtube_connection.identity='different';self.assertFalse(w.apply_youtube_updates());self.assertEqual(w.rows,before);self.assertIsNone(w.youtube_job)
 def test_active_category_window_is_not_replaced_by_late_catalog(self):
  w=self.w;cats=[{'label':'Old '+str(i),'path':'old-'+str(i),'local_items':[video(10+i)]} for i in range(6)];w.page_definitions.extend(cats);w.row_offset=4;w.paths=[cats[2]['path'],cats[3]['path']];w.rows=[[video(12)],[video(13)]];before=copy.deepcopy(w.rows);self.focus[0]=901
  with patch.object(mod,'_fetch_feed',return_value=[video(3)]),patch.object(mod,'load_home_rows',return_value=[{'label':'Recommended'},{'label':'New','path':'new','local_items':[video(20)]}]):
   w.refresh_youtube_recommendations();self.fixture.jobs.pop()()
  self.drain();self.assertEqual(w.rows,before);self.assertEqual(self.focus[0],901);self.assertEqual(w.page_definitions[w.row_offset]['path'],w.paths[0]);self.assertEqual(w.page_definitions[w.row_offset+1]['path'],w.paths[1]);self.assertIn('new',[d['path'] for d in w.page_definitions])

 def test_empty_subscriptions_do_not_block_categories(self):
  w=self.w
  with patch.object(mod,'_fetch_feed',side_effect=[[video(3)],[]]),patch.object(mod,'load_home_rows',return_value=[{'label':'Recommended'},{'label':'New','path':'new'}]):
   w.refresh_youtube_recommendations();self.fixture.jobs.pop()()
  self.drain();self.assertIn('new',[d['path'] for d in w.page_definitions]);self.assertFalse(w.youtube_refreshing)
 def test_watch_status_refresh_retires_prepared_rows(self):
  w=self.w;before=copy.deepcopy(w.rows)
  with patch.object(mod,'_fetch_feed',return_value=[video(3)]),patch.object(mod,'load_home_rows',return_value=[{'label':'Recommended'}]):
   w.refresh_youtube_recommendations();self.fixture.jobs.pop()()
  from test_window_lifecycle import extract,ROOT
  w.invalidate_row_results=lambda:None
  method=extract(ROOT/'live_review.py','refresh_watch_status',{'threading':mod.threading},'LiveReview')
  method(w)
  # The real watcher clears this temporary field before the monitor resumes.
  w.watch_refresh_generation=None;w.actions_open=False
  self.assertFalse(w.apply_youtube_updates());self.assertEqual(w.rows,before)

 def test_native_publication_rollback_restores_focus_and_releases_job(self):
  w=self.w;before=copy.deepcopy(w.rows[0]);apply=w.apply_row;fail=[True]
  def partial(*a,**kw):
   apply(*a,**kw)
   if fail[0]:fail[0]=False;self.focus[0]=0;raise RuntimeError('native rebind')
  w.apply_row=partial
  with patch.object(mod,'_fetch_feed',return_value=[video(3)]),patch.object(mod,'load_home_rows',return_value=[{'label':'Recommended'}]):
   w.refresh_youtube_recommendations();self.fixture.jobs.pop()()
  self.drain();self.assertEqual(w.rows[0],before);self.assertEqual(self.focus[0],900);self.assertIsNone(w.youtube_job)

class SameRefreshReuse(unittest.TestCase):
 def test_only_missing_video_ids_are_resolved_and_fresh_metadata_is_exact(self):
  from test_youtube_home import response,shelf
  client=SimpleNamespace(get_browse_items=lambda **kw:response(shelf('Recommended',['Abc_123-Xyz','Def_123-Xyz'])),json_traverse=lambda *a:None)
  reused={'file':'plugin://plugin.video.youtube/play/?video_id=Abc_123-Xyz&resume=true','title':'Fresh','playcount':1,'resume':{'position':22,'total':100},'art':{'thumb':'correct.jpg'}};before=copy.deepcopy(reused);calls=[]
  def resolve(runtime,unique,current):calls.extend(unique);return [{'file':'plugin://plugin.video.youtube/play/?video_id='+x} for x in unique]
  try:
   with patch.object(provider,'_resolve',side_effect=resolve):rows=provider._load_home(object(),client,lambda:True,resolved_items=[reused])
  except TypeError:self.fail('No request-owned metadata reuse support')
  self.assertEqual(calls,['Def_123-Xyz']);self.assertEqual(rows[0]['local_items'][0],before);self.assertEqual(reused,before)
