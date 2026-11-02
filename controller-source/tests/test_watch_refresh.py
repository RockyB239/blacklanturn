"""Provider refresh must preserve title identity, cached history and failure evidence."""
import copy,sys,threading,unittest
from unittest.mock import patch
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
    def queued(self,loader,display_rows=None):
        work=[]
        class QueuedThread(InlineThread):
            def start(self):work.append(self.target)
        with patch(__name__+'.InlineThread',QueuedThread):obj,props,applied=self.refresh(loader,display_rows=display_rows)
        return obj,props,applied,work
    def test_slow_watch_refresh_does_not_lock_play_or_navigation(self):
        obj,_,_,work=self.queued(lambda source:[])
        self.assertEqual(len(work),1);self.assertFalse(obj.actions_open,'Read-only progress fetch locked the controls')
    def test_late_refresh_keeps_the_new_title_position_and_header_focus(self):
        path='plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=12&season=1&episode=2'
        newer={'file':'new-title','title':'New title'};old={'file':path}
        obj,props,applied,work=self.queued(lambda source:[old,newer] if source=='list-0' else [{'file':'second'}],display_rows=[old,newer])
        obj.getFocusId=lambda:101;obj.getControl=lambda cid:SimpleNamespace(getSelectedPosition=lambda:1 if cid==900 else 0)
        obj.selected=newer;obj.input_generation=1;work[0]()
        self.assertEqual(obj.selected['file'],'new-title');self.assertEqual(applied[0][2],1)
        self.assertNotEqual(props.get('restored_focus'),900)
    def test_read_only_refresh_does_not_release_a_newer_action_lock(self):
        obj,_,_,work=self.queued(lambda source:[]);obj.actions_open=True;work[0]()
        self.assertTrue(obj.actions_open,'Background refresh released a newer action lock')
    def test_refresh_does_not_replace_a_newer_explicit_page(self):
        obj,_,applied,work=self.queued(lambda source:[{'file':'old-page-title'}])
        obj.paths[0]='new-page';obj.selected={'file':'new-page-title'};obj.input_generation=1;work[0]()
        self.assertFalse(any(row[0]==0 for row in applied),'Old watched data replaced the newer provider page')
        self.assertEqual(obj.selected['file'],'new-page-title')
    def test_repeated_refresh_does_not_duplicate_the_same_inflight_job(self):
        obj,_,_,work=self.queued(lambda source:[]);obj.actions_open=False
        class QueuedThread(InlineThread):
            def start(self):work.append(self.target)
        namespace={'threading':SimpleNamespace(Thread=QueuedThread),'get_list':lambda source:[],
            'restored_position':restored_position,'refreshed_watch_item':refreshed_watch_item,'item_key':item_key,
            'trakt_command':trakt_command,'title_details_params':title_details_params,'event':lambda *a,**k:None}
        extract(ROOT/'live_review.py','refresh_watch_status',namespace,'LiveReview')(obj)
        self.assertEqual(len(work),1,'Refresh created duplicate provider work')
    def test_cancelled_refresh_does_not_read_retired_native_controls(self):
        holder=[];reads=[]
        def loader(source):
            holder[0].alive=False;holder[0].input_generation=1
            return [{'file':'old-title'}]
        obj,_,_,work=self.queued(loader);holder.append(obj)
        obj.getControl=lambda cid:(reads.append(cid) or SimpleNamespace(getSelectedPosition=lambda:0))
        work[0]();self.assertEqual(reads,[],'Cancelled refresh touched a retired native window')
    def test_newer_same_path_request_supersedes_old_watched_results(self):
        obj,_,applied,work=self.queued(lambda source:[{'file':'old-provider-result'}])
        obj.path_tokens={0:2};obj.rows[0]=[{'file':'new-explicit-result'}]
        obj.selected=obj.rows[0][0];obj.input_generation=1;obj.focus_key=('new',1);obj.dwell=999;work[0]()
        self.assertFalse(any(row[0]==0 for row in applied),'Older watched result replaced newer same-path results')
        self.assertEqual(obj.focus_key,('new',1));self.assertEqual(obj.dwell,999)
    def test_native_position_read_cannot_rebind_after_row_ownership_changes(self):
        obj,_,applied,work=self.queued(lambda source:[{'file':'old-provider-result'}])
        obj.selected={'file':'current-title'};obj.input_generation=1
        def position():obj.path_tokens={0:2};return 0
        obj.getControl=lambda cid:SimpleNamespace(getSelectedPosition=position)
        work[0]();self.assertFalse(any(row[0]==0 for row in applied),'Native yield allowed an obsolete bind')
    def test_cache_revision_change_retires_pending_watched_results(self):
        obj,_,applied,work=self.queued(lambda source:[{'file':'old-provider-result'}])
        obj.result_cache.clear();work[0]();self.assertEqual(applied,[])
    def test_cache_invalidation_allows_a_fresh_refresh_before_old_job_finishes(self):
        obj,_,_,work=self.queued(lambda source:[]);obj.result_cache.clear()
        class QueuedThread(InlineThread):
            def start(self):work.append(self.target)
        namespace={'threading':SimpleNamespace(Thread=QueuedThread),'get_list':lambda source:[],
            'restored_position':restored_position,'refreshed_watch_item':refreshed_watch_item,'item_key':item_key,
            'trakt_command':trakt_command,'title_details_params':title_details_params,'event':lambda *a,**k:None}
        extract(ROOT/'live_review.py','refresh_watch_status',namespace,'LiveReview')(obj)
        self.assertEqual(len(work),2,'Invalidated work suppressed a fresh refresh')
    def test_job_is_reserved_before_native_preview_stop_can_reenter(self):
        work=[];entered=[]
        class QueuedThread(InlineThread):
            def start(self):work.append(self.target)
        def setup(obj,method):
            def stop():
                if not entered:entered.append(True);method(obj)
            obj.stop_preview=stop
        with patch(__name__+'.InlineThread',QueuedThread):self.refresh(lambda source:[],before_start=setup)
        self.assertEqual(len(work),1,'Native preview stop started duplicate refresh jobs')

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
    def refresh(self,loader,failed=None,browse_state=None,display_rows=None,before_start=None):
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
        method=extract(ROOT/'live_review.py','refresh_watch_status',namespace,'LiveReview')
        if before_start:before_start(obj,method)
        method(obj,**kwargs)
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
