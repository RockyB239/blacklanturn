import importlib.util,hashlib,json,tempfile,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
class NoticeProofScope(unittest.TestCase):
 def curate(self,entry):
  path=R/'tools/curate_notice_proofs.py'
  self.assertTrue(path.is_file(),'Need an explicit operational notice-proof policy')
  s=importlib.util.spec_from_file_location('curate165',path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m.curate(entry)
 def test_newer_unmodified_stock_dependency_does_not_block_owned_patch_completion(self):
  src=R/'controller-source/addon/release_updates.py';s=importlib.util.spec_from_file_location('notice165',src);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
  files={'addons/script.blacklanturn.preview/live_review.py':b'controller','addons/plugin.video.umbrella/owned.py':b'patch','addons/script.skinvariables/addon.xml':b'2.2.11'};entry=dict(id='blacklanturn-apple-1.1.58-r0',edition='apple',version='1.1.58',revision=0,title='BlackLanturn',summary='Update',sections=[dict(heading='Update',bullets=['Changes'])],files={p:hashlib.sha256(v).hexdigest()for p,v in files.items()});curated=self.curate(entry)
  self.assertEqual(set(entry['files'])-set(curated['files']),{'addons/script.skinvariables/addon.xml'});self.assertEqual(len(entry['files']),3)
  with tempfile.TemporaryDirectory()as td:
   h=Path(td)
   for p,v in files.items():f=h/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(v)
   (h/'addons/script.skinvariables/addon.xml').write_bytes(b'2.2.12');u=h/'userdata';u.mkdir();(u/'blacklanturn-install-complete.json').write_text(json.dumps(dict(schema=1,id=entry['id'],edition='apple',version='1.1.58',revision=0,complete=True)))
   self.assertFalse(m.verified(h,entry));self.assertTrue(m.verified(h,curated));(h/'addons/plugin.video.umbrella/owned.py').write_bytes(b'foreign');self.assertFalse(m.verified(h,curated))
 def test_other_release_proofs_and_original_input_stay_unchanged(self):
  e={'version':'1.1.57','files':{'addons/script.skinvariables/addon.xml':'a'*64}};self.assertEqual(self.curate(e),e)
