"""The selected installed pack follows menus and cached category cards offline."""
import copy,importlib.util,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=(Path(__file__).parents[1]/'addon').resolve();sys.path.insert(0,str(ROOT))
import icon_packs
from youtube_folder_artwork import display_items
from youtube_rows import YouTubeRows
class Item:
 def __init__(self,label='',label2='',**kwargs):self.label=label;self.art={}
 def setArt(self,art):self.art.update(art)
class Control:
 def __init__(self):self.items=[];self.position=0
 def addItems(self,items):self.items.extend(items)
 def reset(self):self.items=[]
 def selectItem(self,n):self.position=n
 def getSelectedPosition(self):return self.position
class Dialog:
 def __init__(self,*args):self.controls={100:Control(),200:Control(),5000:Control()};self.props={}
 def getControl(self,cid):return self.controls[cid]
 def setProperty(self,key,value):self.props[key]=value
 def setFocusId(self,cid):self.focus=cid

def load(name):
 spec=importlib.util.spec_from_file_location('art134_'+name,ROOT/(name+'.py'));mod=importlib.util.module_from_spec(spec)
 with patch.dict(sys.modules,{'xbmcgui':types.SimpleNamespace(WindowXMLDialog=Dialog,ListItem=Item)}):spec.loader.exec_module(mod)
 return mod
class SelectedMenus(unittest.TestCase):
 def setUp(self):icon_packs.configure([]);self.addCleanup(icon_packs.configure,[])
 def test_genre_grid_uses_selected_pack_and_missing_assets_keep_fallback(self):
  # A direct resources/media path makes the silver/glass choices indistinguishable.
  mod=load('genre_picker')
  for pack in ('sculpted-silver','smoked-glass','original'):
   s=mod.GenrePicker();s.section='Movies';s.pages=[{'id':'h','label':'Horror'}];s.current_page='h';s.pack=pack;s.onInit()
   suffix='resources/media' if pack=='original' else 'resources/icon-packs/packs/'+pack
   self.assertEqual(s.controls[5000].items[1].art['icon'],str(ROOT/suffix/'horror.png'))
  icon_packs._assets['smoked-glass'].pop('horror');s.pack='smoked-glass';s.onInit();self.assertEqual(s.controls[5000].items[1].art['icon'],str(ROOT/'resources/media/horror.png'))
 def test_backend_categories_options_and_header_share_pack(self):
  # Supplying art only to the sidebar leaves backend menus with another style.
  mod=load('backend_ui')
  for pack in ('sculpted-silver','smoked-glass'):
   s=mod.BackendSettings();s.config={'IconPack':pack};s.preview_mode='manual';s.category=0;s.row=0;s.onInit()
   for item in s.controls[100].items+s.controls[200].items:
    self.assertIn('/'+pack+'/',item.art.get('icon',''));self.assertTrue(Path(item.art['icon']).is_file())
   for category in range(len(mod.SETTINGS_GROUPS)):
    s.populate(category)
    self.assertIn('/'+pack+'/',s.props.get('sectionIcon',''))
    self.assertTrue(all('/'+pack+'/' in x.art.get('icon','') and Path(x.art['icon']).is_file() for x in s.controls[200].items))
 def state(self,pack):
  path='plugin://plugin.video.youtube/special/my_subscriptions'
  return types.SimpleNamespace(section='YouTube',paths=[path],page_definitions=[{'path':path}],config={'IconPack':pack})
 def folder(self):return {'file':'plugin://plugin.video.youtube/special/my_subscriptions/shorts/','filetype':'directory','label':'Shorts','art':{'thumb':'original-provider.png','fanart':'original-fanart.jpg'}}
 def test_finite_cached_rows_redecorate_without_contaminating_raw_cache(self):
  # A completed row must not store its previous theme as source art.
  original=self.folder();state=self.state('sculpted-silver')
  with patch('youtube_rows._fetch_feed',side_effect=AssertionError('provider access')):
   first=YouTubeRows.prepare_youtube_row(state,0,[original]);first[0]['playcount']=1
   state.config['IconPack']='smoked-glass';second=YouTubeRows.prepare_youtube_row(state,0,first)
  self.assertIn('/smoked-glass/',second[0]['art']['thumb']);self.assertEqual(second[0]['playcount'],1)
  self.assertEqual(state.youtube_pages[state.paths[0]]['items'][0]['art'],original['art'])
  self.assertNotIn('_youtube_folder_icon',state.youtube_pages[state.paths[0]]['items'][0]);self.assertEqual(original,self.folder())
 def test_decorated_saved_or_restored_items_roundtrip_to_provider_art_before_cache(self):
  # Restored display records need raw art for later pack changes/fallback.
  original=self.folder();saved=copy.deepcopy(display_items([original],{'IconPack':'sculpted-silver'}));state=self.state('smoked-glass')
  with patch('youtube_rows._fetch_feed',side_effect=AssertionError('provider access')):result=YouTubeRows.prepare_youtube_row(state,0,saved)
  self.assertIn('/smoked-glass/',result[0]['art']['thumb']);self.assertEqual(state.youtube_pages[state.paths[0]]['items'],[original])
if __name__=='__main__':unittest.main()
