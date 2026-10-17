import ast,sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from backend_core import SETTINGS_GROUPS
p=Path(__file__).parents[1]/'addon/backend_ui.py'
tree=ast.parse(p.read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='BackendSettings');method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='onClick')
namespace={'SETTINGS_GROUPS':SETTINGS_GROUPS};exec(compile(ast.Module(body=[method],type_ignores=[]),str(p),'exec'),namespace)
class BackendNavigation(unittest.TestCase):
 def state(self,category):
  calls=[];ctrl=SimpleNamespace(getSelectedPosition=lambda:0,selectItem=lambda p:calls.append(('position',p)))
  s=SimpleNamespace(category=category,result=None,getControl=lambda cid:SimpleNamespace(getSelectedPosition=lambda:category) if cid==100 else ctrl,close=lambda:calls.append('close'),handler=lambda a:calls.append(('handler',a)),populate=lambda n:calls.append(('populate',n)),setFocusId=lambda cid:calls.append(('focus',cid)))
  return s,calls
 def test_editor_keeps_branded_hub_open_and_restores_focus(self):
  s,calls=self.state(2);namespace['onClick'](s,200)
  self.assertIn(('handler','ratings'),calls);self.assertNotIn('close',calls);self.assertIn(('focus',200),calls)
 def test_core_kodi_route_closes_hub_without_calling_editor(self):
  s,calls=self.state(4);namespace['onClick'](s,200)
  self.assertEqual(s.result,'kodi:settings');self.assertEqual(calls,['close'])
 def test_sidebar_editor_is_dispatched_after_hub_modal_returns(self):
  s,calls=self.state(0);s.getControl=lambda cid:SimpleNamespace(getSelectedPosition=lambda:0 if cid==100 else 3,selectItem=lambda row:None)
  namespace['onClick'](s,200)
  self.assertEqual(s.result,'sidebar');self.assertEqual(calls,['close'])
 def test_status_editor_is_dispatched_after_hub_modal_returns(self):
  s,calls=self.state(6);namespace['onClick'](s,200)
  self.assertEqual(s.result,'status_display');self.assertEqual(calls,['close'])
