"""Provider refresh must preserve title identity, cached history and failure evidence."""
import copy,sys,threading,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from test_window_lifecycle import extract,ROOT
from playback_core import restored_position,refreshed_watch_item,item_key,trakt_command
from live_core import PageHistory,title_details_params

class InlineThread:
    def __init__(self,target,**kwargs):self.target=target
    def start(self):self.target()

class WatchRefresh(unittest.TestCase):
    def test_snapshot_is_independent_of_background_row_and_history_mutations(self):
        history=PageHistory();history.push('previous-list',4)
        obj=SimpleNamespace(section='Shows',mode='home',navigation_id='shows',active_page='trakt',
            page_definitions=[{'label':'Watching','path':'provider-list'}],row_offset=2,row_cache={},
            rows=[[{'file':'episode','resume':{'position':20,'total':100}}],[]],paths=['provider-list',''],
            histories=[history,PageHistory()],last_row=0,return_focus=900,selected={'file':'episode'},
            person_context=None,episode_browser_context=None,season_sources=[],season_title='',season_position=0,getFocusId=lambda:900,
            getControl=lambda cid:SimpleNamespace(getSelectedPosition=lambda:0),getProperty=lambda key:'top' if key=='scroll' else '')
        snapshot=extract(ROOT/'live_review.py','capture_browse',{'copy':copy},'LiveReview')(obj)
        obj.rows[0][0]['resume']['position']=70;history.push('another-list',8)
        self.assertEqual(snapshot['rows'][0][0]['resume']['position'],20)
        self.assertEqual(snapshot['histories'][0].pages,[('previous-list',4)])
        self.assertEqual(snapshot['focus'],900);self.assertEqual(snapshot['row_offset'],2)
    def refresh(self,loader,failed=None,browse_state=None,display_rows=None):
        path='plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=12&season=1&episode=2'
        selected={'file':path,'resume':{'position':20,'total':100},'title':'Episode 2'}
        obj=SimpleNamespace(actions_open=False,stop_preview=lambda:None,generation=2,alive=True,
            getFocusId=lambda:900,setFocusId=lambda cid:props.__setitem__('restored_focus',cid),
            list_lock=threading.Lock(),selected=selected,paths=['list-0','list-1'],rows=[[selected],[{'file':'second'}]],row_cache={8:'stale'},failed_paths=copy.deepcopy(failed or {}),
            getControl=lambda cid:SimpleNamespace(getSelectedPosition=lambda:0),
            setProperty=lambda key,value:props.__setitem__(key,value),getProperty=lambda key:'Row',section='Shows')
        props={};applied=[]
        obj.apply_row=lambda n,files,label,position,**kwargs:applied.append((n,files,position,label))
        obj.update=lambda item:setattr(obj,'selected',item)
        namespace={'threading':SimpleNamespace(Thread=InlineThread),'time':SimpleNamespace(monotonic=lambda:100),
            'get_list':loader,'restored_position':restored_position,'refreshed_watch_item':refreshed_watch_item,
            'item_key':item_key,'trakt_command':trakt_command,'title_details_params':title_details_params,
            'event':lambda *args,**kwargs:None}
        kwargs={'browse_state':browse_state} if browse_state else {}
        if browse_state:obj.rows[0].insert(0,{'file':'neighbor'})
        if display_rows is not None:obj.rows[0]=display_rows
        extract(ROOT/'live_review.py','refresh_watch_status',namespace,'LiveReview')(obj,**kwargs)
        return obj,props,applied
    def test_playback_return_passes_saved_selection_to_refresh_before_native_frame(self):
        state={'positions':[1,-1],'focus':101};calls=[]
        obj=SimpleNamespace(resume_playback=state,restore_browse=lambda value:None,
            refresh_watch_status=lambda **kwargs:calls.append(kwargs))
        extract(ROOT/'live_review.py','start',{'event':lambda *a,**k:None},'LiveReview')(obj)
        self.assertEqual(calls,[{'sync':True,'browse_state':state}])
    def test_refresh_uses_saved_card_and_focus_when_native_controls_are_still_at_zero(self):
        path='plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=12&season=1&episode=2'
        obj,props,applied=self.refresh(lambda source:[{'file':'neighbor'},{'file':path}] if source=='list-0' else [{'file':'second'}],
            browse_state={'positions':[1,0],'focus':101})
        self.assertEqual(applied[0][2],1)
        self.assertEqual(props['restored_focus'],101)
    def test_raw_saved_position_keeps_selected_title_after_hidden_title_is_filtered(self):
        path='plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=12&season=1&episode=2'
        hidden={'file':'hidden'};selected={'file':path};neighbor={'file':'neighbor'}
        state={'rows':[[hidden,selected,neighbor],[{'file':'second'}]],'positions':[1,0],'focus':900}
        obj,props,applied=self.refresh(lambda source:[selected,neighbor] if source=='list-0' else [{'file':'second'}],browse_state=state,display_rows=[selected,neighbor])
        self.assertEqual(applied[0][2],0,'Saved raw position must anchor Selected, not its visible neighbor')
        self.assertEqual(obj.selected['file'],path)
        self.assertEqual(props['restored_focus'],900)

    def test_provider_reordering_keeps_exact_episode_and_updates_its_real_progress(self):
        path='plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=12&season=1&episode=2'
        def loader(source):
            return [{'file':'other'},{'file':path,'resume':{'position':75,'total':100}}] if source=='list-0' else [{'file':'second'}]
        obj,props,applied=self.refresh(loader)
        self.assertEqual(applied[0][2],1)
        self.assertEqual(obj.selected['title'],'Episode 2');self.assertEqual(obj.selected['resume']['position'],75)
        self.assertEqual(obj.row_cache,{})
        self.assertEqual(props['restored_focus'],900)
        self.assertFalse(obj.actions_open)
    def test_unavailable_provider_keeps_old_rows_and_status(self):
        calls=[]
        def loader(source):
            calls.append(source)
            raise RuntimeError('offline')
        obj,props,applied=self.refresh(loader)
        self.assertEqual(calls,['list-0','list-1'])
        self.assertEqual(applied,[]);self.assertEqual(obj.selected['resume']['position'],20)
        self.assertIn('could not refresh',props['notice']);self.assertFalse(obj.actions_open)
    def test_successful_refresh_removes_recovered_rows_old_error_heading_and_retry(self):
        obj,props,applied=self.refresh(lambda source:[{'file':'second'}],failed={1:{'path':'list-1','label':'Next episodes'}})
        self.assertEqual(applied[1][3],'Next episodes')
        self.assertNotIn(1,obj.failed_paths)

if __name__=='__main__':unittest.main()
