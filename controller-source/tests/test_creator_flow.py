import sys,unittest,time
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).parent))
from test_discovery_controller import methods

class CreatorFlow(unittest.TestCase):
 def test_selector_blocks_home_preview_monitor_until_cancel(self):
  state=SimpleNamespace(actions_open=False)
  def select(*args):
   self.assertTrue(state.actions_open,'Creator selector must hold the same preview/input guard as title actions')
   return -1
  ns=methods(['discover_more'],{'time':time,'xbmcgui':SimpleNamespace(Dialog=lambda:SimpleNamespace(select=select)),'event':lambda *a,**k:None})
  ns['discover_more'](state,{'title':'Title'})
  self.assertFalse(state.actions_open)

if __name__=='__main__':unittest.main()
