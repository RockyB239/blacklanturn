import ast,sys,unittest,os
from pathlib import Path
from types import SimpleNamespace,MethodType
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from navigation_core import *
ROOT=Path(__file__).parents[1]
def methods(names,extra):
 cls=next(n for n in ast.parse(Path(os.environ.get('BL_CONTROLLER_SOURCE',str(ROOT/'addon/live_review.py'))).read_text()).body if isinstance(n,ast.ClassDef) and n.name=='LiveReview')
 ns=dict(extra);exec(compile(ast.Module(body=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'live_review','exec'),ns)
 return ns
class NavigationController(unittest.TestCase):
 def fixture(self):
  return migrate_navigation({'Saved':[{'file':'retained'}],'Genres':[{'id':'action','label':'Action','section':'Movies','rows':[{'label':'Action hits','path':'plugin://plugin.video.test/action'}]}]})
 def controller(self,available=True):
  calls=[];config=self.fixture()
  ns=methods(['activate_navigation','load_navigation_page'],{'resolve_destination':resolve_destination,'event':lambda *a,**k:None,'xbmc':SimpleNamespace(getCondVisibility=lambda q:available),'rpc':lambda *a,**k:{'result':{'value':''}},'xbmcgui':SimpleNamespace(Dialog=lambda:SimpleNamespace(ok=lambda *a:calls.append(('unavailable',a))))})
  state=SimpleNamespace(config=config,section='Home',active_page=None,backend_position=(0,0),navigation_id='home',alive=True,stop_preview=lambda:calls.append(('stop',)),set_nav=lambda v,**kw:None,setFocusId=lambda i:calls.append(('focus',i)),load_section=lambda:calls.append(('section',state.section)),finish=lambda:calls.append(('finish',)),refresh_navigation=lambda:None,setProperty=lambda *a:None,load_browse_sources=lambda:None,set_rows=lambda rows:calls.append(('rows',rows)),browse_sources=[],getControl=lambda c:None)
  for name in ('activate_navigation','load_navigation_page'):
   self.assertIn(name,ns,'Sidebar routing is not implemented');setattr(state,name,MethodType(ns[name],state))
  return state,calls
 def test_sidebar_page_uses_its_own_rows(self):
  s,calls=self.controller();s.activate_navigation({'id':'action-link','destination':{'kind':'page','page_id':'action'}})
  self.assertEqual(s.section,'Movies');self.assertEqual(s.active_page,'action');self.assertIn(('rows',[{'label':'Action hits','path':'plugin://plugin.video.test/action'}]),calls)
 def test_native_request_remembers_sidebar_origin_and_page(self):
  s,calls=self.controller();s.active_page='action';s.section='Movies'
  s.activate_navigation({'id':'music-link','destination':{'kind':'kodi','window':'music'}})
  self.assertEqual(s.core_settings_request['target'],'music');self.assertEqual(s.core_settings_request['origin'],'sidebar');self.assertEqual(s.core_settings_request['active_page'],'action');self.assertEqual(s.core_settings_request['navigation_id'],'music-link');self.assertIn(('finish',),calls)
 def test_missing_addon_does_not_close_or_erase_configuration(self):
  s,calls=self.controller(False);before=s.config.copy()
  s.activate_navigation({'id':'gone','destination':{'kind':'addon','path':'plugin://plugin.video.missing/'}})
  self.assertTrue(any(c[0]=='unavailable' for c in calls));self.assertNotIn(('finish',),calls);self.assertEqual(s.config,before)
 def test_edit_loop_persists_reorder_and_visibility(self):
  choices=iter([2,3,1,5,-1]);saved=[];d=SimpleNamespace(select=lambda *a,**k:next(choices))
  ns=methods(['sidebar_settings'],{'xbmcgui':SimpleNamespace(Dialog=lambda:d),'edit_navigation':edit_navigation,'ICON_CHOICES':ICON_CHOICES,'event':lambda *a,**k:None})
  self.assertIn('sidebar_settings',ns,'Sidebar editor is not implemented')
  s=SimpleNamespace(alive=True,config=self.fixture(),save=lambda:saved.append(True),refresh_navigation=lambda:None)
  original=s.config;ns['sidebar_settings'](s);self.assertIs(s.config,original,'The open settings hub must retain the same preference object')
  self.assertEqual([e['id'] for e in s.config['Sidebar']],['home','movies','shows','saved']);self.assertFalse(s.config['Sidebar'][1]['enabled']);self.assertEqual(len(saved),2)
 def test_icon_grid_result_is_saved_to_the_original_shortcut(self):
  choices=iter([2,2,-1]);picked=[];saved=[]
  def choose(current):picked.append(current);return 'bookmark'
  ns=methods(['sidebar_settings'],{'choose_icon':choose,'xbmcgui':SimpleNamespace(Dialog=lambda:SimpleNamespace(select=lambda *a,**k:next(choices))),'edit_navigation':edit_navigation,'event':lambda *a,**k:None})
  s=SimpleNamespace(alive=True,config=self.fixture(),save=lambda:saved.append(True),refresh_navigation=lambda:None)
  ns['sidebar_settings'](s)
  self.assertEqual(picked,['movies']);self.assertEqual(s.config['Sidebar'][2]['id'],'movies')
  self.assertEqual(s.config['Sidebar'][2]['icon'],'bookmark');self.assertEqual(saved,[True])
 def test_cancelled_icon_grid_does_not_save_or_change_preferences(self):
  from copy import deepcopy
  choices=iter([2,2,-1]);saved=[]
  ns=methods(['sidebar_settings'],{'choose_icon':lambda current:None,'xbmcgui':SimpleNamespace(Dialog=lambda:SimpleNamespace(select=lambda *a,**k:next(choices))),'edit_navigation':edit_navigation,'event':lambda *a,**k:None})
  s=SimpleNamespace(alive=True,config=self.fixture(),save=lambda:saved.append(True),refresh_navigation=lambda:None)
  before=deepcopy(s.config);ns['sidebar_settings'](s)
  self.assertEqual(s.config,before);self.assertEqual(saved,[])
 def test_status_toggle_only_changes_display_and_persists(self):
  picks=iter([0,2,-1]);saved=[];props={}
  ns=methods(['status_options','apply_status'],{'status_settings':status_settings,'xbmcgui':SimpleNamespace(Dialog=lambda:SimpleNamespace(select=lambda *a,**k:next(picks)))})
  self.assertIn('status_options',ns,'Status options are not implemented');self.assertIn('apply_status',ns)
  s=SimpleNamespace(alive=True,config=self.fixture(),save=lambda:saved.append(True),setProperty=lambda k,v:props.update({k:v}))
  s.apply_status=MethodType(ns['apply_status'],s);ns['status_options'](s)
  self.assertEqual(s.config['Saved'],[{'file':'retained'}]);self.assertEqual(props,{'showClock':'false','showDate':'false','showWeather':'true'});self.assertEqual(len(saved),2)
 def test_sidebar_return_restores_selected_menu_after_content_load(self):
  ns=methods(['restore_sidebar_focus'],{'event':lambda *a,**k:None});self.assertTrue('restore_sidebar_focus' in ns,'Sidebar return focus is not implemented')
  calls=[];s=SimpleNamespace(pending_sidebar_return=True,window_ready=[True,False],navigation_items=[{'id':'music'}],set_nav=lambda v,**kw:calls.append(('nav',v)),setFocusId=lambda v:calls.append(('focus',v)))
  ns['restore_sidebar_focus'](s);self.assertEqual(calls,[])
  s.window_ready=[True,True];ns['restore_sidebar_focus'](s)
  self.assertEqual(calls,[('nav',True),('focus',50)]);self.assertFalse(s.pending_sidebar_return)
 def test_installed_addon_picker_produces_typed_youtube_destination(self):
  choices=iter([2,1,0]);dialog=SimpleNamespace(select=lambda *a,**k:next(choices))
  ns=methods(['choose_destination'],{'default_icon':default_icon,'xbmcgui':SimpleNamespace(Dialog=lambda:dialog),'SECTIONS':SECTIONS,'KODI_DESTINATIONS':KODI_DESTINATIONS,'rpc':lambda *a,**k:{'result':{'addons':[{'addonid':'plugin.video.youtube','name':'YouTube','enabled':True},{'addonid':'plugin.video.umbrella','name':'Umbrella','enabled':True},{'addonid':'plugin.video.disabled','name':'Disabled','enabled':False}]}}})
  self.assertTrue('choose_destination' in ns,'Installed add-on picker is missing')
  result=ns['choose_destination'](SimpleNamespace(config=self.fixture()))
  self.assertEqual(result,{'label':'YouTube','icon':'youtube','destination':{'kind':'addon','path':'plugin://plugin.video.youtube/'}})
