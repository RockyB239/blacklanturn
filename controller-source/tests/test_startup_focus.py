"""Cold boot stays neutral; deliberate browsing owns the preview dwell timer."""
import ast, sys, unittest
from pathlib import Path
from types import SimpleNamespace, MethodType
from xml.etree import ElementTree as E

ROOT=Path(__file__).parents[1]/'addon'
sys.path.insert(0,str(ROOT))
from live_core import row_items
def methods(names,extra=None):
    cls=next(n for n in ast.parse((ROOT/'live_review.py').read_text()).body if isinstance(n,ast.ClassDef) and n.name=='LiveReview')
    ns=dict(extra or {},row_items=row_items)
    exec(compile(ast.Module(body=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'live_review.py','exec'),ns)
    if "show_row_window" in names:
        from cache_fixture import with_cache
        ns["show_row_window"]=with_cache(ns["show_row_window"],ns)
    return ns

class StartupFocus(unittest.TestCase):
    def test_boot_has_neutral_focus_and_collapsed_sidebar(self):
        ns=methods(['initialize_startup_focus'])
        self.assertIn('initialize_startup_focus',ns,'Cold boot currently focuses the first title')
        calls=[];props={}
        s=SimpleNamespace(setFocusId=lambda v:calls.append(v),setProperty=props.__setitem__)
        ns['initialize_startup_focus'](s)
        self.assertTrue(s.startup_idle);self.assertEqual(calls,[5]);self.assertEqual(props['startupIdle'],'true')
        for attr in ('resume_backend','resume_playback'):
            calls.clear();setattr(s,attr,{'section':'Shows'})
            ns['initialize_startup_focus'](s)
            self.assertFalse(s.startup_idle);self.assertEqual(calls,[900]);delattr(s,attr)

    def test_neutral_control_is_invisible_but_remote_reachable(self):
        root=E.parse(ROOT/'resources/skins/Default/1080i/LiveReview.xml').getroot()
        self.assertEqual(root.find('defaultcontrol').text,'5')
        c=root.find("./controls/control[@id='5']")
        self.assertIsNotNone(c)
        self.assertEqual(c.find('onleft').text,'50');self.assertEqual(c.find('onright').text,'900')
        self.assertEqual(c.find('ondown').text,'900');self.assertEqual(c.find('texturefocus').text,'nav-clear.png')
        self.assertEqual(c.find('visible').text,'String.IsEqual(Window.Property(startupIdle),true)')

    def test_idle_does_not_play_and_entering_a_row_restarts_five_second_dwell(self):
        clock=[100.0];focus=[5];props={};played=[]
        def sleep(_):s.alive=False
        ns=methods(['monitor'],{'time':SimpleNamespace(monotonic=lambda:clock[0],sleep=sleep),
            'gui_labels':lambda labels:{label:1920 for label in labels},
            'xbmc':SimpleNamespace(getSkinDir=lambda:'skin.blacklanturn.preview',Monitor=lambda:SimpleNamespace(abortRequested=lambda:False),getInfoLabel=lambda _:1920),
            'caption_fit_step':lambda *a:0,'event':lambda *a,**k:None})
        control=SimpleNamespace(getSelectedPosition=lambda:0)
        s=SimpleNamespace(alive=True,owner_skin='skin.blacklanturn.preview',settings_open=False,actions_open=False,
            startup_idle=True,mode='home',fixed_hero=True,nav=False,focus_key=None,mouse=False,owned_preview=False,preview_attempts=None,preview_generation=0,
            preview_mode='auto',episode_browser_context=None,selected={'file':'a'},dwell=0,preview_key=None,config={'PreviewDelay':5},
            getProperty=lambda k:props.get(k,''),setProperty=props.__setitem__,getFocusId=lambda:focus[0],getControl=lambda _:control,
            set_nav=lambda v,**kw:setattr(s,'nav',v),sync_nav_focus=lambda focus:None,apply_nav_width=lambda:None,chosen=lambda _:s.selected,stop_preview=lambda **kw:None,
            update=lambda _:setattr(s,'dwell',clock[0]),hover=SimpleNamespace(tick=lambda *a:None),
            selected_ratings=lambda:None,rating_identity=lambda _:True,preview=lambda **kw:played.append(clock[0]))
        ns['monitor'](s);self.assertEqual(played,[]);self.assertTrue(s.startup_idle)
        focus[0]=900;s.alive=True;ns['monitor'](s)
        self.assertFalse(s.startup_idle);self.assertEqual(props['startupIdle'],'false');self.assertEqual(played,[])
        clock[0]=104.9;s.alive=True;ns['monitor'](s);self.assertEqual(played,[])
        clock[0]=105;s.alive=True;ns['monitor'](s);self.assertEqual(played,[105])

    def test_delayed_row_loader_cannot_steal_idle_focus(self):
        callbacks=[];focus=[];props={};generation=0
        control=SimpleNamespace(reset=lambda:None,setVisible=lambda _:None)
        ns=methods(['show_row_window'],{'trim_row_cache':lambda *a:None,'copy':SimpleNamespace(deepcopy=lambda x:x),
            'PageHistory':lambda:None,'row_message':lambda *a,**k:'loading','get_list':lambda _: [{'file':'a'}],
            'threading':SimpleNamespace(Thread=lambda target,**k:SimpleNamespace(start=lambda:callbacks.append(target))),
            'event':lambda *a,**k:None})
        class Lock:
            def __enter__(self):pass
            def __exit__(self,*args):pass
        s=SimpleNamespace(startup_idle=True,alive=True,row_offset=0,row_cache={},rows=[[],[]],paths=['',''],histories=[None,None],
            generation=0,page_definitions=[{'label':'Home','path':'test'}],section='Home',search_state=None,
            episode_browser_context=None,discovery_stack=[],active_page=None,adaptive_browsing=True,fixed_hero=True,
            list_lock=Lock(),getControl=lambda _:control,setProperty=props.__setitem__,getProperty=lambda k:props.get(k,''),
            stop_preview=lambda **kw:None,row_navigation=lambda:None,setFocusId=focus.append,
            apply_row=lambda n,files,*a:s.rows.__setitem__(n,files))
        ns['show_row_window'](s,0,0);self.assertEqual(focus,[])
        callbacks[0]();self.assertEqual(focus,[]);self.assertEqual(s.rows[0],[{'file':'a'}])

if __name__=='__main__':unittest.main()
