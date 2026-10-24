"""Exact edition guards and preservation: synthetic installer integration evidence."""
import hashlib,inspect,json,sqlite3,unittest,zipfile
from pathlib import Path
import test_managed_umbrella as fixture

AID='plugin.video.youtube'; PREFIX='addons/'+AID+'/'
class ManagedYouTubeTests(unittest.TestCase):
 def setUp(self):
  self.f=fixture.ManagedUmbrellaTests()
  self.f.setUp();self.addCleanup(self.f.doCleanups);self.m=self.f.m
  self.variants={e:{'addon.xml':b'<addon id="plugin.video.youtube" version="7.4.4a"/>','platform.py':e.encode(),'cache.py':b'fixed cache'} for e in ('general','apple')}
  self.manifest={'patch':'youtube-freshness-1','variants':{e:{'files':self.hashes(v)} for e,v in self.variants.items()},'installed_tree_sha256':[]}
  for v in self.variants.values():
   self.manifest['installed_tree_sha256'] += [self.tree(self.hashes(v)),self.tree(self.hashes(dict(v,**{'cache.py':b'original cache'})))]
  (self.f.resources/'managed-youtube.json').write_text(json.dumps(self.manifest))
 def hashes(self,v):return {n:hashlib.sha256(b).hexdigest() for n,b in v.items()}
 def tree(self,v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 def invoke(self,fn,*args,**kwargs):
  self.assertIn('youtube',inspect.signature(fn).parameters,'Missing managed YouTube source protection')
  return fn(*args,**kwargs)
 def archive(self,edition='general',change=None):
  with zipfile.ZipFile(self.f.archive()) as z:data={n:z.read(n) for n in z.namelist()}
  data.update({PREFIX+n:b for n,b in self.variants[edition].items()})
  if change:change(data)
  path=self.f.root/'yt.zip'
  with zipfile.ZipFile(path,'w') as z:
   for n,b in data.items():z.writestr(n,b)
  return path
 def install(self,edition='general',original=False):
  home=self.f.root/edition
  for n,b in self.variants[edition].items():
   p=home/'addons'/AID/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
  if original:(home/'addons'/AID/'cache.py').write_bytes(b'original cache')
  return home
 def test_both_exact_candidate_editions_are_accepted(self):
  for e in self.variants:
   with zipfile.ZipFile(self.archive(e)) as z:self.invoke(self.m.verify_archive,z,youtube=True)
 def test_missing_modified_foreign_or_future_payload_fails(self):
  for mode in ('missing','old','foreign','version'):
   def change(v):
    if mode=='missing':del v[PREFIX+'cache.py']
    elif mode=='old':v[PREFIX+'cache.py']=b'original cache'
    elif mode=='foreign':v[PREFIX+'extra.py']=b'pass'
    else:v[PREFIX+'addon.xml']=b'<addon version="7.5"/>'
   with self.subTest(mode=mode),zipfile.ZipFile(self.archive(change=change)) as z:
    self.assertIn('youtube',inspect.signature(self.m.verify_archive).parameters)
    with self.assertRaises(self.m.ProtectionError):self.m.verify_archive(z,youtube=True)
 def test_known_original_and_candidate_installed_trees_pass(self):
  for e in self.variants:
   for original in (True,False):self.invoke(self.m.verify_installed,self.install(e,original),youtube=True)
 def test_unknown_installed_tree_fails_before_cleanup(self):
  h=self.install();(h/'addons'/AID/'foreign.py').write_text('pass')
  self.assertIn('youtube',inspect.signature(self.m.verify_installed).parameters)
  with self.assertRaises(self.m.ProtectionError):self.m.verify_installed(h,youtube=True)
 def test_whitelist_requires_candidate_not_original(self):
  h=self.install(original=True)
  self.assertIn('youtube',inspect.signature(self.m.verify_kept).parameters)
  with self.assertRaises(self.m.ProtectionError):self.m.verify_kept(h,{AID},youtube=True)
  self.invoke(self.m.verify_kept,self.install(),{AID},youtube=True)
 def test_youtube_update_rule_is_idempotent_and_unrelated_rules_preserved(self):
  db=self.f.registry();before=self.f.rules(db)
  self.invoke(self.m.protect,db,youtube=True);self.invoke(self.m.protect,db,youtube=True)
  self.assertEqual(self.f.rules(db),before+[(self.m.HELPER,1),(AID,1)])
