import ast
from pathlib import Path
from types import SimpleNamespace,MethodType
import sys,unittest
ROOT=Path(__file__).parents[1]/'addon'
sys.path.insert(0,str(ROOT))
from navigation_core import ICON_CHOICES

class IconPickerTests(unittest.TestCase):
 def picker(self,current):
  path=ROOT/'icon_picker.py';self.assertTrue(path.exists(),'The graphical picker has not been implemented')
  cls=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='IconPicker')
  class Item:
   def __init__(self,label):self.label=label;self.art={}
   def setArt(self,art):self.art.update(art)
  ns={'ROOT':ROOT,'ICON_CHOICES':ICON_CHOICES,'xbmcgui':SimpleNamespace(ListItem=Item)}
  exec(compile(ast.Module(body=[m for m in cls.body if isinstance(m,ast.FunctionDef)],type_ignores=[]),'icon_picker','exec'),ns)
  state=SimpleNamespace(current_icon=current,choices=ICON_CHOICES,items=[],position=0,result=None,closed=False)
  control=SimpleNamespace(reset=lambda:state.items.clear(),addItems=lambda items:state.items.extend(items),selectItem=lambda p:setattr(state,'position',p),getSelectedPosition=lambda:state.position)
  state.getControl=lambda cid:control;state.setFocusId=lambda cid:setattr(state,'focus',cid);state.close=lambda:setattr(state,'closed',True)
  for name in ('onInit','onClick','onAction'):setattr(state,name,MethodType(ns[name],state))
  state.onInit();return state
 def test_preselection_and_selection_return_stable_ids_with_real_asset_paths(self):
  p=self.picker('creature-features');self.assertEqual(p.position,[n for n,_ in ICON_CHOICES].index('creature-features'))
  for item,(icon,label) in zip(p.items,ICON_CHOICES):
   self.assertEqual(item.label,label);self.assertTrue(Path(item.art['icon']).is_file())
  p.position=[n for n,_ in ICON_CHOICES].index('thriller');p.onClick(5000)
  self.assertEqual(p.result,'thriller');self.assertTrue(p.closed)
 def test_back_and_cancel_leave_selection_empty(self):
  for action in ('back','cancel'):
   p=self.picker('home')
   if action=='back':p.onAction(SimpleNamespace(getId=lambda:92))
   else:p.onClick(5001)
   self.assertIsNone(p.result);self.assertTrue(p.closed)
