"""The public Update action cannot enter profile cleanup or data restoration."""
import importlib.util,sys,types,unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
import test_compatibility as fixtures
from test_compatibility import Kodi,ROOT as LIB
class UpdateFlow(unittest.TestCase):
 def setUp(self):
  self.f=fixtures.CompatibilityTests();self.f.setUp();self.addCleanup(self.f.tearDown)
  self.k=Kodi();self.cfg,self.mods=self.f.install_environment(self.k);self.cfg.ADDONTITLE='BlackLanturn Installer'
  self.events=[];self.cfg.set_setting=lambda key,value:self.events.append((key,value));self.k.Player=lambda:types.SimpleNamespace(isPlaying=lambda:False)
  self.tx=types.ModuleType('resources.libs.inplace_update');self.tx.UpdateError=ValueError;self.tx.recover=MagicMock(return_value=False);self.tx.prepare=MagicMock(return_value={'version':'1.1.24'});self.tx.apply=MagicMock(return_value={'version':'1.1.24','updated':['plugin.video.umbrella'],'retained':[]});self.tx.cancel=MagicMock()
  self.mods['resources.libs.inplace_update']=self.tx
  self.mods['resources'].libs=self.mods['resources.libs']
  self.mods['resources.libs'].inplace_update=self.tx
  self.mods['resources.libs.managed_addons']=types.SimpleNamespace(protect=MagicMock(),ProtectionError=ValueError)
  self.mods['resources.libs.install'].wipe=MagicMock(side_effect=AssertionError('update called wipe'))
 def run_update(self):
  with patch.dict(sys.modules,self.mods):
   import resources.libs
   with patch.object(resources.libs,'inplace_update',self.tx,create=True):
    spec=importlib.util.spec_from_file_location('wizard_update_test',LIB/'wizard.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);self.w=m.Wizard();self.w.update('Apple TV and Mac')
 def test_update_runs_transaction_without_wipe_or_save_restore(self):
  self.run_update();self.tx.prepare.assert_called_once();self.tx.apply.assert_called_once();self.mods['resources.libs.install'].wipe.assert_not_called();self.assertIn(('buildversion','1.1.24'),self.events)
 def test_active_playback_refuses_without_stopping_or_downloading(self):
  self.k.Player=lambda:types.SimpleNamespace(isPlaying=lambda:True);self.run_update();self.tx.prepare.assert_not_called();self.tx.apply.assert_not_called();self.assertEqual(self.k.commands,[])
 def test_failed_update_does_not_advance_installed_version(self):
  self.tx.apply.side_effect=ValueError('failed');self.run_update();self.assertFalse(any(k=='buildversion' for k,v in self.events))
 def test_only_completed_update_defaults_to_close_kodi(self):
  self.mods['xbmcgui'].DLG_YESNO_YES_BTN=11
  dialog=self.mods['xbmcgui'].Dialog();dialog.yesno=MagicMock(return_value=True)
  self.run_update();confirm,completed=dialog.yesno.call_args_list
  self.assertNotIn('defaultbutton',confirm.kwargs)
  self.assertEqual(completed.kwargs['defaultbutton'],11)
  self.assertEqual(completed.kwargs['yeslabel'],'Close Kodi')
  self.assertEqual(completed.kwargs['nolabel'],'Close later')
  self.assertIn('Quit',self.k.commands)
 def test_close_later_keeps_kodi_running_after_successful_update(self):
  self.mods['xbmcgui'].DLG_YESNO_YES_BTN=11
  dialog=self.mods['xbmcgui'].Dialog();dialog.yesno=MagicMock(side_effect=[True,False])
  self.run_update();self.tx.apply.assert_called_once();self.assertNotIn('Quit',self.k.commands)
 def test_legacy_update_notice_uses_update_without_standard_install(self):
  import ast
  source=LIB/'gui/window.py';tree=ast.parse(source.read_text())
  fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='show_update_window')
  self.cfg.ADDON_ICON='icon.png';self.cfg.ADDON_FANART='fanart.jpg';self.cfg.BUILDNAME='Old saved build name'
  self.mods['xbmcgui'].WindowXMLDialog=object
  wizard=MagicMock();self.mods['resources.libs.wizard']=types.SimpleNamespace(Wizard=lambda:wizard)
  env={'CONFIG':self.cfg,'xbmcgui':self.mods['xbmcgui']}
  with patch.dict(sys.modules,self.mods):
   exec(compile(ast.Module(body=[fn],type_ignores=[]),str(source),'exec'),env)
   env['show_update_window'](name='BlackLanturn General',current='1.1.26',new='1.1.27')
  wizard.update.assert_called_once_with('BlackLanturn General');wizard.build.assert_not_called()
 def test_unavailable_catalog_shows_retry_without_download_or_install(self):
  for value in (False,None,'', 'not-a-version'):
   with self.subTest(value=value):
    self.mods['resources.libs.check'].check_build=lambda *args,v=value:v
    dialog=self.mods['xbmcgui'].Dialog();dialog.ok=MagicMock()
    self.run_update();self.tx.prepare.assert_not_called();self.tx.apply.assert_not_called()
    dialog.ok.assert_called_once();self.assertIn('try again',dialog.ok.call_args.args[1])
 def test_preflight_failure_cannot_fall_back_to_build_install(self):
  self.tx.prepare.side_effect=ValueError('foreign source');self.run_update();self.tx.apply.assert_not_called();self.mods['resources.libs.install'].wipe.assert_not_called()
 def test_each_download_uses_its_own_archive(self):
  self.run_update();self.run_update()
  names=[str(c.args[0]) for c in self.tx.prepare.call_args_list];self.assertEqual(len(set(names)),2)
 def test_update_entry_is_distinct_from_standard_install(self):
  s=(LIB/'gui/build_menu.py').read_text();self.assertIn('Update BlackLanturn',s);self.assertIn("'action': 'update'",s);self.assertIn("'action': 'build'",s)
 def test_router_update_and_legacy_normal_lead_to_true_update(self):
  s=(LIB/'common/router.py').read_text();self.assertIn("action in ('update', 'normal')",s);self.assertIn('Wizard().update(name)',s)
 def test_legacy_update_dialog_has_no_recommended_fresh_install(self):
  s=(LIB/'gui/window.py').read_text();self.assertNotIn('Recommened: Fresh install',s);self.assertNotIn('Recommended: Fresh install',s);self.assertIn('action=update',s)
