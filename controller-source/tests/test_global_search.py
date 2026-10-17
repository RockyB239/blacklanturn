"""Global search must send movie and TV requests without losing the user's query."""
import sys,unittest
from pathlib import Path
from types import SimpleNamespace,MethodType
from urllib.parse import urlsplit,parse_qs
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
import search_ui
from test_window_lifecycle import extract,ROOT

class GlobalSearch(unittest.TestCase):
 def window(self):
  self.loaded=[];self.props={}
  w=SimpleNamespace(search_state=None,search_origin=None,config={},selected={'title':'Previous'},
   capture_browse=lambda **kw:{'navigation_id':'shows','positions':[3,0]},
   stop_preview=lambda:None,save=lambda **kw:None,populate_search=lambda:None,
   setProperty=lambda key,value:self.props.__setitem__(key,value),
   getControl=lambda cid:SimpleNamespace(setHeight=lambda height:None),
   set_rows=lambda rows:self.loaded.append(rows))
  w.select_search=MethodType(extract(ROOT/'live_review.py','select_search',{'search_sources':search_ui.search_sources,'clear_search_selection':search_ui.clear_search_selection},'LiveReview'),w)
  w.open_search=MethodType(extract(ROOT/'live_review.py','open_search',{},'LiveReview'),w)
  return w
 def test_default_search_requests_movies_and_shows_for_the_full_query(self):
  w=self.window();w.open_search('The Beauty & Dune?')
  self.assertEqual(len(self.loaded[-1]),6,'Global search omitted discovery categories')
  params=[parse_qs(urlsplit(x['path']).query) for x in self.loaded[-1]]
  self.assertEqual([x['tmdb_type'] for x in params],[['both'],['movie'],['tv'],['person'],['company'],['collection']])
  self.assertEqual([x['query'] for x in params],[['The Beauty & Dune?']]*6)
  self.assertEqual(w.search_origin,{'navigation_id':'shows','positions':[3,0]})
 def test_switching_from_combined_search_to_shows_keeps_query_and_only_requests_tv(self):
  w=self.window();w.open_search('The Beauty')
  self.assertEqual(len(self.loaded[-1]),6,'Start from All results')
  w.select_search(next(i for i,(kind,label) in enumerate(search_ui.SEARCH_KINDS) if kind=='tv'))
  self.assertEqual(len(self.loaded[-1]),1)
  params=parse_qs(urlsplit(self.loaded[-1][0]['path']).query)
  self.assertEqual(params['tmdb_type'],['tv']);self.assertEqual(params['query'],['The Beauty'])
 def test_franchise_discovery_still_searches_collections_after_combined_tab_is_added(self):
  w=self.window();dialog=SimpleNamespace(select=lambda *args:0,input=lambda *args,**kw:'Dune')
  method=extract(ROOT/'live_review.py','discover_more',{'xbmcgui':SimpleNamespace(Dialog=lambda:dialog),'event':lambda *args,**kw:None,'SEARCH_KINDS':search_ui.SEARCH_KINDS},'LiveReview')
  method(w,{'title':'Dune'})
  self.assertEqual(len(self.loaded[-1]),1)
  params=parse_qs(urlsplit(self.loaded[-1][0]['path']).query)
  self.assertEqual(params['tmdb_type'],['collection'],'Franchise discovery must not switch to People')
 def test_blank_search_keeps_previous_results_and_does_not_send_provider_requests(self):
  w=self.window();w.open_search('The Beauty');before=w.search_state.copy();loaded=len(self.loaded)
  w.open_search('   ')
  self.assertEqual(w.search_state,before);self.assertEqual(len(self.loaded),loaded)

if __name__=='__main__':unittest.main()
