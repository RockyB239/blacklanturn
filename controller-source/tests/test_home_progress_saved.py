"""Saving a guarded display card must not persist its temporary scope proof."""
import copy,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from test_window_lifecycle import extract,ROOT
from live_runtime import write_controller_config
from personal_library import snapshot
MARK='_home_progress_scope'
class SavedProgressBoundary(unittest.TestCase):
 def test_actual_legacy_save_preserves_metadata_and_keeps_live_selection_guarded(self):
  with tempfile.TemporaryDirectory() as folder:
   item={'file':'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=12&season=1&episode=2','filetype':'file','title':'Episode','showtitle':'Show','season':1,'episode':2,'art':{'poster':'https://image.tmdb.org/t/p/w500/poster.jpg'},'uniqueid':{'tmdb':'22','tvshow.tmdb':'12'},'genre':['Drama'],'plot':'Plot','playcount':0,'resume':{'position':40,'total':100},'custom_metadata':{'preserved':True},MARK:'opaque-live-scope'}
   original=copy.deepcopy(item);config={'Saved':[]};properties={};updates=[];path=Path(folder)/'rows.json'
   state=SimpleNamespace(selected=item,config=config,save=lambda:write_controller_config(path,config),update=updates.append,setProperty=lambda key,value:properties.__setitem__(key,value))
   click=extract(ROOT/'live_review.py','onClick',{'copy':copy},'LiveReview');click(state,103)
   saved=json.loads(path.read_text())['Saved'][0]
   self.assertNotIn(MARK,saved);self.assertEqual(saved,{key:value for key,value in original.items() if key!=MARK});self.assertEqual(item,original);self.assertIs(state.selected,item);self.assertIs(updates[0],item);self.assertIsNot(config['Saved'][0],item)
   click(state,103);self.assertEqual(json.loads(path.read_text())['Saved'],[]);self.assertEqual(item,original)
 def test_collection_snapshot_already_excludes_pending_scope_without_changing_live_item(self):
  item={'file':'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=movie&tmdb_id=42','filetype':'file','title':'Movie','art':{'poster':'https://image.tmdb.org/t/p/w500/poster.jpg'},'playcount':0,'resume':{'position':40,'total':100},MARK:'opaque-live-scope'}
  original=copy.deepcopy(item);saved=snapshot(item)
  self.assertNotIn(MARK,saved);self.assertEqual(saved['art'],item['art']);self.assertEqual(saved['resume'],item['resume']);self.assertEqual(item,original)
if __name__=='__main__':unittest.main()
