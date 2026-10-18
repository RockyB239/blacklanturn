"""Decorative preview resolution must never leave Kodi a cancellable plug-in job."""
import threading,unittest,sys
from pathlib import Path
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
import youtube_provider as provider

class PreviewResolution(unittest.TestCase):
 def state(self):
  effects=[];params={'existing':'keep'}
  ui=SimpleNamespace(set_property=lambda *a,**k:effects.append(('property',a)),clear_property=lambda *a,**k:effects.append(('clear',a)),
   get_property=lambda *a,**k:True,pop_property=lambda *a,**k:effects.append(('pop',a)),show_notification=lambda *a,**k:effects.append(('toast',a)))
  settings=SimpleNamespace(default_player_web_urls=lambda:True,default_player_fallback=lambda:True)
  context=SimpleNamespace(get_params=lambda:params,get_ui=lambda:ui,get_settings=lambda **k:settings,
   send_notification=lambda *a,**k:effects.append(('notification',a)))
  @contextmanager
  def session(current):yield SimpleNamespace(context=context,provider=object())
  def prepare(runtime,ctx):
   self.assertEqual(ctx.get_params(),{'video_id':'Abc_123-Xyz','incognito':True,'screensaver':True,'start':0.0,'end':30.0})
   self.assertFalse(ctx.get_settings().default_player_web_urls());self.assertFalse(ctx.get_settings().default_player_fallback())
   self.assertFalse(ctx.get_ui().get_property('external-player-intent',as_bool=True))
   self.assertIsNone(ctx.get_ui().pop_property('full-video-quality-prompt',as_bool=True))
   ctx.get_ui().set_property('player-data',{'use_local_history':False,'use_remote_history':False})
   ctx.send_notification('playback-init',{'preview':True})
   return SimpleNamespace(getPath=lambda:'https://fixture.invalid/resolved.mpd')
  return effects,params,session,prepare
 def resolve(self,*args,**kwargs):
  fn=getattr(provider,'resolve_preview',None);self.assertTrue(callable(fn),'Preview must resolve off the Kodi playback queue')
  return fn(*args,**kwargs)
 def test_resolution_keeps_native_side_effects_private_until_current_dispatch(self):
  effects,params,session,prepare=self.state()
  with patch.object(provider,'_session',session),patch.object(provider,'_prepare_preview',prepare,create=True):
   result=self.resolve('plugin://plugin.video.youtube/play/?video_id=Abc_123-Xyz&end=30',lambda:True)
  self.assertEqual(effects,[]);self.assertEqual(params,{'existing':'keep'})
  self.assertEqual(result.path,'https://fixture.invalid/resolved.mpd');self.assertTrue(result.publish());self.assertFalse(result.publish())
  self.assertEqual([x[0] for x in effects],['property','notification'])
 def test_cancelled_resolution_never_publishes_or_returns_a_late_player_job(self):
  effects,params,session,prepare=self.state();entered=threading.Event();release=threading.Event();owner=[True];result=[]
  def blocked(runtime,ctx):entered.set();release.wait(2);return prepare(runtime,ctx)
  with patch.object(provider,'_session',session),patch.object(provider,'_prepare_preview',blocked,create=True):
   t=threading.Thread(target=lambda:result.append(self.resolve('plugin://plugin.video.youtube/play/?video_id=Abc_123-Xyz&end=30',lambda:owner[0])));t.start()
   try:
    self.assertTrue(entered.wait(1));owner[0]=False
   finally:release.set();t.join(2)
  self.assertEqual(result,[None]);self.assertEqual(effects,[])
 def test_cancellation_after_resolution_still_prevents_native_publication(self):
  effects,params,session,prepare=self.state();owner=[True]
  with patch.object(provider,'_session',session),patch.object(provider,'_prepare_preview',prepare,create=True):result=self.resolve('plugin://plugin.video.youtube/play/?video_id=Abc_123-Xyz&end=30',lambda:owner[0])
  owner[0]=False;self.assertFalse(result.publish());self.assertEqual(effects,[])
 def test_native_plugin_or_command_fallback_is_never_sent_to_the_player(self):
  effects,params,session,prepare=self.state()
  for path in ['plugin://plugin.video.youtube/play/?video_id=wrong','command://PlayMedia(wrong)']:
   with self.subTest(path=path),patch.object(provider,'_session',session),patch.object(provider,'_prepare_preview',lambda *a:SimpleNamespace(getPath=lambda:path),create=True):
    with self.assertRaises(ValueError):self.resolve('plugin://plugin.video.youtube/play/?video_id=Abc_123-Xyz',lambda:True)
  self.assertEqual(effects,[])
