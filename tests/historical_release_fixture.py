"""Reconstruct published129 source without comparing old releases to new code."""
import atexit,hashlib,io,json,shutil,subprocess,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).parents[1]
_temp=None
CONTROLLER_COMMITS={
 '95':'bc3a6e3e5b6822f6168ff35f58f6ae9059be8936',
 '121':'548f03032d3ed1f0bc3ffd48d2c587863fbbf3f6',
}
def published_controller(version):
 prefix='controller-source/addon/'
 raw=subprocess.check_output(['git','archive','--format=zip',CONTROLLER_COMMITS[version],prefix.rstrip('/')],cwd=ROOT)
 with zipfile.ZipFile(io.BytesIO(raw)) as archive:
  source={name[len(prefix):]:archive.read(name) for name in archive.namelist() if name.startswith(prefix) and not name.endswith('/')}
 manifest=json.loads((ROOT/'controller-source'/f'manifest{version}.json').read_text())['files']
 if {name:hashlib.sha256(raw).hexdigest() for name,raw in source.items()}!=manifest:
  raise AssertionError('Published controller source differs from manifest '+version)
 return source
def published129():
 global _temp
 if _temp is not None:return Path(_temp.name).resolve()
 temp=tempfile.TemporaryDirectory(prefix='BlackLanturn-historical129-');out=Path(temp.name).resolve()
 for name,raw in published_controller('95').items():
  target=out/'controller-source/addon'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
 shutil.copytree(ROOT/'tools',out/'tools',ignore=shutil.ignore_patterns('__pycache__'))
 for folder in ('compatibility','plugin.program.blacklanturninstaller'):(out/folder).symlink_to(ROOT/folder,target_is_directory=True)
 for item in (ROOT/'controller-source').iterdir():
  if item.name.startswith('manifest') or item.name.startswith('historical') or item.name.endswith('.json'):
   (out/'controller-source'/item.name).symlink_to(item.resolve(),target_is_directory=item.is_dir())
 with zipfile.ZipFile(ROOT/'plugin.program.blacklanturninstaller/plugin.program.blacklanturninstaller-1.0.34.zip') as z:z.extractall(out/'installer-source')
 _temp=temp;atexit.register(temp.cleanup)
 return out
