import ast,types,unittest
from test_session_sources import ROOT,p
from test_dispatch import Window
class SessionStop(unittest.TestCase):
 def stop(self,transition):
  path=ROOT/'candidate/resources/lib/modules/player.py';tree=ast.parse(path.read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Player');fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='onPlayBackStopped')
  window=Window();window.setProperty(p.SESSION_PROPERTY,'chosen');window.setProperty('umbrella.playnext.transition','true' if transition else 'false')
  ns={'playerWindow':window,'homeWindow':Window(),'clear_local_bookmarks':lambda:None,'control':types.SimpleNamespace(playlist=types.SimpleNamespace(getposition=lambda:0,size=lambda:2,clear=lambda:None)),'log_utils':types.SimpleNamespace(error=lambda:None)}
  exec(compile(ast.Module(body=[fn],type_ignores=[]),str(path),'exec'),ns)
  ns['onPlayBackStopped'](types.SimpleNamespace(onPlayBackStopped_ran=True,scrobble_sent=True))
  return window.getProperty(p.SESSION_PROPERTY)
 def test_explicit_stop_retires_the_viewing_session(self):self.assertEqual(self.stop(False),'')
 def test_real_next_episode_transition_retains_the_viewing_session(self):self.assertEqual(self.stop(True),'chosen')
