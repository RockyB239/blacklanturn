"""Real controller composition against native API substitutes; not device evidence."""
import subprocess,sys,unittest,ast,json,tempfile
from pathlib import Path
from unittest.mock import patch
from test_startup_network_imports import PROBE,ADDON
class Integration(unittest.TestCase):
    def probe(self,source):
        result=subprocess.run([sys.executable,'-I','-B','-c',PROBE+source,str(ADDON),'live_review'],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
    def test_actual_initializer_defers_workers_and_preserves_native_export(self):
        self.probe(r'''
from light_home_adapter import ControllerAdapter
from types import SimpleNamespace
assert issubclass(module.LiveReview,sys.modules['xbmcgui'].WindowXML)
class Fights(module.LiveReview):
    def onInit(self):return super().onInit()
assert Fights.__mro__[1] is module.LiveReview
class Native:
    def __getattr__(self,name):raise AssertionError('Buffered initialization touched native '+name)
queued=[]
class Thread:
    def __init__(self,target,name='',**kw):self.target=target;self.name=name
    def start(self):queued.append(self)
class Item:
    def __init__(self,**kwargs):pass
    def setArt(self,*a):pass
    def setProperty(self,*a):pass
class Window:
    def __init__(self,window_id):self.window_id=window_id;self.properties={}
    def setProperty(self,key,value):self.properties[key]=value
    def getProperty(self,key):return self.properties.get(key,'')
sys.modules['xbmcgui'].Window=Window
sys.modules['xbmcgui'].ListItem=Item
sys.modules['xbmc'].getSkinDir=lambda:'skin.blacklanturn.preview'
sys.modules['xbmc'].getCondVisibility=lambda _:False
module.threading=SimpleNamespace(Thread=Thread,RLock=threading.RLock,Lock=threading.Lock)
with tempfile.TemporaryDirectory() as temp:
    module.STORE=module.PROFILE=module.EVIDENCE=Path(temp)
    config={'Home':[],'Movies':[],'Shows':[],'Categories':[],'Saved':[],'Genres':[],'Sidebar':[]}
    (Path(temp)/'rows.json').write_text(json.dumps(config))
    c=ControllerAdapter(module.LiveReview,Native(),{'hero':'kept'})
    # These are native/network identity boundaries; all initialization and
    # native buffer behavior under test remain the real implementation.
    c.restore_preview_renderer=lambda:None
    c.refresh_preview_setup=lambda:setattr(c,'previews_ready',True)
    c.configure_icon_resources=lambda:None
    c.configure_row_snapshots=lambda:False
    c.refresh_youtube_connection=lambda **k:None
    c.onInit()
    assert c.alive and not queued, [t.name for t in queued]
    assert c.getProperty('loading')=='true'
    c.adopt({'rows':[['stable']], 'defer_startup_workers':False})
    assert c.rows==[['stable']] and c._native is not None
    c.retire();assert not c.alive and c._native is None
''')
    def test_card_builder_and_hero_projection_match_normal_rendering(self):
        self.probe(r'''
from light_home_model import HeroProjection
from light_home_adapter import ControllerAdapter
from types import SimpleNamespace
item={'file':'plugin://plugin.video.themoviedb.helper/?info=seasons&tmdb_type=tv&tmdb_id=123','filetype':'directory','title':'Example','label':'Example','plot':'A story','year':2026,'genre':['Drama'],'art':{'fanart':'https://image.tmdb.org/t/p/original/hero.jpg','landscape':'https://image.tmdb.org/t/p/w780/card.jpg','clearlogo':'https://image.tmdb.org/t/p/original/logo.png'},'rating':7.2}
owner=SimpleNamespace(_behavior=module.LiveReview,config={'TitleLogos':True,'Saved':[]},preview_mode='manual',previews_ready=True)
projection=HeroProjection(owner);got=projection.render(owner,item)
assert got['play']=='Episodes' and got['saved']=='+ My Stuff'
assert got['properties']['hero']==item['art']['fanart']
assert got['properties']['titleLogo']==item['art']['clearlogo']
assert got['properties']['allEpisodes']=='false' and got['height']==155
import ast
main=ast.parse((Path(sys.argv[1])/'live_review.py').read_text());early=ast.parse((Path(sys.argv[1])/'light_home_cards.py').read_text())
f=lambda tree:ast.dump(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='media_item'),include_attributes=False)
assert f(main)==f(early), 'Early native cards diverged from normal renderer'
''')
    def test_queued_select_uses_captured_title_when_native_selection_has_moved(self):
        self.probe(r'''
from light_home_adapter import ControllerAdapter
class Native:
    def getFocusId(self):return 900
    def getControl(self,cid):return types.SimpleNamespace(getSelectedPosition=lambda:1)
c=ControllerAdapter(module.LiveReview,Native(),{});c.adopt({})
a={'file':'A','title':'A'};b={'file':'B','title':'B'}
c.rows=[[a,b],[]];c.actions_open=False;c.owned_preview=False;c.input_generation=0;c.section='Home'
seen=[];c.details=lambda item:seen.append(item)
c.dispatch_choice('click',900,a)
assert seen==[a] and c.chosen(900) is b
''')
    def test_real_home_producer_makes_a_valid_display_record_without_mutating_rows(self):
        self.probe(r'''
import copy
import light_home_model as model,icon_packs
with tempfile.TemporaryDirectory() as temp:
    root=Path(temp);store=root/'profile';store.mkdir();icon=root/'addons/resource.images.test/icon.png';icon.parent.mkdir(parents=True);icon.write_bytes(b'image')
    icon_packs.icon_path=lambda *a:str(icon)
    model.display_scope=lambda *a:'proven-scope'
    item={'title':'Example','label':'Example','file':'plugin://plugin.video.themoviedb.helper/?info=seasons&tmdb_type=tv&tmdb_id=123','filetype':'directory','year':2026,'art':{'fanart':'https://image.tmdb.org/t/p/original/hero.jpg','landscape':'https://image.tmdb.org/t/p/w780/card.jpg'}}
    before=copy.deepcopy(item)
    owner=types.SimpleNamespace(_behavior=module.LiveReview,alive=True,section='Home',mode='home',row_offset=0,window_ready=[True,True],preview_dispatch_lock=threading.RLock(),page_definitions=[{'path':'plugin://plugin.video.themoviedb.helper/?info=trakt_recommendations&tmdb_type='+kind,'label':kind} for kind in ('movie','tv')],home_snapshot_cache=types.SimpleNamespace(scope='scope'),raw_title_row=lambda n:[item],navigation_items=[{'id':i,'label':i,'icon':i} for i in ('search','home','settings')],config={'Saved':[]},preview_mode='manual',previews_ready=True)
    owner.page_definitions += [{'label':'Additional '+str(i),'path':'plugin://plugin.video.themoviedb.helper/?info=trending_week&tmdb_type=tv'} for i in range(7)]
    assert len(owner.page_definitions)==9
    assert model.save_home_display(owner,store,root)
    record=model.validated_record(store/'home-display.json','proven-scope')
    assert record is not None
    assert record['rows'][0]['heroes'][0]['properties']['hero']==item['art']['fanart']
    assert record['properties']['notice']=='Live add-on content  ·  Select a title for details', 'Early Home omitted the normal visible navigation hint'
    assert item==before
''')
    def test_home_projection_uses_core_renderer_for_personal_native_subclass(self):
        self.probe(r'''
from light_home_model import HeroProjection
class PersonalReview(module.LiveReview):
    def update(self,item):return super().update(item)
    def rating_identity(self,item):return super().rating_identity(item)
    def display_ratings(self,badges):return super().display_ratings(badges)
owner=PersonalReview()
owner.config={'Saved':[]};owner.preview_mode='manual';owner.previews_ready=True
item={'title':'Example','label':'Example','file':'plugin://plugin.video.themoviedb.helper/?info=seasons&tmdb_type=tv&tmdb_id=123','filetype':'directory','year':2026,'art':{'fanart':'https://image.tmdb.org/t/p/original/hero.jpg'}}
projected=HeroProjection(owner).render(owner,item)
assert projected['play']=='Episodes'
assert projected['properties']['hero']==item['art']['fanart']
assert projected['properties']['allEpisodes']=='false'
''')

    def test_home_cache_proof_does_not_block_input_or_publish_a_departed_home(self):
        self.probe(r'''
import light_home_model as model
from types import SimpleNamespace
owner=SimpleNamespace(alive=True,section='Home',mode='home',row_offset=0,window_ready=[True,True],
                      generation=1,preview_dispatch_lock=threading.RLock(),
                      page_definitions=[{},{}],home_snapshot_cache=SimpleNamespace(scope='original'))
proof_started=threading.Event()
release=threading.Event()
writes=[]
def scope(*_):
    proof_started.set()
    assert release.wait(3)
    return 'verified'
model.policy_bytes=lambda _:()
model.display_scope=scope
model.write_record=lambda *args:writes.append(args)
result=[]
worker=threading.Thread(target=lambda:result.append(model.save_home_display(owner,Path('.'),Path('.'))),daemon=True)
worker.start()
try:
    assert proof_started.wait(1)
    assert owner.preview_dispatch_lock.acquire(timeout=.25), 'Home account proof blocked the navigation lock'
    owner.generation+=1
    owner.preview_dispatch_lock.release()
finally:
    release.set()
    worker.join(2)
assert result==[False] and writes==[]
''')

    def test_focus_paints_cached_ratings_once(self):
        self.probe(r'''
from light_home_model import HeroProjection
from types import SimpleNamespace
owner=SimpleNamespace(config={'Saved':[]},preview_mode='manual',previews_ready=True)
projection=HeroProjection(owner)
projection.rating_cache[('movie','123')]=['cached badge']
painted=[]
projection.display_ratings=painted.append
item={'title':'Example','file':'plugin://plugin.video.themoviedb.helper/?info=details&tmdb_type=movie&tmdb_id=123'}
projection.render(owner,item)
assert painted==[['cached badge']],painted
''')
