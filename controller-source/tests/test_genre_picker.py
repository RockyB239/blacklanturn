"""Native genre choice preserves configured page IDs, cancellation and return state."""
import ast,sys,unittest
from pathlib import Path
from types import SimpleNamespace,MethodType
from test_discovery_controller import methods,Control
from discovery_core import collection_pages,page_rows
ROOT=Path(__file__).parents[1]/'addon'
class Control(Control):
 def getListItem(self,index):return self.items[index]
class Item:
 def __init__(self,label):self.label=label;self.props={};self.art={}
 def setProperty(self,key,value):self.props[key]=value
 def setArt(self,art):self.art.update(art)
 def setLabel(self,label):self.label=label
class GenrePickerTests(unittest.TestCase):
 def picker(self):
  source=ROOT/'genre_picker.py';self.assertTrue(source.exists(),'Native genre picker is missing')
  cls=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.ClassDef))
  from navigation_core import default_icon
  ns={'ROOT':ROOT,'default_icon':default_icon,'xbmcgui':SimpleNamespace(ListItem=Item)}
  exec(compile(ast.Module(body=[n for n in cls.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'genre-picker','exec'),ns)
  panel=Control();s=SimpleNamespace(section='Shows',pages=[{'id':'h','label':'Horror'},{'id':'s','label':'Stand-up'}],current_page='s',result=None,closed=False,getControl=lambda _:panel,setFocusId=lambda _:None,close=lambda:None)
  for name in ('onInit','onClick','onAction'):setattr(s,name,MethodType(ns[name],s))
  s.setProperty=lambda *a:None;s.onInit();return s,panel
 def test_picker_preselects_id_displays_labels_and_returns_stable_page(self):
  s,p=self.picker();self.assertEqual(p.pos,2);self.assertEqual([i.label for i in p.items],['All','Horror','Stand-up'])
  for i in p.items:self.assertTrue(Path(i.art['icon']).is_file())
  p.selectItem(1);s.onClick(5000);self.assertEqual(s.result,'h')
  p.selectItem(0);s.onClick(5000);self.assertEqual(s.result,'')
 def test_back_returns_no_selection(self):
  s,p=self.picker();s.onAction(SimpleNamespace(getId=lambda:92));self.assertIsNone(s.result)
class GenreControllerTests(unittest.TestCase):
 def state(self,result='h'):
  controls={600:Control(),900:Control()};props={};calls=[]
  cfg={'Movies':[{'label':'All','path':'plugin://plugin.video.test/all'}],'Genres':[{'id':'h','label':'Horror','section':'Movies','rows':[{'label':'Slashers','path':'plugin://plugin.video.test/slashers'}]}],'Categories':[]}
  ns=methods(['load_browse_sources','browse_source'],{'collection_pages':collection_pages,'page_rows':page_rows,'xbmcgui':SimpleNamespace(ListItem=Item),'choose_genre':lambda *a:result,'event':lambda *a,**k:None})
  s=SimpleNamespace(section='Movies',config=cfg,active_page='h',browse_sources=[],search_state=None,actions_open=False,getControl=lambda i:controls[i],setProperty=lambda k,v:props.__setitem__(k,v),getProperty=lambda k:props.get(k,''),setFocusId=lambda i:calls.append(('focus',i)),set_rows=lambda r:calls.append(('rows',r)),stop_preview=lambda:calls.append(('stop',)),load_section=lambda:calls.append(('all',)),page_definitions=[])
  for name in ('load_browse_sources','browse_source'):setattr(s,name,MethodType(ns[name],s))
  s.load_browse_sources();return s,controls,calls
 def test_movies_uses_one_genre_control_and_rebuilds_selection_on_return(self):
  s,c,_=self.state();self.assertEqual(len(c[600].items),1);self.assertIn('Horror',c[600].items[0].label)
  self.assertEqual(c[600].items[0].props.get('genreChooser'),'true')
  self.assertEqual(c[600].pos,0);self.assertEqual(s.getProperty('genreChooser'),'true')
 def test_picker_selected_page_loads_its_configured_rows(self):
  s,c,calls=self.state();s.browse_source();self.assertEqual(s.active_page,'h');self.assertIn(('rows',s.config['Genres'][0]['rows']),calls);self.assertFalse(s.actions_open)
 def test_cancel_retains_current_page_and_rows(self):
  s,c,calls=self.state(None);s.browse_source();self.assertEqual(s.active_page,'h');self.assertFalse(any(x[0] in ('rows','all') for x in calls));self.assertFalse(s.actions_open)
 def test_all_returns_to_section_landing_rows(self):
  s,c,calls=self.state('');s.browse_source();self.assertIn(('all',),calls)
 def test_addons_keep_video_and_program_category_strip(self):
  s,c,calls=self.state();s.section='Add-ons';s.config['Add-ons']=[{'label':'Video add-ons','path':'plugin://plugin.video.test/video'},{'label':'Program add-ons','path':'plugin://plugin.video.test/program'}]
  s.load_browse_sources();self.assertEqual([i.label for i in c[600].items],['All','Video add-ons','Program add-ons'])
  self.assertNotIn('genreChooser',c[600].items[0].props);self.assertEqual(s.getProperty('genreChooser'),'false')
if __name__=='__main__':unittest.main()
