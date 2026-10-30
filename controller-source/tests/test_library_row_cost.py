"""Local shelves isolate source metadata once and reread current watched state."""
import ast,copy,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from live_core import row_items
from local_watch import hydrate_local
ROOT=Path(__file__).parents[1]/'addon'
def method():
 cls=next(n for n in ast.parse((ROOT/'live_review.py').read_text()).body if isinstance(n,ast.ClassDef) and n.name=='LiveReview')
 fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='cached_row_items')
 ns={'row_items':row_items,'get_list':lambda path:(_ for _ in ()).throw(AssertionError('Local shelf queried a provider'))}
 exec(compile(ast.Module(body=[fn],type_ignores=[]),'native-row-method','exec'),ns);return ns[fn.name]
class CopyProbe(dict):
 copies=0
 def __deepcopy__(self,memo):
  type(self).copies+=1
  return CopyProbe({k:copy.deepcopy(v,memo) for k,v in self.items()})
class LibraryRowCost(unittest.TestCase):
 def test_visible_shelf_copies_metadata_once_without_changing_saved_source(self):
  with tempfile.TemporaryDirectory() as d:
   CopyProbe.copies=0;items=[CopyProbe(label='Original',art={'landscape':'wide'})]
   w=SimpleNamespace(hydrate_library_items=lambda values:hydrate_local(d,values))
   got=method()(w,{'path':'','local_items':items});got[0]['art']['landscape']='rendered'
   self.assertEqual(items[0]['art']['landscape'],'wide')
   self.assertEqual(CopyProbe.copies,1,'Visible metadata should not be deep-copied twice')
