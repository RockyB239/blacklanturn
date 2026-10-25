"""Keep126 feature proof scoped to unchanged127 source and navigation methods.

Changed startup/recovery/transaction paths require separate fresh exact-artifact
native acceptance. This module never fabricates or promotes that receipt.
"""
import ast,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CONTROLLER_CHANGED={'addon.xml','default.py','installer_recovery.py'}
INSTALLER_CHANGED={'addon.xml','resources/libs/inplace_update.py','resources/libs/gui/navigation_model.py'}
def inventory(root):
 return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in root.rglob('*')if p.is_file()and '__pycache__'not in p.parts and p.suffix not in ('.pyc','.pyo')and p.name!='.DS_Store'}
def baseline_installer(raw=False):
 receipt=json.loads((ROOT/'controller-source/release126-feature-verification.json').read_text())
 with zipfile.ZipFile(ROOT/'plugin.program.blacklanturninstaller/plugin.program.blacklanturninstaller-1.0.31.zip')as z:
  prefix='plugin.program.blacklanturninstaller/'
  assert z.testzip() is None and all(n.startswith(prefix)for n in z.namelist()),'Unknown historical Installer archive'
  files={n[len(prefix):]:z.read(n)for n in z.namelist()if not n.endswith('/')}
 assert {n:hashlib.sha256(v).hexdigest()for n,v in files.items()}==receipt['installer_files'],'Historical Installer tree differs from126 native basis'
 return files if raw else receipt['installer_files']
def stable_ast(raw,excluded):
 tree=ast.parse(raw)
 def stable(nodes,prefix=''):
  result=[]
  for node in nodes:
   name=prefix+getattr(node,'name','')
   if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))and name in excluded:continue
   if isinstance(node,ast.ClassDef):node.body=stable(node.body,name+'.')
   result.append(node)
  return result
 tree.body=stable(tree.body)
 return ast.dump(tree,include_attributes=False)
def default_ast(raw,remove_recovery=False):
 tree=ast.parse(raw)
 if remove_recovery:
  top=next(n for n in tree.body if isinstance(n,ast.Try))
  first=top.body[:3]
  assert len(first)==3 and isinstance(first[0],ast.ImportFrom) and first[0].module=='installer_recovery' and {n.name for n in first[0].names}=={'recover_installer','RecoveryError'},'Missing scoped recovery startup import'
  assert isinstance(first[1],ast.Try) and isinstance(first[2],ast.If) and isinstance(first[2].test,ast.Name) and first[2].test.id=='recovered','Recovery startup preamble has changed shape'
  top.body=top.body[3:]
 return ast.dump(tree,include_attributes=False)
def verify_default_methods():
 prior=json.loads((ROOT/'controller-source/manifest93.json').read_text())['files']
 raw=(ROOT/'controller-source/historical-default93.py').read_bytes()
 assert hashlib.sha256(raw).hexdigest()==prior['default.py'],'Historical93 entrypoint is not the accepted source'
 assert default_ast(raw)==default_ast((ROOT/'controller-source/addon/default.py').read_bytes(),remove_recovery=True),'Existing controller startup/playback entrypoint changed outside the recovery preamble'
 return True

def verify_navigation_methods():
 before=baseline_installer(raw=True);source=ROOT/'installer-source/plugin.program.blacklanturninstaller'
 path='resources/libs/gui/navigation_model.py'
 assert stable_ast(before[path],{'handoff','perform'})==stable_ast((source/path).read_bytes(),{'handoff','perform'}),'Unchanged navigation presentation/state methods changed'
 return True

def verify_source(manifest,installer_files):
 assert manifest.get('controller')=='0.1.94'
 current=inventory(ROOT/'controller-source/addon');installed=inventory(ROOT/'installer-source/plugin.program.blacklanturninstaller')
 assert manifest.get('files')==current,'127 controller manifest differs from current source'
 assert installer_files==installed,'127 installer inventory differs from current source'
 prior=json.loads((ROOT/'controller-source/manifest93.json').read_text())['files'];old_installer=baseline_installer()
 changed={n for n in set(prior)|set(current)if prior.get(n)!=current.get(n)}
 assert changed==CONTROLLER_CHANGED,'Controller delta requires fresh feature acceptance beyond startup/recovery'
 changed={n for n in set(old_installer)|set(installed)if old_installer.get(n)!=installed.get(n)}
 assert changed==INSTALLER_CHANGED,'Installer delta requires fresh feature acceptance beyond transaction/handoff'
 assert verify_default_methods() and verify_navigation_methods()
 return True
