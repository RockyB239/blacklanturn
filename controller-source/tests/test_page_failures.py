from urllib.parse import parse_qs,urlsplit
import copy,sys,unittest,threading
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from test_window_lifecycle import extract,ROOT
from test_watch_refresh import InlineThread
from live_core import PageHistory,valid_source
from row_feedback import row_message,provider_page_label
from filtered_pages import provider_path

class PageFailures(unittest.TestCase):
    def state(self,loader,thread=InlineThread):
        history=PageHistory();props={};applied=[];old='plugin://plugin.video.example/first'
        obj=SimpleNamespace(paths=[old,''],histories=[history,PageHistory()],rows=[[{'file':'original'}],[]],
            preview_dispatch_lock=threading.RLock(),alive=True,generation=2,row_offset=0,row_cache={},row_states={},failed_paths={},path_tokens={},stop_preview=lambda:None,
            getControl=lambda n:SimpleNamespace(getSelectedPosition=lambda:4),setFocusId=lambda n:None,
            getProperty=lambda k:'Original row',setProperty=lambda k,v:props.__setitem__(k,v),
            apply_row=lambda *args,**kwargs:applied.append(args))
        ns={'parse_qs':parse_qs,'urlsplit':urlsplit,'copy':copy,'valid_source':valid_source,'provider_page_label':provider_page_label,'provider_path':provider_path,'threading':SimpleNamespace(Thread=thread),
            'get_list':loader,'row_message':row_message,'event':lambda *a,**kw:None}
        method=extract(ROOT/'live_review.py','load_path',ns,'LiveReview')
        return obj,props,applied,method
    def test_failed_forward_page_keeps_current_route_titles_and_history(self):
        def fail(path):raise RuntimeError('offline')
        obj,props,applied,method=self.state(fail);target='plugin://plugin.video.example/next'
        method(obj,0,target,'Next')
        self.assertEqual(obj.paths[0],'plugin://plugin.video.example/first')
        self.assertEqual(obj.histories[0].pages,[]);self.assertEqual(applied,[])
        self.assertEqual(obj.failed_paths[0]['path'],target);self.assertEqual(obj.row_states[0],'error')
    def test_newer_page_request_wins_when_workers_finish_out_of_order(self):
        queue=[]
        class Thread(InlineThread):
            def start(self):queue.append(self.target)
        obj,props,applied,method=self.state(lambda p:[{'file':p}],Thread)
        method(obj,0,'plugin://plugin.video.example/old');method(obj,0,'plugin://plugin.video.example/new')
        queue[1]();queue[0]()
        self.assertEqual(len(applied),1);self.assertEqual(obj.paths[0],'plugin://plugin.video.example/new')
        self.assertEqual(obj.histories[0].pages,[('plugin://plugin.video.example/first',4)])
    def test_retrying_failed_back_does_not_leave_a_duplicate_back_step(self):
        obj,props,applied,_=self.state(lambda p:[]);calls=[]
        target='plugin://plugin.video.example/prior';obj.histories[0].push(target,2)
        obj.row_states={0:'error'};obj.failed_paths={0:{'path':target,'label':'Prior','back':True,'position':2}}
        obj.load_path=lambda n,**kwargs:calls.append((n,kwargs))
        extract(ROOT/'live_review.py','retry_lists',{},'LiveReview')(obj)
        self.assertEqual(obj.histories[0].pages,[]);self.assertEqual(calls[0][1]['path'],target)

    def test_paging_keeps_the_list_heading_and_back_keeps_the_card_position(self):
        obj,props,applied,method=self.state(lambda p:[{'file':p}])
        origin='plugin://plugin.video.themoviedb.helper/?info=search&tmdb_type=movie&query=Alien&nextpage=true&widget=true'
        obj.paths[0]=origin
        method(obj,0,origin+'&page=2&cacheonly=False&plugin_category=Search+-+Alien&reload=1791750000','Next page')
        self.assertEqual(applied[0][2],'Original row','Pagination must retain the list name')
        prior=obj.histories[0].pop();method(obj,0,prior[0],back=True,position=prior[1])
        self.assertEqual(applied[1][2],'Original row')
        self.assertEqual(applied[1][3],4)

    def test_new_category_with_a_page_parameter_keeps_its_own_heading(self):
        obj,props,applied,method=self.state(lambda p:[{'file':p}])
        obj.paths[0]='plugin://plugin.video.themoviedb.helper/?info=episodes&tmdb_id=42&season=1&page=1'
        method(obj,0,'plugin://plugin.video.themoviedb.helper/?info=episodes&tmdb_id=42&season=2&page=2','Season 2')
        self.assertEqual(applied[0][2],'Season 2')

    def test_page_loading_guard_survives_an_obsolete_worker_and_clears_on_completion(self):
        queue=[]
        class Thread(InlineThread):
            def start(self):queue.append(self.target)
        obj,props,applied,method=self.state(lambda p:[{'file':p}],Thread)
        method(obj,0,'plugin://plugin.video.example/old')
        method(obj,0,'plugin://plugin.video.example/new')
        self.assertTrue(getattr(obj,'loading_paths',{}),'Pending page loads must block the preview monitor')
        queue[0]()
        self.assertTrue(obj.loading_paths,'An obsolete worker must not release the newer page guard')
        queue[1]()
        self.assertEqual(obj.loading_paths,{})
        self.assertEqual(obj.paths[0],'plugin://plugin.video.example/new')

    def test_monitor_does_not_restart_the_previous_title_while_page_is_loading(self):
        abort=iter([False,True]);sleeps=[]
        obj=SimpleNamespace(alive=True,owner_skin='skin.blacklanturn.preview',settings_open=False,actions_open=False,
            loading_paths={0:1},apply_nav_width=lambda:None,getProperty=lambda k:'false',getFocusId=lambda:self.fail('Pending page must guard old row selection'))
        ns={'xbmc':SimpleNamespace(getSkinDir=lambda:obj.owner_skin,Monitor=lambda:SimpleNamespace(abortRequested=lambda:next(abort))),
            'time':SimpleNamespace(sleep=lambda seconds:sleeps.append(seconds))}
        extract(ROOT/'live_review.py','monitor',ns,'LiveReview')(obj)
        self.assertEqual(len(sleeps),1)

