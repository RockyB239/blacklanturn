import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from update_notes import observe,acknowledge,pending,read_state,write_state,notes_text

def inv(version='1.0',extra=False):
 result=[{'addonid':'plugin.video.example','name':'Example','version':version,'enabled':True}]
 if extra:result.append({'addonid':'plugin.video.other','name':'Other','version':'2.0','enabled':True})
 return result
class UpdateNotesTests(unittest.TestCase):
 def test_first_run_quiet_and_unchanged(self):
  state=observe({},inv(),1);self.assertFalse(pending(state));self.assertEqual(observe(state,inv(),2),state)
 def test_changes_grouped_once_and_acknowledged(self):
  state=observe(observe({},inv(),1),inv('2.0',True),2)
  self.assertEqual(len(state['history']),1);self.assertEqual(len(pending(state)[0]['changes']),2)
  self.assertFalse(pending(acknowledge(state)));self.assertEqual(observe(state,inv('2.0',True),3),state)
 def test_invalid_inventory_leaves_old_state(self):
  state=observe({},inv(),1)
  for bad in (None,[],[{'addonid':'plugin.video.example','version':''}],[{'addonid':'bad','version':'1'}]):
   with self.assertRaises(ValueError):observe(state,bad,2)
  self.assertEqual(state['inventory']['plugin.video.example']['version'],'1.0')
 def test_failed_install_no_success(self):
  state=observe({},inv(),1);self.assertEqual(observe(state,inv(),3),state)
 def test_removed_addon_is_not_an_update(self):
  state=observe({},inv(extra=True),1);state=observe(state,inv(),2,complete=True)
  self.assertFalse(pending(state));state=observe(state,inv(extra=True),3)
  self.assertEqual(pending(state)[0]['changes'][0]['kind'],'installed')
 def test_wording_does_not_claim_upstream_improvements(self):
  state=observe(observe({},inv('2.0'),1),inv('1.0'),2)
  text=notes_text(state);self.assertIn('2.0 → 1.0',text);self.assertNotIn('improvements',text)
 def test_disabled_hides_notice_not_history(self):
  state=observe(observe({},inv(),1),inv('2'),2);state['enabled']=False
  self.assertFalse(pending(state));self.assertIn('Example',notes_text(state))
 def test_no_credentials_and_markup_from_rpc(self):
  data=inv('2');data[0].update(name='[B]Example[/B]',token='SECRET',path='https://secret')
  state=observe(observe({},inv(),1),data,2);raw=json.dumps(state)
  self.assertNotIn('SECRET',raw);self.assertNotIn('https',raw);self.assertNotIn('[B]',raw)
 def test_history_bounded(self):
  state=observe({},inv(),0)
  for n in range(35):state=observe(state,inv(str(n)),n+1)
  self.assertEqual(len(state['history']),20)
 def test_atomic_round_trip_and_corrupt_state_fails_closed(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'state.json';state=observe({},inv(),1);write_state(path,state);self.assertEqual(read_state(path),state)
   path.write_text('{broken')
   with self.assertRaises(ValueError):read_state(path)
   self.assertEqual(path.read_text(),'{broken')
 def test_pending_respects_unseen_batches_only(self):
  state=observe(observe({},inv(),1),inv('2'),2);state=acknowledge(state)
  state=observe(state,inv('3'),3);self.assertEqual(len(pending(state)),1)
 def test_does_not_mutate_inputs(self):
  old=observe({},inv(),1);before=copy.deepcopy(old);observe(old,inv('2'),2);self.assertEqual(old,before)
 def test_notice_preference_can_be_saved_before_inventory(self):
  from update_notes import empty_state
  old=empty_state();old['enabled']=False
  state=observe(old,inv(),1);self.assertFalse(pending(state));self.assertFalse(state['enabled']);self.assertEqual(state['history'],[])
 def test_cross_process_transaction_retains_both_changes(self):
  from update_notes import transact,empty_state
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'state.json';transact(path,lambda s:empty_state())
   transact(path,lambda s:dict(s,enabled=False));transact(path,lambda s:dict(s,enabled=True))
   state=read_state(path);self.assertTrue(state['enabled']);self.assertEqual(state['seen'],0)
 def test_exact_reviewed_release_notes_only(self):
  catalog={'plugin.video.example':{'2':{'summary':['Retains tested playback fix']}}}
  old=observe({},inv(),1)
  state=observe(old,inv('2'),2,catalog);self.assertIn('Retains tested playback fix',notes_text(state))
  state=observe(old,inv('3'),2,catalog);self.assertNotIn('Retains tested playback fix',notes_text(state))
 def test_transaction_persists_mutating_acknowledgement(self):
  from update_notes import transact
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'state.json';state=observe(observe({},inv(),1),inv('2'),2);write_state(path,state)
   def mutate(s):s['seen']=s['sequence'];return s
   transact(path,mutate);self.assertFalse(pending(read_state(path)))
 def test_partial_rpc_inventory_is_rejected_without_erasing_prior(self):
  state=observe({},inv(extra=True),1)
  with self.assertRaises(ValueError):observe(state,inv(),2)
 def test_structural_corruption_rejected_before_rewrite(self):
  from update_notes import validate
  state=observe(observe({},inv(),1),inv('2'),2)
  variants=[]
  bad=copy.deepcopy(state);del bad['history'][0]['time'];variants.append(bad)
  bad=copy.deepcopy(state);del bad['history'][0]['changes'][0]['id'];variants.append(bad)
  bad=copy.deepcopy(state);bad['sequence']=0;variants.append(bad)
  bad=copy.deepcopy(state);bad['seen']=3;variants.append(bad)
  bad=copy.deepcopy(state);bad['history'].append(copy.deepcopy(bad['history'][0]));variants.append(bad)
  for broken in variants:
   with self.subTest(broken=broken),self.assertRaises(ValueError):validate(broken)
 def test_native_kodi_invalid_dialog_id_is_not_an_open_dialog(self):
  from update_notes import has_dialog
  for value in (9999,0,-1):self.assertFalse(has_dialog(value))
  self.assertTrue(has_dialog(10100))
 def test_complete_inventory_rejects_truncated_rpc_lists(self):
  from update_notes import complete_inventory
  good={'result':{'addons':inv(),'limits':{'start':0,'end':1,'total':1}}}
  self.assertEqual(complete_inventory(good),inv())
  good['result']['limits']['total']=2
  with self.assertRaises(ValueError):complete_inventory(good)
