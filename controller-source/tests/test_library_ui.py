import sys,unittest
from types import SimpleNamespace
from unittest.mock import patch
from library_ui import LibraryActions
import personal_library as lib
class Window(LibraryActions):
 def __init__(self,config):self.config=config;self.alive=True;self.actions_open=False;self.saves=0;self.opened=[];self.section='Home';self.search_state=None
 def stop_preview(self):pass
 def save(self,**kw):self.saves+=1
 def open_search(self,**kw):self.opened.append(kw)
 def load_section(self):pass
class LibraryUI(unittest.TestCase):
 def test_saved_search_reopens_original_category(self):
  c=lib.save_search({},'Space','space','movie');w=Window(c)
  with patch.dict(sys.modules,{'xbmcgui':SimpleNamespace(Dialog=lambda:SimpleNamespace(select=lambda *a,**k:1))}):choice=w.choose_saved_search()
  self.assertEqual(choice,('space',1));self.assertFalse(w.actions_open);self.assertEqual(w.saves,0)
 def test_cancel_new_collection_does_not_write(self):
  w=Window({});dialog=SimpleNamespace(select=lambda *a,**k:0,input=lambda *a,**k:'',ok=lambda *a:None)
  with patch.dict(sys.modules,{'xbmcgui':SimpleNamespace(Dialog=lambda:dialog)}):w.manage_collections()
  self.assertEqual(w.config,{});self.assertEqual(w.saves,0)
 def test_create_collection_then_exit_uses_saved_config(self):
  choices=iter([0,-1]);w=Window({});dialog=SimpleNamespace(select=lambda *a,**k:next(choices),input=lambda *a,**k:'Family',ok=lambda *a:None)
  with patch.dict(sys.modules,{'xbmcgui':SimpleNamespace(Dialog=lambda:dialog)}):w.manage_collections()
  self.assertEqual(w.config['PersonalCollections'][0]['name'],'Family');self.assertEqual(w.saves,1)
 def test_failed_write_restores_in_memory_preferences(self):
  w=Window({'Private':'kept'});w.save=lambda **k:(_ for _ in ()).throw(OSError('disk full'))
  with self.assertRaises(OSError):w.commit_library({'Private':'changed'})
  self.assertEqual(w.config,{'Private':'kept'})
class LibraryWatchUI(unittest.TestCase):
 def test_refresh_repaints_local_rows_and_persists_membership_status(self):
  from test_personal_library import title
  w=Window(lib.create_collection({},'One'));w.config=lib.membership(w.config,w.config['PersonalCollections'][0]['id'],title(),True)
  w.rows=[[title()],[]];w.paths=['',''];w.row_labels={0:'One'};w.selected=title();w.page_definitions=w.personal_rows();seen=[]
  w.apply_row=lambda n,files,label,pos,**kw:seen.append(files[0]);w.getControl=lambda n:SimpleNamespace(getSelectedPosition=lambda:0);w.getProperty=lambda k:'One';w.setProperty=lambda *a:None
  w.refresh_library_watch(dict(title(),playcount=0,resume={'position':30,'total':100}))
  self.assertEqual(seen[0]['resume']['position'],30);self.assertEqual(w.config['PersonalCollections'][0]['items'][0]['playcount'],0);self.assertEqual(w.saves,1)
class FranchiseOwnership(unittest.TestCase):
 def test_new_details_selection_cancels_old_franchise_lookup_before_provider_call(self):
  import library_ui
  from test_personal_library import title
  pending=[];opened=[];calls=[];w=Window({});w.selected=title(1);w.generation=1;w.window_lifetime=object();w.setProperty=lambda *a:None;w.open_discovery=lambda value:opened.append(value)
  class Worker:
   def __init__(self,target,**kw):self.target=target
   def start(self):pending.append(self.target)
  fake=SimpleNamespace(PROFILE=__import__('pathlib').Path('/unused'),tmdb=lambda *a,**k:'details',get_list=lambda path:calls.append(path))
  with patch.dict(sys.modules,{'live_review':fake,'xbmcgui':SimpleNamespace()}),patch.object(library_ui.threading,'Thread',Worker):
   w.open_movie_series(w.selected);w.selected=title(2);pending.pop()()
  self.assertEqual(opened,[]);self.assertEqual(calls,[])
