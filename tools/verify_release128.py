"""Only reviewed update-flow and title-menu changes may inherit127 behavior."""
import ast,hashlib,importlib.util,json,zipfile,xml.etree.ElementTree as E
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CONTROLLER_CHANGED={'addon.xml','update_notes_ui.py','live_review.py','preview_geometry.py','resources/skins/Default/1080i/LiveReview.xml'}
INSTALLER_CHANGED={'addon.xml','resources/libs/wizard.py','resources/libs/gui/window.py'}
def inventory(root):
 return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in root.rglob('*')if p.is_file()and '__pycache__'not in p.parts and p.suffix not in ('.pyc','.pyo')and p.name!='.DS_Store'}
def baseline_installer(raw=False):
 path=ROOT/'plugin.program.blacklanturninstaller/plugin.program.blacklanturninstaller-1.0.32.zip'
 assert hashlib.sha256(path.read_bytes()).hexdigest()=='b28268005eba059732a901e9beb13aa752d80161a8a75f6a1f54e4ed68aabe18','Published127 Installer changed'
 with zipfile.ZipFile(path)as z:
  assert z.testzip()is None
  files={n.split('/',1)[1]:z.read(n)for n in z.namelist()if not n.endswith('/')}
 return files if raw else {n:hashlib.sha256(v).hexdigest()for n,v in files.items()}
def prior_controller():
 return json.loads((ROOT/'controller-source/manifest94.json').read_text())['files']
def normalized_wizard(raw,completion_default=False):
 tree=ast.parse(raw)
 if completion_default:
  imports=[n for n in tree.body if isinstance(n,ast.Import)and [a.name for a in n.names]==['re']]
  assert len(imports)==1
  tree.body.remove(imports[0])
  wizard=next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='Wizard')
  update=next(n for n in wizard.body if isinstance(n,ast.FunctionDef)and n.name=='update')
  pos=next(i for i,n in enumerate(update.body)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='target_version'for t in n.targets))
  expected=ast.parse("if not isinstance(target_version, str) or not re.fullmatch(r'\\d+(?:\\.\\d+){1,3}', target_version):\n self.dialog.ok(CONFIG.ADDONTITLE, 'The update catalog is unavailable. Check your connection and try again. Nothing has been changed.')\n return").body[0]
  assert ast.dump(update.body[pos+1])==ast.dump(expected),'Unexpected offline catalog guard'
  del update.body[pos+1]
  call=update.body[-1].test
  default=[k for k in call.keywords if k.arg=='defaultbutton']
  assert len(default)==1 and ast.dump(default[0].value)==ast.dump(ast.parse('xbmcgui.DLG_YESNO_YES_BTN',mode='eval').body),'Unexpected completion default'
  call.keywords=[k for k in call.keywords if k.arg!='defaultbutton']
 return ast.dump(tree,include_attributes=False)
def verify_methods():
 spec=importlib.util.spec_from_file_location('scoped127',ROOT/'tools/verify_release127.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
 before=baseline_installer(raw=True);source=ROOT/'installer-source/plugin.program.blacklanturninstaller'
 assert normalized_wizard(before['resources/libs/wizard.py'])==normalized_wizard((source/'resources/libs/wizard.py').read_bytes(),True),'Wizard changed outside completion focus'
 for path,excluded in [('update_notes_ui.py',{'request_update'}),('live_review.py',{'LiveReview.title_actions'})]:
  raw=(ROOT/'controller-source/historical128'/path).read_bytes()
  assert hashlib.sha256(raw).hexdigest()==prior_controller()[path],'Historical127 controller basis changed'
  if path=='live_review.py':
   raw=raw.replace(b'from preview_geometry import preview_fill_viewmode,preview_display_aspect,PreviewRendererGuard',b'from preview_geometry import preview_fill_viewmode,preview_display_aspect,PreviewRendererGuard,preview_uses_compact_hero').replace(b"self.getProperty('heroCompact')=='true' and self.mode=='home'",b"preview_uses_compact_hero(self.mode,self.getProperty('heroCompact')=='true')")
  assert old.stable_ast(raw,excluded)==old.stable_ast((ROOT/'controller-source/addon'/path).read_bytes(),excluded),'Unrelated controller behavior changed'
 path='preview_geometry.py';raw=(ROOT/'controller-source/historical128'/path).read_bytes()
 assert hashlib.sha256(raw).hexdigest()==prior_controller()[path]
 expected=raw+b"\ndef preview_uses_compact_hero(mode,hero_compact):\n    return mode=='details' or (mode=='home' and bool(hero_compact))\n"
 assert ast.dump(ast.parse(expected))==ast.dump(ast.parse((ROOT/'controller-source/addon'/path).read_bytes())),'Unrelated preview geometry changed'
 path='resources/skins/Default/1080i/LiveReview.xml';raw=(ROOT/'controller-source/historical128'/path).read_bytes()
 assert hashlib.sha256(raw).hexdigest()==prior_controller()[path]
 before_xml=E.fromstring(raw);after_xml=E.parse(ROOT/'controller-source/addon'/path).getroot()
 condition='String.IsEqual(Window.Property(heroCompact),true) + String.IsEqual(Window.Property(page),home)'
 for c in before_xml.find('./controls/control[@type="group"]').findall('control')[:11]:
  node=c.find('visible');node.text=node.text.replace(condition,'[String.IsEqual(Window.Property(page),details) | ['+condition+']]')
 assert E.tostring(before_xml)==E.tostring(after_xml),'Details XML changed outside decorative hero visibility'
 path='resources/libs/gui/window.py'
 # The legacy prompt's sole behavior change is update(name), plus its label.
 expected=before[path].replace(b"yeslabel='Install', nolabel='Ignore'",b"yeslabel='Update', nolabel='Ignore'").replace(b'Wizard().build(CONFIG.BUILDNAME)',b'Wizard().update(name)')
 assert ast.dump(ast.parse(expected))==ast.dump(ast.parse((source/path).read_bytes())),'Legacy prompt changed outside in-place route'
 return True
def verify_source(manifest,installer_files):
 current=inventory(ROOT/'controller-source/addon');installed=inventory(ROOT/'installer-source/plugin.program.blacklanturninstaller')
 assert manifest.get('controller')=='0.1.95'and manifest.get('files')==current,'128 controller differs from manifest95'
 assert installer_files==installed,'128 Installer inventory differs'
 before=prior_controller();old=baseline_installer()
 assert {n for n in set(before)|set(current)if before.get(n)!=current.get(n)}==CONTROLLER_CHANGED,'Controller changes exceed reviewed128 scope'
 assert {n for n in set(old)|set(installed)if old.get(n)!=installed.get(n)}==INSTALLER_CHANGED,'Installer changes exceed reviewed128 scope'
 assert verify_methods()
 return True
