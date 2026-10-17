"""Exercise the actual Kodi controller methods with small native-API substitutes."""
import ast,os,sys,threading,unittest,copy
from pathlib import Path
from types import SimpleNamespace,MethodType
from urllib.parse import parse_qs,urlsplit
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from live_core import PageHistory,row_items,my_stuff_rows,show_identity
from discovery_core import window_shift
from episode_ui import episode_item
from row_feedback import trim_row_cache,row_message
from search_ui import discovery_result,best_matches,clear_search_selection,entity_kind
from filtered_pages import provider_path,upstream_path,needs_fill
SOURCE=Path(os.environ.get('BL_CONTROLLER_SOURCE',str(Path(__file__).parents[1]/'addon/live_review.py')))
class Control:
 def __init__(self):self.items=[];self.pos=0
 def reset(self):self.items=[];self.pos=0
 def addItems(self,items):self.items+=items
 def selectItem(self,pos):self.pos=pos
 def getSelectedPosition(self):return self.pos
 def setVisible(self,visible):pass
 def controlUp(self,control):pass
 def controlDown(self,control):pass
 def controlLeft(self,control):pass
 def controlRight(self,control):pass
class SyncThread:
 def __init__(self,target,**kwargs):self.target=target
 def start(self):self.target()
def methods(names,namespace):
 from browse_controls import page_cards,should_exclude_anime
 namespace.update(page_cards=page_cards,should_exclude_anime=should_exclude_anime,best_matches=best_matches,clear_search_selection=clear_search_selection,entity_kind=entity_kind,show_identity=show_identity,parse_qs=parse_qs,urlsplit=urlsplit)
 namespace.update(row_items=row_items,provider_path=provider_path,upstream_path=upstream_path,needs_fill=needs_fill)
 cls=next(n for n in ast.parse(SOURCE.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='LiveReview')
 nodes=[next((n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name),None) for name in names]
 if None in nodes:raise AssertionError('Required discovery controller method is absent')
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SOURCE),'exec'),namespace)
 if "show_row_window" in names:
  from cache_fixture import with_cache
  namespace["show_row_window"]=with_cache(namespace["show_row_window"],namespace)
 return namespace