if __name__=='__main__':unittest.main()

class RetryFocus(unittest.TestCase):
    state=PageFailures.state
    def test_retry_completion_does_not_steal_focus_from_a_different_row(self):
        queue=[];focus=[900]
        class Thread(InlineThread):
            def start(self):queue.append(self.target)
        obj,props,applied,method=self.state(lambda p:[{'file':p}],Thread)
        obj.getFocusId=lambda:focus[0]
        obj.setFocusId=lambda cid:focus.__setitem__(0,cid)
        obj.rows[1]=[{'file':'second-original'}];obj.paths[1]='plugin://plugin.video.example/second'
        obj.row_states={1:'error'};obj.load_path=lambda n,*args,**kwargs:method(obj,n,*args,**kwargs)
        extract(ROOT/'live_review.py','retry_lists',{},'LiveReview')(obj)
        queue[0]()
        self.assertEqual(focus[0],900,'Background retry stole the selected row')


class ExplicitOpenFocus(unittest.TestCase):
    state=PageFailures.state
    def test_hero_open_from_second_row_focuses_loaded_child_row(self):
        obj,props,applied,load=self.state(lambda path:[{'file':'child-episode'}])
        focus=[901];obj.getFocusId=lambda:focus[0];obj.setFocusId=lambda cid:focus.__setitem__(0,cid)
        obj.selected={'file':'plugin://plugin.video.example/seasons','title':'Show','filetype':'directory'}
        obj.load_path=lambda n,*args,**kwargs:load(obj,n,*args,**kwargs)
        extract(ROOT/'live_review.py','onClick',{'discovery_result':lambda item:None},'LiveReview')(obj,101)
        self.assertEqual(obj.paths[0],'plugin://plugin.video.example/seasons')
        self.assertEqual(focus[0],900,'Explicit Open must focus the child results')
