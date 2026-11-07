"""Show-level one-time playback selects a real episode; defaults remain separate."""
import copy,sys,threading,unittest,inspect
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs,urlsplit
from test_window_lifecycle import ROOT,extract
import playback_core
from live_core import episode_identity,show_identity
from player_preferences import player_path
from episode_ui import season_entries
BASE='plugin://plugin.video.themoviedb.helper/?tmdb_type=tv&tmdb_id=123&info='
def show(season=None):
 return {'file':BASE+('seasons' if season is None else 'episodes&season='+str(season)),'filetype':'directory','title':'Show','type':'tvshow' if season is None else 'season'}
def episode(showid=123,season=0):
 return {'file':f'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id={showid}&season={season}&episode=2&resume=true','filetype':'file','title':'Exact episode','showtitle':'Show','season':season,'episode':2,'resume':{'position':30,'total':100}}
def kind(item):return getattr(playback_core,'playback_kind',lambda _:None)(item)
class ShowPlayer154(unittest.TestCase):
 def test_show_season_and_specials_are_episode_player_contexts_without_relaxing_play_routes(self):
  for item in (show(),show(1),show(0),episode()):
   self.assertEqual(kind(item),'episode')
   if item['filetype']=='directory':
    self.assertIsNone(playback_core.choose_player_path(item));self.assertIsNone(player_path(item,'umbrella.select.json'))
 def test_eligibility_rejects_unrelated_or_malformed_folders_and_episode_summary_fields(self):
  for item in ({**show(), 'file':BASE+'popular'}, {**show(), 'file':BASE+'seasons&tmdb_id=bad'}, {**show(), 'file':show()['file'].replace('plugin.video.themoviedb.helper','plugin.video.blacklanturn.fights')}, {**show(0),'file':BASE+'episodes&season=-1'}, {**show(),'_page_control':'next'}):
   self.assertIsNone(kind(item))
  self.assertEqual(kind({**show(),'season':8,'episode':20}),'episode')
 def title_menu(self,item,mode='home',focus=900,hero=None,selection=None):
  from browse_controls import can_choose_genre
  from search_ui import discovery_result
  options=[];calls=[]
  def choose(choices,*args):
   options.extend(choices);return next((n for n,(key,_) in enumerate(choices) if key==selection),-1)
  w=SimpleNamespace(actions_open=False,input_generation=0,section='Shows',mode=mode,nav=False,search_state=None,episode_browser_context=None,discovery_stack=[],getFocusId=lambda:focus,last_row=0,rows=[[item],[]],histories=[],related_history=None,selected=hero,chosen=lambda cid:item,row_states={},config={'Saved':[]},rating_identity=lambda _:None,stop_preview=lambda:None,show_title_actions=choose)
  w.update=lambda value:calls.append(('update',value,w.actions_open))
  w.browse_all_episodes=lambda **kw:calls.append(('episodes',kw,w.actions_open))
  ns={'trakt_command':lambda _:None,'choose_player_path':playback_core.choose_player_path,'playback_kind':kind,'can_choose_genre':can_choose_genre,'discovery_result':discovery_result,'resume_options':playback_core.resume_options,'event':lambda *a,**k:None}
  extract(ROOT/'live_review.py','title_actions',ns,'LiveReview')(w)
  return options,calls,w
 def test_series_and_season_open_the_episode_browser_without_player_selection(self):
  from action_panel_model import build_panel
  for item in (show(),show(0)):
   options,calls,w=self.title_menu(item,selection='browse_episodes')
   expected=['browse_episodes','details']+(['genre'] if item['type']=='tvshow' else [])
   self.assertEqual([a['id'] for a in build_panel(options)['quick']],expected)
   self.assertNotIn(('default_player','Set default player…'),options)
   self.assertEqual(calls,[('update',item,True),('episodes',{},True)])
   self.assertFalse(w.actions_open);self.assertFalse(hasattr(w,'playback_request'))
 def test_direct_episode_and_movie_keep_the_one_time_player_choice(self):
  movie={'file':BASE.replace('tv&','movie&')+'play','filetype':'file','title':'Movie'}
  for item in (episode(),movie):
   self.assertIn(('player','Play using…'),self.title_menu(item)[0])
 def test_details_is_available_only_when_it_can_open_another_title(self):
  item=show()
  self.assertNotIn(('details','Details'),self.title_menu(item,mode='details',focus=101,hero=dict(item))[0])
  self.assertIn(('details','Details'),self.title_menu(item,mode='details',focus=3100,hero=episode())[0])
 def test_episode_refresh_label_describes_one_episode_including_specials(self):
  from live_core import title_details_params
  state=SimpleNamespace(mode='home',section='Shows',config={},paths=[],last_row=0)
  ns={'choose_action_panel':lambda *a,**kw:None,'episode_identity':episode_identity,'title_details_params':title_details_params,'valid_source':lambda p:False}
  run=extract(ROOT/'live_review.py','show_title_actions',ns,'LiveReview')
  for item,label in ((show(),'Check for new episodes'),(episode(),'Refresh episode information')):
   options=[];run(state,options,item,900)
   self.assertIn(('refresh_metadata',label),options)
 def test_episode_default_is_available_in_playback_settings_without_a_selected_title(self):
  from backend_core import SETTINGS_GROUPS
  playback=next(group for group in SETTINGS_GROUPS if group[0]=='Playback & sync')
  self.assertIn(('default_episode_player','Default episode player…'),[entry[:2] for entry in playback[2]])
  method,w,_,values,calls=self.preferences(0)
  w.choose_playback_player=lambda *a,**kw:method(w,*a,**kw)
  extract(ROOT/'live_review.py','run_setting',{'event':lambda *a,**kw:None},'LiveReview')(w,'default_episode_player')
  self.assertEqual(values,{'default_player_episodes':'umbrella.select.json play_episode','default_player_movies':'original movie default'})
  self.assertFalse(hasattr(w,'playback_request'));self.assertNotIn('finish',calls)
 def test_cancelling_options_during_episode_selection_retires_pending_intent(self):
  item=episode();context={'play_using_show':'123'};w=SimpleNamespace(actions_open=False,input_generation=0,section='Shows',mode='home',episode_browser_context=context,getFocusId=lambda:900,last_row=0,rows=[[item],[]],histories=[],chosen=lambda cid:item,row_states={},config={'Saved':[]},rating_identity=lambda _:None,stop_preview=lambda:None,setProperty=lambda *a:None,show_title_actions=lambda *a:-1)
  ns={'trakt_command':lambda _:None,'choose_player_path':playback_core.choose_player_path,'playback_kind':kind,'can_choose_genre':lambda *a:False,'discovery_result':lambda _:None,'resume_options':playback_core.resume_options,'event':lambda *a,**k:None}
  extract(ROOT/'live_review.py','title_actions',ns,'LiveReview')(w);self.assertNotIn('play_using_show',context)
 def test_show_play_using_opens_episode_browser_before_reading_players_or_launching(self):
  calls=[];w=SimpleNamespace(stop_preview=lambda:None)
  def owned(event,value):
   self.assertTrue(getattr(w,'actions_open',False),'Monitor must stay paused while the selected show becomes the episode-browser owner');calls.append((event,value))
  w.update=lambda item:owned('selected',item);w.browse_all_episodes=lambda **kw:owned('browse',kw)
  ns={'episode_identity':episode_identity,'playback_kind':kind,'choose_player_path':playback_core.choose_player_path,'rpc':lambda *a,**k:self.fail('Provider lookup before explicit episode selection')}
  extract(ROOT/'live_review.py','choose_playback_player',ns,'LiveReview')(w,show(0))
  self.assertEqual(calls,[('selected',show(0)),('browse',{'choose_player':True})]);self.assertFalse(hasattr(w,'playback_request'))
 def preferences(self,choice):
  from test_player_preferences import PlayerPreferenceController
  fixture=PlayerPreferenceController();self.addCleanup(fixture.doCleanups);return fixture.state(choice)
 def test_show_and_season_set_default_changes_episode_default_only_without_browsing_or_playback(self):
  for item in (show(),show(0)):
   method,w,_,values,calls=self.preferences(0);w.browse_all_episodes=lambda **kw:self.fail('Default must not open episodes');method(w,item,True)
   self.assertEqual(values,{'default_player_episodes':'umbrella.select.json play_episode','default_player_movies':'original movie default'});self.assertFalse(hasattr(w,'playback_request'));self.assertNotIn('finish',calls)
 def test_cancel_show_default_preserves_both_defaults(self):
  method,w,_,values,calls=self.preferences(-1);before=dict(values);method(w,show(),True);self.assertEqual(values,before);self.assertFalse(hasattr(w,'playback_request'))
 def test_cancel_direct_episode_chooser_also_consumes_pending_series_intent(self):
  method,w,item,values,calls=self.preferences(-1);w.setProperty=lambda *a:None;w.episode_browser_context={'play_using_show':'123'};before=dict(values)
  method(w,item);self.assertNotIn('play_using_show',w.episode_browser_context);self.assertEqual(values,before);self.assertFalse(hasattr(w,'playback_request'))
 def test_cancelling_pending_episode_chooser_replaces_the_choose_episode_hint(self):
  method,w,item,values,calls=self.preferences(-1);w.episode_browser_context={'play_using_show':'123'};props={'notice':'Select an episode, then choose Source Select, Auto Play or Rescrape'};w.setProperty=lambda k,v:props.__setitem__(k,v)
  method(w,item);self.assertEqual(props['notice'],'Live add-on content  ·  Select a title for details')
 def browser(self,item):
  jobs=[];selected=[];props={};control=SimpleNamespace(getSelectedPosition=lambda:2,setHeight=lambda n:None,reset=lambda:None)
  w=SimpleNamespace(selected=item,mode='home',last_row=0,rows=[[item],[]],paths=['old',''],histories=[],page_definitions=[],row_offset=0,row_cache={},active_page='trakt',generation=3,alive=True,list_lock=threading.Lock(),stop_preview=lambda:None,getControl=lambda n:control,getProperty=lambda key:'old',setProperty=lambda k,v:props.__setitem__(k,v),setFocusId=lambda n:None,populate_seasons=lambda:None,select_episode_season=lambda n:selected.append(n))
  class Deferred:
   def __init__(self,target,**kw):self.target=target
   def start(self):jobs.append(self.target)
  ns={'show_identity':show_identity,'action_identity':playback_core.action_identity,'threading':SimpleNamespace(Thread=Deferred),'tmdb':lambda *a,**k:'seasons','season_entries':season_entries,'event':lambda *a,**kw:None,'get_list':lambda p:[show(1),show(0)]}
  return w,jobs,selected,props,extract(ROOT/'live_review.py','browse_all_episodes',ns,'LiveReview')
 def test_browser_defers_provider_work_and_seeds_url_only_specials_with_clear_hint(self):
  w,jobs,selected,props,run=self.browser(show(0));self.assertIn('choose_player',inspect.signature(run).parameters);run(w,choose_player=True)
  self.assertEqual(w.episode_browser_context.get('play_using_show'),'123');self.assertEqual(selected,[]);self.assertFalse(hasattr(w,'playback_request'))
  self.assertIn('EPISODE',props['eyebrow']);jobs.pop()();self.assertEqual(selected,[1]);self.assertEqual(w.season_sources[1]['season'],0)
 def click_state(self,item,pending='123'):
  calls=[];context={'play_using_show':pending,'item':show()};w=SimpleNamespace(actions_open=False,input_generation=0,setProperty=lambda *a:None,selected=item,episode_browser_context=context,mode='home',section='Shows',stop_preview=lambda:None,choose_playback_player=lambda item:calls.append(('chooser',copy.deepcopy(item))),capture_browse=lambda:{'episode_browser_context':copy.deepcopy(context)},finish=lambda:calls.append(('finish',)),update=lambda item:setattr(w,'selected',item),chosen=lambda cid:item)
  ns={'episode_identity':episode_identity,'show_identity':show_identity,'discovery_result':lambda _:None,'is_browse_folder':lambda i:i.get('filetype')=='directory','resume_options':playback_core.resume_options,'choose_player_path':playback_core.choose_player_path}
  method=extract(ROOT/'live_review.py','onClick',ns,'LiveReview');w.onClick=lambda cid:method(w,cid);return w,calls
 def test_exact_selected_episode_consumes_intent_then_uses_existing_chooser(self):
  for cid in (101,900):
   item=episode();w,calls=self.click_state(item);w.onClick(cid)
   self.assertEqual(calls,[('chooser',item)]);self.assertNotIn('play_using_show',w.episode_browser_context);self.assertFalse(hasattr(w,'playback_request'));self.assertEqual(w.selected['resume'],{'position':30,'total':100})
 def test_cancelled_player_choice_does_not_intercept_a_later_normal_click(self):
  w,calls=self.click_state(episode());w.onClick(101);w.onClick(101)
  self.assertEqual([x[0] for x in calls],['chooser','finish']);self.assertEqual(w.playback_request,episode()['file']);self.assertEqual(w.playback_options,{'resume':True})
 def test_unrelated_show_episode_never_consumes_the_old_player_choice(self):
  item=episode(showid=999);w,calls=self.click_state(item);w.onClick(101)
  self.assertEqual(calls,[('finish',)]);self.assertNotIn('play_using_show',w.episode_browser_context);self.assertEqual(w.playback_request,item['file'])
 def test_back_clears_pending_intent_even_when_only_closing_sidebar(self):
  context={'play_using_show':'123'};w=SimpleNamespace(setProperty=lambda *a:None,actions_open=False,input_generation=0,episode_browser_context=context,nav=True,mode='home',return_focus=900,stop_preview=lambda:None,set_nav=lambda *a,**k:None,setFocusId=lambda cid:None)
  extract(ROOT/'live_review.py','onAction',{},'LiveReview')(w,SimpleNamespace(getId=lambda:92));self.assertNotIn('play_using_show',context)
 def test_sidebar_navigation_clears_intent_before_dispatch(self):
  w,calls=self.click_state(episode());w.navigation_items=[{'id':'movies'}];w.getControl=lambda cid:SimpleNamespace(getSelectedPosition=lambda:0)
  w.activate_navigation=lambda entry:self.assertNotIn('play_using_show',w.episode_browser_context)
  w.onClick(50)
 def test_browse_snapshots_do_not_persist_one_time_player_intent(self):
  item=episode();context={'item':show(),'play_using_show':'123'};w=SimpleNamespace(section='Shows',mode='home',navigation_id='shows',active_page=None,page_definitions=[],row_offset=0,row_cache={},rows=[[item],[]],paths=['old',''],histories=[],last_row=0,return_focus=900,selected=item,person_context=None,episode_browser_context=context,season_sources=[],season_title='Show',season_position=0,getControl=lambda cid:SimpleNamespace(getSelectedPosition=lambda:0),getFocusId=lambda:900,getProperty=lambda key:'')
  snap=extract(ROOT/'live_review.py','capture_browse',{'copy':copy},'LiveReview')(w)
  self.assertNotIn('play_using_show',snap['episode_browser_context']);self.assertEqual(context['play_using_show'],'123')
