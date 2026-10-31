"""Explicit Play must validate progress before opening a saved private title."""
import copy,importlib.util,io,json,sys,tempfile,time,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from home_rows import HomeRowSnapshots,home_scope
from public_rows import helper_settings_identity
from playback_core import resume_options
from watch_metadata import refreshed_display_metadata
ROOT=Path(__file__).parents[1]/'addon'
MARK='_home_progress_scope'
BASE='plugin://plugin.video.themoviedb.helper/?'
MOVIE={'file':BASE+'info=play&tmdb_type=movie&tmdb_id=42','filetype':'file','title':'Example','year':2020,'playcount':0,'resume':{'position':40,'total':100}}
EPISODE={'file':BASE+'info=play&tmdb_type=tv&tmdb_id=12&season=1&episode=2','filetype':'file','title':'Episode','showtitle':'Show','season':1,'episode':2,'playcount':0,'resume':{'position':40,'total':100}}
ROWS=[BASE+'info=trakt_ondeck&tmdb_type=tv',BASE+'info=trakt_inprogress&tmdb_type=movie',BASE+'info=trakt_nextepisodes&tmdb_type=tv']
class SavedProgress(unittest.TestCase):
 def test_only_progress_display_reads_get_an_ephemeral_scope_marker(self):
  with tempfile.TemporaryDirectory() as d:
   cache=HomeRowSnapshots(Path(d)/'home.json','scope')
   next_page={'file':ROWS[0]+'&page=2','label':'Next page','filetype':'directory'}
   for row in ROWS:
    self.assertTrue(cache.put(row,[MOVIE]));self.assertEqual(cache.get(row)[0].get(MARK),'scope')
   self.assertTrue(cache.put(ROWS[0],[EPISODE,next_page]));self.assertNotIn(MARK,cache.get(ROWS[0])[-1]);self.assertNotIn(MARK,cache.path.read_text())
   path=BASE+'info=trakt_recommendations&tmdb_type=movie';cache.put(path,[MOVIE]);self.assertNotIn(MARK,cache.get(path)[0])
 def test_only_matched_authoritative_progress_hydration_retires_pending_scope(self):
  pending={**MOVIE,MARK:'scope'}
  for fresh in ({'playcount':0},dict(MOVIE,file=MOVIE['file'].replace('42','43')),dict(MOVIE,resume={'position':10**1000,'total':10**1000}),dict(MOVIE,resume={'position':'bad','total':100})):
   self.assertEqual(refreshed_display_metadata(pending,fresh).get(MARK),'scope')
  self.assertNotIn(MARK,refreshed_display_metadata(pending,MOVIE))
  self.assertEqual(pending[MARK],'scope','Captured context item must remain pending after another item is hydrated')
