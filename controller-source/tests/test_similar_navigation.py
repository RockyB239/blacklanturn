"""Details must normalize provider pagination while keeping Similar order and routes."""
import ast,copy,tempfile,threading,unittest
from types import MethodType,SimpleNamespace
from urllib.parse import parse_qs,urlsplit,urlencode
import test_experiment_lifecycle as lifecycle_fixture
from test_window_lifecycle import ROOT,extract
from browse_controls import page_cards,can_choose_genre
from live_core import PageHistory,card_artwork

class SimilarNavigation(unittest.TestCase):
    def test_details_similar_next_card_uses_owned_art_and_preserves_titles_and_exact_route(self):
        tmdb=extract(ROOT/'live_review.py','tmdb',{'TMDB':'plugin://plugin.video.themoviedb.helper/','urlencode':urlencode})
        source={'file':tmdb('play','movie',tmdb_id=42),'label':'Source'}
        origin=tmdb('recommendations','movie',tmdb_id=42)
        next_path=origin+'&page=2&cacheonly=False&plugin_category=Similar&reload=1791750000'
        titles=[{'file':tmdb('play','movie',tmdb_id=n),'label':str(n)} for n in (1,2)]
        provider=[titles[0],{'file':next_path,'filetype':'directory','label':'Next page →','art':{'landscape':'tmdb-next.png','fanart':'tmdb-next-hero.png'}},titles[1]]
        untouched=copy.deepcopy(provider);requests=[]
        with tempfile.TemporaryDirectory() as folder:
            window,queue,effects=lifecycle_fixture.ExperimentLifecycle().state(folder)
            window.configure_icon_resources=lambda:None
            window.onInit()
            ns=window.details.__func__.__globals__
            def get_list(path):
                requests.append(path)
                kind=parse_qs(urlsplit(path).query)['info'][0]
                return provider if kind=='recommendations' else []
            ns.update(tmdb=tmdb,get_list=get_list,page_cards=page_cards,PageHistory=PageHistory)
            window.details(source)
            next(worker for worker in queue if worker.name=='BlackLanturnLiveDetails').run()
            self.assertEqual([x['label'] for x in window.related],['1','2','Next'])
            self.assertEqual(window.related[:2],titles)
            next_card=window.related[-1]
            self.assertEqual(next_card['file'],next_path)
            self.assertEqual(card_artwork(next_card)['kind'],'paging')
            self.assertEqual(card_artwork(next_card)['image'],str(ROOT/'resources/media/page-next.png'))
            self.assertNotIn('landscape',next_card['art']);self.assertNotIn('fanart',next_card['art'])
            self.assertEqual(requests,[tmdb('details','movie',tmdb_id='42'),tmdb('cast','movie',tmdb_id='42'),origin])
            self.assertEqual(provider,untouched)

