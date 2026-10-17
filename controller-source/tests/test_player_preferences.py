import unittest
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
import importlib.util
class PlayerPreferences(unittest.TestCase):
 def module(self):
  p=Path(__file__).parents[1]/'addon/player_preferences.py'
  self.assertTrue(p.exists(),'A curated Umbrella player chooser is missing')
  spec=importlib.util.spec_from_file_location('player_preferences',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 def test_only_supported_umbrella_playback_modes_are_offered(self):
  defs={name:{'plugin':'plugin.video.umbrella','play_episode':'plugin://plugin.video.umbrella/?action=play'} for name in ('umbrella.select.json','umbrella.autoplay.json','umbrella.rescrape.json','umbrella.traktmanager.json')}
  defs['direct.thecrew.json']={'plugin':'plugin.video.thecrew','play_episode':'plugin://plugin.video.thecrew/?action=play'}
  choices=self.module().player_choices(defs,True,'episode')
  self.assertEqual([c['file'] for c in choices],['umbrella.select.json','umbrella.autoplay.json','umbrella.rescrape.json'])
  self.assertEqual(self.module().player_choices(defs,False,'episode'),[])
 def test_exact_episode_identity_and_resume_parameters_survive_a_one_time_override(self):
  item={'file':'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=123&season=0&episode=2&resume=true&player=old&ignore_default=false','filetype':'file'}
  path=self.module().player_path(item,'umbrella.select.json');q=parse_qs(urlsplit(path).query)
  self.assertEqual(q['player'],['umbrella.select.json']);self.assertEqual(q['mode'],['play']);self.assertEqual(q['ignore_default'],['true']);self.assertEqual(q['resume'],['true']);self.assertEqual(q['episode'],['2']);self.assertEqual(q['season'],['0'])
  self.assertIsNone(self.module().player_path({**item,'filetype':'directory'},'umbrella.select.json'))
  self.assertIsNone(self.module().player_path(item,'../bad.json'))
 def test_default_setting_is_separate_for_movies_and_episodes(self):
  m=self.module();self.assertEqual(m.default_setting('episode'),'default_player_episodes');self.assertEqual(m.default_setting('movie'),'default_player_movies')
if __name__=='__main__':unittest.main()

class PlayerPreferenceController(unittest.TestCase):
 def state(self,choice):
  import tempfile,json,sys
  from types import SimpleNamespace
  from test_window_lifecycle import ROOT,extract
  sys.path.insert(0,str(ROOT));from player_preferences import player_choices,player_path,default_setting
  from live_core import episode_identity
  from playback_core import resume_options
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);folder=Path(temp.name)
  for name in ('umbrella.select.json','umbrella.autoplay.json','umbrella.rescrape.json'):
   (folder/name).write_text(json.dumps({'plugin':'plugin.video.umbrella','play_episode':'plugin://plugin.video.umbrella/?action=play'}))
  values={'default_player_episodes':'umbrella.autoplay.json play_episode','default_player_movies':'original movie default'};calls=[]
  helper=SimpleNamespace(getSetting=lambda k:values.get(k,''),setSetting=lambda k,v:values.__setitem__(k,v))
  dialogs=SimpleNamespace(select=lambda *args:choice,notification=lambda *a,**kw:None,ok=lambda *a:None)
  item={'file':'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=123&season=1&episode=2','filetype':'file'}
  state=SimpleNamespace(actions_open=False,stop_preview=lambda:calls.append('stop'),update=lambda i:None,capture_browse=lambda:{'focus':900},finish=lambda:calls.append('finish'))
  ns={'Path':Path,'json':json,'player_choices':player_choices,'player_path':player_path,'default_setting':default_setting,'episode_identity':episode_identity,'resume_options':resume_options,'rpc':lambda *a:{'result':{'addon':{'enabled':True}}},'xbmcvfs':SimpleNamespace(translatePath=lambda p:temp.name),'xbmcaddon':SimpleNamespace(Addon=lambda a:helper),'xbmcgui':SimpleNamespace(Dialog=lambda:dialogs)}
  method=extract(ROOT/'live_review.py','choose_playback_player',ns,'LiveReview')
  return method,state,item,values,calls
 def test_cancel_changes_neither_defaults_nor_playback(self):
  method,state,item,values,calls=self.state(-1);before=dict(values);method(state,item,True)
  self.assertEqual(values,before);self.assertEqual(calls,['stop']);self.assertFalse(state.actions_open);self.assertFalse(hasattr(state,'playback_request'))
 def test_save_episode_default_does_not_start_playback_or_change_movie_default(self):
  method,state,item,values,calls=self.state(0);method(state,item,True)
  self.assertEqual(values,{'default_player_episodes':'umbrella.select.json play_episode','default_player_movies':'original movie default'});self.assertEqual(calls,['stop']);self.assertFalse(state.actions_open)
 def test_choose_once_preserves_defaults_and_closes_before_provider_launch(self):
  method,state,item,values,calls=self.state(0);before=dict(values);method(state,item)
  self.assertEqual(values,before);self.assertEqual(calls,['stop','finish']);self.assertIn('player=umbrella.select.json',state.playback_request);self.assertEqual(state.playback_return,{'focus':900});self.assertFalse(state.actions_open)
