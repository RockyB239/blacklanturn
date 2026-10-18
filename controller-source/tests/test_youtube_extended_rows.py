"""Finite personalized shelves continue from their own original video choices."""
import copy,unittest
from types import SimpleNamespace
from contextlib import contextmanager
from unittest.mock import patch
import youtube_home as home,youtube_provider as provider,youtube_rows as rows
import test_youtube_row_updates as row_fixture
from test_youtube_continuation import video

class RelatedRows(unittest.TestCase):
 def test_finite_shelf_gets_row_specific_related_cursor_without_touching_cards(self):
  items={'00000000001':video(1),'00000000002':video(2)};before=copy.deepcopy(items)
  result=home.local_rows([{'label':'Guitar and more','items':[{'id':x} for x in items],'youtube_cursor':None}],items)[0]
  self.assertEqual(result['local_items'],list(items.values()));self.assertEqual(items,before)
  self.assertIsNotNone(result['youtube_cursor']);self.assertEqual(result['youtube_cursor'].get('related_seeds'),['v0000000001','v0000000002'])
  self.assertEqual(result['youtube_cursor'],result['youtube_fallback'])
 def test_native_shelf_keeps_its_real_cursor_before_related_extension(self):
  cursor={'continuation':'original-token'}
  result=home.local_rows([{'label':'Guitar','items':[{'id':'00000000001'}],'youtube_cursor':cursor}],{'00000000001':video(1)})[0]
  self.assertEqual(result['youtube_cursor'],cursor);self.assertTrue(result.get('youtube_fallback'))
 def test_related_loader_uses_current_seed_then_native_token_and_moves_to_next_seed(self):
  method=getattr(provider,'load_related_page',None);self.assertTrue(callable(method),'Related shelf loader missing')
  calls=[];raw={'kind':'youtube#videoListResponse','items':[],'nextPageToken':'next'}
  def related(**kwargs):calls.append(kwargs);return raw
  runtime=SimpleNamespace(context=object(),provider=SimpleNamespace(get_client=lambda context:SimpleNamespace(get_related_videos=related)))
  @contextmanager
  def session(current):yield runtime
  cursor={'related_seeds':['00000000001','00000000002'],'seed_index':0}
  with patch.object(provider,'_session',session),patch.object(provider,'_resolve_entries',return_value=[video(3)]):
   files,more=method(cursor,lambda:True);self.assertEqual(files,[video(3)]);self.assertEqual(more['page_token'],'next')
   raw.pop('nextPageToken');files,last=method(more,lambda:True)
  self.assertEqual(calls,[{'video_id':'00000000001','page_token':None,'click_tracking':None,'visitor':None},{'video_id':'00000000001','page_token':'next','click_tracking':None,'visitor':None}])
  self.assertEqual(last,{'related_seeds':['00000000001','00000000002'],'seed_index':1})
 def test_native_end_switches_to_related_but_related_end_does_not_restart_it(self):
  fixture=row_fixture.RowUpdates();w=fixture.window();self.addCleanup(fixture.doCleanups);fixture.ready(w)
  fallback={'related_seeds':['00000000001'],'seed_index':0};w.page_definitions[0]['youtube_fallback']=fallback
  with patch.object(rows,'_fetch_feed',return_value=[video(3)]):w.request_youtube_more(0);fixture.jobs.pop()()
  w.apply_youtube_updates();self.assertEqual(w.youtube_pages[w.paths[0]]['cursor'],fallback)
  related=getattr(rows,'load_related_page',None);self.assertTrue(callable(related),'Related request dispatch missing')
  with patch.object(rows,'load_related_page',return_value=([video(4)],None)):
   w.request_youtube_more(0,explicit=True);fixture.jobs.pop()()
  w.apply_youtube_updates();self.assertIsNone(w.youtube_pages[w.paths[0]]['cursor']);self.assertEqual(w.rows[0],[video(1),video(2),video(3),video(4)])
 def test_related_tokens_do_not_collide_across_seeds(self):
  a={'related_seeds':['00000000001','00000000002'],'seed_index':0,'page_token':'same'};b=dict(a,seed_index=1)
  self.assertNotEqual(rows._token(a),rows._token(b))

class EmptyRelatedSeed(unittest.TestCase):
 def test_empty_native_seed_advances_and_final_empty_seed_is_terminal(self):
  method=provider.load_related_page
  runtime=SimpleNamespace(context=object(),provider=SimpleNamespace(get_client=lambda context:SimpleNamespace(get_related_videos=lambda **k:{})))
  @contextmanager
  def session(current):yield runtime
  with patch.object(provider,'_session',session):
   try:files,next_=method({'related_seeds':['00000000001','00000000002'],'seed_index':0},lambda:True)
   except RuntimeError:self.fail('Native empty related result must advance to the next seed')
   self.assertEqual(files,[]);self.assertEqual(next_,{'related_seeds':['00000000001','00000000002'],'seed_index':1})
   files,next_=method(next_,lambda:True);self.assertEqual(files,[]);self.assertIsNone(next_)
