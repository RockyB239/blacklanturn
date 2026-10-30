"""Run the real entrypoint with a deterministic clock and native API substitutes."""
import builtins,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
import live_runtime
SOURCE=(Path(__file__).parents[1]/'addon/default.py').read_text()

class StartupOverlap(unittest.TestCase):
 def run_entry(self,cost=.6,confirmation=0,switch=None,import_error=False,abort_import=False,recovered=False,running=False):
  s=SimpleNamespace(now=0.,aborted=False,imports=[],windows=[],dialogs=[],events=[],props={'BlackLanturn.Preview.Running':'1'} if running else {})
  with tempfile.TemporaryDirectory() as folder:
   home=Path(folder);root=home/'addons/script.blacklanturn.preview';root.mkdir(parents=True);profile=home/'userdata';profile.mkdir()
   native_home=SimpleNamespace(getProperty=lambda k:s.props.get(k,''),setProperty=s.props.__setitem__,clearProperty=lambda k:s.props.pop(k,None))
   class Review:
    def __init__(self,*args):s.windows.append(s.now);self.core_settings_request=None
    def doModal(self):s.aborted=True
   def recover(*args):s.events.append('recovery');return recovered
   def sleep(ms):s.now+=ms/1000
   kodi=SimpleNamespace(getSkinDir=lambda:'other.skin' if switch is not None and s.now>=switch else 'skin.blacklanturn.preview',getCondVisibility=lambda flag:s.now<confirmation,Monitor=lambda:SimpleNamespace(abortRequested=lambda:s.aborted),sleep=sleep)
   modules={'sys':SimpleNamespace(path=[],argv=['default.py'],exc_info=sys.exc_info),'time':SimpleNamespace(monotonic=lambda:s.now,time=lambda:1000+s.now),'xbmc':kodi,'xbmcgui':SimpleNamespace(Window=lambda wid:native_home,Dialog=lambda:SimpleNamespace(ok=lambda *a:s.dialogs.append(s.now))),
    'xbmcvfs':SimpleNamespace(translatePath=lambda p:str(home if p=='special://home/' else profile)),
    'xbmcaddon':SimpleNamespace(Addon=lambda aid:SimpleNamespace(getAddonInfo=lambda k:str(profile/'addon_data/script.blacklanturn.preview'))),
    'live_runtime':live_runtime,'installer_recovery':SimpleNamespace(recover_installer=recover,RecoveryError=ValueError),'backend_core':SimpleNamespace(CoreSettingsReturn=lambda start:None)}
   def importing(name,*args,**kwargs):
    if name=='live_review':
     if not s.imports:
      s.imports.append(s.now);s.events.append('import');s.now+=cost
      if abort_import:s.aborted=True
     if import_error:raise ImportError('fixture unavailable')
     return SimpleNamespace(LiveReview=Review)
    if name in modules:return modules[name]
    return builtins.__import__(name,*args,**kwargs)
   namespace={'__file__':str(root/'default.py'),'__name__':'__main__','__builtins__':dict(vars(builtins),__import__=importing)}
   try:exec(compile(SOURCE,str(root/'default.py'),'exec'),namespace)
   except SystemExit:pass
  return s
 def test_import_work_is_inside_the_existing_one_second_wait(self):
  s=self.run_entry();self.assertEqual(s.events[:2],['recovery','import']);self.assertLess(s.imports[0],.1)
  self.assertGreaterEqual(s.windows[0],1);self.assertLessEqual(s.windows[0],1.2)
 def test_visible_skin_confirmation_still_blocks_opening(self):
  s=self.run_entry(confirmation=3);self.assertGreaterEqual(s.windows[0],3);self.assertLessEqual(s.windows[0],3.2)
 def test_skin_switch_during_preparation_cancels_opening(self):
  s=self.run_entry(switch=.3);self.assertEqual(s.windows,[]);self.assertEqual(s.dialogs,[])
 def test_import_failure_is_reported_after_confirmation_finishes(self):
  s=self.run_entry(import_error=True,confirmation=3);self.assertEqual(s.windows,[]);self.assertGreaterEqual(s.dialogs[0],3);self.assertNotIn('BlackLanturn.Preview.Running',s.props)
 def test_abort_during_import_leaves_no_window_or_error_dialog(self):
  s=self.run_entry(abort_import=True);self.assertEqual(s.windows,[]);self.assertEqual(s.dialogs,[])
 def test_pending_recovery_and_duplicate_sessions_do_not_preload(self):
  for opts in ({'recovered':True},{'running':True}):
   with self.subTest(opts=opts):
    s=self.run_entry(**opts);self.assertEqual(s.imports,[]);self.assertEqual(s.windows,[])

if __name__=='__main__':unittest.main()
