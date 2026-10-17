"""Responses superseded while waiting for preview shutdown cannot publish."""
import threading,unittest
from types import SimpleNamespace
from test_window_lifecycle import extract,ROOT
import test_page_failures
from test_watch_refresh import InlineThread
from row_feedback import RowResultCache

class WaitingLock:
    def __init__(self):
        self.lock=threading.RLock();self.waiting=threading.Event()
    def __enter__(self):
        self.waiting.set();self.lock.acquire();return self
    def __exit__(self,*args):self.lock.release()

class ResponsePublication(unittest.TestCase):
    def run_waiting(self,obj,worker,applied,mutate):
        lock=WaitingLock();obj.preview_dispatch_lock=lock
        # Model the real apply_row lock too: old code validates before it waits.
        def apply(*args,**kwargs):
            with lock:applied.append(args)
        obj.apply_row=apply
        with lock.lock:
            thread=threading.Thread(target=worker);thread.start()
            self.assertTrue(lock.waiting.wait(2),'Response did not reach publication')
            mutate()
        thread.join(2);self.assertFalse(thread.is_alive())
    def test_row_response_rechecks_after_waiting(self):
        queue=[];applied=[];props={}
        class Thread(InlineThread):
            def start(self):queue.append(self.target)
        obj=SimpleNamespace(alive=True,generation=1,paths=['old',''],path_tokens={},result_cache=RowResultCache(),
            list_lock=threading.RLock(),cached_row_items=lambda *a,**kw:[{'file':'old/title'}],
            rows=[[],[]],failed_paths={},row_states={},setProperty=lambda k,v:props.__setitem__(k,v))
        method=extract(ROOT/'live_review.py','request_row_loads',{'threading':SimpleNamespace(Thread=Thread),'event':lambda *a,**k:None},'LiveReview')
        method(obj,[(0,{'path':'old','label':'Old'})])
        self.run_waiting(obj,queue.pop(),applied,lambda:(setattr(obj,'generation',2),obj.paths.__setitem__(0,'new')))
        self.assertEqual(applied,[]);self.assertEqual(props,{})
    def test_page_response_rechecks_before_history_and_path(self):
        queue=[]
        class Thread(InlineThread):
            def start(self):queue.append(self.target)
        obj,props,applied,method=test_page_failures.PageFailures().state(lambda p:[{'file':p}],Thread)
        method(obj,0,'plugin://plugin.video.example/old','Old');props.clear()
        self.run_waiting(obj,queue.pop(),applied,lambda:(setattr(obj,'generation',3),obj.paths.__setitem__(0,'new')))
        self.assertEqual(applied,[]);self.assertEqual(obj.paths[0],'new');self.assertEqual(obj.histories[0].pages,[])
    def test_page_error_rechecks_after_waiting(self):
        queue=[]
        class Thread(InlineThread):
            def start(self):queue.append(self.target)
        def fail(p):raise RuntimeError('offline')
        obj,props,applied,method=test_page_failures.PageFailures().state(fail,Thread)
        method(obj,0,'plugin://plugin.video.example/old','Old');props.clear()
        self.run_waiting(obj,queue.pop(),applied,lambda:setattr(obj,'generation',3))
        self.assertEqual(obj.failed_paths,{});self.assertEqual(props,{})

if __name__=='__main__':unittest.main()
