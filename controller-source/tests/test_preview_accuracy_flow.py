"""Actual preview worker must screen titles and retain cancellation ownership."""
import ast,sys,threading,unittest
from pathlib import Path
from types import SimpleNamespace,MethodType
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from live_core import preview_candidates,PreviewAttempts
from preview_identity import TitleVerifier
from preview_fallback import SecondaryPreviewLookup
from youtube_core import preview_path,video_id
class AccuracyFlow(unittest.TestCase):
 def state(self,fetcher,candidate_id='nLJR2twdK00'):
  self.clock=[100.];self.effects=[];self.calls=[];self.videos=[{'file':'plugin://plugin.video.youtube/play/?video_id='+candidate_id,'label':'Season 1 Trailer'}]
  source=Path(__file__).parents[1]/'addon/live_review.py';tree=ast.parse(source.read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LiveReview');node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='preview')
  class Thread:
   def __init__(self,target,**kw):self.target=target
   def start(self):self.target()
  def load(path):
   self.calls.append(path)
   return getattr(self,'secondary_videos',[]) if path.startswith('plugin://plugin.video.youtube/kodion/search/') else self.videos
  ns={'youtube_preview_path':preview_path,'youtube_video_id':video_id,'time':SimpleNamespace(monotonic=lambda:self.clock[0]),'threading':SimpleNamespace(Thread=Thread),'event':lambda *a,**k:None,'tmdb':lambda *a,**k:str((a,k)),'get_list':load,'cached_video_metadata':lambda *a:{},'cached_title_aliases':lambda *a:[],'preview_candidates':preview_candidates,'PreviewAttempts':PreviewAttempts,'Path':Path,'xbmcvfs':SimpleNamespace(translatePath=lambda _:'.')}
  exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),ns)
  o=SimpleNamespace(config={'PreviewLanguage':'en'},selected={'file':'selected-path','title':'American Horror Story','trailer':self.videos[0]['file']},alive=True,nav=False,player=SimpleNamespace(isPlaying=lambda:False),owned_preview=False,preview_generation=0,input_generation=0,dwell=0,preview_cache={},preview_dispatch_lock=threading.RLock(),setProperty=lambda *a:None,rating_identity=lambda item:('tv','1413'),play_preview_candidate=lambda url,*a:self.effects.append(url),preview_title_verifier=TitleVerifier(fetcher=fetcher,clock=lambda:self.clock[0]),preview_secondary_lookup=SecondaryPreviewLookup(clock=lambda:self.clock[0]))
  def stop():o.preview_generation+=1;o.owned_preview=False
  o.stop_preview=stop;o.preview=MethodType(ns['preview'],o);return o
 def test_wrong_actual_series_is_never_dispatched_or_sticky_cached(self):
  o=self.state(lambda key:'American Horror Stories Season 1 Trailer');o.preview()
  self.assertEqual(self.effects,[None]);self.assertFalse(o.preview_cache)
 def test_correct_title_is_dispatched(self):
  o=self.state(lambda key:'American Horror Story Official Trailer');o.preview();self.assertEqual(self.effects,[self.videos[0]['file']])
 def test_numbered_installment_uses_the_selected_tv_identity(self):
  o=self.state(lambda key:'American Horror Story | Installment 13 Official Teaser | FX','_DGQ0EpPdds');o.preview();self.assertEqual(self.effects,[self.videos[0]['file']])
 def test_numbered_installment_cannot_be_used_for_a_movie_identity(self):
  o=self.state(lambda key:'American Horror Story | Installment 13 Official Teaser | FX','_DGQ0EpPdds');o.rating_identity=lambda item:('movie','1413');o.preview();self.assertEqual(self.effects,[None])
 def test_failed_public_metadata_can_recover_on_reselection(self):
  values=['','American Horror Story Official Trailer'];o=self.state(lambda key:values.pop(0));o.preview();self.clock[0]+=16;o.preview()
  self.assertEqual(self.effects,[None,self.videos[0]['file']]);self.assertEqual(len([p for p in self.calls if not p.startswith('plugin://plugin.video.youtube/')]),2)
 def test_same_path_changed_title_cannot_reuse_old_approval(self):
  o=self.state(lambda key:'American Horror Story Official Trailer');o.preview();o.selected['title']='American Horror Stories';o.preview()
  self.assertEqual(self.effects,[self.videos[0]['file'],None])
 def test_cancel_during_public_lookup_never_dispatches(self):
  holder={}
  def fetch(key):holder['owner'].input_generation+=1;return 'American Horror Story Official Trailer'
  o=self.state(fetch);holder['owner']=o;o.preview();self.assertEqual(self.effects,[])
 def test_success_cache_expires_and_reloads_provider(self):
  o=self.state(lambda key:'American Horror Story Official Trailer');o.preview();o.preview();self.assertEqual(len(self.calls),1);self.clock[0]+=301;o.preview();self.assertEqual(len(self.calls),2)

 def test_episode_title_cannot_approve_a_different_series_pilot(self):
  o=self.state(lambda key:"Another Show Pilot Official Trailer");o.selected.update(title="Pilot",showtitle="American Horror Story");o.preview();self.assertEqual(self.effects,[None])

 def test_youtube_selection_previews_its_exact_id_without_a_trailer_lookup(self):
  from urllib.parse import parse_qs,urlsplit
  o=self.state(lambda key:'American Horror Story Official Trailer')
  o.selected={'file':'plugin://plugin.video.youtube/play/?video_id=Abc_123-Xyz','filetype':'file','title':'Highlighted video'}
  o.preview()
  self.assertEqual(self.calls,[])
  query=parse_qs(urlsplit(self.effects[0]).query)
  self.assertEqual(query['video_id'],['Abc_123-Xyz'])
  self.assertEqual(query['incognito'],['true']);self.assertEqual(query['screensaver'],['true']);self.assertEqual(query['end'],['0'])
  self.assertEqual(o.selected['file'],'plugin://plugin.video.youtube/play/?video_id=Abc_123-Xyz')

 def test_missing_primary_finds_correct_secondary_without_changing_selected_title(self):
  def actual(key):return 'American Horror Story Season 1 Trailer' if key=='2cFhUp_2N00' else 'American Horror Stories Season 1 Trailer'
  o=self.state(actual);self.secondary_videos=[{'file':'plugin://plugin.video.youtube/play/?video_id=2cFhUp_2N00','title':'American Horror Story Season 1 Trailer'}]
  before=dict(o.selected);o.preview()
  self.assertEqual(self.effects,['plugin://plugin.video.youtube/play/?video_id=2cFhUp_2N00'])
  self.assertEqual(o.selected,before);self.assertEqual(len(self.calls),2)
  o.preview();self.assertEqual(len(self.calls),2,'successful result must reuse existing preview cache')
 def test_approved_normal_preview_makes_no_secondary_request(self):
  o=self.state(lambda key:'American Horror Story Official Trailer');o.preview()
  self.assertEqual(len(self.calls),1);self.assertFalse(any('search/query' in p for p in self.calls))
