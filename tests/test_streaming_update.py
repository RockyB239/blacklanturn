"""Bounded update I/O must preserve exact trees and reject drift before expansion."""
import hashlib,importlib.util,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import test_inplace_update as fixtures
ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/libs'
def component():
 s=importlib.util.spec_from_file_location('streaming_component_test',LIB/'component_update.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class StreamingInPlace(unittest.TestCase):
 def setUp(self):
  self.fixture=fixtures.InPlace();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
 def test_large_addon_payload_and_installed_files_are_streamed(self):
  f=self.fixture;raw=b'abcdefgh'*1024*1024
  (f.home/'addons'/f.aid/'lib/large.bin').write_bytes(raw)
  f.data['addons/'+f.aid+'/lib/large.bin']=raw[::-1]
  full_reads=[];real_zip=zipfile.ZipFile.read;real_path=Path.read_bytes
  def zip_read(z,name,*a,**k):
   if z.getinfo(name).file_size>262144:full_reads.append('zip:'+str(name))
   return real_zip(z,name,*a,**k)
  def path_read(p):
   if p.is_file() and p.stat().st_size>262144:full_reads.append('file:'+p.name)
   return real_path(p)
  archive=f.archive()
  with patch.object(zipfile.ZipFile,'read',zip_read),patch.object(Path,'read_bytes',path_read):
   plan=f.m.prepare(archive,f.home,f.kodi);f.m.apply(plan)
  self.assertEqual(full_reads,[],'Large update files must use bounded reads')
  self.assertEqual((f.home/'addons'/f.aid/'lib/large.bin').read_bytes(),raw[::-1]);self.assertEqual(f.saved(),f.before)
class StreamingComponents(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name);self.home=self.root/'home';self.home.mkdir();self.m=component()
  self.old={'addons/script.retained/addon.xml':b'<addon id="script.retained"/>','addons/script.retained/large.bin':b'retained'*1024*1024,'addons/script.changed/addon.xml':b'<addon id="script.changed"/>','addons/script.changed/large.bin':b'old','userdata/blacklanturn-build.json':b'{"release_id":"old"}'}
  self.new=dict(self.old);self.new['addons/script.changed/large.bin']=b'incoming'*1024*1024;self.new['userdata/blacklanturn-build.json']=b'{"release_id":"new"}'
  for name,data in [('base.zip',self.old),('target.zip',self.new)]:
   with zipfile.ZipFile(self.root/name,'w',zipfile.ZIP_DEFLATED) as z:
    for n,v in data.items():z.writestr(n,v)
  with zipfile.ZipFile(self.root/'base.zip') as z:z.extractall(self.home)
  self.archive=self.root/'component.zip';self.m.build(self.root/'base.zip',self.root/'target.zip',self.archive)
 def test_component_reconstruction_streams_large_content_and_is_exact(self):
  reads=[];real=zipfile.ZipFile.read;path_read=Path.read_bytes
  def read(z,name,*a,**k):
   if z.getinfo(name).file_size>262144:reads.append('zip:'+str(name))
   return real(z,name,*a,**k)
  def disk(p):
   if p.is_file() and p.stat().st_size>262144:reads.append('disk:'+p.name)
   return path_read(p)
  with patch.object(zipfile.ZipFile,'read',read),patch.object(Path,'read_bytes',disk):expanded=self.m.expand(self.archive,self.home,self.root)
  try:
   with zipfile.ZipFile(expanded) as z:self.assertEqual({n:z.read(n) for n in z.namelist()},self.new)
   self.assertEqual(reads,[],'Reconstruction must not retain whole payloads in RAM')
  finally:expanded.unlink()
 def test_retained_drift_is_rejected_before_incoming_content_is_read(self):
  (self.home/'addons/script.retained/large.bin').write_bytes(b'newer local source')
  read_content=[];real=zipfile.ZipFile.read
  def read(z,name,*a,**k):
   if str(name).endswith('/large.bin'):read_content.append(name)
   return real(z,name,*a,**k)
  with patch.object(zipfile.ZipFile,'read',read),self.assertRaises(ValueError):self.m.expand(self.archive,self.home,self.root)
  self.assertEqual(read_content,[],'Check fallback eligibility before reading incoming payloads')
  self.assertEqual(list(self.root.glob('.BlackLanturn-components-*.zip')),[])
 def test_small_retained_mismatch_is_checked_before_large_retained_files(self):
  for tree in (self.old,self.new):tree['addons/script.zzz.small/addon.xml']=b'<addon id="script.zzz.small"/>'
  for name,data in [('base.zip',self.old),('target.zip',self.new)]:
   with zipfile.ZipFile(self.root/name,'w',zipfile.ZIP_DEFLATED) as z:
    for n,v in data.items():z.writestr(n,v)
  with zipfile.ZipFile(self.root/'base.zip') as z:z.extractall(self.home)
  self.m.build(self.root/'base.zip',self.root/'target.zip',self.archive)
  (self.home/'addons/script.zzz.small/addon.xml').write_bytes(b'newer small addon')
  opened=[];real=Path.open
  def opening(p,*a,**k):
   if p.name=='large.bin':opened.append(p)
   return real(p,*a,**k)
  with patch.object(Path,'open',opening),self.assertRaises(ValueError):self.m.expand(self.archive,self.home,self.root)
  self.assertEqual(opened,[],'Cheap fallback checks should precede large file hashing')
 def test_source_changes_after_preflight_are_rejected_and_output_is_removed(self):
  source=self.home/'addons/script.retained/large.bin';real=Path.open;reads=0
  def opening(p,*a,**k):
   nonlocal reads
   mode=a[0] if a else k.get('mode','r')
   if p==source and mode=='rb':
    reads+=1
    if reads==2:
     with real(p,'wb') as out:out.write(b'drift after first verification')
   return real(p,*a,**k)
  with patch.object(Path,'open',opening),self.assertRaises(ValueError):self.m.expand(self.archive,self.home,self.root)
  self.assertEqual(list(self.root.glob('.BlackLanturn-components-*.zip')),[])
if __name__=='__main__':unittest.main()
