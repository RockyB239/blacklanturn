"""Exercise real row publication/refresh with only native IO replaced."""
import copy,threading,unittest,importlib.util
from types import SimpleNamespace,MethodType
from unittest.mock import patch
from youtube_core import BASE,video_id
from test_youtube_continuation import video

spec=importlib.util.find_spec('youtube_rows')
if spec:import youtube_rows as mod
else:mod=None

class Control:
 def __init__(self):self.position=0
 def getSelectedPosition(self):return self.position
 def selectItem(self,n):self.position=n
 def controlDown(self,other):self.down=other

class RowUpdates(unittest.TestCase):
 def test_refresh_button_and_more_card_dispatch_inside_skin_without_generic_folder_navigation(self):
  from test_window_lifecycle import extract,ROOT
  for control in (610,900):
   with self.subTest(control=control):
    calls=[]
    window=SimpleNamespace(actions_open=False,owned_preview=False,chosen=lambda cid:{'_youtube_more':True,'_page_control':'next','file':'blacklanturn://youtube/more'},
     refresh_youtube_recommendations=lambda:calls.append('refresh'),request_youtube_more=lambda n,**k:calls.append(('more',n,k)),
     load_path=lambda *a,**k:calls.append('wrong-folder'))
    extract(ROOT/'live_review.py','onClick',{},'LiveReview')(window,control)
    self.assertEqual(calls,['refresh'] if control==610 else [('more',0,{'explicit':True})])
 def window(self):
  self.assertIsNotNone(mod,'YouTube row publication is missing')
  self.jobs=[];self.props={};self.applied=[];self.controls={900:Control(),901:Control(),610:Control()}
  self.w=SimpleNamespace(alive=True,window_lifetime=object(),generation=3,section='YouTube',youtube_tab='home',mode='home',nav=False,
   actions_open=False,settings_open=False,owned_preview=False,discovery_stack=[],youtube_connection=SimpleNamespace(connected=True,identity='account-a'),
   preview_dispatch_lock=threading.RLock(),rows=[[video(1),video(2)],[]],paths=[BASE+'/special/recommendations',''],row_offset=0,
   page_definitions=[{'label':'Recommended','path':BASE+'/special/recommendations'},{'label':'Subscriptions','path':BASE+'/special/my_subscriptions'}],
   row_cache={},window_ready=[True,True],selected=video(2),focus_key=(900,1),config={'Saved':[],'YouTubePreviews':True},
   setProperty=lambda k,v:self.props.__setitem__(k,v),getProperty=lambda k:self.props.get(k,''),getControl=lambda n:self.controls[n],
   getFocusId=lambda:900,setFocusId=lambda n:None,stop_preview=lambda:None,
   player=SimpleNamespace(isPlaying=lambda:False),row_navigation=lambda:None)
  for name in dir(mod.YouTubeRows):
   if not name.startswith('__'):setattr(self.w,name,MethodType(getattr(mod.YouTubeRows,name),self.w))
  def guard(generation=None):
   lifetime=self.w.window_lifetime;identity=self.w.youtube_connection.identity
   return lambda:self.w.alive and self.w.window_lifetime is lifetime and (generation is None or self.w.generation==generation) and self.w.youtube_connection.connected and self.w.youtube_connection.identity==identity
  self.w.youtube_request_guard=guard
  def apply(n,files,label,position=0,**kwargs):
   self.w.rows[n]=self.w.prepare_youtube_row(n,files);self.controls[900+n].position=position;self.applied.append((n,position,kwargs))
  self.w.apply_row=apply
  self.w.set_rows=lambda rows:self.applied.append(copy.deepcopy(rows))
  class Thread:
   def __init__(s,target,**kwargs):self.jobs.append(target)
   def start(s):pass
  focus_patch=patch.object(mod,'_focus_id',lambda:self.w.getFocusId());focus_patch.start();self.addCleanup(focus_patch.stop)
  self.thread_patch=patch.object(mod.threading,'Thread',Thread);self.thread_patch.start();self.addCleanup(self.thread_patch.stop)
  return self.w
 def ready(self,w):
  cursor=BASE+'/special/recommendations/?page_token=next&page=2&visitor=private'
  w.rows[0]=w.prepare_youtube_row(0,[video(1),video(2),{'file':cursor,'filetype':'directory','label':'Native next'}])
  self.controls[900].position=1
 def test_append_keeps_selected_video_and_does_not_hydrate_over_existing_watch_or_art(self):
  w=self.window();self.ready(w);before=copy.deepcopy(w.rows[0][:2])
  with patch.object(mod,'_fetch_feed',return_value=[dict(video(2),playcount=0),video(3)]):
   w.request_youtube_more(0);self.assertEqual(len(self.jobs),1);self.jobs.pop()()
  self.assertEqual(w.rows[0][:2],before,'Worker must not publish native controls')
  self.assertTrue(w.apply_youtube_updates());self.assertEqual(w.rows[0],before+[video(3)])
  self.assertEqual(self.controls[900].position,1);self.assertEqual(w.selected,video(2));self.assertFalse(self.applied[0][2]['update_selected'])
 def test_navigation_or_account_change_rejects_pending_private_page(self):
  for change in ['generation','account','lifetime']:
   with self.subTest(change=change):
    w=self.window();self.ready(w);before=copy.deepcopy(w.rows)
    with patch.object(mod,'_fetch_feed',return_value=[video(3)]):w.request_youtube_more(0);self.jobs.pop()()
    if change=='generation':w.generation+=1
    elif change=='account':w.youtube_connection.identity='account-b'
    else:w.window_lifetime=object()
    w.apply_youtube_updates();self.assertEqual(w.rows,before);self.assertEqual(self.applied,[])
 def test_failed_page_retains_cards_and_cursor_and_requires_explicit_retry(self):
  w=self.window();self.ready(w);before=copy.deepcopy(w.rows[0][:2])
  with patch.object(mod,'_fetch_feed',side_effect=RuntimeError('offline')):w.request_youtube_more(0);self.jobs.pop()()
  w.apply_youtube_updates();self.assertEqual(w.rows[0][:2],before);self.assertEqual(w.rows[0][-1]['label'],'Retry')
  w.request_youtube_more(0);self.assertEqual(self.jobs,[])
  with patch.object(mod,'_fetch_feed',return_value=[video(3)]):w.request_youtube_more(0,explicit=True);self.jobs.pop()()
  w.apply_youtube_updates();self.assertEqual(w.rows[0],before+[video(3)])
 def test_only_one_request_runs_and_no_background_request_runs_during_playback(self):
  w=self.window();self.ready(w);w.player.isPlaying=lambda:True;w.request_youtube_more(0);self.assertEqual(self.jobs,[])
  w.player.isPlaying=lambda:False;w.request_youtube_more(0);w.request_youtube_more(0);self.assertEqual(len(self.jobs),1)
 def test_refresh_worker_stages_rows_without_touching_native_controls(self):
  w=self.window();self.ready(w);before=copy.deepcopy(w.rows);config=copy.deepcopy(w.config)
  fresh=[{'label':'Provider recommendations','local_items':[video(3)]},{'label':'New personalized interest','local_items':[video(4)],'youtube_cursor':{'continuation':'new-token'}}]
  feed_calls=[]
  def feed(path):feed_calls.append(path);return [video(5)]
  with patch.object(mod,'_fetch_feed',feed),patch.object(mod,'load_home_rows',return_value=fresh):
   w.refresh_youtube_recommendations();self.assertEqual(w.rows,before);self.jobs.pop()()
  self.assertEqual(self.applied,[]);self.assertTrue(all('refresh=1' in p for p in feed_calls));self.assertEqual(len(feed_calls),2)
  self.assertTrue(w.apply_youtube_updates());self.assertEqual(len(self.applied),1)
  while w.apply_youtube_updates():pass
  self.assertEqual([x['label'] for x in w.page_definitions],['Recommended for you','Subscriptions','New personalized interest'])
  self.assertEqual(w.config,config);self.assertFalse(w.youtube_refreshing)
 def test_refresh_failure_or_retirement_keeps_current_rows_and_cursors(self):
  for failed in [True,False]:
   with self.subTest(failed=failed):
    w=self.window();self.ready(w);before=copy.deepcopy(w.rows);pages=copy.deepcopy(w.youtube_pages)
    with patch.object(mod,'_fetch_feed',side_effect=RuntimeError('offline') if failed else None,return_value=[video(3)]),patch.object(mod,'load_home_rows',return_value=[{'label':'Fresh'}]):
     w.refresh_youtube_recommendations();self.jobs.pop()()
    if not failed:w.youtube_connection.identity='account-b'
    w.apply_youtube_updates();self.assertEqual(w.rows,before);self.assertEqual(w.youtube_pages,pages);self.assertEqual(self.applied,[])
 def test_refresh_can_finish_after_moving_to_another_row_of_same_home(self):
  w=self.window();self.ready(w)
  with patch.object(mod,'_fetch_feed',return_value=[video(3)]),patch.object(mod,'load_home_rows',return_value=[{'label':'Recommendations'},{'label':'New topic'}]):
   w.refresh_youtube_recommendations();w.generation+=1;self.jobs.pop()()
  self.assertTrue(w.apply_youtube_updates())
  while w.apply_youtube_updates():pass
  self.assertEqual(w.page_definitions[-1]['label'],'New topic')
 def test_playlist_continuation_preserves_identity_with_inserted_previous_card(self):
  from browse_controls import page_cards,page_card
  from live_core import PageHistory
  w=self.window();self.ready(w);history=PageHistory();history.push('original-home',0)
  w.rows[0].insert(0,page_card('previous','blacklanturn://previous-page'));self.controls[900].position=2
  def apply(n,files,label,position=0,**kwargs):
   files=w.prepare_youtube_row(n,files);w.rows[n],position=page_cards(files,history,w.paths[n],position,display_position=kwargs.get('display_position',False))
   self.controls[900].position=position
  w.apply_row=apply
  with patch.object(mod,'_fetch_feed',return_value=[video(3)]):w.request_youtube_more(0);self.jobs.pop()()
  w.apply_youtube_updates();self.assertEqual(w.rows[0][self.controls[900].position]['file'],video(2)['file'])
 def test_refresh_cannot_replace_a_playlist_or_details_opened_while_loading(self):
  for destination in ('playlist','details'):
   with self.subTest(destination=destination):
    w=self.window();self.ready(w)
    with patch.object(mod,'_fetch_feed',return_value=[video(3)]),patch.object(mod,'load_home_rows',return_value=[{'label':'Recommendations'},{'label':'New topic'}]):
     w.refresh_youtube_recommendations();self.jobs.pop()()
    if destination=='playlist':w.paths[0]=BASE+'/playlist/PL_example/'
    else:w.mode='details'
    self.assertFalse(w.apply_youtube_updates());self.assertEqual(self.applied,[])
 def test_failed_playlist_continuation_keeps_selected_video_before_retry_card(self):
  from browse_controls import page_cards,page_card
  from live_core import PageHistory
  w=self.window();self.ready(w);history=PageHistory();history.push('original-home',0)
  w.rows[0].insert(0,page_card('previous','blacklanturn://previous-page'));self.controls[900].position=2
  def apply(n,files,label,position=0,**kwargs):
   files=w.prepare_youtube_row(n,files);w.rows[n],position=page_cards(files,history,w.paths[n],position,display_position=kwargs.get('display_position',False));self.controls[900].position=position
  w.apply_row=apply
  with patch.object(mod,'_fetch_feed',side_effect=RuntimeError('offline')):w.request_youtube_more(0);self.jobs.pop()()
  w.apply_youtube_updates();self.assertEqual(w.rows[0][self.controls[900].position]['file'],video(2)['file'])
 def test_home_refresh_controls_are_absent_inside_a_playlist(self):
  w=self.window();w.row_offset=len(w.page_definitions)-1;w.paths[0]=BASE+'/playlist/PL_example/'
  w.youtube_refresh_navigation();self.assertEqual(self.props['youtubeRefreshBottom'],'false')
  w.refresh_youtube_recommendations();self.assertEqual(self.jobs,[])
 def test_empty_terminal_next_page_keeps_the_capped_window(self):
  w=self.window();self.ready(w);page=w.youtube_pages[w.paths[0]];page['items']=[video(n) for n in range(1,151)]
  w.rows[0]=w.prepare_youtube_row(0,page['items']+[w.rows[0][-1]]);self.controls[900].position=150
  before=copy.deepcopy(page['items'])
  with patch.object(mod,'_fetch_feed',return_value=[]):w.request_youtube_more(0,explicit=True);self.jobs.pop()()
  w.apply_youtube_updates();self.assertEqual(w.rows[0],before);self.assertIsNone(w.youtube_pages[w.paths[0]]['cursor'])
  self.assertEqual(self.controls[900].position,149)

 def test_terminal_category_page_never_refilters_existing_cards_against_other_rows(self):
  w=self.window();path=w.paths[0]
  w.page_definitions[0].update(youtube_category=True,youtube_cursor={'continuation':'category-token'})
  w.rows[0]=w.prepare_youtube_row(0,[video(n) for n in range(1,9)])
  self.controls[900].position=6;before=copy.deepcopy(w.rows[0][:-1])
  for index in (1,2):w.page_definitions.append({'path':'other-'+str(index),'youtube_category':True,'local_items':[video(n) for n in range(1,9)]})
  with patch.object(mod,'load_shelf_page',return_value=([video(9)],None)):
   w.request_youtube_more(0);self.jobs.pop()()
  w.apply_youtube_updates()
  self.assertEqual(w.rows[0],before+[video(9)])
  self.assertEqual(w.rows[0][self.controls[900].position]['file'],video(7)['file'])
 def test_evicted_category_keeps_its_saved_cards_when_other_categories_overlap(self):
  w=self.window();path=w.paths[0]
  definition=w.page_definitions[0];definition.update(youtube_category=True,local_items=[video(n) for n in range(1,9)],youtube_cursor=None)
  w.rows[0]=w.prepare_youtube_row(0,definition['local_items']);before=copy.deepcopy(w.rows[0])
  for index in (1,2):w.page_definitions.append({'path':'other-'+str(index),'youtube_category':True,'local_items':[video(n) for n in range(1,9)]})
  w.youtube_pages.clear()
  self.assertEqual(w.prepare_youtube_row(0,definition['local_items']),before)

 def test_next_enters_first_new_video_instead_of_chasing_the_trailing_next_card(self):
  w=self.window();self.ready(w);self.controls[900].position=2
  next_path=BASE+'/special/recommendations/?page=3&page_token=third'
  with patch.object(mod,'_fetch_feed',return_value=[video(3),video(4),{'file':next_path,'filetype':'directory','label':'Next page: 3'}]):
   w.request_youtube_more(0,explicit=True);self.jobs.pop()()
  w.apply_youtube_updates()
  self.assertEqual(w.rows[0][self.controls[900].position]['file'],video(3)['file'])
  self.assertTrue(w.rows[0][-1].get('_youtube_more'))
 def test_terminal_next_enters_first_new_video_with_previous_navigation_present(self):
  from browse_controls import page_cards,page_card
  from live_core import PageHistory
  w=self.window();self.ready(w);history=PageHistory();history.push('original-home',0)
  w.rows[0].insert(0,page_card('previous','blacklanturn://previous-page'));self.controls[900].position=3
  def apply(n,files,label,position=0,**kwargs):
   files=w.prepare_youtube_row(n,files);w.rows[n],position=page_cards(files,history,w.paths[n],position,display_position=kwargs.get('display_position',False));self.controls[900].position=position
  w.apply_row=apply
  with patch.object(mod,'_fetch_feed',return_value=[video(3),video(4)]):
   w.request_youtube_more(0,explicit=True);self.jobs.pop()()
  w.apply_youtube_updates()
  self.assertEqual(w.rows[0][self.controls[900].position]['file'],video(3)['file'])


 def test_right_at_cap_requests_bounded_next_and_consumes_end_signal(self):
  w=self.window();self.ready(w);page=w.youtube_pages[w.paths[0]]
  page['items']=[video(n) for n in range(1,151)];w.rows[0]=page['items']+[mod._more_card()];self.controls[900].position=150
  self.props['youtubeRowEnd']='true';w.prefetch_youtube_row()
  self.assertEqual(self.props['youtubeRowEnd'],'false')
  self.assertEqual(len(self.jobs),1)

 def test_native_publication_failure_releases_job_so_retry_can_run(self):
  w=self.window();self.ready(w)
  with patch.object(mod,'_fetch_feed',return_value=[video(3),{'file':BASE+'/special/recommendations/?page=3&page_token=third','filetype':'directory','label':'Next page: 3'}]):w.request_youtube_more(0);self.jobs.pop()()
  apply=w.apply_row
  def failed(*a,**k):raise RuntimeError('native vector unavailable')
  w.apply_row=failed
  with self.assertRaises(RuntimeError):w.apply_youtube_updates()
  self.assertIsNone(w.youtube_job);self.assertIsNone(w.youtube_update)
  w.apply_row=apply;w.request_youtube_more(0,explicit=True)
  self.assertEqual(len(self.jobs),1)

 def test_rebinding_restores_lost_row_focus_without_stealing_intentional_navigation(self):
  for before,after,expected in [(900,0,900),(600,600,600),(900,600,600)]:
   with self.subTest(before=before,after=after):
    w=self.window();self.ready(w);focus=[before];w.getFocusId=lambda:focus[0];w.setFocusId=lambda n:focus.__setitem__(0,n)
    apply=w.apply_row
    def rebind(*a,**k):apply(*a,**k);focus[0]=after
    w.apply_row=rebind
    with patch.object(mod,'_fetch_feed',return_value=[video(3)]):w.request_youtube_more(0);self.jobs.pop()()
    w.apply_youtube_updates();self.assertEqual(focus[0],expected)

 def test_failed_terminal_publication_restores_cursor_and_native_retry_before_retrying(self):
  w=self.window();self.ready(w);before=copy.deepcopy(w.rows[0][:2]);cursor=copy.deepcopy(w.youtube_pages[w.paths[0]]['cursor'])
  with patch.object(mod,'_fetch_feed',return_value=[video(3)]):w.request_youtube_more(0);self.jobs.pop()()
  apply=w.apply_row;fail=[True]
  def partial(n,files,*a,**k):
   apply(n,files,*a,**k)
   if fail[0]:fail[0]=False;raise RuntimeError('native vector rejected')
  w.apply_row=partial
  with self.assertRaises(RuntimeError):w.apply_youtube_updates()
  page=w.youtube_pages[w.paths[0]]
  self.assertEqual(page['cursor'],cursor);self.assertEqual(page['items'],before)
  self.assertEqual(w.rows[0][:-1],before);self.assertEqual(w.rows[0][-1]['label'],'Retry')
  self.assertEqual(w.page_definitions[0]['youtube_cursor'],cursor);self.assertIsNone(w.youtube_job)
  with patch.object(mod,'_fetch_feed',return_value=[video(3)]):w.request_youtube_more(0,explicit=True);self.jobs.pop()()
  w.apply_youtube_updates();self.assertEqual(w.rows[0],before+[video(3)])

 def test_focus_check_waits_for_queued_native_reset_before_restoring(self):
  w=self.window();self.ready(w);focus=[900];w.getFocusId=lambda:focus[0];w.setFocusId=lambda n:focus.__setitem__(0,n)
  reads=[]
  def dispatched():reads.append(True);focus[0]=0;return 0
  with patch.object(mod,'_fetch_feed',return_value=[video(3)]):w.request_youtube_more(0);self.jobs.pop()()
  with patch.object(mod,'_focus_id',dispatched,create=True):w.apply_youtube_updates()
  self.assertEqual(reads,[True]);self.assertEqual(focus[0],900)

 def test_focus_dispatch_failure_does_not_discard_successfully_published_items(self):
  w=self.window();self.ready(w)
  with patch.object(mod,'_fetch_feed',return_value=[video(3)]):w.request_youtube_more(0);self.jobs.pop()()
  with patch.object(mod,'_focus_id',side_effect=RuntimeError('closed native window')):
   try:w.apply_youtube_updates()
   except RuntimeError:pass
  self.assertEqual(w.page_definitions[0].get('local_items'),[video(1),video(2),video(3)])
  self.assertIsNone(w.page_definitions[0]['youtube_cursor'])

 def test_focus_repair_rechecks_owner_after_native_dispatch(self):
  w=self.window();self.ready(w);restored=[];w.setFocusId=lambda n:restored.append(n)
  with patch.object(mod,'_fetch_feed',return_value=[video(3)]):w.request_youtube_more(0);self.jobs.pop()()
  def dispatch():w.generation+=1;return 0
  with patch.object(mod,'_focus_id',dispatch):w.apply_youtube_updates()
  self.assertEqual(restored,[])

if __name__=='__main__':unittest.main()
