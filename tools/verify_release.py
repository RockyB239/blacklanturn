"""Fail the release gate if packaged Helper, installer, policy or native proof drift."""
import argparse,hashlib,importlib.util,io,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'installer-source/plugin.program.blacklanturninstaller'
def verify(folder):
 receipt=json.loads((ROOT/'compatibility/helper-empty-cache/native-verification.json').read_text())
 approved=json.loads((SOURCE/'resources/managed-helper.json').read_text())
 assert receipt['passed'] and receipt['tests']==12 and receipt['failures']==receipt['errors']==0
 assert receipt['source_version']==approved['upstream_version'] and receipt['source_files']==approved['files'],'New Helper requires fresh native regression evidence'
 spec=importlib.util.spec_from_file_location('managed',SOURCE/'resources/libs/managed_addons.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 with zipfile.ZipFile(folder/'plugin.program.blacklanturninstaller-1.0.10.zip') as z:
  assert z.testzip() is None
  installer={n:z.read(n) for n in z.namelist()}
  assert all(n.startswith('plugin.program.blacklanturninstaller/') for n in installer)
 for ed in ('General','Apple-TV-Mac'):
  with zipfile.ZipFile(folder/f'BlackLanturn-{ed}-Kodi21-1.1.2.zip') as z:
   assert z.testzip() is None;m.verify_archive(z)
   p=json.loads(z.read('userdata/blacklanturn-build.json'))
   assert p['schema']==2 and p['helper_patch']=='empty-cache-1' and p['installer_min_version']=='1.0.10'
   for n,d in installer.items():assert z.read('addons/'+n)==d,'Installer mismatch'
   assert z.read('addons/plugin.program.blacklanturninstaller/resources/libs/managed_addons.py')==(SOURCE/'resources/libs/managed_addons.py').read_bytes()
 print('PASS: both packages, protected schema, exact installer, full Helper manifest and native regression evidence')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('artifacts',type=Path);verify(p.parse_args().artifacts)
