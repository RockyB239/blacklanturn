import ast,unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]/'compatibility/addons139/patched'
def function(path,name,cls=None):
 nodes=ast.parse(path.read_text()).body
 if cls:nodes=next(n for n in nodes if isinstance(n,ast.ClassDef) and n.name==cls).body
 node=next(n for n in nodes if isinstance(n,ast.FunctionDef) and n.name==name)
 ns={};exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),ns);return ns[name]
class Playback139(unittest.TestCase):
 def due(self,position,total,credits,remaining=59):
  path=ROOT/'plugin.video.umbrella/resources/lib/modules/player.py'
  return function(path,'_credits_prompt_due')(position,total,credits,remaining,60)
 def test_marker_after_selected_file_cannot_disable_last_minute_fallback(self):
  self.assertTrue(self.due(2141,2200,2297.45))
  self.assertFalse(self.due(2000,2200,2297.45,200))
 def test_reachable_marker_retains_credits_timing(self):
  self.assertFalse(self.due(2280,2460,2297.45,180));self.assertTrue(self.due(2298,2460,2297.45,162))
 def test_absent_or_nonfinite_marker_falls_back_without_network_work(self):
  for value in (None,float('nan'),float('inf'),'invalid'):
   with self.subTest(value=value):self.assertTrue(self.due(2401,2460,value))
 def test_eof_or_invalid_duration_cannot_prompt(self):
  self.assertFalse(self.due(2460,2460,None,0));self.assertFalse(self.due(0,0,None,0))
 def test_native_integer_episode_identifiers_do_not_break_end_callback_rating(self):
  f=function(ROOT/'plugin.video.themoviedb.helper/resources/tmdbhelper/lib/script/sync/item.py','get_item_id','ItemSync')
  for values,want in [(('285322',1,5),'285322.1.5'),((285322,1,6),'285322.1.6'),(('285322',None,None),'285322')]:
   with self.subTest(values=values):self.assertEqual(f(SimpleNamespace(tmdb_id=values[0],season=values[1],episode=values[2])),want)
if __name__=='__main__':unittest.main()
