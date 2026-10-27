import ast,importlib.util,sqlite3,tempfile,unittest,time
from pathlib import Path
from types import SimpleNamespace,MethodType
from test_window_lifecycle import ROOT,extract
from live_core import PageHistory
from live_core import directory_items,valid_source
from urllib.parse import urlsplit,parse_qs

def module(test):
    path=ROOT/'browse_controls.py'
    test.assertTrue(path.exists(),'Browse controls and scoped anime filtering are missing')
    spec=importlib.util.spec_from_file_location('browse_controls',path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def item(n,genre=None,country=None):
    return {'label':str(n),'file':'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id='+str(n),'genre':genre or [],'country':country or []}

class BrowseControls(unittest.TestCase):
    def test_first_page_has_no_previous_and_provider_next_moves_to_end(self):
        m=module(self);origin='plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=tv'
        more={'label':'Next page','filetype':'directory','file':origin+'&page=2'}
        files,pos=m.page_cards([item(1),more,item(2)],PageHistory(),origin,0)
        self.assertEqual([x['label'] for x in files],['1','2','Next'])
        self.assertEqual(pos,0);self.assertEqual(files[-1]['file'],more['file'])
    def test_previous_card_is_visible_once_and_initial_focus_is_a_title(self):
        m=module(self);history=PageHistory();history.push('plugin://test/first',7)
        files,pos=m.page_cards([item(1),item(2)],history,'plugin://test/second',0)
        self.assertEqual(files[0]['label'],'Previous');self.assertEqual(pos,1)
        again,restored=m.page_cards(files,history,'plugin://test/second',2,display_position=True)
        self.assertEqual(len(again),3);self.assertEqual(again[restored]['file'],item(2)['file'])
    def test_back_display_position_survives_navigation_card_offset(self):
        m=module(self);history=PageHistory();history.push('plugin://test/one',0)
        files,pos=m.page_cards([item(3),item(4),item(5)],history,'plugin://test/two',2,display_position=True)
        self.assertEqual(pos,2);self.assertEqual(files[pos]['file'],item(4)['file'])
    def test_an_unrelated_paged_folder_is_not_moved_to_the_end(self):
        m=module(self);folder={'label':'A collection','filetype':'directory','file':'plugin://test/collection?page=2'}
        files,_=m.page_cards([folder,item(1)],PageHistory(),'plugin://test/list?page=1',0)
        self.assertEqual(files[0],folder)
    def test_genre_shortcut_requires_movie_or_show_discovery(self):
        m=module(self)
        state=SimpleNamespace(section='Movies',mode='home',search_state=None,episode_browser_context=None,discovery_stack=[],nav=False)
        self.assertTrue(m.can_choose_genre(state))
        for field,value in [('search_state',{'query':'Alien'}),('episode_browser_context',{}),('mode','details'),('section','Home')]:
            old=getattr(state,field);setattr(state,field,value)
            self.assertFalse(m.can_choose_genre(state),field);setattr(state,field,old)
    def test_anime_policy_keeps_intentional_access_and_the_dedicated_section(self):
        m=module(self);s=SimpleNamespace(section='Shows',active_page='international',config={'Genres':[{'id':'animation','label':'Animation','rows':[]}], 'Categories':[]},search_state=None,episode_browser_context=None,person_context=None,discovery_stack=[])
        path='plugin://plugin.video.themoviedb.helper/?info=trakt_trending&tmdb_type=tv'
        self.assertTrue(m.should_exclude_anime(s,path))
        s.active_page='animation';self.assertFalse(m.should_exclude_anime(s,path));s.active_page=None
        for kind in ['trakt_watchlist','trakt_ondeck','trakt_inprogress','trakt_nextepisodes','trakt_history']:
            self.assertFalse(m.should_exclude_anime(s,path.replace('trakt_trending',kind)),kind)
        s.search_state={'query':'Naruto'};self.assertFalse(m.should_exclude_anime(s,path))
        s.search_state=None;s.section='My Stuff';self.assertFalse(m.should_exclude_anime(s,path))
    def test_cached_metadata_separates_anime_from_other_animation_and_live_action(self):
        m=module(self)
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'database_07';db.mkdir()
            with sqlite3.connect(db/'ItemDetails.db') as c:
                c.executescript('CREATE TABLE genre(parent_id TEXT,tmdb_id INTEGER); CREATE TABLE country(parent_id TEXT,iso_country TEXT);')
                c.executemany('INSERT INTO genre VALUES(?,?)',[('tv.1',16),('tv.2',16),('tv.3',18)])
                c.executemany('INSERT INTO country VALUES(?,?)',[('tv.1','JP'),('tv.2','US'),('tv.3','JP')])
            reader=m.AnimeMetadata(folder)
            files=[item(1),item(2,['Animation']),item(3,['Drama']),item(4,['Animation'])]
            self.assertEqual([x['label'] for x in reader.without_anime(files)],['2','3','4'])
            self.assertEqual([x['label'] for x in reader.without_anime(files)],['2','3','4'])
            self.assertEqual(reader.reads,1,'Known metadata should be reused without per-title I/O')
    def test_missing_or_changed_metadata_never_hides_unknown_titles(self):
        m=module(self)
        with tempfile.TemporaryDirectory() as folder:
            reader=m.AnimeMetadata(folder);files=[item(1,['Animation'])]
            self.assertEqual(reader.without_anime(files),files)
    def test_malformed_optional_cache_cells_keep_unknown_and_neighboring_titles(self):
        m=module(self)
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'database_07';db.mkdir()
            with sqlite3.connect(db/'ItemDetails.db') as c:
                c.executescript('CREATE TABLE genre(parent_id TEXT,tmdb_id INTEGER); CREATE TABLE country(parent_id TEXT,iso_country TEXT);')
                c.executemany('INSERT INTO genre VALUES(?,?)',[('tv.1',16),('tv.2',16),('tv.3',16),('tv.4',sqlite3.Binary(b'16'))])
                c.executemany('INSERT INTO country VALUES(?,?)',[('tv.1',sqlite3.Binary(b'JP')),('tv.2',42),('tv.3',' JP '),('tv.4','JP')])
            files=[item(1,['Animation']),item(2,['Animation']),item(3,['Animation']),item(4),item(5,['Drama'])]
            self.assertEqual([x['label'] for x in m.AnimeMetadata(folder).without_anime(files)],['1','2','4','5'])
    def test_explicit_metadata_does_not_confuse_japanese_live_action_with_anime(self):
        m=module(self)
        with tempfile.TemporaryDirectory() as folder:
            reader=m.AnimeMetadata(folder)
            files=[item(1,['Animation'],['Japan']),item(2,['Animation'],['United States of America']),item(3,['Drama'],['Japan'])]
            self.assertEqual([x['label'] for x in reader.without_anime(files)],['2','3'])

class ControllerControls(unittest.TestCase):
    def test_provider_country_metadata_filters_anime_even_with_an_empty_cache(self):
        m=module(self);ns={}
        tree=ast.parse((ROOT/'live_review.py').read_text())
        assignment=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PROPERTIES' for t in n.targets))
        exec(compile(ast.Module(body=[assignment],type_ignores=[]),'properties','exec'),ns)
        def rpc(method,params):
            title=item(1,['Animation'])
            if 'country' in params['properties']:title['country']=['Japan']
            return {'result':{'files':[title]}}
        ns.update(DIRECTORY_GATE=__import__('threading').BoundedSemaphore(2),parse_qs=parse_qs,time=time,valid_source=valid_source,catalogue_category=lambda _:None,rpc=rpc,directory_items=directory_items,urlsplit=urlsplit,event=lambda *a,**kw:None)
        files=extract(ROOT/'live_review.py','get_list',ns)('plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=tv')
        with tempfile.TemporaryDirectory() as folder:self.assertEqual(m.AnimeMetadata(folder).without_anime(files),[])
    def test_actual_row_renderer_filters_only_discovery_and_keeps_the_raw_cache(self):
        m=module(self)
        from test_discovery_controller import DiscoveryController
        with tempfile.TemporaryDirectory() as folder:
            original=[item(1,['Animation'],['JP']),item(2,['Animation'],['US']),item(3,['Drama'],['JP'])]
            s,_,_=DiscoveryController().state(provider=lambda _:original)
            s.section='Shows';s.search_state=None;s.person_context=None;s.discovery_stack=[];s.config={};s.anime_metadata=m.AnimeMetadata(folder)
            path='plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=tv'
            s.set_rows([{'label':'Popular','path':path}])
            self.assertEqual([x['label'] for x in s.rows[0]],['2','3'])
            self.assertEqual(s.result_cache.get(path),original,'Filtering must not poison shared provider data')
            s.search_state={'query':'anime'};s.set_rows([{'label':'Search','path':path}])
            self.assertEqual(s.rows[0],original)
            s.search_state=None;s.active_page='animation';s.config={'Genres':[{'id':'animation','label':'Animation'}]}
            s.set_rows([{'label':'Animation','path':path}]);self.assertEqual(s.rows[0],original)
    def test_genre_is_available_from_titles_and_page_controls(self):
        m=module(self)
        for selected in [item(1),{'_page_control':'previous','file':'blacklanturn://previous','label':'Previous'}]:
            calls=[];history=PageHistory();history.push('plugin://test/one',2)
            state=SimpleNamespace(section='Movies',mode='home',search_state=None,episode_browser_context=None,discovery_stack=[],nav=False,
                getFocusId=lambda:900,rows=[[selected],[]],histories=[history,PageHistory()],last_row=0,row_states={},
                chosen=lambda cid:selected,config={'Saved':[]},rating_identity=lambda _:None,
                stop_preview=lambda:None,actions_open=False,browse_source=lambda:calls.append('genre'),setFocusId=lambda n:None)
            ns={'xbmcgui':SimpleNamespace(Dialog=lambda:SimpleNamespace(contextmenu=lambda opts:opts.index('Choose genre…') if 'Choose genre…' in opts else -1)),
                'can_choose_genre':m.can_choose_genre,'trakt_command':lambda _:None,'choose_player_path':lambda _:None,'discovery_result':lambda _:None,'resume_options':lambda _: {},'event':lambda *a,**kw:None}
            extract(ROOT/'live_review.py','title_actions',ns,'LiveReview')(state)
            self.assertEqual(calls,['genre']);self.assertFalse(state.actions_open)
    def test_genre_is_immediately_after_details_on_each_visible_row(self):
        m=module(self)
        for section in ('Movies','Shows'):
            for focus in (900,901,101):
                with self.subTest(section=section,focus=focus):
                    selected=item(1);menus=[];calls=[]
                    state=SimpleNamespace(section=section,mode='home',search_state=None,episode_browser_context=None,discovery_stack=[],nav=False,
                        getFocusId=lambda:focus,rows=[[selected],[selected]],histories=[PageHistory(),PageHistory()],last_row=1,row_states={},
                        chosen=lambda cid:selected,config={'Saved':[]},rating_identity=lambda _:('movie','1'),
                        stop_preview=lambda:None,actions_open=False,browse_source=lambda:calls.append('genre'),setFocusId=lambda n:None)
                    def menu(options):
                        menus.append(options)
                        return options.index('Choose genre…') if 'Choose genre…' in options else -1
                    ns={'xbmcgui':SimpleNamespace(Dialog=lambda:SimpleNamespace(contextmenu=menu)),
                        'can_choose_genre':m.can_choose_genre,'trakt_command':lambda _:'trakt',
                        'choose_player_path':lambda _:'plugin://player','discovery_result':lambda _:None,'resume_options':lambda _: {},'event':lambda *a,**kw:None}
                    extract(ROOT/'live_review.py','title_actions',ns,'LiveReview')(state)
                    self.assertEqual(calls,['genre'])
                    choices=menus[0];genre=choices.index('Choose genre…')
                    self.assertEqual(genre,choices.index('Details')+1)
                    for label in ('Play','Play using…','Details'):
                        self.assertLess(choices.index(label),genre)
                    for label in ('Save to My Stuff on this device','Trakt: Watched, progress & lists','Discover collections & creator credits','Set default player…','Refresh watched status'):
                        self.assertGreater(choices.index(label),genre)
    def test_title_genre_shortcut_is_excluded_from_seasons_episodes_youtube_and_details(self):
        m=module(self)
        for section,mode,episode_context in [('Shows','home',{'season':1}),('Shows','home',{'episode':2}),('YouTube','home',None),('Movies','details',None)]:
            with self.subTest(section=section,mode=mode,episode_context=episode_context):
                selected=item(1);menus=[]
                state=SimpleNamespace(section=section,mode=mode,search_state=None,episode_browser_context=episode_context,discovery_stack=[],nav=False,
                    getFocusId=lambda:901,rows=[[selected],[selected]],histories=[PageHistory(),PageHistory()],last_row=1,row_states={},
                    chosen=lambda cid:selected,config={'Saved':[]},rating_identity=lambda _:None,stop_preview=lambda:None,actions_open=False)
                ns={'xbmcgui':SimpleNamespace(Dialog=lambda:SimpleNamespace(contextmenu=lambda opts:menus.append(opts) or -1)),
                    'can_choose_genre':m.can_choose_genre,'trakt_command':lambda _:None,'choose_player_path':lambda _:None,
                    'discovery_result':lambda _:None,'resume_options':lambda _: {},'event':lambda *a,**kw:None}
                extract(ROOT/'live_review.py','title_actions',ns,'LiveReview')(state)
                self.assertNotIn('Choose genre…',menus[0])
    def test_folder_navigation_omits_genres_only_in_the_season_or_episode_row(self):
        m=module(self)
        show_path='plugin://plugin.video.themoviedb.helper/?info=seasons&tmdb_type=tv&tmdb_id=83659'
        episodes=show_path.replace('info=seasons','info=episodes')+'&season=1'
        discovery='plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=tv'
        show={'label':'Cabinet of Curiosities','file':show_path,'filetype':'directory'}
        season={'label':'Season 1','file':episodes,'filetype':'directory','season':1}
        previous={'label':'Previous','file':'blacklanturn://previous-page','_page_control':'previous'}
        next_page={'label':'Next','file':episodes+'&page=2','_page_control':'next'}
        for paths,focus,selected,want_genre in [
            ([discovery,''],900,show,True),
            ([show_path,discovery],900,season,False),
            ([episodes,discovery],900,previous,False),
            ([episodes,discovery],900,next_page,False),
            ([episodes.replace('season=1','season=0'),discovery],900,next_page,False),
            ([episodes,discovery],901,show,True),
            ([episodes,discovery],101,previous,False),
            ([discovery,''],900,show,True),
        ]:
            with self.subTest(paths=paths,focus=focus,title=selected['label']):
                menus=[]
                history=PageHistory();history.push(discovery,0)
                state=SimpleNamespace(section='Shows',mode='home',nav=False,search_state=None,
                    episode_browser_context=None,discovery_stack=[],paths=paths,last_row=0,
                    getFocusId=lambda:focus,rows=[[selected],[selected]],
                    histories=[history,PageHistory()],row_states={},chosen=lambda cid:selected,
                    config={'Saved':[]},rating_identity=lambda _:None,stop_preview=lambda:None,actions_open=False)
                ns={'xbmcgui':SimpleNamespace(Dialog=lambda:SimpleNamespace(contextmenu=lambda opts:menus.append(opts) or -1)),
                    'can_choose_genre':m.can_choose_genre,'trakt_command':lambda _:None,'choose_player_path':lambda _:None,
                    'discovery_result':lambda _:None,'resume_options':lambda _: {},'event':lambda *a,**kw:None}
                extract(ROOT/'live_review.py','title_actions',ns,'LiveReview')(state)
                self.assertEqual('Choose genre…' in menus[0],want_genre)
                if want_genre:self.assertEqual(menus[0].index('Choose genre…'),menus[0].index('Details')+1)
    def test_clicking_previous_restores_that_rows_path_and_position(self):
        m=module(self);history=PageHistory();history.push('plugin://test/first',6);calls=[]
        state=SimpleNamespace(actions_open=False,histories=[PageHistory(),history],chosen=lambda cid:{'_page_control':'previous','file':'blacklanturn://previous'},
            load_path=lambda *a,**kw:calls.append((a,kw)))
        extract(ROOT/'live_review.py','onClick',{'discovery_result':lambda _:None,'is_browse_folder':lambda _:True},'LiveReview')(state,901)
        self.assertEqual(calls,[((1,'plugin://test/first'),{'back':True,'position':6})])
        self.assertEqual(history.pages,[])

if __name__=='__main__':unittest.main()
