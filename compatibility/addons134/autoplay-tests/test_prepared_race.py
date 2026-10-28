"""An older background resolver must not publish after the user lowers the cap."""
import types,unittest,json
from test_dispatch import Window,method
from test_session_sources import p,source,META
class PreparedRace(unittest.TestCase):
 def test_policy_change_during_resolution_rejects_prepared_url(self):
  window=Window();state={'stamp':'old'}
  pref=types.SimpleNamespace(get=lambda m:None,get_session=lambda m: {'ceiling':4,'debrid':'TorBox'},session_candidates=lambda items,policy:items,session_stamp=lambda m:state['stamp'],PREPARED_PROPERTY='prepared-policy')
  def resolve(item):state['stamp']='new';return 'https://torbox.test/large.mp4'
  obj=types.SimpleNamespace(metaProperty='meta',debuglog=False,url='https://torbox.test/large.mp4',sourcesResolve=resolve)
  ctrl=types.SimpleNamespace(sleep=lambda _:None,monitor=types.SimpleNamespace(abortRequested=lambda:False),condVisibility=lambda _:True)
  ns={'source_preferences':pref,'playerWindow':window,'homeWindow':window,'control':ctrl,'getSetting':lambda k:'1' if k=='play.mode.tv' else 'false','jsdumps':json.dumps,'re':__import__('re'),'video_extensions':['.mp4'],'log_utils':types.SimpleNamespace(error=lambda:None)}
  method('preResolve',ns)(obj,[source(4)],dict(META,episode='2'))
  self.assertEqual(window.getProperty('umbrella.preResolved_nextUrl'),'')
