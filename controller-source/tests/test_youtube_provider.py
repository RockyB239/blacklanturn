import unittest
from types import SimpleNamespace
from unittest.mock import patch
import youtube_provider as provider

class RuntimeLifecycle(unittest.TestCase):
 def setUp(self):provider._runtime=None
 def tearDown(self):provider._runtime=None
 def test_repeated_reads_reuse_one_runtime_and_account_change_retires_it(self):
  calls=[]
  def create(identity):calls.append(('create',identity));return SimpleNamespace(identity=identity,context=SimpleNamespace(get_settings=lambda **kwargs:None))
  with patch.object(provider,'_identity',side_effect=['a','a','b']),patch.object(provider,'_create_runtime',create),patch.object(provider,'_retire',lambda r:calls.append(('retire',r.identity))):
   with provider._session(lambda:True) as a:pass
   with provider._session(lambda:True) as again:self.assertIs(a,again)
   with provider._session(lambda:True) as b:self.assertIsNot(a,b)
  self.assertEqual(calls,[('create','a'),('retire','a'),('create','b')])
 def test_busy_store_is_not_dropped_or_unregistered(self):
  store=SimpleNamespace(_close_timer=None,_db=object(),_close=lambda **kwargs:False)
  runtime=SimpleNamespace(context=SimpleNamespace(_data_cache=store))
  with patch.object(provider.atexit,'unregister') as unregister:
   with self.assertRaises(RuntimeError):provider._retire(runtime)
   unregister.assert_not_called()

 def test_watch_refresh_keeps_category_membership_art_and_full_play_urls(self):
  from contextlib import contextmanager
  @contextmanager
  def session(current):yield object()
  files=[{'file':'plugin://plugin.video.youtube/play/?video_id=Abc_123-Xyz&resume=true','title':'Original title','art':{'thumb':'original.jpg'},'playcount':0,'resume':{'position':0}}, {'file':'plugin://plugin.video.youtube/play/?video_id=Def_123-Xyz','title':'Second'}]
  fresh=[{'file':files[0]['file'],'title':'Changed title','art':{'thumb':'changed.jpg'},'playcount':1,'resume':{'position':75,'total':100}}]
  with patch.object(provider,'_session',session),patch.object(provider,'_resolve',return_value=fresh):result=provider.refresh_watch_items(files)
  self.assertEqual([x['file'] for x in result],[x['file'] for x in files]);self.assertEqual(result[0]['art'],files[0]['art']);self.assertEqual(result[0]['title'],'Original title');self.assertEqual(result[0]['resume']['position'],75);self.assertEqual(files[0]['playcount'],0)

class AdaptiveDepth(unittest.TestCase):
 def test_explicit_refresh_bypasses_native_request_cache_only_for_owned_read(self):
  from contextlib import contextmanager
  params={'existing':'kept'};runtime=SimpleNamespace(context=SimpleNamespace(get_params=lambda:params))
  runtime.provider=SimpleNamespace(get_client=lambda context:object())
  @contextmanager
  def session(current):yield runtime
  seen=[]
  def read(*args):seen.append(dict(params));return [{'label':'Fresh interest'}]
  with patch.object(provider,'_session',session),patch.object(provider,'_load_home',read):
   try:rows=provider.load_home_rows(lambda:True,refresh=True)
   except TypeError:self.fail('Explicit Home refresh is not supported')
  self.assertEqual(seen,[{'existing':'kept','refresh':1}]);self.assertEqual(params,{'existing':'kept'});self.assertEqual(rows,[{'label':'Fresh interest'}])
  with patch.object(provider,'_session',session),patch.object(provider,'_load_home',side_effect=RuntimeError('offline')):
   with self.assertRaises(RuntimeError):provider.load_home_rows(lambda:True,refresh=True)
  self.assertEqual(params,{'existing':'kept'})
 def test_shelf_page_follows_exact_opaque_cursor_and_keeps_playlist_navigation(self):
  from contextlib import contextmanager
  calls=[]
  def browse(**kwargs):
   calls.append(kwargs)
   return {'continuationContents':{'horizontalListContinuation':{'items':[
    {'tileRenderer':{'onSelectCommand':{'watchEndpoint':{'videoId':'Abc_123-Xyz'}}}},
    {'tileRenderer':{'onSelectCommand':{'browseEndpoint':{'browseId':'VLPL_real'}},'metadata':{'tileMetadataRenderer':{'title':{'simpleText':'Playlist'}}}}}
   ]}}}
  runtime=SimpleNamespace(context=object(),provider=SimpleNamespace(get_client=lambda context:SimpleNamespace(get_browse_items=browse)))
  @contextmanager
  def session(current):yield runtime
  f=getattr(provider,'load_shelf_page',None);self.assertTrue(callable(f),'Shelf continuation loader missing')
  with patch.object(provider,'_session',session),patch.object(provider,'_resolve',return_value=[{'file':'plugin://plugin.video.youtube/play/?video_id=Abc_123-Xyz','art':{'thumb':'verified.jpg'}}]):
   files,cursor=f({'continuation':'opaque','clickTrackingParams':'track','visitor':'visit'},lambda:True)
  self.assertEqual(calls,[{'browse_id':'FEwhat_to_watch','client':'tv','do_auth':True,'json_path':None,'page_token':'opaque','click_tracking':'track','visitor':'visit'}])
  self.assertEqual(len(files),2);self.assertEqual(files[0]['art']['thumb'],'verified.jpg');self.assertEqual(files[1]['file'],'plugin://plugin.video.youtube/playlist/PL_real/');self.assertIsNone(cursor)
 def test_follows_additional_pages_and_resolves_all_categories_in_bounded_batches(self):
  from test_youtube_home import response,shelf
  pages=[response(shelf('Recommended',['Abc_123-Xyz']))]
  for n in range(1,6):pages.append(response(shelf('Interest '+str(n),[str(n)+'bc_123-Xyz'])))
  for n,page in enumerate(pages):
   section=page['contents']['tvBrowseRenderer']['content']['tvSurfaceContentRenderer']['content']['sectionListRenderer']
   section['continuations']=[{'nextContinuationData':{'continuation':'token-'+str(n)}}] if n<5 else []
  client=SimpleNamespace(get_browse_items=__import__('unittest.mock',fromlist=['Mock']).Mock(side_effect=pages),json_traverse=lambda *a:None)
  def resolve(runtime,unique,current):return [{'file':'plugin://plugin.video.youtube/play/?video_id='+i} for i in unique]
  with patch.object(provider,'_resolve',side_effect=resolve):rows=provider._load_home(object(),client,lambda:True)
  self.assertEqual(len(rows),6);self.assertEqual(client.get_browse_items.call_count,6)
 def test_repeated_continuation_does_not_loop_and_late_failure_keeps_first_groups(self):
  from test_youtube_home import response,shelf
  page=response(shelf('A real interest',['Abc_123-Xyz']))
  client=SimpleNamespace(get_browse_items=__import__('unittest.mock',fromlist=['Mock']).Mock(side_effect=[page,RuntimeError('temporary service failure')]),json_traverse=lambda *a:None)
  def resolve(runtime,unique,current):return [{'file':'plugin://plugin.video.youtube/play/?video_id='+i} for i in unique]
  with patch.object(provider,'_resolve',side_effect=resolve):rows=provider._load_home(object(),client,lambda:True)
  self.assertEqual(len(rows),1)
