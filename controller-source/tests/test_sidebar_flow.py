import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
import navigation_core

class SidebarFlow(unittest.TestCase):
 def test_search_and_settings_are_part_of_the_same_complete_list(self):
  self.assertTrue(hasattr(navigation_core,'sidebar_items'),'Pinned items must move with all sidebar fields')
  cfg=navigation_core.migrate_navigation({'Sidebar':[{'id':str(i),'label':str(i),'icon':'home','enabled':True} for i in range(8)]})
  items=navigation_core.sidebar_items(cfg)
  self.assertEqual([i['id'] for i in items],['search']+[str(i) for i in range(8)]+['settings'])
  self.assertNotIn('fixed_action',cfg['Sidebar'][0])
 def test_added_items_move_settings_down_and_keep_ordinary_lists_fully_visible(self):
  self.assertTrue(hasattr(navigation_core,'sidebar_layout'))
  a=navigation_core.sidebar_layout(5);b=navigation_core.sidebar_layout(6)
  self.assertGreater(b['settings_top'],a['settings_top'])
  self.assertGreaterEqual(b['height'],8*b['row_height'])
  self.assertLessEqual(b['top']+b['height'],1060)
 def test_long_sidebars_scroll_search_and_settings_together_without_smaller_icons(self):
  self.assertTrue(hasattr(navigation_core,'sidebar_layout'))
  l=navigation_core.sidebar_layout(18)
  self.assertLess(l['height'],20*l['row_height'])
  self.assertGreaterEqual(l['row_height'],80)
