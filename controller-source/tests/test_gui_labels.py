"""Worker label reads must use Kodi GUI message dispatch, not native pointers."""
import ast
from pathlib import Path
import threading
import unittest
SOURCE=Path(__file__).parents[1]/'addon/live_review.py'
class GuiLabels(unittest.TestCase):
 def function(self,rpc):
  nodes=[n for n in ast.parse(SOURCE.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='gui_labels']
  self.assertEqual(len(nodes),1,'The worker label reader must marshal through JSON-RPC')
  scope={'rpc':rpc};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SOURCE),'exec'),scope);return scope['gui_labels']
 def test_background_read_is_one_gui_dispatch_and_retains_exact_keys(self):
  keys=['System.ScreenWidth','System.ScreenHeight'];calls=[];out=[]
  def rpc(method,params):
   calls.append((method,params,threading.current_thread().name));return {'result':{keys[0]:'3840',keys[1]:'2160'}}
  read=self.function(rpc);t=threading.Thread(target=lambda:out.append(read(keys)),name='page-worker');t.start();t.join(2)
  self.assertEqual(out,[{keys[0]:'3840',keys[1]:'2160'}]);self.assertEqual(calls,[('XBMC.GetInfoLabels',{'labels':keys},'page-worker')])
 def test_missing_label_retains_empty_string_semantics(self):
  self.assertEqual(self.function(lambda *a:{'result':{}})(['unknown']),{'unknown':''})
 def test_rpc_error_is_not_reported_as_valid_gui_state(self):
  read=self.function(lambda *a:{'error':{'message':'unavailable'}})
  with self.assertRaises(RuntimeError):read(['System.CurrentControlId'])
 def test_live_workers_do_not_read_native_gui_label_pointers(self):
  tree=ast.parse(SOURCE.read_text());calls=[n.lineno for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='xbmc' and n.func.attr=='getInfoLabel']
  self.assertEqual(calls,[],'Background label reads must be dispatched to the GUI thread')
 def test_cancel_during_decoder_read_cannot_reframe_another_player(self):
  from types import SimpleNamespace
  calls=[]
  w=SimpleNamespace(preview_generation=3,owned_preview=True,preview_dispatch_lock=threading.RLock(),preview_bar_context=(3,True,1.77,{'zoom':1},'key'),player=SimpleNamespace(isPlayingVideo=lambda:True),preview_framing_cache=SimpleNamespace(put=lambda *a:calls.append('cache')))
  def read(labels):w.preview_generation+=1;w.owned_preview=False;return {labels[0]:'amc-hevc'}
  cls=next(n for n in ast.parse(SOURCE.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='LiveReview');node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='apply_preview_bar_alignment')
  scope={'gui_labels':read,'top_aligned_viewmode':lambda *a,**k:{'verticalshift':-1},'rpc':lambda *a:calls.append(a) or {'result':'OK'},'event':lambda *a,**k:calls.append('event')};exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),scope)
  scope['apply_preview_bar_alignment'](w,.03)
  self.assertEqual(calls,[],'Cancelled decoder response must not alter playback or cache framing')
 def test_focus_dispatch_does_not_refocus_an_obsolete_row(self):
  from types import SimpleNamespace
  from test_discovery_controller import DiscoveryController
  w,calls,controls=DiscoveryController().state();focused=[]
  w.setFocusId=focused.append
  reads=[]
  def label(key):reads.append(key);w.generation+=1;return '900'
  w.set_rows.__func__.__globals__['xbmc']=SimpleNamespace(getInfoLabel=label)
  w.set_rows([{'label':'Movies','path':'plugin://plugin.video.test/movies'}])
  self.assertEqual(reads,['System.CurrentControlId'],'The fixture must cancel during the GUI wait')
  self.assertEqual(focused,[900],'Only the initial focus before the GUI wait is valid')
  self.assertTrue(w.rows[0],'Successful row publication must not become an exception')
if __name__=='__main__':unittest.main()
