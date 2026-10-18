"""YouTube transitions preserve preferences and normal playback intent."""
import copy,importlib.util,unittest,json,sys
from unittest.mock import patch
from types import SimpleNamespace,MethodType
from test_window_lifecycle import extract,ROOT
from youtube_core import tab_rows,video_id
spec=importlib.util.find_spec('youtube_browser')
if spec:from youtube_browser import YouTubeBrowser
else:YouTubeBrowser=None

class YouTubeBrowserFlow(unittest.TestCase):
 def test_back_from_youtube_home_opens_sidebar_without_restarting_feed_requests(self):
  calls=[]
  w=SimpleNamespace(actions_open=False,owned_preview=False,nav=False,mode='home',section='YouTube',youtube_tab='home',active_page='home',
   histories=[SimpleNamespace(pop=lambda:None)],last_row=0,episode_browser_context=None,person_context=None,discovery_stack=[],search_state=None,
   stop_preview=lambda:calls.append('stop'),setProperty=lambda *a:None,set_nav=lambda *a,**k:calls.append('sidebar'),setFocusId=lambda x:calls.append(('focus',x)),
   load_section=lambda:self.fail('Back on YouTube Home must not reload the same feeds'))
  method=extract(ROOT/'live_review.py','onAction',{},'LiveReview');method(w,SimpleNamespace(getId=lambda:92))
  self.assertEqual(calls,['stop','sidebar',('focus',50)])

 def test_back_from_youtube_tab_returns_home_before_sidebar(self):
  calls=[]
  w=SimpleNamespace(actions_open=False,owned_preview=False,nav=False,mode='home',section='YouTube',youtube_tab='subscriptions',active_page='subscriptions',
   histories=[SimpleNamespace(pop=lambda:None)],last_row=0,episode_browser_context=None,person_context=None,discovery_stack=[],search_state=None,
   stop_preview=lambda:None,setProperty=lambda *a:None,setFocusId=lambda x:calls.append(('focus',x)),load_youtube_section=lambda tab:calls.append(('youtube',tab)),
   load_section=lambda:self.fail('Back must explicitly return to YouTube Home'))
  extract(ROOT/'live_review.py','onAction',{},'LiveReview')(w,SimpleNamespace(getId=lambda:92))
  self.assertEqual(calls,[('youtube','home'),('focus',600)])
 def test_tab_transition_loads_account_feed_without_writing_preferences(self):
  self.assertIsNotNone(YouTubeBrowser,'YouTube browsing transition is missing')
  config={'PreviewMode':'manual','PreviewDelay':8,'Saved':[{'file':'existing'}]};before=copy.deepcopy(config);props={};rows=[]
  obj=SimpleNamespace(config=config,youtube_connection=SimpleNamespace(connected=True),generation=4,
   stop_preview=lambda:None,setProperty=lambda k,v:props.__setitem__(k,v),populate_youtube_tabs=lambda:None,set_rows=lambda x:rows.extend(x))
  YouTubeBrowser.load_youtube_section(obj,'subscriptions')
  self.assertEqual(rows,tab_rows('subscriptions'));self.assertEqual(obj.section,'YouTube');self.assertEqual(props['youtubeBrowser'],'true');self.assertEqual(props['captionRows'],'true');self.assertEqual(props['previewMode'],'auto');self.assertEqual(config,before)
 def state(self,item):
  calls=[]
  w=SimpleNamespace(section='YouTube',actions_open=False,selected=item,chosen=lambda cid:item,
   update=lambda i:calls.append(('update',i)),stop_preview=lambda:calls.append('stop'),finish=lambda:calls.append('close'),
   capture_browse=lambda:{'section':'YouTube'},load_path=lambda *args,**kwargs:calls.append(('folder',args)),setProperty=lambda *args:None,details=lambda i:calls.append('details'))
  ns={'resume_options':__import__('playback_core').resume_options,'discovery_result':__import__('search_ui').discovery_result,'youtube_video_id':video_id,'is_youtube':__import__('youtube_core').is_youtube,'is_browse_folder':__import__('live_core').is_browse_folder,'episode_identity':__import__('live_core').episode_identity}
  w.onClick=MethodType(extract(ROOT/'live_review.py','onClick',ns,'LiveReview'),w)
  return w,calls
 def test_video_click_starts_full_video_using_original_history_resume_url(self):
  item={'file':'plugin://plugin.video.youtube/play/?video_id=Abc_123-Xyz&resume=true','filetype':'file','title':'Video','label':'Video','resume':{'position':73,'total':600}};w,calls=self.state(item)
  w.onClick(900)
  self.assertNotIn('details',calls);self.assertEqual(w.playback_request,item['file']);self.assertEqual(w.playback_options,{'resume':True});self.assertEqual(calls[-2:],['stop','close'])
 def test_folder_with_plot_and_year_opens_its_contents_in_skin(self):
  item={'file':'plugin://plugin.video.youtube/channel/example/','filetype':'directory','title':'Channel','label':'Channel','plot':'Channel description','year':2026};w,calls=self.state(item)
  w.onClick(900);self.assertNotIn('details',calls);self.assertEqual(calls[0][0],'folder');self.assertEqual(calls[0][1][1],item['file'])
 def test_youtube_automatic_preview_setting_is_independent_of_movie_preference(self):
  import youtube_core
  func=getattr(youtube_core,'automatic_preview',None);self.assertTrue(callable(func),'Independent preview policy missing')
  self.assertTrue(func({},'YouTube','manual'));self.assertFalse(func({'YouTubePreviews':False},'YouTube','auto'));self.assertFalse(func({},'Movies','manual'));self.assertTrue(func({},'Movies','auto'))


 def test_account_change_or_disconnect_rejects_private_browse_snapshot_before_copy(self):
  for connected,identity,target in [(False,'','Home'),(True,'account-b','YouTube')]:
   with self.subTest(connected=connected):
    calls=[];window=SimpleNamespace(alive=True,window_lifetime=object(),generation=1,section='Home',rows=[[],[]],
     youtube_connection=SimpleNamespace(connected=connected,identity=identity),
     refresh_navigation=lambda:self.fail('Old private snapshot reached native rendering'),
     invalidate_row_results=lambda:calls.append('invalidated'),load_section=lambda:calls.append(window.section))
    state={'section':'YouTube','youtube_identity':'account-a','rows':[[{'title':'Account A private item'}],[]]}
    method=extract(ROOT/'live_review.py','restore_browse',{'copy':copy},'LiveReview');method(window,state)
    self.assertNotEqual(window.rows,state['rows']);self.assertEqual(window.section,target);self.assertEqual(calls[-1],target)
 def test_account_refresh_cannot_mutate_after_rpc_or_store_read_retires_window(self):
  self.assertIsNotNone(YouTubeBrowser)
  import youtube_browser
  for boundary in ['rpc','store']:
   with self.subTest(boundary=boundary):
    effects=[];window=SimpleNamespace(alive=True,window_lifetime=object(),section='Home',apply_youtube_home_rows=lambda:None,
     setProperty=lambda *a:effects.append('property'),invalidate_row_results=lambda:effects.append('cache'),refresh_navigation=lambda:effects.append('navigation'))
    def rpc(*args):
     if boundary=='rpc':window.alive=False
     return json.dumps({'result':{'addon':{'enabled':True}}})
    def store():
     if boundary=='store':window.window_lifetime=object()
     return {'access_manager':{'current_user':'0','users':{'0':{'id':'new-account','refresh_token':'one|two|three|'}}}}
    with patch.dict(sys.modules,{'xbmc':SimpleNamespace(executeJSONRPC=rpc)}),patch.object(youtube_browser,'read_account_store',store):
     YouTubeBrowser.refresh_youtube_connection(window,force=True)
    self.assertEqual(effects,[]);self.assertFalse(getattr(getattr(window,'youtube_connection',None),'connected',False))
 def test_adaptive_home_appends_real_groups_without_resetting_current_rows(self):
  self.adaptive_case(retire=False)
 def test_retired_adaptive_request_cannot_publish_private_rows(self):
  self.adaptive_case(retire=True)
 def test_home_append_rechecks_owner_after_account_store_read(self):
  import youtube_browser,youtube_core,time
  store={'access_manager':{'current_user':'0','users':{'0':{'refresh_token':'first|second|third|'}}}};identity=youtube_core.connected_account(store)[1]
  movies=[{'label':'Movies one'},{'label':'Movies two'}]
  window=SimpleNamespace(alive=True,window_lifetime=object(),youtube_home_request=object(),section='YouTube',youtube_tab='home',discovery_stack=[],
   youtube_connection=SimpleNamespace(connected=True,identity=identity),page_definitions=tab_rows('home'),
   youtube_home_cache={'identity':identity,'time':time.monotonic(),'rows':[{'label':'Recommended'},{'label':'Private shelf'}]})
  def retire_during_read():window.window_lifetime=object();window.section='Movies';window.page_definitions=movies;return store
  with patch.object(youtube_browser,'read_account_store',retire_during_read):YouTubeBrowser.apply_youtube_home_rows(window)
  self.assertEqual(window.page_definitions,[{'label':'Movies one'},{'label':'Movies two'}])
 def test_watch_guard_rejects_account_switch_or_retirement_during_disk_read(self):
  import youtube_browser,youtube_core
  store={'access_manager':{'current_user':'0','users':{'0':{'refresh_token':'first|second|third|'}}}};identity=youtube_core.connected_account(store)[1]
  window=SimpleNamespace(alive=True,window_lifetime=object(),generation=1,youtube_connection=SimpleNamespace(connected=True,identity=identity))
  current=YouTubeBrowser.youtube_request_guard(window,1)
  with patch.object(youtube_browser,'read_account_store',lambda:store):self.assertTrue(current())
  other=copy.deepcopy(store);other['access_manager']['users']['0']['refresh_token']='different|grants|here|'
  with patch.object(youtube_browser,'read_account_store',lambda:other):self.assertFalse(current())
  def retire():window.window_lifetime=object();return store
  with patch.object(youtube_browser,'read_account_store',retire):self.assertFalse(current())
 def adaptive_case(self,retire):
  import youtube_browser,youtube_core
  jobs=[];store={'access_manager':{'current_user':'0','users':{'0':{'refresh_token':'first|second|third|'}}}}
  connected,identity=youtube_core.connected_account(store)
  window=SimpleNamespace(alive=True,window_lifetime=object(),section='YouTube',youtube_tab='home',discovery_stack=[],
   youtube_connection=SimpleNamespace(connected=connected,identity=identity),page_definitions=tab_rows('home'))
  for name in ('start_youtube_home','apply_youtube_home_rows'):setattr(window,name,MethodType(getattr(YouTubeBrowser,name),window))
  before=copy.deepcopy(window.page_definitions)
  class Thread:
   def __init__(self,target,**kwargs):jobs.append(target)
   def start(self):pass
  rows=[{'label':'Recommended','local_items':[{'title':'General'}]},{'label':'Your changing interest','local_items':[{'title':'Private recommendation'}]}]
  with patch.object(youtube_browser.threading,'Thread',Thread),patch.object(youtube_browser,'read_account_store',lambda:store),patch.object(youtube_browser,'load_home_rows',lambda current:rows):
   window.start_youtube_home()
   if retire:window.window_lifetime=object()
   jobs[0]()
  self.assertEqual(window.page_definitions[:2],before)
  if retire:self.assertEqual(window.page_definitions,before);self.assertFalse(hasattr(window,'youtube_home_cache'))
  else:self.assertEqual(window.page_definitions[2]['label'],'Your changing interest');self.assertTrue(window.page_definitions[2]['local_items'])

 def test_discovery_caption_height_matches_youtube_home_and_keeps_other_sections(self):
  for section,want in [('YouTube',360),('Add-ons',344),('Movies',344)]:
   with self.subTest(section=section):
    heights=[];w=SimpleNamespace(section=section,discovery_stack=[],capture_browse=lambda **k:{},stop_preview=lambda:None,
     setProperty=lambda *a:None,getControl=lambda c:SimpleNamespace(setHeight=heights.append),set_rows=lambda x:None)
    extract(ROOT/'live_review.py','open_discovery',{'clear_search_selection':lambda w:None},'LiveReview')(w,{'heading':'Playlist','rows':[]})
    self.assertEqual(heights,[want,want])
 def test_browse_restore_preserves_youtube_caption_height_after_folder_or_settings(self):
  for section,want in [('YouTube',360),('Add-ons',344),('Movies',276)]:
   with self.subTest(section=section):
    heights=[];state={'section':section,'youtube_identity':'account-a','mode':'home','selected':None,'active_page':None,
     'episode_browser_context':None,'positions':[0,0],'rows':[[],[]],'focus':900,'row_offset':0,
     'properties':{'captionRows':'true' if section!='Movies' else 'false','row0':'A','row1':'B'}}
    w=SimpleNamespace(alive=True,window_lifetime=object(),generation=1,youtube_connection=SimpleNamespace(connected=True,identity='account-a'),
     refresh_navigation=lambda:None,load_browse_sources=lambda:None,setProperty=lambda *a:None,
     getControl=lambda c:SimpleNamespace(setHeight=heights.append),apply_row=lambda *a,**k:None,setFocusId=lambda c:None,restart_pending_rows=lambda:None)
    from youtube_core import resume_allowed
    extract(ROOT/'live_review.py','restore_browse',{'copy':copy,'youtube_resume_allowed':resume_allowed,'event':lambda *a,**k:None},'LiveReview')(w,state)
    self.assertEqual(heights,[want,want])

if __name__=='__main__':unittest.main()
