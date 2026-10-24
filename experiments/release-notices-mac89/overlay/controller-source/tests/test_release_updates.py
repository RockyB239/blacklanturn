import copy,hashlib,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
MODULE=Path(__file__).resolve().parents[1]/'addon/release_updates.py'
class ReleaseTests(unittest.TestCase):
 def setUp(self):
  self.assertTrue(MODULE.exists(),'BlackLanturn release-based notice engine is missing')
  import release_updates as u
  self.u=u;self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.home=Path(self.tmp.name)
  f=self.home/'addons/script.blacklanturn.preview/default.py';f.parent.mkdir(parents=True);f.write_text('tested release')
  self.entry={'id':'blacklanturn-1.1.20-1','edition':'apple','version':'1.1.20','revision':1,'title':'BlackLanturn 1.1.20','summary':'Tested playback and interface improvements.','sections':[{'heading':'Playback','bullets':['Play Next preferences retained.']}],'files':{'addons/script.blacklanturn.preview/default.py':hashlib.sha256(f.read_bytes()).hexdigest()}}
  self.catalog={'schema':1,'releases':[self.entry]};self.marker={'edition':'apple','build_version':'1.1.19'}
 def baseline(self):return self.u.refresh({},self.marker,self.catalog,1,self.home)
 def test_available_on_first_run_and_numeric_versions(self):
  s=self.baseline();self.assertEqual(self.u.pending(s)['kind'],'available');self.assertEqual(s['installed']['version'],'1.1.19')
  self.assertGreater(self.u.version('1.1.20'),self.u.version('1.1.9'))
 def test_same_build_patch_revision_qualifies(self):
  self.entry['version']='1.1.19';self.assertEqual(self.u.pending(self.baseline())['release']['revision'],1)
 def test_wrong_edition_older_and_equal_do_not_notify(self):
  for change in ({'edition':'general'},{'version':'1.1.18'},{'version':'1.1.19','revision':0}):
   self.entry.update(change);self.assertIsNone(self.u.pending(self.baseline()))
 def test_later_and_restart_do_not_repeat_revision(self):
  s=self.u.dismiss(self.baseline());s=self.u.refresh(s,self.marker,self.catalog,2,self.home);self.assertIsNone(self.u.pending(s))
  self.entry.update(id='next',revision=2);self.assertEqual(self.u.pending(self.u.refresh(s,self.marker,self.catalog,3,self.home))['kind'],'available')
 def test_disable_preserves_notes_and_history(self):
  s=self.baseline();s['enabled']=False;self.assertIsNone(self.u.pending(s));self.assertEqual(s['available']['sections'][0]['heading'],'Playback')
 def test_completion_requires_marker_and_required_files(self):
  s=self.baseline();self.assertEqual(self.u.pending(s)['kind'],'available')
  marker=dict(self.marker,build_version='1.1.20',release_revision=1)
  s=self.u.refresh(s,marker,self.catalog,2,self.home);self.assertEqual(self.u.pending(s)['kind'],'completed')
  self.assertEqual(len(s['history']),1);s=self.u.dismiss(s);self.assertIsNone(self.u.pending(self.u.refresh(s,marker,self.catalog,3,self.home)))
 def test_partial_or_failed_install_never_reports_success(self):
  s=self.baseline();(self.home/'addons/script.blacklanturn.preview/default.py').write_text('wrong')
  marker=dict(self.marker,build_version='1.1.20',release_revision=1)
  after=self.u.refresh(s,marker,self.catalog,2,self.home);self.assertEqual(after['installed']['version'],'1.1.19');self.assertEqual(self.u.pending(after)['kind'],'available')
 def test_quiet_existing_install_never_fabricates_completion(self):
  marker=dict(self.marker,build_version='1.1.20',release_revision=1)
  self.assertIsNone(self.u.pending(self.u.refresh({},marker,self.catalog,2,self.home)))
 def test_third_party_updates_cannot_trigger_or_enter_notes(self):
  s=self.baseline();before=copy.deepcopy(s)
  (self.home/'addons/skin.arctic.fuse/addon.xml').parent.mkdir(parents=True);(self.home/'addons/skin.arctic.fuse/addon.xml').write_text('99')
  self.assertEqual(self.u.refresh(s,self.marker,self.catalog,2,self.home),before)
  self.assertNotIn('Arctic',json.dumps(s));self.assertNotIn('inventory',s)
 def test_catalog_validation_rejects_unsafe_proof_and_bad_release(self):
  for mutate in ('path','hash','version','empty','markup'):
   cat=copy.deepcopy(self.catalog);e=cat['releases'][0]
   if mutate=='path':e['files']={'../secret':'0'*64}
   if mutate=='hash':e['files']={'addons/x/y':'oops'}
   if mutate=='version':e['version']='latest'
   if mutate=='empty':e['files']={}
   if mutate=='markup':e['sections'][0]['heading']='[B]Playback'
   with self.assertRaises(ValueError):self.u.validate_catalog(cat)
 def test_symlink_proof_cannot_complete(self):
  f=self.home/'addons/script.blacklanturn.preview/default.py';f.unlink();target=self.home/'other';target.write_text('tested release');f.symlink_to(target)
  s=self.baseline();marker=dict(self.marker,build_version='1.1.20',release_revision=1)
  self.assertNotEqual(self.u.pending(self.u.refresh(s,marker,self.catalog,2,self.home))['kind'],'completed')
 def test_atomic_state_legacy_migrates_preference_only(self):
  p=self.home/'state.json';legacy=self.home/'old.json';legacy.write_text(json.dumps({'enabled':False,'history':[{'name':'Arctic'}]}))
  s=self.u.read_state(p,legacy);self.assertFalse(s['enabled']);self.assertNotIn('Arctic',json.dumps(s));self.u.write_state(p,s);self.assertEqual(self.u.read_state(p),s)
  p.write_text('{bad');with_error=False
  try:self.u.read_state(p)
  except ValueError:with_error=True
  self.assertTrue(with_error);self.assertEqual(p.read_text(),'{bad')
 def test_local_feed_parses_and_bad_feed_does_not_overwrite_state(self):
  p=self.home/'catalog.json';p.write_text(json.dumps(self.catalog));self.assertEqual(self.u.fetch_catalog(p.as_uri()),self.catalog)
  p.write_text('x'*262145)
  with self.assertRaises(ValueError):self.u.fetch_catalog(p.as_uri())
 def test_no_mutation_and_unknown_marker_fails_closed(self):
  s=self.baseline();saved=copy.deepcopy(s);self.u.refresh(s,self.marker,self.catalog,3,self.home);self.assertEqual(s,saved)
  for m in ({},dict(self.marker,edition='unknown'),dict(self.marker,build_version='oops')):
   with self.assertRaises(ValueError):self.u.refresh(s,m,self.catalog,4,self.home)
 def test_slow_stream_cannot_hold_fetch_past_total_deadline(self):
  from unittest.mock import patch
  import types
  clock=[0.0];timeouts=[]
  class Stream:
   url='https://rockyb239.github.io/blacklanturn/hosted-files/releases-v1.json'
   fp=types.SimpleNamespace(raw=types.SimpleNamespace(_sock=types.SimpleNamespace(settimeout=lambda n:timeouts.append(n))))
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def read(self,n):clock[0]+=10;return b'x'
   def read1(self,n):clock[0]+=1;return b'x'
  with patch.object(self.u,'urlopen',return_value=Stream()),patch.object(self.u.time,'monotonic',side_effect=lambda:clock[0]):
   with self.assertRaises(OSError):self.u.fetch_catalog()
  self.assertLessEqual(clock[0],5,'Slow drip held a read beyond the total deadline')
  self.assertTrue(timeouts);self.assertLessEqual(timeouts[-1],1)
