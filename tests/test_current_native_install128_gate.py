"""A historical UI receipt cannot stand in for current installation acceptance."""
import copy,hashlib,json,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
from tools import verify_current_install128 as gate
class CurrentNativeInstallGate(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name)
  self.artifacts={}
  for n in gate.NAMES:
   (self.root/n).write_bytes(n.encode());self.artifacts[n]=hashlib.sha256(n.encode()).hexdigest()
  self.receipt={'passed':True,'network_blocked':True,'personal_profile_denied':True,'personal_profile_accessed':False,'artifacts':self.artifacts,'cases':[]}
  for e in ('General','Apple-TV-Mac'):
   for m in ('clean','standard','update'):
    self.receipt['cases'].append({'edition':e,'mode':m,'passed':True,'source_files_exact':3800,'release_state_verified':True,'native_registry_preserved':True,'synthetic_history_choice_preserved':True,'payload_sha256':self.artifacts['BlackLanturn-'+e+'-Kodi21-1.1.28.zip'],'installer_sha256':self.artifacts[gate.INSTALLER],'synthetic_playback_state_paths_preserved':12 if m!='clean' else 0,'clean_cleared_synthetic_playback_state':m=='clean','native_managed_versions_verified':m=='update','all_saved_data_unchanged':m=='update','unrelated_addon_unchanged':m=='update'})
 def test_exact_current_six_case_native_receipt_passes(self):self.assertTrue(gate.verify(self.receipt,self.root))
 def test_missing_or_duplicate_case_refuses(self):
  for change in ('missing','duplicate'):
   r=copy.deepcopy(self.receipt)
   if change=='missing':r['cases'].pop()
   else:r['cases'][-1]=r['cases'][0]
   with self.subTest(change=change),self.assertRaises(AssertionError):gate.verify(r,self.root)
 def test_source_changed_after_acceptance_refuses(self):
  (self.root/gate.INSTALLER).write_bytes(b'changed')
  with self.assertRaises(AssertionError):gate.verify(self.receipt,self.root)
 def test_missing_sandbox_or_preservation_refuses(self):
  for key in ('passed','network_blocked','personal_profile_denied'):
   r=copy.deepcopy(self.receipt);r[key]=False
   with self.subTest(key=key),self.assertRaises(AssertionError):gate.verify(r,self.root)
  r=copy.deepcopy(self.receipt);r['cases'][1]['synthetic_playback_state_paths_preserved']=0
  with self.assertRaises(AssertionError):gate.verify(r,self.root)

 def test_normal_startup_notice_requires_exact_source_and_artifacts(self):
  f=getattr(gate,'verify_startup_notice',None);self.assertTrue(callable(f),'Missing normal startup acceptance gate')
  controller={'default.py':'a'*64};installer={'default.py':'b'*64}
  receipt=dict.fromkeys(('passed','normal_startup','available_notice','update_dispatches_inplace','offline_update_message','preferences_history_preserved'),True)
  receipt.update(runtime='21.3',personal_profile_accessed=False,build_version='1.1.28',controller_files=controller,installer_files=installer,artifacts=self.artifacts)
  self.assertTrue(f(receipt,self.artifacts,controller,installer))
  for key,value in [('normal_startup',False),('available_notice',False),('offline_update_message',False),('update_dispatches_inplace',False),('personal_profile_accessed',True),('controller_files',{}),('installer_files',{}),('artifacts',{}),('preferences_history_preserved',False)]:
   bad=copy.deepcopy(receipt);bad[key]=value
   with self.subTest(key=key),self.assertRaises(AssertionError):f(bad,self.artifacts,controller,installer)

 def test_self_update_capability_requires_real_native_swap_cold_recovery_and_exact_source(self):
  f=getattr(gate,'verify_self_update',None);self.assertTrue(callable(f),'Missing native SELF/recovery acceptance gate')
  controller={'installer_recovery.py':'a'*64};installer={'resources/libs/inplace_update.py':'b'*64,'addon.xml':'c'*64}
  receipt=dict.fromkeys(('passed','upgraded','registered','close_later_exits','settings_preserved','cold_recovery_missing_installer','normal_startup_recovery','restart_required','fixture_metadata_only'),True)
  receipt.update(native_kodi='21.3',personal_profile_accessed=False,controller_files=controller,installer_files=installer,artifacts=self.artifacts,fixture_version='1.0.34',initial_capability='Installer33 installed first by wrapped addon package + native local-addon registry refresh; no old31 SELF capability claimed',final_restored_installer='1.0.33',evidence={key:{'sha256':'a'*64,'path':'compatibility/current-addons/release128-evidence/'+name}for key,name in [('native_self_update','native-self-update-result.json'),('cold_recovery','native-cold-recovery-result.json')]})
  evidence_root=self.root/'compatibility/current-addons/release128-evidence';evidence_root.mkdir(parents=True)
  native=dict(receipt,completion_default_close_kodi=True,native_dialogs=[{'label':'Update','answer':True},{'label':'Close later','answer':False}],navigation_open_count=1,exact_final_artifact_restored=True,intentional_process_exit=127,cold_backup_files=installer,journal_at_process_loss={'schema':1,'status':'applying','addons':{'plugin.program.blacklanturninstaller':{'before':installer,'after':dict(installer,**{'addon.xml':'e'*64}),'started':True,'enabled_before':True}}})
  native.pop('evidence')
  cold={'passed':True,'native_kodi':'21.3','runtime':'21.3 (21.3.0)','personal_profile_accessed':False,'network_blocked':True,'personal_profile_denied':True,'normal_startup_recovery':True,'restart_required':True,'settings_preserved':True,'restored_installer':'1.0.33','installer_files':installer,'controller_files':controller,'artifacts':self.artifacts,'native_dialog_heading':'BlackLanturn update recovered','native_dialog_body':'Close and reopen Kodi','protected_paths_compared':12,'installer_enabled':True,'addon_constructor_usable':True,'native_installer_version':'1.0.33'}
  for key,body in [('native_self_update',native),('cold_recovery',cold)]:
   path=self.root/receipt['evidence'][key]['path'];path.write_text(json.dumps(body));receipt['evidence'][key]['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
  actual_f=f
  def f(*args):
   with patch.object(gate,'ROOT',self.root):return actual_f(*args)
  self.assertTrue(f(receipt,self.artifacts,controller,installer))
  for key,value in [('registered',False),('close_later_exits',False),('cold_recovery_missing_installer',False),('normal_startup_recovery',False),('restart_required',False),('controller_files',{}),('installer_files',{}),('artifacts',{}),('fixture_metadata_only',False),('initial_capability','old31 upgraded without bootstrap'),('evidence',{})]:
   bad=copy.deepcopy(receipt);bad[key]=value
   with self.subTest(key=key),self.assertRaises(AssertionError):f(bad,self.artifacts,controller,installer)

  for mutation in ('missing','tampered','body_false','source_false','disabled','constructor_unusable','wrong_native_version','lost_prior_enabled_state'):
   bad=copy.deepcopy(receipt);ref=bad['evidence']['native_self_update' if mutation=='lost_prior_enabled_state' else 'cold_recovery'];path=self.root/ref['path'];original=path.read_bytes()
   if mutation=='missing':path.unlink()
   elif mutation=='tampered':path.write_bytes(original+b' ')
   else:
    body=json.loads(original)
    if mutation=='body_false':body['normal_startup_recovery']=False
    elif mutation=='source_false':body['controller_files']={}
    elif mutation=='disabled':body['installer_enabled']=False
    elif mutation=='constructor_unusable':body['addon_constructor_usable']=False
    elif mutation=='wrong_native_version':body['native_installer_version']='1.0.31'
    else:body['journal_at_process_loss']['addons']['plugin.program.blacklanturninstaller']['enabled_before']=False
    path.write_text(json.dumps(body));ref['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
   try:
    with self.subTest(mutation=mutation),self.assertRaises(AssertionError):f(bad,self.artifacts,controller,installer)
   finally:path.write_bytes(original)

 def test_details_hero_requires_current_source_and_reviewed_edges(self):
  controller={'resources/skins/Default/1080i/LiveReview.xml':'a'*64}
  r=dict.fromkeys(('passed','synthetic_local_media','artwork_captured','preview_played','compact'),True)
  r.update(personal_profile_accessed=False,provider_overrides=False,controller_files=controller,artifacts=self.artifacts,visual_review=dict.fromkeys(('artwork_compact','preview_compact','left_fade','right_fade','bottom_fade','metadata_retained'),True))
  self.assertTrue(gate.verify_details_hero(r,self.artifacts,controller))
  for key,value in [('controller_files',{}),('artifacts',{}),('preview_played',False),('personal_profile_accessed',True),('visual_review',{})]:
   bad=copy.deepcopy(r);bad[key]=value
   with self.subTest(key=key),self.assertRaises(AssertionError):gate.verify_details_hero(bad,self.artifacts,controller)
