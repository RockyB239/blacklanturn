"""User arrangements survive adaptive feeds without modifying sources."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
try:from row_layout import RowLayouts,row_key
except ImportError:RowLayouts=None;row_key=None

def defs():return [{'label':x,'path':'plugin://example/'+x} for x in ('A','B','C')]
class LayoutTests(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(RowLayouts,'Saved per-section row arrangements are missing')
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'layouts.json';self.store=RowLayouts(self.path);self.rows=defs()
 def labels(self,scope='Home',all=False):return [x['label'] for x in self.store.rows(scope,self.rows,include_hidden=all)]
 def test_default_returns_original_items_without_writes(self):
  result=self.store.rows('Home',self.rows);self.assertEqual(result,self.rows);self.assertIs(result[0],self.rows[0]);self.assertFalse(self.path.exists())
 def test_saved_order_is_independent_between_sections_and_restart(self):
  self.store.change('Home',self.rows,self.rows[2],'up');self.assertEqual(self.labels(),['A','C','B']);self.assertEqual(self.labels('Shows'),['A','B','C']);self.assertEqual([r['label'] for r in RowLayouts(self.path).rows('Home',self.rows)],['A','C','B'])
 def test_pin_is_stable_and_unpin_restores_manual_order(self):
  self.store.change('Home',self.rows,self.rows[2],'pin');self.assertEqual(self.labels(),['C','A','B']);self.store.change('Home',self.rows,self.rows[2],'unpin');self.assertEqual(self.labels(),['A','B','C'])
 def test_hidden_rows_remain_manageable_and_can_be_shown(self):
  self.store.change('Home',self.rows,self.rows[1],'hide');self.assertEqual(self.labels(),['A','C']);self.assertEqual(self.labels(all=True),['A','B','C']);self.store.change('Home',self.rows,self.rows[1],'show');self.assertEqual(self.labels(),['A','B','C'])
 def test_cannot_hide_last_visible_row(self):
  for r in self.rows[:2]:self.store.change('Home',self.rows,r,'hide')
  prior=self.path.read_bytes()
  with self.assertRaises(ValueError):self.store.change('Home',self.rows,self.rows[2],'hide')
  self.assertEqual(self.path.read_bytes(),prior)
 def test_restore_only_changes_chosen_arrangement(self):
  self.store.change('Home',self.rows,self.rows[2],'pin');self.store.change('Shows',self.rows,self.rows[1],'hide');self.store.reset('Home');self.assertEqual(self.labels(),['A','B','C']);self.assertEqual(self.labels('Shows'),['A','C'])
 def test_new_rows_append_and_temporarily_missing_rows_remain_saved(self):
  self.store.change('Home',self.rows,self.rows[1],'hide');self.store.change('Home',self.rows,self.rows[2],'up');new=[self.rows[2],self.rows[0],{'label':'D','path':'plugin://example/D'}];self.assertEqual([r['label'] for r in self.store.rows('Home',new)],['A','C','D']);self.assertEqual(self.labels(),['A','C'])
 def test_adaptive_youtube_shelf_identity_ignores_changing_content_cursor(self):
  a={'label':'Science and more','path':'plugin://plugin.video.youtube/special/recommendations?bl_shelf=old','youtube_category':True};b=dict(a,path=a['path'].replace('old','new'));self.assertEqual(row_key(a),row_key(b));self.assertNotEqual(row_key(a),row_key(dict(a,label='Music')))
 def test_sources_art_and_cursor_are_unchanged(self):
  self.rows[1].update(local_items=[{'label':'Keep'}],youtube_cursor={'token':'private'});before=copy.deepcopy(self.rows);self.store.change('Home',self.rows,self.rows[1],'pin');self.store.rows('Home',self.rows);self.assertEqual(self.rows,before);self.assertNotIn('private',self.path.read_text())
 def test_failed_write_preserves_file_and_in_memory_state(self):
  self.store.change('Home',self.rows,self.rows[1],'hide');raw=self.path.read_bytes()
  with patch('row_layout.os.replace',side_effect=OSError('disk full')):
   with self.assertRaises(OSError):self.store.change('Home',self.rows,self.rows[2],'pin')
  self.assertEqual(self.path.read_bytes(),raw);self.assertEqual(self.labels(),['A','C']);self.assertFalse(list(self.path.parent.glob('*.pending')))
 def test_corrupt_preferences_never_overwritten(self):
  self.path.write_text('{bad');s=RowLayouts(self.path);self.assertEqual(s.rows('Home',self.rows),self.rows)
  with self.assertRaises(ValueError):s.change('Home',self.rows,self.rows[0],'hide')
  self.assertEqual(self.path.read_text(),'{bad')
 def test_browsing_uses_memory_without_reopening_preference_file(self):
  self.store.change('Home',self.rows,self.rows[2],'pin')
  with patch.object(Path,'read_text',side_effect=AssertionError('Repeated disk read')):
   for _ in range(100):self.assertEqual(self.labels(),['C','A','B'])
 def test_missing_visible_categories_temporarily_fall_back_without_erasing_hidden_choices(self):
  self.store.change('Home',self.rows,self.rows[0],'hide');self.store.change('Home',self.rows,self.rows[1],'hide');raw=self.path.read_bytes();self.assertEqual(self.store.rows('Home',self.rows[:2]),[self.rows[0]]);self.assertEqual(self.store.rows('Home',self.rows),[self.rows[2]]);self.assertEqual(self.path.read_bytes(),raw)
