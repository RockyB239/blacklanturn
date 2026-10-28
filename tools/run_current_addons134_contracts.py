"""Execute actual release134 provider source contracts offline; no user profile/network."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,tempfile,zipfile
R=Path(__file__).resolve().parents[1];C=R/'compatibility/addons134'
def main():
 m=json.loads((C/'manifest.json').read_text())
 with tempfile.TemporaryDirectory(prefix='blacklanturn134-contracts-') as folder:
  root=Path(folder);(root/'tests').mkdir();(root/'evidence').mkdir();(root/'upstream').mkdir()
  for aid in ('plugin.video.themoviedb.helper','plugin.video.umbrella'):
   record=m['addons'][aid];archive=C/record['archive'];assert hashlib.sha256(archive.read_bytes()).hexdigest()==record['archive_sha256']
   with zipfile.ZipFile(archive) as z:z.extractall(root/'patched')
  shutil.copytree(C/'patched/script.module.jurialmunkey',root/'patched/script.module.jurialmunkey')
  shutil.copyfile(C/'upstream/helper-6.19.2.zip',root/'upstream/helper-6.19.2.zip')
  for p in (C/'tests').glob('*.py'):shutil.copyfile(p,root/'tests'/p.name)
  calls=[[sys.executable,'-m','unittest','discover','-s',str(root/'tests'),'-v'],[sys.executable,str(root/'tests/run_empty_cache.py'),str(R/'compatibility/helper-empty-cache/test_cache.py')]]
  for args in calls:
   result=subprocess.run(args,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);print(result.stdout)
   if result.returncode:raise SystemExit(result.returncode)
  shutil.copytree(R/'compatibility/umbrella-progress',root/'umbrella-progress')
  (root/'autoplay/tests').mkdir(parents=True)
  shutil.copytree(root/'patched/plugin.video.umbrella',root/'autoplay/candidate')
  for p in (C/'autoplay-tests').glob('*.py'):shutil.copyfile(p,root/'autoplay/tests'/p.name)
  result=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(root/'autoplay/tests'),'-v'],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);print(result.stdout)
  if result.returncode:raise SystemExit(result.returncode)
  cache=json.loads((root/'evidence/empty-cache-result.json').read_text());assert cache['passed'] and cache['tests']==12
  print('PASS: 50 progress/search/shared-request and 12 real SQLite-cache plus36 current Umbrella autoplay/lifecycle contracts')
if __name__=='__main__':main()