class DiscoveryController(unittest.TestCase):
 def test_my_stuff_scrolls_to_local_saves_and_back_without_extra_provider_calls(self):
  saved=[{'file':'saved-title','resume':{'position':25,'total':100}}]
  s,calls,controls=self.state();s.section='My Stuff';s.adaptive_browsing=True
  definitions=my_stuff_rows(saved,lambda info,kind:'plugin://plugin.video.test/'+kind)
  s.set_rows(definitions);controls[901].selectItem(0)
  self.assertTrue(s.shift_rows(1,0));self.assertEqual(s.row_offset,1)
  self.assertEqual(s.rows[1],[{'file':'plugin://plugin.video.test/tv/title'}]);self.assertEqual(calls,['plugin://plugin.video.test/movie','plugin://plugin.video.test/tv'])
  self.assertTrue(s.shift_rows(-1,0));self.assertEqual(s.row_offset,0)
  self.assertEqual(s.paths[1],definitions[1]['path']);self.assertEqual(controls[901].getSelectedPosition(),0)
  self.assertEqual(s.rows[0],saved)
 def test_empty_device_saves_stay_first_in_my_stuff(self):
  s,calls,_=self.state();s.section='My Stuff';s.adaptive_browsing=True
  s.set_rows(my_stuff_rows([],lambda info,kind:'plugin://plugin.video.test/'+kind))
  self.assertEqual(s.row_offset,0)
  self.assertEqual(s.getProperty('row0'),'Saved on this device  ·  No titles')
  self.assertEqual(s.getProperty('row1'),'Trakt Watchlist · Movies')
 def test_empty_row_label_does_not_accumulate_when_scrolling_back_and_forth(self):
  s,calls,_=self.state();s.section='My Stuff';s.adaptive_browsing=True
  defs=[{'label':'First','path':'first'},{'label':'Movies','path':'movies'},{'label':'Saved on this device','path':'','local_items':[]}]
  s.set_rows(defs)
  for _ in range(4):
   s.shift_rows(1,0);s.shift_rows(-1,0)
  s.shift_rows(1,0)
  self.assertEqual(s.getProperty('row1'),'Saved on this device  ·  No titles')
  self.assertEqual(s.getProperty('rowMessage1'),'Saved on this device · This list returned no titles.')
 def test_fixed_hero_is_compact_on_first_and_deeper_rows(self):
  s,_,_=self.state();s.adaptive_browsing=True;s.fixed_hero=True;s.section='Home'
  s.set_rows([{'label':str(n),'path':'plugin://plugin.video.test/'+str(n)} for n in range(3)])
  self.assertEqual(s.getProperty('heroCompact'),'true')
  s.shift_rows(1,0);self.assertEqual(s.getProperty('heroCompact'),'true')
  s.shift_rows(-1,0);self.assertEqual(s.getProperty('heroCompact'),'true')
 def test_captioned_first_row_uses_compact_layout_to_keep_titles_visible(self):
  s,_,_=self.state();s.adaptive_browsing=True;s.section='Movies'
  s.setProperty('captionRows','true')
  s.set_rows([{'label':'Filmography','path':'plugin://plugin.video.test/credits'}])
  self.assertEqual(s.getProperty('heroCompact'),'true')
 def test_leaving_addons_for_media_rows_clears_square_card_layout(self):
  s,_,_=self.state();s.adaptive_browsing=True;s.section='Shows';s.setProperty('addonBrowser','true')
  s.set_rows([{'label':'Horror','path':'plugin://plugin.video.test/horror'}])
  self.assertEqual(s.getProperty('addonBrowser'),'false')
 def test_adaptive_empty_primary_promotes_visible_secondary_and_keeps_empty_evidence(self):
  focus=[];s,_,_=self.state(provider=lambda path:[] if path.endswith('/0') else [{'file':path+'/title'}])
  s.adaptive_browsing=True;s.setFocusId=focus.append
  s.set_rows([{'label':str(n),'path':'plugin://plugin.video.test/'+str(n)} for n in range(3)])
  self.assertEqual(s.row_offset,1);self.assertEqual(s.rows[0][0]['file'],'plugin://plugin.video.test/1/title')
  self.assertEqual(focus[-1],900);self.assertEqual(s.row_cache[0]['state'],'empty')
 def test_adaptive_hover_scroll_keeps_hover_target_for_repeated_vertical_steps(self):
  s,_,_=self.state();s.adaptive_browsing=True;s.mouse=True;focus=[];s.setFocusId=focus.append
  s.set_rows([{'label':str(n),'path':'plugin://plugin.video.test/'+str(n)} for n in range(3)])
  ns=methods(['arrow'],{'event':lambda *a,**k:None})
  ns['arrow'](s,701)
  self.assertEqual(s.row_offset,1);self.assertEqual(focus[-1],701)

 def test_adaptive_browsing_promotes_next_row_and_restores_exact_card_on_return(self):
  s,calls,controls=self.state(provider=lambda path:[{'file':path+'/'+str(n)} for n in range(6)])
  s.adaptive_browsing=True
  s.set_rows([{'label':str(n),'path':'plugin://plugin.video.test/'+str(n)} for n in range(9)])
  s.paths[0]+='/nextpage';controls[900].selectItem(4)
  self.assertTrue(s.shift_rows(1,0),'Down from the primary shelf should advance the configured row')
  self.assertEqual(s.row_offset,1);self.assertEqual(s.rows[0][0]['file'],'plugin://plugin.video.test/1/0')
  for _ in range(5):self.assertTrue(s.shift_rows(1,0))
  self.assertEqual(s.row_offset,6)
  for _ in range(6):self.assertTrue(s.shift_rows(-1,0))
  self.assertEqual(s.row_offset,0);self.assertEqual(s.paths[0],'plugin://plugin.video.test/0/nextpage')
  self.assertEqual(controls[900].getSelectedPosition(),4)
  self.assertFalse(s.shift_rows(-1,0),'Up from the first row must reach hero controls normally')

 def state(self,thread=SyncThread,provider=None):
  controls={cid:Control() for cid in (900,901,101,102,103,105,106,600,15)};props={};calls=[]
  ns={'copy':copy,'discovery_result':discovery_result,'PageHistory':PageHistory,'episode_item':episode_item,'trim_row_cache':trim_row_cache,'row_message':row_message,'media_item':lambda d:d,'window_shift':window_shift,'threading':SimpleNamespace(Thread=thread),'event':lambda *a,**kw:None,'get_list':lambda path:calls.append(path) or (provider(path) if provider else [{'file':path+'/title'}])}
  ns=methods(['set_rows','show_row_window','apply_row','row_navigation','shift_rows'],ns)
  s=SimpleNamespace(preview_dispatch_lock=threading.RLock(),alive=True,mode='home',episode_browser_context=None,season_title='',preview_mode='auto',generation=0,active_page='genre',rows=[[],[]],paths=['',''],histories=[PageHistory(),PageHistory()],row_offset=0,row_cache={},page_definitions=[],window_ready=[False,False],list_lock=threading.Lock(),browse_sources=[],focus_key=None,stop_preview=lambda:None,finish_loading=lambda reason:None,update=lambda item:None,setFocusId=lambda cid:None,getFocusId=lambda:900,getControl=lambda cid:controls[cid],setProperty=lambda k,v:props.__setitem__(k,v),getProperty=lambda k:props.get(k,''))
  for name in ['set_rows','show_row_window','apply_row','row_navigation','shift_rows']:setattr(s,name,MethodType(ns[name],s))
  return s,calls,controls
 def test_episode_provider_rows_keep_the_show_heading_and_resume_point(self):
  item={'title':'Pilot','season':1,'episode':1,'file':'exact','resume':{'position':25,'total':100}}
  s,calls,controls=self.state(provider=lambda path:[item]);s.episode_browser_context={'item':{}};s.season_title='Show'
  s.set_rows([{'label':'Season 1','path':'episodes'}])
  self.assertEqual(s.rows[0][0],{**item,'showtitle':'Show'})
  self.assertEqual(controls[900].items[0]['resume'],{'position':25,'total':100})
 def test_full_rows_load_on_demand_and_provider_position_survives_return(self):
  s,calls,controls=self.state();defs=[{'label':str(n),'path':'plugin://plugin.video.test/'+str(n)} for n in range(4)]
  s.set_rows(defs);self.assertEqual(len(calls),2)
  s.paths[0]+='/nextpage';s.histories[0].push(defs[0]['path'],0)
  self.assertTrue(s.shift_rows(1,1));self.assertEqual(s.row_offset,1);self.assertEqual(s.rows[1][0]['file'],defs[2]['path']+'/title')
  self.assertTrue(s.shift_rows(1,1));self.assertEqual(s.row_offset,2);self.assertEqual(s.rows[1][0]['file'],defs[3]['path']+'/title')
  self.assertTrue(s.shift_rows(-1,0));self.assertTrue(s.shift_rows(-1,0));self.assertEqual(len(calls),4)
  self.assertEqual(s.paths[0],defs[0]['path']+'/nextpage');self.assertEqual(s.histories[0].pop(),(defs[0]['path'],0))
 def test_obsolete_row_work_does_not_fetch_or_overwrite_the_new_page(self):
  queue=[]
  class QueuedThread(SyncThread):
   def start(self):queue.append(self.target)
  s,calls,_=self.state(QueuedThread)
  s.set_rows([{'label':'Old','path':'plugin://plugin.video.test/old'}]);s.set_rows([{'label':'New','path':'plugin://plugin.video.test/new'}])
  for target in queue:target()
  self.assertEqual(calls,['plugin://plugin.video.test/new']);self.assertEqual(s.rows[0][0]['file'],'plugin://plugin.video.test/new/title')
 def test_row_editor_changes_its_own_list_and_keeps_source_visibility(self):
  choices=iter([0,0,-1]);saved=[];dialog=SimpleNamespace(select=lambda *a,**k:next(choices))
  ns=methods(['edit_rows'],{'xbmcgui':SimpleNamespace(Dialog=lambda:dialog)})
  rows=[{'label':'Action','path':'plugin://plugin.video.test/old','enabled':False}]
  state=SimpleNamespace(alive=True,choose_source=lambda:{'label':'Provider name','path':'plugin://plugin.video.test/new'},save=lambda:saved.append(True))
  ns['edit_rows'](state,rows,'Action');self.assertEqual(rows,[{'label':'Action','path':'plugin://plugin.video.test/new','enabled':False}]);self.assertEqual(len(saved),1)
 def test_empty_first_lists_do_not_block_a_later_configured_row(self):
  s,calls,_=self.state(provider=lambda path:[] if path.endswith(('/0','/1')) else [{'file':path+'/title'}])
  s.set_rows([{'label':str(n),'path':'plugin://plugin.video.test/'+str(n)} for n in range(3)])
  self.assertEqual(s.row_offset,1);self.assertEqual(s.rows[1][0]['file'],'plugin://plugin.video.test/2/title')
 def test_empty_next_slot_can_be_passed_using_the_visible_first_row(self):
  s,_,_=self.state(provider=lambda path:[] if path.endswith('/1') else [{'file':path+'/title'}])
  s.set_rows([{'label':str(n),'path':'plugin://plugin.video.test/'+str(n)} for n in range(3)])
  self.assertTrue(s.shift_rows(1,0));self.assertEqual(s.rows[1][0]['file'],'plugin://plugin.video.test/2/title')
 def test_loaded_first_row_receives_focus_after_empty_controls_were_replaced(self):
  focus=[];s,_,_=self.state();s.setFocusId=lambda cid:focus.append(cid)
  s.set_rows([{'label':'Movies','path':'plugin://plugin.video.test/movies'}])
  self.assertEqual(focus[-1],900)
 def test_evicted_rows_reload_the_last_provider_page_at_the_saved_card(self):
  s,calls,controls=self.state(provider=lambda path:[{'file':path+'/'+str(n)} for n in range(6)])
  s.set_rows([{'label':str(n),'path':'plugin://plugin.video.test/'+str(n)} for n in range(13)])
  s.paths[0]+='/nextpage';controls[900].selectItem(3);s.histories[0].push('original',2)
  for _ in range(9):s.shift_rows(1,1)
  self.assertIsNone(s.row_cache[0]['files'])
  for _ in range(9):s.shift_rows(-1,0)
  self.assertEqual(s.paths[0],'plugin://plugin.video.test/0/nextpage')
  self.assertEqual(controls[900].getSelectedPosition(),3);self.assertEqual(s.histories[0].pop(),('original',2))

 def test_failed_row_retains_its_error_and_retry_when_scrolling_away_and_back(self):
  def provider(path):
   if path.endswith('/0'):raise RuntimeError('offline')
   return [{'file':path+'/title'}]
  s,calls,controls=self.state(provider=provider)
  s.set_rows([{'label':str(n),'path':'plugin://plugin.video.test/'+str(n)} for n in range(3)])
  self.assertEqual(s.row_states[0],'error')
  s.shift_rows(1,1);s.shift_rows(-1,0)
  self.assertEqual(s.row_states[0],'error','An unavailable row must not become an empty success on return')
  self.assertEqual(s.getProperty('rowState0'),'error')
  self.assertIn('could not load',s.getProperty('rowMessage0'))

 def test_failed_forward_route_and_selected_title_survive_row_window_return(self):
  s,_,controls=self.state(provider=lambda path:[{'file':path+'/'+str(n)} for n in range(6)])
  s.set_rows([{'label':str(n),'path':'plugin://plugin.video.test/'+str(n)} for n in range(3)])
  failed={'path':'plugin://plugin.video.test/next','label':'Next','back':False,'position':0}
  s.row_states[0]='error';s.failed_paths[0]=failed;controls[900].selectItem(4)
  s.shift_rows(1,1);s.shift_rows(-1,0)
  self.assertEqual(s.failed_paths[0],failed)
  self.assertEqual(s.paths[0],'plugin://plugin.video.test/0')
  self.assertEqual(controls[900].getSelectedPosition(),4)
 def test_initial_failure_remembers_clean_label_for_a_successful_retry(self):
  def fail(path):
   if path.endswith('/0'):raise RuntimeError('offline')
   return [{'file':path+'/title'}]
  s,_,_=self.state(provider=fail)
  s.set_rows([{'label':'Original row','path':'plugin://plugin.video.test/0'},{'label':'Available','path':'plugin://plugin.video.test/1'}])
  self.assertIn(0,s.failed_paths,'Initial failures must retain a retry request')
  self.assertEqual(s.failed_paths[0]['label'],'Original row','Retry must not inherit the unavailable decoration')
  self.assertTrue(s.failed_paths[0]['back'])

 def test_failed_next_page_remains_retryable_after_a_long_browse_evicts_titles(self):
  s,_,controls=self.state(provider=lambda path:[{'file':path+'/'+str(n)} for n in range(6)])
  s.set_rows([{'label':str(n),'path':'plugin://plugin.video.test/'+str(n)} for n in range(13)])
  failure={'path':'plugin://plugin.video.test/0/next','label':'0','back':False,'position':0}
  s.row_states[0]='error';s.failed_paths[0]=failure
  s.setProperty('rowMessage0','Next page could not load');controls[900].selectItem(4)
  for _ in range(9):s.shift_rows(1,1)
  self.assertIsNone(s.row_cache[0]['files'])
  for _ in range(9):s.shift_rows(-1,0)
  self.assertEqual(s.failed_paths.get(0),failure,'Reloading old titles must not forget the failed Next-page request')
  self.assertEqual(s.row_states[0],'error');self.assertEqual(s.getProperty('rowState0'),'ready')
  self.assertEqual(s.getProperty('rowMessage0'),'Next page could not load')
  self.assertEqual(controls[900].getSelectedPosition(),4)

 def test_initial_error_can_recover_when_evicted_row_reloads_successfully(self):
  unavailable=[True]
  def provider(path):
   if unavailable[0] and path.endswith('/0'):raise RuntimeError('offline')
   return [{'file':path+'/title'}]
  s,_,controls=self.state(provider=provider)
  s.set_rows([{'label':str(n),'path':'plugin://plugin.video.test/'+str(n)} for n in range(13)])
  for _ in range(9):s.shift_rows(1,1)
  unavailable[0]=False
  for _ in range(9):s.shift_rows(-1,0)
  self.assertEqual(s.row_states[0],'ready');self.assertNotIn(0,s.failed_paths)
  self.assertEqual(s.getProperty('row0'),'0')
