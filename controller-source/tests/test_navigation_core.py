import importlib.util,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
SPEC=importlib.util.find_spec('navigation_core')
if SPEC:
 from navigation_core import migrate_navigation,visible_navigation,resolve_destination,edit_navigation,status_settings

@unittest.skipUnless(SPEC,'navigation model not implemented')
class NavigationCore(unittest.TestCase):
 def fixture(self):
  return {'Saved':[{'file':'private'}],'PreviewDelay':5,'RatingSources':['imdb','metacritic'],'Genres':[{'id':'action-id','label':'Action','section':'Movies','rows':[{'label':'Top action','path':'plugin://plugin.video.test/action'}]}]}
 def test_defaults_preserve_content_and_migrate_idempotently(self):
  source=self.fixture();actual=migrate_navigation(source)
  self.assertNotIn('Sidebar',source)
  for key in source:self.assertEqual(actual[key],source[key])
  self.assertEqual([x['label'] for x in visible_navigation(actual)],['Home','Shows','Movies','My Stuff'])
  self.assertEqual(migrate_navigation(actual),actual)
 def test_reorder_hide_show_and_remove_keep_stable_destinations(self):
  c=migrate_navigation(self.fixture());c=edit_navigation(c,'movies','up')
  self.assertEqual([x['id'] for x in visible_navigation(c)],['home','movies','shows','saved'])
  c=edit_navigation(c,'movies','toggle');self.assertEqual(len(visible_navigation(c)),3)
  c=edit_navigation(c,'movies','toggle');c=edit_navigation(c,'movies','rename','Cinema')
  self.assertEqual(resolve_destination(c['Sidebar'][1]['destination'],c),{'kind':'section','section':'Movies'})
  c=edit_navigation(c,'movies','remove');self.assertEqual(len(c['Sidebar']),3)
 def test_page_reference_follows_rename_and_missing_page_is_unavailable(self):
  c=self.fixture();c['Genres'][0]['label']='Action movies'
  route=resolve_destination({'kind':'page','page_id':'action-id'},c)
  self.assertEqual(route['label'],'Action movies');self.assertEqual(route['rows'][0]['path'],'plugin://plugin.video.test/action')
  self.assertIsNone(resolve_destination({'kind':'page','page_id':'deleted'},c))
 def test_add_rejects_duplicate_ids_and_unsafe_destination(self):
  c=migrate_navigation(self.fixture())
  item={'id':'yt','label':'YouTube','icon':'tv','destination':{'kind':'addon','path':'plugin://plugin.video.youtube/'},'enabled':True}
  c=edit_navigation(c,'','add',item);self.assertEqual(visible_navigation(c)[-1]['id'],'yt')
  with self.assertRaises(ValueError):edit_navigation(c,'','add',item)
  for bad in ({'kind':'kodi','window':'RunScript(evil)'},{'kind':'addon','path':'https://evil/'},{'kind':'addon','path':'plugin://x/",Quit()'},{'kind':'section','section':'Unknown'}):
   self.assertIsNone(resolve_destination(bad,c))
 def test_long_menu_keeps_all_entries_and_explicit_false_status(self):
  c=migrate_navigation(self.fixture())
  for i in range(12):c=edit_navigation(c,'','add',{'id':str(i),'label':str(i),'icon':'bookmark','destination':{'kind':'kodi','window':'music'}})
  self.assertEqual(len(visible_navigation(c)),16)
  c['StatusDisplay']={'clock':False,'date':True,'weather':False}
  self.assertEqual(status_settings(c),{'clock':False,'date':True,'weather':False})
 def test_unknown_icon_falls_back_without_erasing_saved_entry(self):
  c=migrate_navigation(self.fixture());c['Sidebar'][0]['icon']='missing'
  self.assertEqual(visible_navigation(c)[0]['icon'],'bookmark');self.assertEqual(c['Sidebar'][0]['icon'],'missing')
 def test_branded_genre_and_kodi_icons_can_be_saved(self):
  c=migrate_navigation(self.fixture())
  for icon in ('music','sports','action','comedy','video-addons','program-addons','my-stuff','stand-up','adventure-mountains','adventure-backpack','warning','creature-features'):
   c=edit_navigation(c,'home','icon',icon)
   self.assertEqual(visible_navigation(c)[0]['icon'],icon)
 def test_rejected_icons_are_retired_without_erasing_existing_assignments(self):
  from navigation_core import ICON_CHOICES
  for rejected in ('western-horse','western-tumbleweed','crime'):
   self.assertNotIn(rejected,dict(ICON_CHOICES))
   c=migrate_navigation(self.fixture());c['Sidebar'][0]['icon']=rejected
   self.assertEqual(visible_navigation(c)[0]['icon'],rejected)
 def test_new_shortcuts_get_matching_icons_with_safe_fallback(self):
  import navigation_core as nav
  self.assertTrue(hasattr(nav,'default_icon'))
  self.assertEqual(nav.default_icon('Music',{'kind':'kodi','window':'music'}),'music')
  self.assertEqual(nav.default_icon('Science Fiction',{'kind':'page','page_id':'scifi'}),'science-fiction')
  self.assertEqual(nav.default_icon('YouTube',{'kind':'addon','path':'plugin://plugin.video.youtube/'}),'youtube')
  self.assertEqual(nav.default_icon('Custom source',{'kind':'addon','path':'plugin://plugin.video.custom/'}),'video-addons')
 def test_all_selectable_icons_have_transparent_native_assets(self):
  from navigation_core import ICON_CHOICES
  from PIL import Image
  for icon,label in ICON_CHOICES:
   p=Path(__file__).parents[1]/'addon/resources/media'/(icon+'.png')
   self.assertTrue(p.exists(),label+' asset is missing')
   with Image.open(p) as im:
    self.assertEqual(im.mode,'RGBA',label+' must have transparency')

