import ast
import sys
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from row_feedback import RowResultCache
from streaming_lookahead import StreamingLookahead
from test_streaming_foreground import NETFLIX
import test_streaming_services_grid as grids

SOURCE=Path(__file__).parents[1]/'addon/live_review.py'
def method(name,**namespace):
    cls=next(x for x in ast.parse(SOURCE.read_text()).body if isinstance(x,ast.ClassDef) and x.name=='LiveReview')
    fn=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name==name)
    ns=dict(event=lambda *a,**k:None,time=time,**namespace)
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(SOURCE),'exec'),ns)
    return ns[name]

class ServiceFocusController179(unittest.TestCase):
    def owner(self,now):
        return SimpleNamespace(alive=True,result_cache=RowResultCache(clock=lambda:now[0]),snapshot_cache=object(),preview_dispatch_lock=threading.RLock(),streaming_snapshot=lambda path:None,configure_row_snapshots=lambda:False)
    def prepare(self,owner,fetch):
        xbmc=SimpleNamespace(Monitor=lambda:SimpleNamespace(abortRequested=lambda:False),Player=lambda:SimpleNamespace(isPlaying=lambda:False))
        return method('prepare_streaming_lookahead',xbmc=xbmc,get_list=fetch)(owner)
    def settle(self,request):
        request.since-=1
        request.observe(NETFLIX)
        self.assertTrue(request.done.wait(1))
    def test_completed_focus_result_uses_completion_expiry_in_existing_session_cache(self):
        now=[1000.];owner=self.owner(now);calls=[]
        request,cache,revision=self.prepare(owner,lambda path:calls.append(path) or [{'file':'full','art':{'thumb':'full'},'playcount':1}])
        request.observe(NETFLIX);self.settle(request)
        now[0]=1119.
        self.assertEqual(cache.get(NETFLIX)[0]['playcount'],1)
        now[0]=1120.
        self.assertIsNone(cache.get(NETFLIX),'Picker dwell must not renew freshness')
        self.assertEqual(calls,[NETFLIX])
    def test_cache_revision_change_rejects_late_result_without_publishing(self):
        now=[1000.];owner=self.owner(now);started=threading.Event();release=threading.Event()
        def fetch(path):started.set();release.wait(2);return [{'file':'old'}]
        request,cache,_=self.prepare(owner,fetch)
        try:
            request.observe(NETFLIX);request.since-=1;request.observe(NETFLIX)
            self.assertTrue(started.wait(1));cache.clear();release.set()
            self.assertTrue(request.done.wait(1));self.assertIsNone(cache.get(NETFLIX))
            self.assertIsNone(request.take(NETFLIX,lambda:True))
        finally:release.set()
    def test_fresh_cached_service_does_not_prefetch(self):
        now=[1000.];owner=self.owner(now);owner.result_cache.put(NETFLIX,[{'file':'fresh'}]);calls=[]
        request,_,_=self.prepare(owner,lambda path:calls.append(path))
        request.observe(NETFLIX);self.settle(request);self.assertEqual(calls,[])
    def test_retained_older_service_does_not_fetch_until_its_shelf_is_opened(self):
        now=[1000.];owner=self.owner(now);calls=[]
        owner.streaming_snapshot=lambda path:SimpleNamespace(display=lambda key:([{'file':'saved'}],True))
        request,_,_=self.prepare(owner,lambda path:calls.append(path))
        request.observe(NETFLIX);self.settle(request)
        self.assertEqual(calls,[])

    def test_browse_hands_exact_selected_request_to_existing_row_handoff(self):
        request=StreamingLookahead(lambda path:None);request.path=NETFLIX
        owner=SimpleNamespace(section='Movies',actions_open=False,alive=True,generation=1,result_cache=SimpleNamespace(revision=0),stop_preview=lambda:None,configure_row_snapshots=lambda:False,retained_row_items=lambda d:([{'file':NETFLIX}],False),prepare_streaming_lookahead=lambda:(request,owner.result_cache,0),last_row=0,discovery_stack=[{}])
        def open_discovery(value):
            self.assertEqual(owner.genre_request,(request,owner.result_cache,0));self.assertTrue(request.closed.is_set())
        owner.open_regional_service=open_discovery
        store=SimpleNamespace(selected=lambda default:default,default_region=lambda:'US',visible=lambda cards,kind,region:cards)
        owner.regional_services=lambda:store
        def choose(*args,**kwargs):
            self.assertEqual(kwargs['observe'],request.observe)
            return {'file':NETFLIX}
        with patch.dict(sys.modules,{'streaming_services_ui':SimpleNamespace(choose_streaming_service=choose)}):
            method('browse_streaming_services',ROOT=None,PROFILE=None,gui_labels=lambda x:{},discovery_result=lambda card:{'rows':[]})(owner,lambda *a:'catalog')
        self.assertFalse(owner.actions_open)
        self.assertEqual(owner.discovery_stack[-1]['streaming_grid_return'],{'file':NETFLIX})

class ServiceFocusNativeGrid179(grids.GridTests):
    def test_tiles_expose_exact_catalog_path_only_when_focus_observation_enabled(self):
        self.dialog.observe=lambda path:None
        self.dialog.show_page()
        self.assertEqual(self.dialog.panel.items[0].properties['streamingLookaheadPath'],self.dialog.visible_services[0].card['file'])
        self.dialog.dismiss()
    def test_focus_observer_stops_when_modal_is_dismissed(self):
        observed=[];called=threading.Event()
        self.dialog.observe=lambda path:(observed.append(path),called.set())
        self.dialog.read_labels=lambda keys:dict(zip(keys,('5000',NETFLIX)))
        self.dialog.onInit();self.dialog.lookahead_input=True
        self.assertTrue(called.wait(1));self.dialog.dismiss();count=len(observed)
        time.sleep(.15);self.assertEqual(len(observed),count)
    def test_default_tile_does_not_consume_request_before_directional_intent(self):
        observed=[];called=threading.Event()
        self.dialog.observe=lambda path:(observed.append(path),called.set())
        self.dialog.read_labels=lambda keys:dict(zip(keys,('5000',NETFLIX)))
        self.dialog.onInit();self.assertTrue(called.wait(1))
        self.assertEqual(observed,[''])
        self.dialog.onAction(SimpleNamespace(getId=lambda:2))
        self.assertTrue(self.dialog.lookahead_input)
        self.dialog.dismiss()

    def test_manage_mode_suppresses_service_focus_requests(self):
        observed=[];called=threading.Event()
        self.dialog.observe=lambda path:(observed.append(path),called.set())
        self.dialog.read_labels=lambda keys:dict(zip(keys,('5000',NETFLIX)))
        self.dialog.onInit();self.dialog.manage=True
        self.assertTrue(called.wait(1));self.dialog.dismiss()
        self.assertEqual(observed,[''])

if __name__=='__main__':unittest.main(verbosity=2)
