import sys,unittest,importlib.util
import threading
from types import SimpleNamespace
from pathlib import Path
ROOT=Path(__file__).parents[1]/'addon'
sys.path.insert(0,str(ROOT))

class EpisodeBrowser(unittest.TestCase):
    def core(self):
        path=ROOT/'episode_ui.py'
        self.assertTrue(path.exists(),'Season selector and episode presentation are missing')
        spec=importlib.util.spec_from_file_location('episode_ui',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
    def test_season_selector_preserves_specials_and_ignores_paging_and_unrelated_folders(self):
        base='plugin://plugin.video.themoviedb.helper/?info=episodes&tmdb_type=tv&tmdb_id=123&season='
        entries=self.core().season_entries([
            {'file':base+'0','filetype':'directory','season':0,'episode':3},
            {'file':base+'1','filetype':'directory','season':1,'episode':8},
            {'file':'plugin://plugin.video.themoviedb.helper/?info=seasons&tmdb_id=123&page=2','label':'Next page','filetype':'directory'},
            {'file':base+'bad','filetype':'directory'}])
        self.assertEqual([(s['season'],s['label']) for s in entries],[(0,'Specials · 3 episodes'),(1,'Season 1 · 8 episodes')])
        self.assertEqual(entries[0]['path'],base+'0')
    def test_episode_caption_and_supplied_date_are_visible_without_the_hero(self):
        ui=self.core()
        card=ui.episode_card({'title':'First Period','season':1,'episode':2,'runtime':2700,'premiered':'2025-05-14'})
        self.assertEqual(card,{'caption':'S01 · E02 — First Period','meta':'45 min · May 14, 2025'})
        self.assertEqual(ui.episode_card({'label':'Next page','filetype':'directory'}),{'caption':'Next page','meta':''})
        self.assertEqual(ui.episode_card({'title':'Unknown date','season':0,'episode':1,'premiered':'bad'}),{'caption':'S00 · E01 — Unknown date','meta':''})
    def test_missing_show_heading_is_filled_without_replacing_episode_identity_or_progress(self):
        ui=self.core();old={'title':'First Period','season':1,'episode':2,'resume':{'position':25,'total':100},'file':'exact'}
        item=ui.episode_item(old,'Carrie')
        self.assertEqual(item,{**old,'showtitle':'Carrie'});self.assertNotIn('showtitle',old)
        self.assertEqual(ui.episode_item({**old,'showtitle':'Existing'},'Carrie')['showtitle'],'Existing')
    def test_season_selection_loads_the_selected_provider_route_and_keeps_selector_focusable(self):
        from test_window_lifecycle import extract
        calls=[];props={};selected=[]
        chip=SimpleNamespace(setProperty=lambda *args:None)
        control=SimpleNamespace(getSelectedPosition=lambda:1,getListItem=lambda n:chip,selectItem=lambda n:selected.append(n))
        obj=SimpleNamespace(season_sources=[{'label':'Specials','path':'specials'},{'label':'Season 1','path':'season-one'}],
            episode_browser_context={'item':{}},mode='home',stop_preview=lambda:None,getControl=lambda n:control,
            setProperty=lambda k,v:props.__setitem__(k,v),set_rows=lambda defs:calls.extend(defs))
        method=extract(ROOT/'live_review.py','select_episode_season',{},'LiveReview')
        method(obj)
        self.assertEqual(calls,[{'label':'Episodes · Season 1','path':'season-one'}])
        self.assertEqual(obj.season_position,1);self.assertEqual(selected,[1]);self.assertEqual(props['episodeBrowser'],'true')
    def test_opening_from_an_episode_selects_its_season_including_specials(self):
        from test_window_lifecycle import extract
        from test_watch_refresh import InlineThread
        from live_core import show_identity
        item={'file':'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=123&season=0&episode=2','showtitle':'Show','season':0}
        selected=[];props={};control=SimpleNamespace(getSelectedPosition=lambda:2,setHeight=lambda n:None,reset=lambda:None)
        obj=SimpleNamespace(selected=item,mode='home',last_row=0,rows=[[item],[]],paths=['old',''],histories=[],page_definitions=[],row_offset=0,row_cache={},active_page='trakt',generation=3,alive=True,list_lock=threading.Lock(),
            stop_preview=lambda:None,getControl=lambda n:control,getProperty=lambda key:'old',setProperty=lambda k,v:props.__setitem__(k,v),setFocusId=lambda n:None,
            populate_seasons=lambda:None,select_episode_season=lambda n:selected.append(n))
        namespace={'show_identity':show_identity,'threading':SimpleNamespace(Thread=InlineThread),'tmdb':lambda *args,**kwargs:'seasons',
            'season_entries':self.core().season_entries,'event':lambda *a,**kw:None,
            'get_list':lambda p:[{'file':'plugin://plugin.video.themoviedb.helper/?info=episodes&tmdb_type=tv&tmdb_id=123&season=1'}, {'file':'plugin://plugin.video.themoviedb.helper/?info=episodes&tmdb_type=tv&tmdb_id=123&season=0'}]}
        extract(ROOT/'live_review.py','browse_all_episodes',namespace,'LiveReview')(obj)
        self.assertEqual(selected,[1]);self.assertEqual(obj.season_sources[1]['season'],0)
        self.assertEqual(obj.episode_browser_context['rows'][0],[item]);self.assertEqual(props['episodeBrowser'],'true')

if __name__=='__main__':unittest.main()
