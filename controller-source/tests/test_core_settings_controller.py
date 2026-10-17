import ast,itertools,os,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
ROOT=Path(__file__).parents[1]
class CoreControllerReturn(unittest.TestCase):
 def test_settings_records_exact_resume_without_relaunching_on_its_callback(self):
  path=Path(os.environ.get('BL_CONTROLLER_SOURCE',str(ROOT/'addon/live_review.py')))
  cls=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='LiveReview')
  method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='settings')
  class Hub:
   def __init__(self,*a):self.result='kodi:PlayerSettings';self.category=4;self.row=1
   def doModal(self):pass
  actions=[];state=SimpleNamespace(alive=True,backend_position=(4,1),backend_focus=200,config={},preview_mode='auto',section='Movies',run_setting=lambda a:None,finish=lambda:actions.append('finish'))
  ns={'ROOT':ROOT/'addon','BackendSettings':Hub,'event':lambda *a,**k:None,'xbmc':SimpleNamespace(executebuiltin=lambda a:actions.append(a))}
  exec(compile(ast.Module(body=[method],type_ignores=[]),str(path),'exec'),ns);ns['settings'](state)
  self.assertEqual(getattr(state,'core_settings_request',None),{'target':'PlayerSettings','category':4,'row':1,'section':'Movies'})
  self.assertEqual(actions,['finish']);self.assertFalse(state.settings_open)
 def test_launcher_waits_for_real_core_return_then_reopens_with_saved_selection(self):
  path=Path(os.environ.get('BL_LAUNCHER_SOURCE',str(ROOT/'addon/default.py')))
  method=next((n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='run_live_review'),None)
  self.assertIsNotNone(method,'Normal launcher must own core-window restoration')
  windows=[];events=[];request={'target':'PlayerSettings','category':4,'row':1,'section':'Movies'}
  class Review:
   def __init__(self,*a):self.core_settings_request=request if not windows else None;windows.append(self)
   def doModal(self):events.append(('modal',self.resume_backend))
  ids=iter([10000,10016,10000]);ticks=itertools.count()
  def window():value=next(ids);events.append(('window',value));return value
  ns={'ROOT':ROOT/'addon','time':SimpleNamespace(monotonic=lambda:next(ticks)),'record':lambda *a,**k:None,'xbmc':SimpleNamespace(getSkinDir=lambda:'skin.blacklanturn.preview',Monitor=lambda:SimpleNamespace(abortRequested=lambda:False),executebuiltin=lambda a:events.append(('activate',a)),sleep=lambda n:None),'xbmcgui':SimpleNamespace(getCurrentWindowId=window,Dialog=lambda:None)}
  exec(compile(ast.Module(body=[method],type_ignores=[]),str(path),'exec'),ns)
  with patch.dict(sys.modules,{'live_review':SimpleNamespace(LiveReview=Review)}):ns['run_live_review']()
  self.assertEqual(len(windows),2);self.assertIsNone(windows[0].resume_backend);self.assertEqual(windows[1].resume_backend,request)
  self.assertGreater(events.index(('modal',request)),events.index(('window',10016)))
  self.assertEqual(sum(e[0]=='activate' for e in events),1)
 def test_launcher_opens_addon_parameters_then_restores_sidebar_origin(self):
  path=ROOT/'addon/default.py';method=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='run_live_review')
  import json
  windows=[];calls=[];request={'target':'videos','parameters':['plugin://plugin.video.youtube/','return'],'category':0,'row':3,'section':'Movies','origin':'sidebar','navigation_id':'youtube','active_page':'action'}
  class Review:
   def __init__(self,*a):self.core_settings_request=request if not windows else None;windows.append(self)
   def doModal(self):pass
  ids=iter([10000,10025,10000]);ticks=itertools.count()
  ns={'json':json,'ROOT':ROOT/'addon','time':SimpleNamespace(monotonic=lambda:next(ticks)),'record':lambda *a,**k:None,'xbmc':SimpleNamespace(getSkinDir=lambda:'skin.blacklanturn.preview',Monitor=lambda:SimpleNamespace(abortRequested=lambda:False),executeJSONRPC=lambda raw:calls.append(json.loads(raw)),executebuiltin=lambda raw:calls.append(raw),sleep=lambda n:None),'xbmcgui':SimpleNamespace(getCurrentWindowId=lambda:next(ids),Dialog=lambda:None)}
  exec(compile(ast.Module(body=[method],type_ignores=[]),str(path),'exec'),ns)
  with patch.dict(sys.modules,{'live_review':SimpleNamespace(LiveReview=Review)}):ns['run_live_review']()
  self.assertEqual(calls,[{'jsonrpc':'2.0','id':1,'method':'GUI.ActivateWindow','params':{'window':'videos','parameters':['plugin://plugin.video.youtube/','return']}}]);self.assertEqual(windows[1].resume_backend,request)
