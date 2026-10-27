"""Reconstruct published129 source without comparing old releases to new code."""
import atexit,hashlib,json,shutil,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).parents[1]
_temp=None
def published129():
 global _temp
 if _temp is not None:return Path(_temp.name).resolve()
 _temp=tempfile.TemporaryDirectory(prefix='BlackLanturn-historical129-');atexit.register(_temp.cleanup);out=Path(_temp.name).resolve()
 manifest=json.loads((ROOT/'controller-source/manifest95.json').read_text())['files']
 for name,digest in manifest.items():
  source=ROOT/'controller-source/historical129'/name
  if not source.is_file():source=ROOT/'controller-source/addon'/name
  if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:raise AssertionError('Historical source changed: '+name)
  target=out/'controller-source/addon'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
 shutil.copytree(ROOT/'tools',out/'tools',ignore=shutil.ignore_patterns('__pycache__'))
 for folder in ('compatibility','plugin.program.blacklanturninstaller'):(out/folder).symlink_to(ROOT/folder,target_is_directory=True)
 for item in (ROOT/'controller-source').iterdir():
  if item.name.startswith('manifest') or item.name.startswith('historical') or item.name.endswith('.json'):
   (out/'controller-source'/item.name).symlink_to(item.resolve(),target_is_directory=item.is_dir())
 with zipfile.ZipFile(ROOT/'plugin.program.blacklanturninstaller/plugin.program.blacklanturninstaller-1.0.34.zip') as z:z.extractall(out/'installer-source')
 return out
