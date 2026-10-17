import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import live_core

class LiveLists(unittest.TestCase):
    def test_next_page_keeps_exact_provider_parameters(self):
        path='plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=movie&page=2&nextpage=true'
        result=live_core.directory_items({'result':{'files':[{'label':'Next Page','file':path,'filetype':'directory'}]}})
        self.assertEqual(result[0]['file'],path)
        self.assertEqual(result[0]['filetype'],'directory')
    def test_directory_errors_are_not_empty_success(self):
        with self.assertRaises(ValueError):live_core.directory_items({'error':{'message':'Invalid params'}})
    def test_page_back_restores_exact_source_and_selection(self):
        history=live_core.PageHistory();history.push('plugin://first',17)
        self.assertEqual(history.pop(),('plugin://first',17))
        self.assertIsNone(history.pop())
    def test_missing_rating_is_hidden_and_valid_source_is_named(self):
        self.assertEqual(live_core.rating_line({'rating':0}), '')
        self.assertEqual(live_core.rating_line({'rating':7.4}), 'TMDb 7.4/10')
        self.assertIn('IMDb 8.1/10',live_core.rating_line({'ratings':{'imdb':{'rating':8.1,'votes':20}}}))
    def test_sources_must_be_addon_directories(self):
        self.assertTrue(live_core.valid_source('plugin://plugin.video.umbrella/?action=movies'))
        self.assertFalse(live_core.valid_source('https://example.com/video.mp4'))
        self.assertFalse(live_core.valid_source('/Users/ChrisFaulkner/Library/Application Support/Kodi'))
    def test_cast_filmography_uses_person_identity_and_not_a_name_search(self):
        path='plugin://plugin.video.themoviedb.helper/?info=details&tmdb_type=person&tmdb_id=1100'
        self.assertEqual(live_core.person_identity(path),'1100')
        self.assertIsNone(live_core.person_identity('plugin://plugin.video.themoviedb.helper/?info=details&tmdb_type=movie&tmdb_id=1100'))
        self.assertIsNone(live_core.person_identity('plugin://plugin.video.themoviedb.helper/?info=search&tmdb_type=person&query=Someone'))
    def test_critic_and_audience_scores_keep_distinct_names_and_scales(self):
        data={'ratings':[{'source':'tomatoes','value':91},{'source':'tomatoesaudience','value':84},{'source':'metacritic','value':72},{'source':'imdb','value':7.4},{'source':'trakt','value':None}]}
        line=getattr(live_core,'mdblist_line',lambda data:'')(data)
        self.assertIn('RT critics 91%',line)
        self.assertIn('RT audience 84%',line)
        self.assertIn('Metacritic 72/100',line)
        self.assertIn('IMDb 7.4/10',line)
        self.assertNotIn('Trakt',line)
    def test_rating_badges_identify_icons_without_visible_source_names(self):
        data={'ratings':[{'source':'tomatoes','value':91},{'source':'tomatoesaudience','value':84},{'source':'metacritic','value':72}]}
        badges=getattr(live_core,'rating_badges',lambda item,data:[] )({},data)
        self.assertEqual([(b['icon'],b['value']) for b in badges],[('rottentomatoes','91%'),('metacritic','72/100'),('popcorn','84%')])

if __name__=='__main__':unittest.main()
