import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
class BackendRoutes(unittest.TestCase):
 def test_core_kodi_settings_are_all_reachable(self):
  from backend_core import SETTINGS_GROUPS
  routes={r[0][5:] for _,_,rows in SETTINGS_GROUPS for r in rows if r[0].startswith('kodi:')}
  self.assertTrue({'settings','PlayerSettings','MediaSettings','PVRSettings','ServiceSettings','GameSettings','InterfaceSettings','Profiles','SystemSettings','filemanager','addonbrowser','systeminfo','eventlog','SkinSettings'}<=routes)
 def test_live_skin_controls_have_unique_actions(self):
  from backend_core import SETTINGS_GROUPS
  actions=[r[0] for _,_,rows in SETTINGS_GROUPS for r in rows]
  self.assertEqual(len(actions),len(set(actions)))
  self.assertTrue({'rows','genres','categories','ratings','rating_order','preview_mode','preview_delay'}<=set(actions))
