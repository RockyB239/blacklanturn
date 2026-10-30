"""CI must execute patches on current source rather than only historical fixtures."""
from pathlib import Path
import subprocess,sys,unittest
class CurrentPatchContracts(unittest.TestCase):
 def test_current_full_source_progress_search_cache_and_privacy(self):
  root=Path(__file__).resolve().parents[1]
  result=subprocess.run([sys.executable,str(root/'tools/run_current_addons139_contracts.py')],capture_output=True,text=True,timeout=30)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr)
  self.assertIn('51 progress/search/shared-request and 12 real SQLite-cache',result.stdout)
