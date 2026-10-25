"""Registry selection must inspect database basenames, never profile ancestor names."""
import ast,glob,os,re,tempfile,types,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
class DatabaseDiscovery(unittest.TestCase):
 def test_profile_ancestor_containing_addons_does_not_hide_active_registry(self):
  with tempfile.TemporaryDirectory(prefix='current-addons-repair-') as d:
   root=Path(d)/'userdata/Database';root.mkdir(parents=True)
   for n in ('Addons3.db','Addons33.db','Addonsbad.db','Addons999.db.extra'):(root/n).touch()
   source=ast.parse((R/'installer-source/plugin.program.blacklanturninstaller/resources/libs/db.py').read_text());node=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='latest_db')
   env={'CONFIG':types.SimpleNamespace(DB_FILES=['Addons'],DATABASE=str(root)),'glob':glob,'os':os,'re':re}
   exec(compile(ast.Module(body=[node],type_ignores=[]),'actual_db_latest_db','exec'),env)
   self.assertEqual(env['latest_db']('Addons'),'Addons33.db')
   self.assertFalse(env['latest_db']('Unsupported'))
