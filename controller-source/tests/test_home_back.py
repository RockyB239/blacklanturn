"""Root Back must not drop into the shell's recovery/loading screen."""
import ast,unittest,time
from pathlib import Path
from types import SimpleNamespace
tree=ast.parse((Path(__file__).parents[1]/'addon/live_review.py').read_text())
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LiveReview')
method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='onAction')
ns={"time":time};exec(compile(ast.Module(body=[method],type_ignores=[]),'live_review.py','exec'),ns)
class HomeBack(unittest.TestCase):
 def test_root_back_reveals_navigation_without_closing_the_browser(self):
  state={'closed':False,'nav':False,'focus':900};props={}
  obj=SimpleNamespace(actions_open=False,mode='home',nav=False,last_row=0,histories=[SimpleNamespace(pop=lambda:None)],episode_browser_context=None,person_context=None,discovery_stack=[],search_state=None,active_page=None,
    setProperty=props.__setitem__,stop_preview=lambda:None,finish=lambda:state.update(closed=True),
    set_nav=lambda value,**kw:state.update(nav=value),setFocusId=lambda value:state.update(focus=value))
  ns['onAction'](obj,SimpleNamespace(getId=lambda:92))
  self.assertFalse(state['closed'])
  self.assertTrue(state['nav'])
  self.assertEqual(state['focus'],50)
if __name__=='__main__':unittest.main()
