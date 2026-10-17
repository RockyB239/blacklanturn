from urllib.parse import parse_qs,urlsplit
import sys,unittest,importlib.util,ast,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from live_core import card_artwork

class AddonCatalogue(unittest.TestCase):
 def test_enabled_addons_keep_square_icons_and_exact_launch_identity(self):
  self.assertIsNotNone(importlib.util.find_spec('addon_catalog'),'Installed add-on shelves are missing')
  import addon_catalog
  items=addon_catalog.catalogue_items([
   {'addonid':'plugin.video.example','name':'Video example','enabled':True,'thumbnail':'square.png','fanart':'wide.jpg','description':'Example description'},
   {'addonid':'plugin.video.disabled','name':'Disabled','enabled':False},
   {'addonid':'plugin.video.bad\"id','name':'Unsafe','enabled':True}], 'video')
  self.assertEqual(len(items),1)
  self.assertEqual(items[0]['addonid'],'plugin.video.example')
  self.assertEqual(items[0]['file'],'plugin://plugin.video.example/')
  self.assertEqual(card_artwork(items[0]),{'image':'square.png','kind':'square'})
  self.assertEqual(items[0]['plot'],'Example description')
 def test_program_scripts_and_plugin_programs_use_distinct_launch_methods(self):
  self.assertIsNotNone(importlib.util.find_spec('addon_catalog'),'Installed add-on shelves are missing')
  import addon_catalog
  items=addon_catalog.catalogue_items([
   {'addonid':'script.example','name':'Script','enabled':True,'type':'xbmc.python.script','thumbnail':'s.png'},
   {'addonid':'plugin.program.example','name':'Program','enabled':True,'type':'xbmc.python.pluginsource','thumbnail':'p.png'}],'program')
  by_id={x['addonid']:x for x in items}
  self.assertEqual(by_id['script.example']['launch_kind'],'script')
  self.assertEqual(by_id['plugin.program.example']['launch_kind'],'plugin')
 def test_empty_installed_list_has_no_placeholder_launchers(self):
  self.assertIsNotNone(importlib.util.find_spec('addon_catalog'),'Installed add-on shelves are missing')
  import addon_catalog
  self.assertEqual(addon_catalog.catalogue_items([], 'video'),[])
 def test_installed_shelf_excludes_repositories_and_skin_resources_at_api_boundary(self):
  import addon_catalog
  from live_core import valid_source
  path=Path(__file__).parents[1]/'addon/live_review.py'
  node=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='get_list')
  def rpc(method,params):
   self.assertEqual(method,'Addons.GetAddons')
   items=[{'addonid':'plugin.video.example','name':'Video','enabled':True,'type':'xbmc.python.pluginsource'}]
   if params.get('type')!='xbmc.addon.video':items.append({'addonid':'repository.example','name':'Repository','enabled':True,'type':'xbmc.addon.repository'})
   return {'result':{'addons':items}}
  ns={'valid_source':valid_source,'time':time,'rpc':rpc,'catalogue_items':addon_catalog.catalogue_items,'catalogue_category':addon_catalog.catalogue_category}
  exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),ns)
  ns.update(parse_qs=parse_qs,urlsplit=urlsplit)
  result=ns['get_list']('plugin://script.blacklanturn.preview/?info=installed_addons&category=video')
  self.assertEqual([item['addonid'] for item in result],['plugin.video.example'])

if __name__=='__main__':unittest.main()
