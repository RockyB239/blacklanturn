"""Standard build extraction must never downgrade the public repository/icon."""
import hashlib,importlib.util,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('repository_builder',ROOT/'tools/build_release.py');B=importlib.util.module_from_spec(s);s.loader.exec_module(B)
class RepositoryPayload(unittest.TestCase):
 def test_current_public_repository_replaces_old_baseline_before_packaging(self):
  apply=getattr(B,'apply_repository',None);self.assertTrue(callable(apply),'Missing current repository overlay')
  data={'addons/repository.blacklanturn/addon.xml':b'old','addons/repository.blacklanturn/obsolete.txt':b'old','userdata/keep':b'private'}
  apply(data)
  with zipfile.ZipFile(ROOT/'repository.blacklanturn.zip') as z:expected={'addons/'+n:z.read(n) for n in z.namelist()}
  self.assertEqual({n:v for n,v in data.items() if n.startswith('addons/repository.blacklanturn/')},expected);self.assertEqual(data['userdata/keep'],b'private')
 def test_unknown_repository_archive_is_rejected_without_mutation(self):
  apply=getattr(B,'apply_repository',None);self.assertTrue(callable(apply),'Missing current repository overlay')
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);(p/'repository.blacklanturn.zip').write_bytes(b'unreviewed');data={'userdata/keep':b'private'}
   with patch.object(B,'ROOT',p),self.assertRaisesRegex(AssertionError,'Public repository archive changed'):apply(data)
   self.assertEqual(data,{'userdata/keep':b'private'})
