"""Display-only section cards must regain current resume at explicit Play."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs,urlsplit
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from home_rows import HomeRowSnapshots
from playback_core import resume_options
from live_runtime import write_controller_config
import test_home_progress_playback as playback
import test_section_display_snapshots as sections
from test_window_lifecycle import extract
MARK='_home_progress_scope'

class SectionSnapshotPlayback(unittest.TestCase):
 def cached(self,folder,path,item,scope,private=False):
  state,calls,controls,queue=sections.SectionDisplaySnapshots().state(folder,'Movies' if 'tmdb_type=movie' in path else 'Shows',lambda p:[copy.deepcopy(item)],scope)
  store=state.home_snapshot_cache if private else state.snapshot_cache
  self.assertTrue(store.put(path,[item]));state.set_rows([{'path':path,'label':'Saved display'}])
  self.assertEqual(calls,[],'Painting retained cards must not query metadata')
  return state,state.rows[0][0],calls,controls,queue

 def test_cached_recommendation_and_public_movie_episode_play_resolve_exact_progress_before_open(self):
  cases=((sections.route('trakt_recommendations','movie'),playback.MOVIE,True),
         (sections.route('discover','movie','&with_genres=18'),playback.MOVIE,False),
         (sections.route('discover','tv','&with_genres=18'),playback.EPISODE,False))
  for path,item,private in cases:
   with self.subTest(path=path),tempfile.TemporaryDirectory() as folder:
    runtime,modules,events,notes,scope,_=playback.PlaybackBoundary().environment(folder,lambda p,v:[copy.deepcopy(item)])
    state,cached,calls,_,_=self.cached(folder,path,item,scope,private)
    self.assertNotIn('resume',cached);self.assertEqual(cached.get(MARK),scope)
    original=copy.deepcopy(cached)
    with patch.dict(sys.modules,modules):runtime.play_and_wait(cached['file'],'owner',resume_options(cached),cached)
    self.assertEqual([kind for kind,_ in events],['provider','Player.Open']);self.assertEqual(calls,[])
    query=parse_qs(urlsplit(events[0][1]).query);self.assertEqual(query['info'],['details']);self.assertEqual(query['tmdb_id'],['42' if item is playback.MOVIE else '12'])
    if item is playback.EPISODE:self.assertEqual(query['season'],['1']);self.assertEqual(query['episode'],['2'])
    self.assertEqual(events[-1][1],{'item':{'file':item['file']},'options':{'resume':True}});self.assertEqual(notes,[]);self.assertEqual(cached,original)
    for store in (state.snapshot_cache,state.home_snapshot_cache):
     if store.path.exists():self.assertNotIn(MARK,store.path.read_text())

 def test_cached_movie_zero_progress_clears_stale_incoming_resume(self):
  with tempfile.TemporaryDirectory() as folder:
   runtime,modules,events,notes,scope,_=playback.PlaybackBoundary().environment(folder,lambda p,v:[dict(playback.MOVIE,resume={})])
   _,cached,_,_,_=self.cached(folder,sections.route('trakt_recommendations','movie'),playback.MOVIE,scope,True)
   with patch.dict(sys.modules,modules):runtime.play_and_wait(cached['file'],'owner',{'resume':True},cached)
   self.assertEqual([kind for kind,_ in events],['provider','Player.Open']);self.assertEqual(events[-1][1],{'item':{'file':cached['file']}});self.assertEqual(notes,[])

 def test_cached_movie_missing_progress_or_scope_change_cannot_open_player(self):
  for boundary in ('missing','account-before','account-during','config-during'):
   with self.subTest(boundary=boundary),tempfile.TemporaryDirectory() as folder:
    def provider(path,values):
     if boundary=='account-during':values['trakt_token']=''
     elif boundary=='config-during':Path(folder,'rows.json').write_text(json.dumps({'Saved':[{'title':'Changed'}]}))
     return [{key:value for key,value in playback.MOVIE.items() if key!='resume'}] if boundary=='missing' else [playback.MOVIE]
    runtime,modules,events,notes,scope,values=playback.PlaybackBoundary().environment(folder,provider)
    _,cached,_,_,_=self.cached(folder,sections.route('trakt_recommendations','movie'),playback.MOVIE,scope,True)
    if boundary=='account-before':values['trakt_token']=''
    with patch.dict(sys.modules,modules):runtime.play_and_wait(cached['file'],'owner',{},cached)
    self.assertFalse(any(kind=='Player.Open' for kind,_ in events));self.assertEqual(sum(kind=='provider' for kind,_ in events),0 if boundary=='account-before' else 1);self.assertTrue(notes)

 def test_matched_fresh_hydration_retires_section_guard_but_captured_card_stays_pending(self):
  with tempfile.TemporaryDirectory() as folder:
   runtime,modules,events,notes,scope,_=playback.PlaybackBoundary().environment(folder,lambda p,v:[playback.MOVIE])
   state,cached,calls,controls,queue=self.cached(folder,sections.route('trakt_recommendations','movie'),playback.MOVIE,scope,True)
   self.assertEqual(cached.get(MARK),scope);native=controls[900].items[0];queue.pop(0)()
   self.assertNotIn(MARK,state.rows[0][0]);self.assertEqual(cached[MARK],scope);self.assertIs(controls[900].items[0],native);self.assertEqual(native.resume,(40.,100.))
   fresh,refresh=state.retained_row_items({'path':sections.route('trakt_recommendations','movie')})
   self.assertFalse(refresh);self.assertNotIn(MARK,fresh[0]);self.assertEqual(fresh[0]['resume'],{'position':40,'total':100})
   with patch.dict(sys.modules,modules):runtime.play_and_wait(cached['file'],'owner',{},cached)
   self.assertEqual([kind for kind,_ in events],['provider','Player.Open']);self.assertEqual(events[-1][1]['options'],{'resume':True});self.assertEqual(notes,[])

 def test_only_playable_disk_cards_with_proven_scope_are_marked(self):
  with tempfile.TemporaryDirectory() as folder:
   path=sections.route('discover','movie','&with_genres=18');state,_,_,_=sections.SectionDisplaySnapshots().state(folder,'Movies',lambda p:[]);state.anime_metadata=None
   folder_item=dict(playback.MOVIE,filetype='directory');next_item={'file':path+'&page=2','filetype':'directory','label':'Next page'}
   state.snapshot_cache.put(path,[playback.MOVIE,folder_item,next_item],age=901);retained,refresh=state.retained_row_items({'path':path})
   self.assertTrue(refresh);self.assertEqual(retained[0].get(MARK),'account');self.assertNotIn(MARK,retained[1]);self.assertNotIn(MARK,retained[2])
   for scope_state in (None,SimpleNamespace(scope=None)):
    state.home_snapshot_cache=scope_state;retained,refresh=state.retained_row_items({'path':path});self.assertTrue(refresh);self.assertTrue(all(MARK not in item for item in retained))
   state.result_cache.put(path,[playback.MOVIE]);fresh,refresh=state.retained_row_items({'path':path});self.assertFalse(refresh);self.assertNotIn(MARK,fresh[0]);self.assertEqual(fresh[0]['resume'],playback.MOVIE['resume'])

 def test_saving_actual_guarded_movie_omits_scope_without_mutating_live_card(self):
  with tempfile.TemporaryDirectory() as folder:
   state,cached,_,_,_=self.cached(folder,sections.route('trakt_recommendations','movie'),playback.MOVIE,'account',True)
   self.assertEqual(cached.get(MARK),'account');original=copy.deepcopy(cached);target=Path(folder)/'saved.json'
   state.selected=cached;state.config={'Saved':[]};state.save=lambda:write_controller_config(target,state.config)
   click=extract(Path(__file__).parents[1]/'addon/live_review.py','onClick',{'copy':copy},'LiveReview');click(state,103)
   saved=json.loads(target.read_text())['Saved'][0];self.assertNotIn(MARK,saved);self.assertEqual(saved,{key:value for key,value in original.items() if key!=MARK});self.assertEqual(cached,original)

if __name__=='__main__':unittest.main()
