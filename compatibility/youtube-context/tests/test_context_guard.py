"""Exercise the actual upstream/candidate method, without importing Kodi's UI."""
import ast,unittest
from pathlib import Path
from types import MethodType,SimpleNamespace
ROOT=Path(__file__).parents[1]
def method(file):
 cls=next(n for n in ast.parse(file.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='XbmcContext')
 nodes=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in ('is_plugin_path','is_plugin_folder')]
 ns={'XbmcContextUI':SimpleNamespace(get_container_info=lambda _:False),'FOLDER_URI':'uri','FOLDER_NAME':'name'};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(file),'exec'),ns)
 owner=SimpleNamespace(create_uri=lambda path:'plugin://plugin.video.youtube/'+path.lstrip('/'),_plugin_name='plugin.video.youtube')
 for n in nodes:setattr(owner,n.name,MethodType(ns[n.name],owner))
 return owner
class Guard(unittest.TestCase):
 def setUp(self):self.c=method(ROOT/'candidate/xbmc_context.py')
 def test_upstream_reproduces_reported_boolean_failure(self):
  with self.assertRaises(AttributeError):method(ROOT/'upstream/xbmc_context.py').is_plugin_folder()
 def test_absent_kodi_plugin_folder_is_false(self):self.assertIs(self.c.is_plugin_folder(),False)
 def test_non_text_values_are_not_plugin_paths(self):
  for value in (None,False,True,0,1,[],{}):
   with self.subTest(type=type(value).__name__):self.assertIs(self.c.is_plugin_path(value),False)
 def test_matching_plugin_paths_still_match(self):
  for value in ('plugin://plugin.video.youtube/','plugin://plugin.video.youtube/?refresh=true'):
   self.assertIs(self.c.is_plugin_path(value),True)
 def test_other_and_empty_paths_do_not_match(self):
  for value in ('','plugin://other/','/local/file','https://youtube.com/'):
   self.assertIs(self.c.is_plugin_path(value),False)
 def test_multiple_and_partial_route_matching_still_work(self):
  self.assertTrue(self.c.is_plugin_path('plugin://plugin.video.youtube/videos/item',('videos','channels'),partial=True));self.assertFalse(self.c.is_plugin_path('plugin://other/videos',('videos','channels'),partial=True));self.assertTrue(self.c.is_plugin_path('plugin://plugin.video.youtube/videos/',('videos','channels')))
 def test_non_text_never_builds_plugin_uri(self):
  self.c.create_uri=lambda _:(_ for _ in ()).throw(RuntimeError('Should not be called'))
  self.assertFalse(self.c.is_plugin_path(False))
if __name__=='__main__':unittest.main()
