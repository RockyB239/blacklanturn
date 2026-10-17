import ast,sys,unittest
from pathlib import Path
from types import SimpleNamespace,MethodType
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from backend_core import SETTINGS_GROUPS
class BackendSelection(unittest.TestCase):
 def state(self):
  cls=next(n for n in ast.parse((Path(__file__).parents[1]/'addon/backend_ui.py').read_text()).body if isinstance(n,ast.ClassDef) and n.name=='BackendSettings')
  ns={'SETTINGS_GROUPS':SETTINGS_GROUPS};exec(compile(ast.Module(body=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in ('onFocus','onClick')],type_ignores=[]),'backend_ui','exec'),ns)
  calls=[];s=SimpleNamespace(category=0,row=0,result=None,getControl=lambda c:SimpleNamespace(getSelectedPosition=lambda:4 if c==100 else 0,selectItem=lambda i:None),close=lambda:calls.append('closed'),setFocusId=lambda c:None,handler=lambda a:calls.append(a))
  def populate(index):s.category=index;calls.append(('populated',index))
  s.populate=populate
  for name in ('onFocus','onClick'):setattr(s,name,MethodType(ns[name],s))
  return s,calls
 def test_entering_options_syncs_to_highlighted_category(self):
  s,c=self.state();s.onFocus(200);self.assertEqual(s.category,4)
 def test_click_routes_to_current_category_even_if_previous_callback_lagged(self):
  s,c=self.state();s.onClick(200);self.assertEqual(s.result,'kodi:settings');self.assertIn('closed',c);self.assertNotIn('rows',c)
