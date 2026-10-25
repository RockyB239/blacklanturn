"""Re-run the current Helper/shared patches against pinned full source, offline.

Kodi and provider boundaries are synthetic; Helper classes, cache and SQLite run.
No device profile, account or network is accessed.
"""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,tempfile,zipfile
R=Path(__file__).resolve().parents[1];C=R/'compatibility/current-addons'
def main():
 m=json.loads((C/'manifest.json').read_text())['addons']['plugin.video.themoviedb.helper']
 with tempfile.TemporaryDirectory(prefix='blacklanturn-current-contracts-') as tmp:
  root=Path(tmp);(root/'tests').mkdir();(root/'evidence').mkdir();(root/'upstream').mkdir()
  source=C/m['archive'];assert hashlib.sha256(source.read_bytes()).hexdigest()==m['archive_sha256']
  with zipfile.ZipFile(source) as z:z.extractall(root/'candidate')
  with zipfile.ZipFile(R/'compatibility/shared-requests/upstream-general-0.2.35.zip') as z:
   for n in z.namelist():
    prefix='script.module.jurialmunkey/'
    if n.startswith(prefix) and not n.endswith('/'):
     p=root/'candidate/script.module.jurialmunkey'/n[len(prefix):];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
  shutil.copyfile(R/'compatibility/shared-requests/reqapi.py',root/'candidate/script.module.jurialmunkey/resources/modules/jurialmunkey/reqapi.py')
  upstream=C/'helper-upstream-6.18.2.zip'
  assert hashlib.sha256(upstream.read_bytes()).hexdigest()==m['upstream_archive_sha256']
  shutil.copyfile(upstream,root/'upstream/plugin.video.themoviedb.helper-6.18.2.zip')
  for p in (C/'contract-tests').glob('*.py'):shutil.copyfile(p,root/'tests'/p.name)
  for args in ([sys.executable,'-m','unittest','discover','-s',str(root/'tests'),'-v'],[sys.executable,str(root/'tests/run_empty_cache.py'),str(R/'compatibility/helper-empty-cache/test_cache.py')]):
   result=subprocess.run(args,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
   print(result.stdout)
   if result.returncode:raise SystemExit(result.returncode)
  cache=json.loads((root/'evidence/empty-cache-result.json').read_text());assert cache['passed'] and cache['tests']==12
  print('PASS: 37 progress/search/shared-request and 12 real SQLite-cache current-source contracts')
if __name__=='__main__':main()
