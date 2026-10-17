import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))

class RowFeedback(unittest.TestCase):
    def module(self):
        import row_feedback
        return row_feedback
    def test_empty_and_failed_lists_have_distinct_explanations(self):
        ui=self.module()
        self.assertIn('No results',ui.row_message('Search','empty',search=True))
        self.assertIn('could not load',ui.row_message('Search','error',search=True))
        self.assertNotIn('No results',ui.row_message('Search','error',search=True))
    def test_row_cache_discards_old_title_data_but_keeps_paging_and_position(self):
        ui=self.module();cache={n:{'files':[{'file':str(n)}],'path':'route'+str(n),'history':[('prior',4)],'position':3} for n in range(12)}
        ui.trim_row_cache(cache,offset=10,limit=4)
        self.assertEqual(sum(x['files'] is not None for x in cache.values()),4)
        self.assertEqual(cache[0]['path'],'route0');self.assertEqual(cache[0]['position'],3)
        self.assertEqual(cache[0]['history'],[('prior',4)]);self.assertEqual(cache[10]['files'],[{'file':'10'}])

if __name__=='__main__':unittest.main()