class PlaybackBoundary(unittest.TestCase):
 def environment(self,d,provider):
  events=[];notifications=[];values={'trakt_token':json.dumps({'access_token':'account-a','refresh_token':'refresh','created_at':time.time()-10,'expires_in':3600})};config={'Home':[],'Saved':[]};Path(d,'rows.json').write_text(json.dumps(config));schema='<settings><setting id="trakt_token" type="string"/></settings>'
  helper=types.SimpleNamespace(getAddonInfo=lambda key:d,getSetting=lambda key:values.get(key,''))
  scope=home_scope(config,helper_settings_identity(schema,helper.getSetting),values['trakt_token'])
  class Player:
   def isPlaying(self):return False
   def isPlayingVideo(self):return False
  class Window:
   def setProperty(self,*a):pass
   def clearProperty(self,*a):pass
   def getProperty(self,*a):return ''
  def rpc(raw):
   request=json.loads(raw);events.append((request['method'],request.get('params',{})));return json.dumps({'result':{}})
  def get_list(path):events.append(('provider',path));return provider(path,values)
  from urllib.parse import urlencode
  modules={'xbmc':types.SimpleNamespace(Player=Player,Monitor=lambda:types.SimpleNamespace(abortRequested=lambda:any(kind=='Player.Open' for kind,_ in events)),getSkinDir=lambda:'owner',executeJSONRPC=rpc),'xbmcgui':types.SimpleNamespace(Window=lambda wid:Window(),Dialog=lambda:types.SimpleNamespace(notification=lambda *a:notifications.append(a))),'xbmcaddon':types.SimpleNamespace(Addon=lambda aid:helper),'xbmcvfs':types.SimpleNamespace(File=lambda path:io.StringIO(schema)),'live_review':types.SimpleNamespace(STORE=Path(d),get_list=get_list,tmdb=lambda info,kind='movie',**params:BASE+urlencode(dict(info=info,tmdb_type=kind,nextpage='true',widget='true',**params)))}
  with patch.dict(sys.modules,modules):
   spec=importlib.util.spec_from_file_location('progress_playback_runtime',ROOT/'playback_runtime.py');runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
  return runtime,modules,events,notifications,scope,values
 def run_play(self,d,target,provider,path=None,options=None):
  runtime,modules,events,notes,scope,values=self.environment(d,provider);target={**copy.deepcopy(target),MARK:scope};original=copy.deepcopy(target)
  with patch.dict(sys.modules,modules):runtime.play_and_wait(path or target['file'],'owner',options or {},target)
  return events,notes,target,original
 def test_pending_movie_episode_and_captured_context_item_resolve_before_player_open(self):
  for target in (MOVIE,EPISODE):
   with self.subTest(target=target['file']),tempfile.TemporaryDirectory() as d:
    events,notes,target,original=self.run_play(d,target,lambda path,values:[copy.deepcopy(target)])
    self.assertEqual([kind for kind,_ in events],['provider','Player.Open'])
    self.assertIn('info=details',events[0][1]);self.assertEqual(events[1][1]['options'],{'resume':True});self.assertEqual(events[1][1]['item']['file'],target['file']);self.assertEqual(notes,[]);self.assertEqual(target,original)
 def test_fresh_progress_reaches_normal_resume_handoff_fallback(self):
  from playback_core import ResumeHandoff
  with tempfile.TemporaryDirectory() as d:
   guards=[];runtime,modules,events,notes,scope,_=self.environment(d,lambda p,v:[MOVIE])
   class ObservedHandoff(ResumeHandoff):
    def __init__(self,item):super().__init__(item);guards.append(self)
   runtime.ResumeHandoff=ObservedHandoff
   with patch.dict(sys.modules,modules):runtime.play_and_wait(MOVIE['file'],'owner',{},dict(MOVIE,**{MARK:scope}))
   self.assertEqual(events[-1][1]['options'],{'resume':True});self.assertEqual(len(guards),1)
   self.assertIsNone(guards[0].tick({'type':'movie','title':'Example','year':2020},0,10));self.assertEqual(guards[0].tick({'type':'movie','title':'Example','year':2020},0,14),40)
 def test_current_zero_resume_clears_old_resume_option_and_preserves_custom_player_url(self):
  with tempfile.TemporaryDirectory() as d:
   path=MOVIE['file']+'&player=umbrella.select.json&ignore_default=true'
   events,notes,_,_=self.run_play(d,MOVIE,lambda p,v:[dict(MOVIE,resume={'position':0,'total':100})],path=path,options={'resume':True})
   self.assertEqual(events[-1],('Player.Open',{'item':{'file':path}}));self.assertEqual([kind for kind,_ in events],['provider','Player.Open']);self.assertEqual(notes,[])
 def test_unmatched_unavailable_missing_or_invalid_progress_never_opens_player(self):
  cases=[[],[MOVIE,MOVIE],[dict(EPISODE,file=EPISODE['file'].replace('episode=2','episode=3'))],[dict(MOVIE,file=MOVIE['file'].replace('42','43'))],[dict(MOVIE,file='plugin://other/?tmdb_type=movie&tmdb_id=42')],[{k:v for k,v in MOVIE.items() if k!='resume'}],[dict(MOVIE,resume={'position':float('nan'),'total':100})],OSError('offline')]
  for result in cases:
   with self.subTest(result=result),tempfile.TemporaryDirectory() as d:
    def provider(path,values):
     if isinstance(result,Exception):raise result
     return result
    events,notes,_,_=self.run_play(d,MOVIE,provider);self.assertFalse(any(kind=='Player.Open' for kind,_ in events));self.assertTrue(notes)
 def test_account_change_during_lookup_or_before_play_never_opens_player(self):
  for during in (False,True):
   with self.subTest(during=during),tempfile.TemporaryDirectory() as d:
    def provider(path,values):values['trakt_token']='';return [MOVIE]
    runtime,modules,events,notes,scope,values=self.environment(d,provider)
    if not during:values['trakt_token']=''
    with patch.dict(sys.modules,modules):runtime.play_and_wait(MOVIE['file'],'owner',{},dict(MOVIE,**{MARK:scope}))
    self.assertFalse(any(kind=='Player.Open' for kind,_ in events));self.assertEqual(sum(kind=='provider' for kind,_ in events),int(during));self.assertTrue(notes)
 def test_real_controller_keeps_guard_for_unmatched_and_old_context_items(self):
  import test_snapshot_controller as fixture
  for match in (False,True):
   with self.subTest(match=match),tempfile.TemporaryDirectory() as d:
    runtime,modules,events,notes,scope,_=self.environment(d,lambda p,v:[EPISODE])
    state,_,_,queue=fixture.SnapshotController().state(d,lambda path:[EPISODE] if match else [])
    state.section='Home';state.home_snapshot_cache=HomeRowSnapshots(Path(d)/'home.json',scope);state.home_snapshot_cache.put(ROWS[0],[EPISODE]);state.set_rows([{'path':ROWS[0],'label':'Continue'},{'path':'','label':'Local','local_items':[MOVIE]}]);captured=state.rows[0][0]
    self.assertIn(MARK,captured);queue.pop(0)()
    self.assertEqual(MARK in state.rows[0][0],not match);self.assertIn(MARK,captured)
    with patch.dict(sys.modules,modules):runtime.play_and_wait(captured['file'],'owner',{},captured)
    self.assertEqual([kind for kind,_ in events],['provider','Player.Open']);self.assertEqual(events[-1][1]['options'],{'resume':True});self.assertEqual(notes,[])
 def test_exact_scope_rejects_nonempty_account_switch_or_config_change(self):
  for change in ('account','config'):
   with self.subTest(change=change),tempfile.TemporaryDirectory() as d:
    def provider(path,values):
     if change=='account':
      token=json.loads(values['trakt_token']);token['access_token']='account-b';values['trakt_token']=json.dumps(token)
     else:Path(d,'rows.json').write_text(json.dumps({'Home':[],'Saved':[{'title':'Changed configuration'}]}))
     return [MOVIE]
    runtime,modules,events,notes,scope,_=self.environment(d,provider)
    with patch.dict(sys.modules,modules):runtime.play_and_wait(MOVIE['file'],'owner',{},dict(MOVIE,**{MARK:scope}))
    self.assertEqual([kind for kind,_ in events],['provider']);self.assertTrue(notes)
 def test_abort_during_pending_progress_lookup_never_opens_player(self):
  for failed in (False,True):
   with self.subTest(failed=failed),tempfile.TemporaryDirectory() as d:
    aborted=[False]
    def provider(path,values):
     aborted[0]=True
     if failed:raise OSError('Kodi is closing')
     return [MOVIE]
    runtime,modules,events,notes,scope,_=self.environment(d,provider)
    modules['xbmc'].Monitor=lambda:types.SimpleNamespace(abortRequested=lambda:aborted[0])
    with patch.dict(sys.modules,modules):returned=runtime.play_and_wait(MOVIE['file'],'owner',{},dict(MOVIE,**{MARK:scope}))
    self.assertFalse(any(kind=='Player.Open' for kind,_ in events),'A provider result arriving after Kodi abort must not start media')
    self.assertEqual([kind for kind,_ in events],['provider']);self.assertIs(returned,False);self.assertEqual(notes,[])
 def test_unmarked_playback_does_not_query_helper_or_change_options(self):
  with tempfile.TemporaryDirectory() as d:
   runtime,modules,events,notes,_,_=self.environment(d,lambda p,v:self.fail('Unmarked playback must not fetch'))
   with patch.dict(sys.modules,modules):runtime.play_and_wait(MOVIE['file'],'owner',{'resume':True},MOVIE)
   self.assertEqual(events,[('Player.Open',{'item':{'file':MOVIE['file']},'options':{'resume':True}})]);self.assertEqual(notes,[])
if __name__=='__main__':unittest.main()
