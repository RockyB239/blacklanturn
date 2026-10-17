import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from discovery_core import migrate_pages,collection_pages,page_rows,window_shift
P='plugin://plugin.video.themoviedb.helper/?info=popular'
class DiscoveryPages(unittest.TestCase):
 def test_old_single_list_becomes_first_row_without_mutating_original(self):
  original={'Genres':[{'label':'Action','section':'Movies','path':P}],'Saved':[{'file':'private-saved-title'}],'PreviewDelay':5}
  before=copy.deepcopy(original);c=migrate_pages(original)
  self.assertEqual(original,before);self.assertEqual(c['Genres'][0]['rows'],[{'label':'Action','path':P,'enabled':True}]);self.assertEqual(c['Saved'],original['Saved']);self.assertEqual(c['PreviewDelay'],5)
  self.assertEqual(migrate_pages(c),c)
 def test_all_rows_and_sources_survive_and_hidden_rows_stay_configured(self):
  rows=[{'label':str(n),'path':P+'&genre='+str(n),'enabled':n!=2} for n in range(5)]
  c=migrate_pages({'Categories':[{'id':'collection','label':'Collection','section':'Movies','rows':rows}]})
  self.assertEqual([r['label'] for r in page_rows(c,'Movies','collection')],['0','1','3','4']);self.assertEqual(len(c['Categories'][0]['rows']),5)
  self.assertEqual(page_rows(c,'Shows','collection'),[])
 def test_genre_and_category_are_independent_and_preserve_order(self):
  c=migrate_pages({'Genres':[{'id':'g','label':'Drama','section':'Shows','rows':[{'label':'Popular drama','path':P}]}],'Categories':[{'id':'c','label':'Awards','section':'Both','rows':[{'label':'Winners','path':P+'&a=1'},{'label':'Nominees','path':P+'&a=2'}]}]})
  self.assertEqual([p['id'] for p in collection_pages(c,'Shows')],['g','c'])
  self.assertEqual([r['label'] for r in page_rows(c,'Shows','c')],['Winners','Nominees']);self.assertEqual(page_rows(c,'Shows','g')[0]['label'],'Popular drama')
 def test_hidden_pages_and_invalid_sources_never_load(self):
  c=migrate_pages({'Genres':[{'id':'off','label':'Hidden','enabled':False,'rows':[{'label':'No','path':P}]}],'Home':[{'label':'Invalid','path':'https://example.com'},{'label':'Good','path':P}]})
  self.assertEqual(collection_pages(c,'Movies'),[]);self.assertEqual([r['label'] for r in page_rows(c,'Home')],['Good'])
 def test_virtual_rows_reach_last_and_back_without_truncation(self):
  self.assertEqual(window_shift(0,1,1,5),1);self.assertEqual(window_shift(1,1,1,5),2);self.assertEqual(window_shift(2,1,1,5),3)
  self.assertIsNone(window_shift(3,1,1,5));self.assertEqual(window_shift(3,0,-1,5),2);self.assertIsNone(window_shift(0,0,-1,5));self.assertIsNone(window_shift(1,0,1,5))
