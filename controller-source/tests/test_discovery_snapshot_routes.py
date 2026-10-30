"""Current public discovery routes must paint saved artwork before refresh."""
import sys,tempfile,unittest
from pathlib import Path
from urllib.parse import urlencode
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from public_rows import PublicRowSnapshots,public_path
from test_public_row_snapshots import ITEM

def route(**extra):
    return 'plugin://plugin.video.themoviedb.helper/?'+urlencode(dict(info='discover',tmdb_type='tv',with_id='true',include_adult='false',sort_by='popularity.desc',with_genres='9648|80',**extra))

class DiscoverySnapshotRoutes(unittest.TestCase):
    def test_first_youtube_account_check_retains_independently_scoped_public_artwork(self):
        self.check_youtube_cache_transition(initial=True)

    def test_actual_youtube_account_switch_still_invalidates_owned_session_results(self):
        self.check_youtube_cache_transition(initial=False)

    def test_youtube_disconnect_still_invalidates_owned_session_results(self):
        self.check_youtube_cache_transition(initial=False,enabled=False)

    def check_youtube_cache_transition(self,initial,enabled=True):
        from types import SimpleNamespace
        from unittest.mock import patch
        import json,youtube_browser
        from youtube_core import ConnectionState
        account={'access_manager':{'current_user':'0','users':{'0':{'refresh_token':'test-current-account'}}}}
        previous=ConnectionState();previous.connected=True;previous.identity='previous-account'
        with tempfile.TemporaryDirectory() as folder:
            path=route();cache=PublicRowSnapshots(Path(folder)/'public.json','proven-tmdb-account-and-config');cache.put(path,[ITEM]);before=cache.path.read_bytes()
            state=SimpleNamespace(alive=True,window_lifetime=object(),section='Home',youtube_connection=None if initial else previous,
                apply_youtube_home_rows=lambda:None,setProperty=lambda *a:None,refresh_navigation=lambda:None,invalidate_row_results=cache.clear)
            api=SimpleNamespace(executeJSONRPC=lambda request:json.dumps({'result':{'addon':{'enabled':enabled}}}))
            with patch.dict(sys.modules,{'xbmc':api}),patch.object(youtube_browser,'read_account_store',lambda:account):
                youtube_browser.YouTubeBrowser.refresh_youtube_connection(state,force=True)
            self.assertEqual(state.youtube_connection.connected,enabled)
            if initial:self.assertEqual(cache.path.read_bytes(),before);self.assertIsNotNone(cache.get(path))
            else:self.assertIsNone(cache.get(path));self.assertFalse(cache.path.exists())

    def test_saved_rows_retain_public_metadata_needed_by_existing_eligibility_filters(self):
        from discovery_order import hard_eligible
        from browse_controls import _classification
        with tempfile.TemporaryDirectory() as folder:
            path=route();item=dict(ITEM,votes='1,200',genre=['Animation'],country=['Japan'])
            s=PublicRowSnapshots(Path(folder)/'rows.json','scope');self.assertTrue(s.put(path,[item]))
            restored=PublicRowSnapshots(s.path,'scope').get(path)[0]
            self.assertEqual(hard_eligible(restored,{'max_votes':2000}),hard_eligible(item,{'max_votes':2000}))
            self.assertEqual(_classification(restored,None),_classification(item,None))
            self.assertEqual(restored['country'],['Japan'])

    def test_current_discovery_filter_families_are_public_but_account_rows_are_not(self):
        path=route(**{'primary_release_date.gte':'t-730','vote_average.gte':'6.7','vote_count.gte':'30','vote_count.lte':'3000','with_keywords':'12339|1299|3133','without_keywords':'9715','with_separator':'OR','with_origin_country':'JP','bl_start':'20'})
        self.assertTrue(public_path(path))
        self.assertFalse(public_path(path.replace('info=discover','info=trakt_recommendations')))
        self.assertFalse(public_path(path.replace('info=discover','info=trakt_watchlist')))

    def test_saved_artwork_paints_before_provider_and_watch_hydration_retains_focus(self):
        from test_snapshot_controller import SnapshotController
        with tempfile.TemporaryDirectory() as folder:
            path=route(**{'first_air_date.gte':'t-730'})
            state,calls,controls,queue=SnapshotController().state(folder,lambda p:[dict(ITEM,playcount=1,resume={})])
            self.assertTrue(state.snapshot_cache.put(path,[ITEM]))
            state.set_rows([{'path':path,'label':'Mystery shows'}])
            self.assertEqual(calls,[])
            card=controls[900].items[0]
            self.assertEqual(card.art['poster'],ITEM['art']['poster'])
            self.assertEqual(card.properties['watchState'],'unknown')
            state.focus=105;queue.pop(0)()
            self.assertEqual(state.focus,105);self.assertIs(controls[900].items[0],card)
            self.assertEqual(card.properties['watchState'],'watched')

    def test_selected_cached_title_receives_fresh_metadata_without_rebinding_artwork(self):
        from test_snapshot_controller import SnapshotController
        with tempfile.TemporaryDirectory() as folder:
            fresh=dict(ITEM,plot='Fresh synopsis',genre=['Mystery'],year=2026)
            state,calls,controls,queue=SnapshotController().state(folder,lambda p:[fresh])
            state.update=lambda item:setattr(state,'selected',item)
            state.set_rows([{'path':'plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=movie','label':'Popular'}])
            card=controls[900].items[0];state.focus=900
            queue.pop(0)()
            self.assertEqual(state.selected['plot'],'Fresh synopsis')
            self.assertEqual(state.selected['genre'],['Mystery'])
            self.assertIs(controls[900].items[0],card)
            self.assertEqual(card.art['poster'],ITEM['art']['poster'])

    def test_fresh_metadata_survives_feedback_repaint_from_the_retained_raw_row(self):
        from test_snapshot_controller import SnapshotController
        from test_public_row_snapshots import P
        from test_window_lifecycle import extract
        from title_preferences import TitlePreferences,discovery_scope
        from types import MethodType
        with tempfile.TemporaryDirectory() as folder:
            state,calls,controls,queue=SnapshotController().state(folder,lambda p:[dict(ITEM,plot='Fresh synopsis',genre=['Mystery'])])
            state.section='Movies';state.mode='home';state.title_preferences=TitlePreferences(Path(folder)/'prefs.json')
            source=Path(__file__).parents[1]/'addon/title_feedback_ui.py'
            for name in ('prepare_title_row','raw_title_row','hydrate_title_row'):
                setattr(state,name,MethodType(extract(source,name,{'discovery_scope':discovery_scope},'TitleFeedback'),state))
            state.set_rows([{'path':P,'label':'Popular'}]);queue.pop(0)()
            state.apply_row(0,state.raw_title_row(0),'Popular',update_selected=False)
            self.assertEqual(state.rows[0][0].get('plot'),'Fresh synopsis')
            self.assertEqual(state.rows[0][0]['genre'],['Mystery'])
            self.assertEqual(len(calls),1)

    def test_current_genre_and_relative_date_routes_survive_disk_round_trip(self):
        for query in ({},{'first_air_date.gte':'t-730','first_air_date.lte':'t+0'}, {'first_air_date.lte':'2026-10-30'}):
            with self.subTest(query=query),tempfile.TemporaryDirectory() as folder:
                path=route(**query);s=PublicRowSnapshots(Path(folder)/'rows.json','scope')
                next_item={'file':path+'&page=2&plugin_category=Browse%20more','label':'Next page','filetype':'directory'}
                self.assertTrue(s.put(path,[ITEM,next_item]))
                restored=PublicRowSnapshots(s.path,'scope').get(path)
                self.assertEqual(restored[0]['art'],ITEM['art'])
                self.assertNotIn('plugin_category',restored[-1]['file'])
                self.assertNotIn('playcount',restored[0]);self.assertNotIn('resume',restored[0])

    def test_discovery_filters_remain_typed_and_unknown_or_private_queries_stay_blocked(self):
        for query in ({'with_id':'secret'},{'include_adult':'anything'}, {'first_air_date.gte':'secret'}, {'first_air_date.gte':'2026-99-99'}, {'first_air_date.gte':'t-9999999'}, {'token':'secret'},{'user':'someone'},{'query':'private'},{'bl_start':'-1'}):
            # Override fixed parameters without duplicate keyword arguments.
            from urllib.parse import parse_qs,urlsplit
            params={k:v[0] for k,v in parse_qs(urlsplit(route()).query).items()};params.update(query)
            self.assertFalse(public_path('plugin://plugin.video.themoviedb.helper/?'+urlencode(params)),query)

