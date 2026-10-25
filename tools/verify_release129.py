"""Installer presentation-only delta from immutable published128."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CHANGED={'addon.xml','resources/libs/gui/navigation.py','resources/libs/gui/navigation_model.py','resources/libs/gui/updates_menu.py'}
def inventory(root):
 return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo') and p.name!='.DS_Store'}
def baseline_installer():
 p=ROOT/'plugin.program.blacklanturninstaller/plugin.program.blacklanturninstaller-1.0.33.zip'
 assert hashlib.sha256(p.read_bytes()).hexdigest()=='48013ba1086fa6002fc5aa40419e6b46054c41a28fa578011674fccd3af60bee'
 with zipfile.ZipFile(p)as z:
  assert z.testzip() is None
  return {n.split('/',1)[1]:hashlib.sha256(z.read(n)).hexdigest()for n in z.namelist()if not n.endswith('/')}
def verify_source(manifest,installer):
 controller=inventory(ROOT/'controller-source/addon');current=inventory(ROOT/'installer-source/plugin.program.blacklanturninstaller');old=baseline_installer()
 assert manifest['controller']=='0.1.95' and manifest['files']==controller,'Controller must remain byte-identical95'
 assert installer==current
 assert {n for n in set(old)|set(current)if old.get(n)!=current.get(n)}==CHANGED,'Unrelated installer source changed'
 proof=json.loads((ROOT/'compatibility/current-addons/release129-source.json').read_text())
 assert proof['changed_files']=={n:current[n]for n in CHANGED},'Reviewed presentation source differs'
 return True
