"""Execute exact packaged Umbrella functions with local cache/HTTP stubs."""
import ast,sys,tempfile,types,re,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'compatibility/managed-updates/umbrella'

def definition(path,name):
 tree=ast.parse(path.read_text())
 return ast.fix_missing_locations(ast.Module(body=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name],type_ignores=[]))

class RuntimeVersions(unittest.TestCase):
 def environment(self,current):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);home=Path(temp.name)
  errors=[];events=[]
  c=types.SimpleNamespace(dataPath=str(home),joinPath=lambda *p:str(Path(*p)),existsPath=lambda p:Path(p).exists(),
    transPath=lambda p:str(home),makeDirs=lambda p:Path(p).mkdir(exist_ok=True),addon=lambda aid:types.SimpleNamespace(getAddonInfo=lambda k:current),
    log=lambda *a:None,condVisibility=lambda *a:False,sleep=lambda *a:None,notification=lambda *a,**k:events.append('notification'),
    lang=lambda k:'New version %s',setSetting=lambda *a:events.append('settings'))
  scope={'xbmcaddon':types.SimpleNamespace(Addon=c.addon),'re_sub':re.sub}
  exec(compile(definition(SOURCE/'candidate/resources/lib/modules/control.py','getUmbrellaVersion'),'packaged-control','exec'),scope)
  c.getUmbrellaVersion=scope['getUmbrellaVersion']
  cache=types.ModuleType('resources.lib.database.cache');cache.control=c
  exec(compile(definition(SOURCE/'candidate/resources/lib/database/cache.py','update_cache_version'),'packaged-cache','exec'),cache.__dict__)
  cache.clrCache_version_update=lambda **k:events.append('cache-clear')
  traktsync=types.SimpleNamespace(delete_tables=lambda *a:events.append('trakt-clear') or True)
  simklsync=types.SimpleNamespace(delete_tables=lambda *a:events.append('simkl-clear') or True)
  log=types.SimpleNamespace(error=lambda:errors.append(sys.exc_info()[1]),log=lambda *a,**k:None,LOGDEBUG=0)
  modules={'resources':types.ModuleType('resources'),'resources.lib':types.ModuleType('resources.lib'),
    'resources.lib.database':types.ModuleType('resources.lib.database'),'resources.lib.modules':types.ModuleType('resources.lib.modules')}
  modules['resources.lib.database'].cache=cache;modules['resources.lib.database'].traktsync=traktsync;modules['resources.lib.database'].simklsync=simklsync
  modules['resources.lib.modules'].log_utils=log
  g={'control':c,'window':types.SimpleNamespace(setProperty=lambda *a:None),'log_utils':log,'LOGINFO':1}
  for cls in ('VersionIsUpdateCheck','AddonCheckUpdate'):
   exec(compile(definition(SOURCE/'upstream/service.py',cls),'packaged-service','exec'),g)
  return home,c,cache,modules,g,events,errors
 def test_plain_and_managed_current_and_saved_versions(self):
  for raw in ('6.7.92','1:6.7.92+blacklanturn.1','1:6.7.97+blacklanturn.2'):
   home,c,cache,mods,g,events,errors=self.environment(raw)
   expected=raw.split(':')[-1].split('+')[0]
   self.assertEqual(c.getUmbrellaVersion(),expected)
   self.assertEqual(c.getUmbrellaVersion(raw),expected)
 def test_migration_empty_old_current_managed_and_future_transitions(self):
  for old,current,clear,changed in [(None,'6.7.92',True,True),('','6.7.92',True,True),('6.7.67','6.7.92',True,True),
    ('6.7.92','6.7.92',False,False),('1:6.7.92+blacklanturn.1','6.7.92',False,False),
    ('1:6.7.92+blacklanturn.1','6.7.97',False,True)]:
   with self.subTest(old=old,current=current):
    home,c,cache,mods,g,events,errors=self.environment('1:'+current+'+blacklanturn.1')
    if old is not None:(home/'cache.v').write_text(old)
    with patch.dict(sys.modules,mods):g['VersionIsUpdateCheck']().run()
    self.assertEqual(errors,[])
    self.assertEqual((home/'cache.v').read_text(),current)
    self.assertEqual('cache-clear' in events,clear);self.assertEqual('trakt-clear' in events,clear)
    self.assertEqual('settings' in events,changed)
    with patch.dict(sys.modules,mods):g['VersionIsUpdateCheck']().run()
    self.assertEqual(errors,[]);self.assertEqual(events.count('settings'),int(changed))
 def test_stable_and_test_repository_selection_still_compare_upstream_versions(self):
  for ver,test in [('6.7.92',False),('6.7.941',True)]:
   home,c,cache,mods,g,events,errors=self.environment('1:'+ver+'+blacklanturn.1');urls=[]
   remote='6.7.97' if not test else '6.7.942'
   def get(url):urls.append(url);return types.SimpleNamespace(status_code=200,text='<addon id="plugin.video.umbrella" name="Umbrella" version="'+remote+'"/>')
   with patch.dict(sys.modules,mods|{'requests':types.SimpleNamespace(get=get)}):g['AddonCheckUpdate']().run()
   self.assertEqual(errors,[]);self.assertEqual(len(urls),1)
   self.assertEqual('umbrellakodi/' in urls[0],test);self.assertIn('notification',events)
if __name__=='__main__':unittest.main()
