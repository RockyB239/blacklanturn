"""Exercise the actual Umbrella play dispatch; only provider/resolver I/O is replaced."""
import ast,copy,json,re,sys,types,unittest,os
from pathlib import Path
from unittest.mock import patch
from test_session_sources import p,source,META,ROOT

def method(name,ns,variant='candidate'):
 path=ROOT/variant/'resources/lib/modules/sources.py';tree=ast.parse(path.read_text())
 cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Sources')
 node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name)
 exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),ns);return ns[name]
class Window:
 def __init__(self):self.props={}
 def getProperty(self,key):return self.props.get(key,'')
 def setProperty(self,key,value):self.props[key]=value
 def clearProperty(self,key):self.props.pop(key,None)
class Dispatch(unittest.TestCase):
 def run_play(self,items,select=None,variant=None,policy=True,saved_pack=None,resolve=True,prepared=False,service='TorBox'):
  calls=[];window=Window()
  if prepared:
   for k,v in [('umbrella.preResolved_nextUrl','https://example.test/stale-large.mp4'),('prepared-policy','old-policy'),('umbrella.preResolved_season','1'),('umbrella.preResolved_episode','2'),('umbrella.preResolved_imdb','tt0386676'),('umbrella.preResolved_tmdb','2316')]:window.setProperty(k,v)
  nextmeta=dict(META,episode='2',title='Diversity Day')
  pref=types.SimpleNamespace(get=lambda meta:saved_pack,matching=p.matching,
   get_session=lambda meta:p.session_policy(META,source(.3,service),100) if policy else None,
   session_candidates=p.session_candidates,session_stamp=lambda m:'policy-v1' if policy else '',PREPARED_PROPERTY='prepared-policy')
  def error(*a,**kw):raise RuntimeError('Unexpected Umbrella exception')
  def autoplay(values):
   calls.append(('auto',[i['hash'] for i in values]));return 'https://example.test/episode.mp4' if resolve else None
  obj=types.SimpleNamespace(prem_providers=[True],highlight_color='white',getTitle=lambda v:v,debuglog=False,useTitleSubs=False,enable_playnext=True,
   get_season_info=lambda *a:(6,False),providercache_hours=1,getSources=lambda:None,
   sourcesAutoPlay=autoplay,sourceSelect=lambda *a:calls.append(('picker',[i['hash'] for i in a[1]])),
   errorForSources=lambda *a:calls.append(('unavailable',None)))
  for name in ['meta','season','episode','title','imdb','tmdb','tvdb','label']:setattr(obj,name+'Property',name)
  player=types.ModuleType('resources.lib.modules.player');player.Player=lambda:types.SimpleNamespace(play_source=lambda *a:calls.append(('play',a[-2])))
  package=types.ModuleType('resources.lib.modules');package.player=player
  mapping=types.ModuleType('resources.lib.modules.episode_mapping');mapping.preresolved_matches=lambda *a:True
  ctrl=types.SimpleNamespace(playlist=types.SimpleNamespace(getposition=lambda:1,size=lambda:2),sleep=lambda _:None,infoLabel=lambda _: '',hide=lambda:None)
  ns={'control':ctrl,'playerWindow':window,'homeWindow':window,'source_preferences':pref,
   'getSetting':lambda key:'1' if key=='play.mode.tv' else 'false','jsloads':json.loads,'jsdumps':json.dumps,'unquote':lambda s:s,
   'providerscache':types.SimpleNamespace(get=lambda *a:copy.deepcopy(items)),
   'log_utils':types.SimpleNamespace(error=error),'re':re}
  with patch.dict(sys.modules,{'resources':types.ModuleType('resources'),'resources.lib':types.ModuleType('resources.lib'),'resources.lib.modules':package,'resources.lib.modules.player':player,'resources.lib.modules.episode_mapping':mapping}):
   method('play',ns,variant or os.environ.get('BL_SOURCE_VARIANT','candidate'))(obj,'Diversity Day','2005','tt0386676','2316','73244','1','2','The Office','2005-03-29',json.dumps(nextmeta),select)
  return calls
 def test_next_episode_uses_only_suitable_source_and_preserves_exact_selected_identity(self):
  calls=self.run_play([source(5,hash='huge'),source(.3,hash='chosen'),source(.2,hash='small')])
  self.assertEqual(calls,[('auto',['chosen','small']),('play','https://example.test/episode.mp4')])
 def test_no_size_match_returns_picker_without_attempting_larger_source(self):
  self.assertEqual(self.run_play([source(5,hash='huge')]),[('picker',['huge'])])
 def test_explicit_source_selection_overrides_session_preference(self):
  self.assertEqual(self.run_play([source(5,hash='huge')],select='0'),[('picker',['huge'])])
 def test_failed_automatic_matches_return_picker(self):
  calls=self.run_play([source(.3,hash='chosen')],resolve=False)
  self.assertEqual(calls,[('auto',['chosen']),('picker',['chosen'])])
 def test_no_session_retains_existing_autoplay(self):
  items=[source(10,'Real-Debrid','configured-best'),source(3,'AllDebrid','second'),source(.2,'TorBox','small')]
  self.assertEqual(self.run_play(items,policy=False)[0],('auto',['configured-best','second','small']))
 def test_manual_alldebrid_choice_does_not_switch_to_torbox_on_next_episode(self):
  calls=self.run_play([source(.28,'TorBox','tb'),source(.29,'AllDebrid','ad')],service='AllDebrid')
  self.assertEqual(calls[0],('auto',['ad']))
 def test_stale_prepared_url_is_rejected_before_playing_a_larger_source(self):
  calls=self.run_play([source(.3,hash='chosen')],prepared=True)
  self.assertEqual(calls,[('auto',['chosen']),('play','https://example.test/episode.mp4')])
if __name__=='__main__':unittest.main()
