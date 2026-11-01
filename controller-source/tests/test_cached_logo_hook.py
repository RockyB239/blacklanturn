import sys,tempfile,threading,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from test_logo_readability import png
class CachedLogoHook(unittest.TestCase):
 def hook(self,*args):
  from logo_readability_runtime import check_cached_logo
  return check_cached_logo(*args)
 def window(self,url):
  props={'titleLogo':url};owner=SimpleNamespace(alive=True,logo_source=url,preview_dispatch_lock=threading.RLock(),light_home_saved=True,getProperty=lambda k:props.get(k,''),setProperty=lambda k,v:props.__setitem__(k,v));return owner,props
 def test_local_dark_mark_becomes_readable_title_without_fetching_or_editing_art(self):
  with tempfile.TemporaryDirectory() as f:
   root=Path(f);thumbs=root/'thumbs';(thumbs/'0').mkdir(parents=True);art=thumbs/'0/0915489f.png';raw=png(1,1,rows=b'\0'+bytes([0,0,0,255]));art.write_bytes(raw)
   url='https://image.tmdb.org/t/p/w500/logo.png';owner,props=self.window(url);calls=[]
   def rpc(method,params):calls.append(method);return {'result':{'textures':[{'cachedurl':'0/0915489f.png'}]}}
   self.hook(owner,rpc,root,thumbs);self.assertEqual(props['titleLogo'],'');self.assertFalse(owner.light_home_saved);self.assertEqual(art.read_bytes(),raw);self.assertEqual(calls,['Textures.GetTextures'])
   self.hook(owner,lambda *a:self.fail('cached decision must skip lookup'),root,thumbs)
 def test_selected_title_change_during_cache_lookup_cannot_hide_the_new_logo(self):
  with tempfile.TemporaryDirectory() as f:
   root=Path(f);thumbs=root/'thumbs';thumbs.mkdir();(thumbs/'a.png').write_bytes(png(1,1,rows=b'\0'+bytes([0,0,0,255])));owner,props=self.window('old')
   def rpc(*args):owner.logo_source='new';props['titleLogo']='new';return {'result':{'textures':[{'cachedurl':'a.png'}]}}
   self.hook(owner,rpc,root,thumbs);self.assertEqual(props['titleLogo'],'new')
 def test_cache_miss_retries_are_bounded_and_cannot_read_outside_thumbnails(self):
  with tempfile.TemporaryDirectory() as f:
   root=Path(f);thumbs=root/'thumbs';thumbs.mkdir();secret=root/'outside.png';secret.write_bytes(png(1,1,rows=b'\0'+bytes([0,0,0,255])));owner,props=self.window('logo');calls=[]
   def rpc(*args):calls.append(1);return {'result':{'textures':[{'cachedurl':'../outside.png'}]}}
   for _ in range(10):self.hook(owner,rpc,root,thumbs)
   self.assertLessEqual(len(calls),5);self.assertEqual(props['titleLogo'],'logo')
 def test_background_queue_returns_immediately_and_allows_only_one_new_decode(self):
  import time
  from logo_readability_runtime import queue_cached_logo
  with tempfile.TemporaryDirectory() as f:
   root=Path(f);thumbs=root/'thumbs';thumbs.mkdir();(thumbs/'a.png').write_bytes(png(1,1,rows=b'\0'+bytes([0,0,0,255])));one,props=self.window('one');two,_=self.window('two');entered=threading.Event();release=threading.Event();calls=[]
   def rpc(*args):calls.append(1);entered.set();release.wait(1);return {'result':{'textures':[{'cachedurl':'a.png'}]}}
   began=time.monotonic();queue_cached_logo(one,rpc,root,thumbs);self.assertLess(time.monotonic()-began,.1);self.assertTrue(entered.wait(.5))
   queue_cached_logo(two,rpc,root,thumbs);self.assertEqual(len(calls),1);release.set()
   end=time.monotonic()+1
   while props['titleLogo'] and time.monotonic()<end:time.sleep(.01)
   self.assertEqual(props['titleLogo'],'')
   queue_cached_logo(one,lambda *args:self.fail('cached logo queued twice'),root,thumbs)
