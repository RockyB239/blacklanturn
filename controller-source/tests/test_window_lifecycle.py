"""Native controls must not survive a skin switch or own provider playback."""
import ast, sys, unittest, time, threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from playback_core import resume_options

ROOT=Path(__file__).parents[1]/'addon'
def extract(path, name, namespace, class_name=None):
    namespace.setdefault("time",time)
    nodes=ast.parse(path.read_text()).body
    if class_name:nodes=next(n for n in nodes if isinstance(n,ast.ClassDef) and n.name==class_name).body
    method=next(n for n in nodes if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[method],type_ignores=[]),str(path),'exec'),namespace)
    if class_name=="LiveReview" and name in ("show_row_window","save","refresh_watch_status"):
        from cache_fixture import with_cache
        return with_cache(namespace[name],namespace)
    if class_name=="LiveReview" and name in ("apply_row","update","row_navigation"):
        method=namespace[name]
        def initialized(window,*args,**kwargs):
            if not hasattr(window,"preview_dispatch_lock"):window.preview_dispatch_lock=threading.RLock()
            return method(window,*args,**kwargs)
        return initialized
    return namespace[name]

class WindowLifecycle(unittest.TestCase):
    def test_foreign_skin_reinitialization_closes_before_touching_native_controls(self):
        calls=[]
        def forbidden(*args):self.fail('Reloaded controls must not be mutated under another skin')
        obj=SimpleNamespace(owner_skin='skin.blacklanturn.preview',alive=True,owned_preview=True,
            stop_preview=lambda:calls.append('stop'),close=lambda:calls.append('close'),setProperty=forbidden)
        method=extract(ROOT/'live_review.py','onInit',{'xbmc':SimpleNamespace(getSkinDir=lambda:'skin.arctic.fuse.2')},'LiveReview')
        method(obj)
        self.assertFalse(obj.alive);self.assertEqual(calls,['stop','close'])

    def test_play_click_returns_a_request_instead_of_launching_inside_window_callback(self):
        calls=[]
        obj=SimpleNamespace(selected={'file':'plugin://plugin.video.test/?action=play'},
            stop_preview=lambda:calls.append('stop'),finish=lambda:calls.append('close'),
            capture_browse=lambda:{'section':'Shows','position':3})
        xbmc=SimpleNamespace(executebuiltin=lambda *args:self.fail('Provider must launch after the window returns'))
        method=extract(ROOT/'live_review.py','onClick',{'xbmc':xbmc,'resume_options':resume_options,'discovery_result':__import__('search_ui').discovery_result},'LiveReview');method(obj,101)
        self.assertEqual(obj.playback_request,obj.selected['file']);self.assertEqual(calls,['stop','close'])
        self.assertEqual(obj.playback_return,{'section':'Shows','position':3})

    def test_playback_return_restores_state_and_does_not_open_provider_in_native_callback(self):
        opened=[];order=[];abort=[False]
        class Window:
            def __init__(self,*args):
                opened.append(self)
                self.core_settings_request=None
                self.playback_request='plugin://plugin.video.test/?play=2' if len(opened)==1 else None
                self.playback_return={'section':'Shows','position':3} if len(opened)==1 else None
                self.playback_options={'resume':22.7}
            def doModal(self):order.append('closed')
        def provider(path,skin,options,target):
            self.assertEqual(order,['closed'])
            self.assertEqual(path,'plugin://plugin.video.test/?play=2')
            self.assertEqual(options,{'resume':22.7})
            order.append('provider');return True
        namespace={'xbmc':SimpleNamespace(getSkinDir=lambda:'skin.blacklanturn.preview',Monitor=lambda:SimpleNamespace(abortRequested=lambda:abort[0])),
            'ROOT':ROOT,'time':SimpleNamespace(monotonic=lambda:0),'record':lambda *a,**k:None}
        run=extract(ROOT/'default.py','run_live_review',namespace)
        with patch.dict(sys.modules,{'live_review':SimpleNamespace(LiveReview=Window),'playback_runtime':SimpleNamespace(play_and_wait=provider),
            'backend_core':SimpleNamespace(CoreSettingsReturn=lambda started:None)}):
            run()
        self.assertEqual(len(opened),2)
        self.assertEqual(opened[1].resume_playback,{'section':'Shows','position':3})

    def test_settings_return_does_not_reopen_blacklanturn_under_a_different_skin(self):
        skin=['skin.blacklanturn.preview'];opened=[]
        class Window:
            def __init__(self,*args):
                opened.append(True)
                if len(opened)>1:raise AssertionError('Preview reopened under the previous skin')
                self.core_settings_request={'target':'interfacesettings','category':4,'row':0}
            def doModal(self):pass
        xbmc=SimpleNamespace(getSkinDir=lambda:skin[0],Monitor=lambda:SimpleNamespace(abortRequested=lambda:False),
            executebuiltin=lambda *args:skin.__setitem__(0,'skin.arctic.fuse.2'))
        namespace={'xbmc':xbmc,'xbmcgui':SimpleNamespace(getCurrentWindowId=lambda:10000),
            'ROOT':ROOT,'time':SimpleNamespace(monotonic=lambda:0),'record':lambda *a,**k:None}
        run=extract(ROOT/'default.py','run_live_review',namespace)
        with patch.dict(sys.modules,{'live_review':SimpleNamespace(LiveReview=Window),
            'backend_core':SimpleNamespace(CoreSettingsReturn=lambda started:SimpleNamespace(tick=lambda *args:'returned'))}):
            run()
        self.assertEqual(len(opened),1)

    def test_pending_trakt_action_ignores_navigation_and_play_clicks(self):
        obj=SimpleNamespace(actions_open=True,getFocusId=lambda:self.fail('Pending action must keep its target'),
                            selected={'file':'provider'},stop_preview=lambda:self.fail('Playback must not start'))
        on_action=extract(ROOT/'live_review.py','onAction',{},'LiveReview')
        on_click=extract(ROOT/'live_review.py','onClick',{},'LiveReview')
        on_action(obj,SimpleNamespace(getId=lambda:4));on_click(obj,101)

if __name__=='__main__':unittest.main()
