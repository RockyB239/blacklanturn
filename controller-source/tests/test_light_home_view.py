"""Native-boundary lifecycle fixtures for the retained early Home window."""
import subprocess,sys,unittest
from test_startup_network_imports import ADDON,PROBE
SETUP=r'''
sys.path.insert(0,str(Path(sys.argv[1]).parent/'tests'))
from native_list_fixture import NativeItem
from title_preferences import TitlePreferences
class Control:
    def __init__(self):self.items=[];self.position=0;self.calls=[]
    def reset(self):self.calls.append('reset');self.items=[]
    def addItems(self,items):self.items+=items
    def selectItem(self,pos):self.position=pos
    def getSelectedPosition(self):return self.position
    def __getattr__(self,name):
        if name.startswith(('set','control')):return lambda *a:None
        raise AttributeError(name)
base=sys.modules['xbmcgui'].WindowXML
base.getControl=lambda self,cid:self.controls.setdefault(cid,Control())
base.setProperty=lambda self,k,v:self.props.__setitem__(k,v)
base.getProperty=lambda self,k:self.props.get(k,'')
base.setFocusId=lambda self,cid:setattr(self,'focus',cid)
base.getFocusId=lambda self:self.focus
base.close=lambda self:setattr(self,'closed',True)
sys.modules['xbmcgui'].ListItem=NativeItem
sys.modules['xbmcgui'].getCurrentWindowId=lambda:13000
sys.modules['xbmc'].getSkinDir=lambda:'skin.blacklanturn.preview'
commands=[];sys.modules['xbmc'].executebuiltin=commands.append
queued=[]
class Thread:
    def __init__(self,target,**kw):self.target=target
    def start(self):queued.append(self)
module.threading=types.SimpleNamespace(Thread=Thread)
w=module.LightweightHome();w.props={};w.controls={};w.focus=0;w.closed=False
item={'title':'Example','label':'Example','file':'plugin://plugin.video.themoviedb.helper/?info=seasons&tmdb_type=tv&tmdb_id=123','filetype':'directory','art':{'fanart':'https://image.tmdb.org/t/p/original/hero.jpg','landscape':'https://image.tmdb.org/t/p/w780/card.jpg'},'year':2026}
hero={'properties':{'hero':item['art']['fanart'],'allEpisodes':'true'},'play':'Episodes','saved':'+ My Stuff','height':155}
rows=[{'label':label,'path':'plugin://plugin.video.themoviedb.helper/?info=trakt_recommendations&tmdb_type='+kind,'items':[dict(item)],'heroes':[hero]} for label,kind in [('Movies','movie'),('Shows','tv')]]
record={'rows':rows,'sidebar':[{'id':i,'label':i,'icon':'/addon/icon.png'} for i in ('search','home','settings')],'properties':{'previewsReady':'true','loading':'false'}}
w.early_home={'record':record,'config':{'Saved':[],'PreviewMode':'manual'},'preferences':TitlePreferences('/nonexistent/preferences.json')}
'''
class ViewTests(unittest.TestCase):
    def probe(self,extra):
        result=subprocess.run([sys.executable,'-I','-B','-c',PROBE+SETUP+extra,str(ADDON),'light_home_view'],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
    def test_native_cards_and_hero_appear_before_full_controller_import(self):
        self.probe(r'''
assert 'live_review' not in sys.modules
w.onInit()
assert 'live_review' not in sys.modules, 'First paint waited for full features'
assert w.props['hero']==item['art']['fanart'] and w.props['loading']=='false'
assert w.controls[900].items[0].art['landscape']==item['art']['landscape']
assert len(queued)==1 and w.focus==5
writes=tuple(w.controls[900].calls)
import live_review
live_review.initialize_addons=lambda:None
queued.pop().target()
assert w._import_error is None
assert commands==['SendClick(13000,5)']
assert tuple(w.controls[900].calls)==writes, 'Import worker wrote native controls'
''')
    def test_close_retires_import_and_back_cancels_pending_action(self):
        self.probe(r'''
w.onInit();w.focus=900;w.onClick(102)
assert w._intent.pending==('click',102,item['file'])
w.onAction(types.SimpleNamespace(getId=lambda:92))
assert w._intent.take() is None and w.focus==50
w.close();queued.pop().target()
assert not commands and not w._alive and w.closed
w.dispose();assert w.controller is None
''')
    def test_empty_filtered_row_falls_back_without_escaping_native_oninit(self):
        self.probe(r'''
w.early_home['preferences'].apply=lambda files:[]
w.onInit();assert w._early is None and w.props['loading']=='true' and len(queued)==1
''')

    def test_failed_attachment_closes_view_and_reports_to_launcher(self):
        self.probe(r'''
w.onInit()
class Broken:
    def onInit(self):raise ValueError('fixture')
w._imported=Broken;w._attach()
assert w.closed and not w._alive and w.startup_error=='ValueError'
assert w.controller is None
''')
