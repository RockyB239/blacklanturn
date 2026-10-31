import subprocess,sys,unittest
from test_startup_network_imports import ADDON,PROBE

class StartupPreviewTools(unittest.TestCase):
 def test_idle_controller_does_not_import_preview_provider_or_worker_pool(self):
  extra="\nassert not {'youtube_provider','concurrent.futures.thread','traceback'} & sys.modules.keys(), sorted({'youtube_provider','concurrent.futures.thread','traceback'} & sys.modules.keys())\n"
  p=subprocess.run([sys.executable,'-I','-c',PROBE+extra,str(ADDON),'live_review'],capture_output=True,text=True,timeout=15)
  self.assertEqual(p.returncode,0,p.stdout+p.stderr)
