import hashlib,tempfile,unittest
from pathlib import Path
from tools.device_validation.verify_performance_evidence import verify
class Evidence(unittest.TestCase):
 def test_legacy_stale_row_protocol_cannot_be_release_evidence(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'manifest.json';p.write_text('source')
   def receipt(n):return {'passed':True,'protocol':'legacy','row_visits':[{'section':s,'seconds':.3} for _ in range(n) for s in ('Home','Shows','Movies','YouTube','My Stuff')],'memory':{'rss_start':100,'rss_end':100}}
   receipts={'before':receipt(4),'after':receipt(4),'soak':receipt(20)}
   bundle={'schema':1,'source_manifest_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'devices':{k:receipts for k in ('mac','apple','fire')}}
   with self.assertRaisesRegex(ValueError,'Fresh-row readiness'):verify(bundle,p)
 def test_missing_device_or_changed_source_cannot_reuse_old_performance_acceptance(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'manifest.json';p.write_text('source1');bundle={'schema':1,'source_manifest_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'devices':{}}
   with self.assertRaisesRegex(ValueError,'three'):verify(bundle,p)
   p.write_text('source2')
   with self.assertRaisesRegex(ValueError,'reviewed source'):verify(bundle,p)