class SimilarPaging(unittest.TestCase):
    def state(self,provider):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        window,queue,effects=lifecycle_fixture.ExperimentLifecycle().state(folder.name)
        window.configure_icon_resources=lambda:None
        window.onInit()
        ns=window.details.__func__.__globals__
        tmdb=extract(ROOT/'live_review.py','tmdb',{'TMDB':'plugin://plugin.video.themoviedb.helper/','urlencode':urlencode})
        ns.update(tmdb=tmdb,get_list=provider,page_cards=page_cards,PageHistory=PageHistory)
        controls={}
        class Control:
            def __init__(self):self.items=[];self.position=0
            def reset(self):self.items=[]
            def addItems(self,items):self.items.extend(items)
            def getSelectedPosition(self):return self.position
            def selectItem(self,n):self.position=n
            def controlDown(self,*a):pass
            def controlRight(self,*a):pass
            def controlLeft(self,*a):pass
        window.getControl=lambda cid:controls.setdefault(cid,Control())
        focus=[900];window.getFocusId=lambda:focus[0];window.setFocusId=lambda cid:focus.__setitem__(0,cid)
        chosen=extract(ROOT/'live_review.py','chosen',{},'LiveReview');window.chosen=lambda cid:chosen(window,cid)
        methods=[n.name for n in ast.walk(ast.parse((ROOT/'live_review.py').read_text())) if isinstance(n,ast.FunctionDef)]
        if 'load_related_page' in methods:window.load_related_page=MethodType(extract(ROOT/'live_review.py','load_related_page',ns,'LiveReview'),window)
        window.onClick=MethodType(extract(ROOT/'live_review.py','onClick',ns,'LiveReview'),window)
        generic=[];window.load_path=lambda *a,**kw:generic.append((a,kw))
        source={'file':tmdb('play','movie',tmdb_id=42),'label':'Selected source','art':{'fanart':'source.jpg'}}
        window.details(source)
        next(worker for worker in queue if worker.name=='BlackLanturnLiveDetails').run();queue.clear()
        return window,queue,controls,focus,generic,source,tmdb
    def test_next_and_previous_change_visible_similar_only_and_restore_exact_anchor(self):
        requests=[]
        def provider(path):
            requests.append(path);q=parse_qs(urlsplit(path).query)
            if q['info']!=['recommendations']:return []
            if q.get('page')==['2']:return [{'file':'plugin://plugin.fixture.title/3','label':'Three'}]
            return [{'file':'plugin://plugin.fixture.title/1','label':'One'},{'file':path+'&page=2','filetype':'directory','label':'Next page'}]
        w,queue,c,focus,generic,source,tmdb=self.state(provider)
        origin=tmdb('recommendations','movie',tmdb_id='42');main_paths=list(w.paths);main_rows=copy.deepcopy(w.rows)
        c[3100].selectItem(1);focus[0]=3100
        w.onClick(3100)
        self.assertEqual(generic,[],'Similar paging must never load the hidden main row')
        queue.pop().run()
        self.assertEqual([x['label'] for x in c[3100].items],['Previous','Three'])
        self.assertEqual(c[3100].position,1);self.assertEqual(focus[0],3100)
        self.assertEqual(w.selected,source);self.assertEqual(w.mode,'details')
        self.assertEqual(w.getProperty('page'),'details');self.assertEqual(w.getProperty('scroll'),'related')
        c[3100].selectItem(0);w.onClick(3100);queue.pop().run()
        self.assertEqual([x['label'] for x in c[3100].items],['One','Next'])
        self.assertEqual(c[3100].position,1);self.assertEqual(w.selected,source)
        self.assertEqual(requests[-2:],[origin+'&page=2',origin])
        self.assertEqual(w.related_history.pages,[]);self.assertEqual(w.paths,main_paths);self.assertEqual(w.rows,main_rows)
    def test_previous_options_uses_similar_history_instead_of_the_main_row(self):
        def provider(path):
            q=parse_qs(urlsplit(path).query)
            if q['info']!=['recommendations']:return []
            if q.get('page')==['2']:return [{'file':'plugin://plugin.fixture.title/2','label':'Two'}]
            return [{'file':'plugin://plugin.fixture.title/1','label':'One'},{'file':path+'&page=2','filetype':'directory','label':'Next page'}]
        w,queue,c,focus,generic,source,tmdb=self.state(provider)
        focus[0]=3100;c[3100].selectItem(len(w.related)-1);w.onClick(3100);queue.pop().run();c[3100].selectItem(0)
        w.histories[0].push('plugin://main-row/previous',5)
        ns={'xbmcgui':SimpleNamespace(Dialog=lambda:SimpleNamespace(contextmenu=lambda labels:labels.index('Previous page') if 'Previous page' in labels else -1)),
            'can_choose_genre':can_choose_genre,'event':lambda *a,**kw:None}
        extract(ROOT/'live_review.py','title_actions',ns,'LiveReview')(w)
        self.assertEqual(generic,[],'Previous in Similar Options must not change the hidden main row')
        queue.pop().run()
        self.assertEqual(w.related_path,tmdb('recommendations','movie',tmdb_id='42'))
        self.assertEqual(w.histories[0].pages,[('plugin://main-row/previous',5)])
    def test_failed_next_retains_cards_source_and_retryable_cursor(self):
        def provider(path):
            q=parse_qs(urlsplit(path).query)
            if q['info']!=['recommendations']:return []
            if q.get('page')==['2']:raise ValueError('Provider unavailable')
            return [{'file':'plugin://plugin.fixture.title/1','label':'One'},{'file':path+'&page=2','filetype':'directory','label':'Next page'}]
        w,queue,c,focus,generic,source,tmdb=self.state(provider)
        before=copy.deepcopy(w.related);c[3100].selectItem(1);focus[0]=3100;c[3100].selectItem(len(w.related)-1);w.onClick(3100)
        self.assertEqual(generic,[])
        queue.pop().run()
        self.assertEqual(w.related,before);self.assertEqual(c[3100].items,before)
        self.assertEqual(w.selected,source);self.assertEqual(w.related_history.pages,[])
        self.assertIn('unavailable',w.getProperty('notice').lower())
    def test_completed_similar_page_does_not_steal_focus_after_user_moves_to_cast(self):
        def provider(path):
            q=parse_qs(urlsplit(path).query)
            if q['info']!=['recommendations']:return []
            if q.get('page')==['2']:return [{'file':'plugin://plugin.fixture.title/2','label':'Two'}]
            return [{'file':'plugin://plugin.fixture.title/1','label':'One'},{'file':path+'&page=2','filetype':'directory','label':'Next page'}]
        w,queue,c,focus,generic,source,tmdb=self.state(provider)
        focus[0]=3100;c[3100].selectItem(len(w.related)-1);w.onClick(3100);self.assertEqual(generic,[])
        focus[0]=3000;w.setProperty('scroll','down');queue.pop().run()
        self.assertEqual([x['label'] for x in c[3100].items],['Previous','Two'])
        self.assertEqual(focus[0],3000);self.assertEqual(w.getProperty('scroll'),'down')
        self.assertEqual(w.selected,source)
    def test_details_opened_during_similar_control_reset_rejects_the_old_commit(self):
        def provider(path):
            q=parse_qs(urlsplit(path).query)
            if q['info']!=['recommendations']:return []
            if q.get('page')==['2']:return [{'file':'plugin://plugin.fixture.title/2','label':'Old page Two'}]
            return [{'file':'plugin://plugin.fixture.title/1','label':'One'},{'file':path+'&page=2','filetype':'directory','label':'Next page'}]
        w,queue,c,focus,generic,source,tmdb=self.state(provider)
        focus[0]=3100;c[3100].selectItem(len(w.related)-1);w.onClick(3100);worker=queue.pop()
        new_title={'file':tmdb('play','movie',tmdb_id=99),'label':'New title'}
        original_reset=c[3100].reset
        def transition_during_reset():
            c[3100].reset=original_reset
            w.details(new_title)
            original_reset()
        c[3100].reset=transition_during_reset
        worker.run()
        self.assertEqual(w.selected,new_title)
        self.assertEqual(w.related,[]);self.assertEqual(c[3100].items,[])
        self.assertEqual(w.related_history.pages,[]);self.assertEqual(w.related_path,'')
        self.assertEqual(w.getProperty('notice'),'Loading details…')
        self.assertEqual(focus[0],101)
    def test_details_opened_during_similar_control_add_rejects_and_removes_the_old_cards(self):
        def provider(path):
            q=parse_qs(urlsplit(path).query)
            if q['info']!=['recommendations']:return []
            if q.get('page')==['2']:return [{'file':'plugin://plugin.fixture.title/2','label':'Old page Two'}]
            return [{'file':'plugin://plugin.fixture.title/1','label':'One'},{'file':path+'&page=2','filetype':'directory','label':'Next page'}]
        w,queue,c,focus,generic,source,tmdb=self.state(provider)
        focus[0]=3100;c[3100].selectItem(len(w.related)-1);w.onClick(3100);worker=queue.pop()
        new_title={'file':tmdb('play','movie',tmdb_id=99),'label':'New title'}
        original_add=c[3100].addItems
        def transition_during_add(items):
            c[3100].addItems=original_add
            w.details(new_title)
            original_add(items)
        c[3100].addItems=transition_during_add
        worker.run()
        self.assertEqual(w.selected,new_title)
        self.assertEqual(w.related,[]);self.assertEqual(c[3100].items,[])
        self.assertEqual(w.related_history.pages,[]);self.assertEqual(w.related_path,'')
        self.assertEqual(w.getProperty('notice'),'Loading details…')
        self.assertEqual(focus[0],101)
    def test_concurrent_details_transition_waits_for_the_native_similar_commit(self):
        def provider(path):
            q=parse_qs(urlsplit(path).query)
            if q['info']!=['recommendations']:return []
            if q.get('page')==['2']:return [{'file':'plugin://plugin.fixture.title/2','label':'Old page Two'}]
            return [{'file':'plugin://plugin.fixture.title/1','label':'One'},{'file':path+'&page=2','filetype':'directory','label':'Next page'}]
        w,queue,c,focus,generic,source,tmdb=self.state(provider)
        focus[0]=3100;c[3100].selectItem(len(w.related)-1);w.onClick(3100);worker=queue.pop()
        new_title={'file':tmdb('play','movie',tmdb_id=99),'label':'New title'}
        attempted=threading.Event();transition=None;errors=[];boundary=[]
        class SharedLock:
            def __init__(self):self.lock=threading.RLock()
            def __enter__(self):
                if threading.current_thread() is transition:attempted.set()
                self.lock.acquire();return self
            def __exit__(self,*args):self.lock.release()
        w.preview_dispatch_lock=SharedLock()
        def open_new_details():
            try:w.details(new_title)
            except BaseException as error:errors.append(error)
        transition=threading.Thread(target=open_new_details)
        original_reset=c[3100].reset
        def transition_during_reset():
            c[3100].reset=original_reset
            transition.start()
            boundary.append((attempted.wait(2),copy.deepcopy(w.selected)))
            original_reset()
        c[3100].reset=transition_during_reset
        worker.run();transition.join(2)
        self.assertFalse(transition.is_alive());self.assertEqual(errors,[])
        self.assertEqual(boundary,[(True,source)],'The owner transition must wait for the shared native commit lock')
        self.assertEqual(w.selected,new_title);self.assertEqual(w.related,[])
        self.assertEqual(c[3100].items,[]);self.assertEqual(w.getProperty('notice'),'Loading details…')
    def test_stale_similar_page_cannot_replace_reopened_details_for_the_same_title(self):
        def provider(path):
            q=parse_qs(urlsplit(path).query)
            if q['info']!=['recommendations']:return []
            return [{'file':'plugin://plugin.fixture.title/1','label':'One'},{'file':path+'&page=2','filetype':'directory','label':'Next page'}]
        w,queue,c,focus,generic,source,tmdb=self.state(provider)
        focus[0]=3100;c[3100].selectItem(len(w.related)-1);w.onClick(3100);self.assertEqual(generic,[])
        worker=queue.pop();w.details(dict(source))
        before=copy.deepcopy(w.related);worker.run()
        self.assertEqual(w.related,before);self.assertEqual(c[3100].items,[])
        self.assertEqual(w.selected,source)

if __name__=='__main__':unittest.main()
