"""Prevent larger, unrelated, uncached or wrongly scoped automatic sources."""
import importlib.util,math,unittest
from pathlib import Path
ROOT=Path(__file__).parents[1]
spec=importlib.util.spec_from_file_location('trial_preferences',ROOT/'candidate/resources/lib/modules/source_preferences.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
META={'tmdb':'2316','season':'1','episode':'1'}
def source(size=0.3,debrid='TorBox',hash='chosen',**kw):
 return dict(size=size,debrid=debrid,hash=hash,source='cached torrent',url='magnet:?xt='+hash,provider='test',**kw)
class SessionSources(unittest.TestCase):
 def policy(self,item=None):
  self.assertTrue(callable(getattr(p,'session_policy',None)),'Size-aware session policy is missing')
  return p.session_policy(META,item or source(),100)
 def select(self,items,policy):
  self.assertTrue(callable(getattr(p,'session_candidates',None)),'Size-aware candidate selection is missing')
  return p.session_candidates(items,policy)
 def test_size_ceiling_chooses_same_available_source_and_does_not_mutate_metadata(self):
  chosen=source();items=[source(5,hash='huge'),source(.2,hash='small'),chosen]
  actual=self.select(items,self.policy(chosen))
  self.assertIs(actual[0],chosen);self.assertEqual([x['hash'] for x in actual],['chosen','small'])
  self.assertEqual([x['hash'] for x in items],['huge','small','chosen'])
 def test_selected_alldebrid_stays_alldebrid_even_when_torbox_is_available(self):
  policy=self.policy(source(.3,'AllDebrid'))
  result=self.select([source(.29,'AllDebrid','ad'),source(.28,'TorBox','tb'),source(.3,'Real-Debrid','rd')],policy)
  self.assertEqual([x['hash'] for x in result],['ad'])
 def test_any_manually_selected_service_is_kept_without_a_brand_preference(self):
  result=self.select([source(.28,'TorBox','tb'),source(.27,'Real-Debrid','rd'),source(.29,'AllDebrid','ad')],self.policy(source(.3,'Real-Debrid')))
  self.assertEqual([x['hash'] for x in result],['rd'])
 def test_selected_torbox_does_not_silently_fall_back_to_alldebrid(self):
  self.assertEqual(self.select([source(.2,'AllDebrid')],self.policy()),[])
 def test_unknown_nonfinite_oversized_uncached_and_folders_never_autoplay(self):
  items=[source(x,hash=str(x)) for x in [None,0,-1,'bad',math.nan,math.inf,.31]]
  items.extend([dict(source(),source='uncached torrent'),source(cloud_folder=True)])
  self.assertEqual(self.select(items,self.policy()),[])
 def test_session_applies_only_to_later_episodes_in_same_show_season_and_expires(self):
  policy=self.policy()
  self.assertTrue(callable(getattr(p,'session_applies',None)),'Session scope check is missing')
  cases=[({'tmdb':'2316','season':'1','episode':'2'},101,True),(META,101,False),({'tmdb':'999','season':'1','episode':'2'},101,False),({'tmdb':'2316','season':'2','episode':'1'},101,False),({'tmdb':'2316','season':'1','episode':'2'},21701,False)]
  for meta,now,want in cases:self.assertEqual(p.session_applies(policy,meta,now),want)
 def test_invalid_manual_choice_does_not_create_automatic_policy(self):
  self.assertIsNone(self.policy(source(size=0)))
  self.assertIsNone(p.session_policy({'tmdb':'2316'},source(),100))
 def test_maximum_three_candidates_limits_resolve_failure_delay(self):
  self.assertLessEqual(len(self.select([source(.3-i*.001,hash=str(i)) for i in range(15)],self.policy())),3)
if __name__=='__main__':unittest.main()

class SessionStorage(unittest.TestCase):
 def test_malformed_saved_window_data_is_ignored(self):
  self.assertFalse(p.session_applies([],dict(META,episode='2'),101))
 def test_resolver_fallback_does_not_raise_the_manually_selected_size_ceiling(self):
  import json,sys,types
  from unittest.mock import patch
  props={}
  window=types.SimpleNamespace(setProperty=lambda k,v:props.__setitem__(k,v),clearProperty=lambda k:props.pop(k,None))
  package=types.ModuleType('resources.lib.modules');package.control=types.SimpleNamespace(playerWindow=window)
  with patch.dict(sys.modules,{'resources':types.ModuleType('resources'),'resources.lib':types.ModuleType('resources.lib'),'resources.lib.modules':package}):
   p.remember_session(META,source(4,hash='resolved-fallback'),source(.3))
  policy=json.loads(props[p.SESSION_PROPERTY])
  self.assertEqual(policy['ceiling'],.3)
  self.assertEqual(policy['hash'],'resolved-fallback')

class ManualPolicySafety(unittest.TestCase):
 def test_unknown_resolver_fallback_keeps_selected_cap_and_provider(self):
  import json,sys,types
  from unittest.mock import patch
  props={};window=types.SimpleNamespace(setProperty=lambda k,v:props.__setitem__(k,v),clearProperty=lambda k:props.pop(k,None))
  package=types.ModuleType('resources.lib.modules');package.control=types.SimpleNamespace(playerWindow=window)
  with patch.dict(sys.modules,{'resources':types.ModuleType('resources'),'resources.lib':types.ModuleType('resources.lib'),'resources.lib.modules':package}):p.remember_session(META,source(None,'AllDebrid','unknown'),source(.3,'TorBox','manual'))
  policy=json.loads(props[p.SESSION_PROPERTY]);self.assertEqual(policy['ceiling'],.3);self.assertEqual(policy['debrid'],'TorBox')
