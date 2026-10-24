import copy,hashlib,importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
V=module('context_verifier',ROOT/'tools/verify_release.py');BUILDER=module('context_builder',ROOT/'tools/build_release.py')
class ContextRelease(unittest.TestCase):
 def inputs(self):return json.loads((ROOT/'compatibility/youtube-context/native-verification.json').read_text())
 def test_current_native_proof_passes(self):
  gate=getattr(V,'verify_youtube_context_acceptance',None);self.assertTrue(callable(gate));gate(self.inputs())
 def test_missing_device_failed_phase_or_stale_source_refused(self):
  r=self.inputs();gate=getattr(V,'verify_youtube_context_acceptance',None);self.assertTrue(callable(gate))
  for kind in ('missing','phase','hash'):
   bad=copy.deepcopy(r)
   if kind=='missing':bad['devices'].pop('apple')
   elif kind=='phase':bad['devices']['apple']['complete_refresh']=False
   else:bad['candidate_sha256']='0'*64
   with self.subTest(kind=kind),self.assertRaises(AssertionError):gate(bad)
 def test_builder_rejects_unknown_context_before_emitting_archive(self):
  cache=json.loads((ROOT/'compatibility/youtube-refresh/receipt.json').read_text());d={'addons/plugin.video.youtube/'+cache['native_path']:(ROOT/'compatibility/youtube-refresh/upstream/function_cache.py').read_bytes(),'addons/plugin.video.youtube/resources/lib/youtube_plugin/kodion/context/xbmc/xbmc_context.py':b'unknown context'}
  with self.assertRaises(ValueError):BUILDER.apply_youtube_refresh(d)
