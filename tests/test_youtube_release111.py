"""Synthetic gate fixtures only: these are not native controller 82 evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools import verify_release


class Release111Acceptance(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.addCleanup(self.temp.cleanup)
  root=Path(self.temp.name)
  (root/'controller-source').mkdir()
  self.baseline={'controller':'0.1.81','files':{name:'synthetic-old-'+name for name in ('addon.xml','youtube_home.py','youtube_provider.py','youtube_relevance.py','live_review.py')}}
  self.manifest=copy.deepcopy(self.baseline)
  self.manifest['controller']='0.1.82'
  for name in ('addon.xml','youtube_home.py','youtube_provider.py','youtube_relevance.py'):
   self.manifest['files'][name]='synthetic-new-'+name
  prior_device={'source_exact':True,'continuation_rows':3,'continuation_batches':3,'inline_preview':{'media_seconds':45,'max_height':720,'codec':'h264','fade':True,'max_probe_gap_seconds':1,'same_hover_no_restart':True},'fullscreen':{'automatic':True,'ceiling':2160,'selected_height':1080},'category_relevance':{'music_rows_checked':1,'nonmusic_in_added_music_choices':0},'ordinary_restart':True,'authorization_grants_preserved':True,'settings_preserved':True,'youtube_history_preserved':True}
  self.prior={'controller':'0.1.81','files':copy.deepcopy(self.baseline['files']),'passed':True,'devices':{name:copy.deepcopy(prior_device) for name in ('mac','fire','apple_tv')}}
  self.prior['devices']['fire'].update(cancel_moments=[{'moment':moment,'no_late_play':True,'normal_core_restored':True} for moment in ('queued','opening','playing')],normal_clip_decoder='amc-h264')
  self.prior_path=root/'controller-source/youtube-release110-verification.json'
  self.prior_path.write_text(json.dumps(self.prior))
  (root/'controller-source/manifest81.json').write_text(json.dumps(self.baseline))
  device={key:True for key in ('source_exact','ordinary_restart','authorization_grants_preserved','settings_preserved','youtube_history_preserved','refresh_recommendations_verified','continuation_preserves_existing_cards')}
  device['category_relevance']={'subject_rows_checked':1,'continued_new_choices':2,'row_mismatches':0}
  self.receipt={'controller':'0.1.82','files':copy.deepcopy(self.manifest['files']),'passed':True,'prior_playback_basis':{'controller':'0.1.81','files':copy.deepcopy(self.baseline['files']),'receipt':'controller-source/youtube-release110-verification.json'},'devices':{name:copy.deepcopy(device) for name in ('mac','fire','apple_tv')}}
  self.root_patch=patch.object(verify_release,'ROOT',root)
  self.root_patch.start()
  self.addCleanup(self.root_patch.stop)
 def check(self,receipt=None,manifest=None):
  gate=getattr(verify_release,'verify_release111_acceptance',None)
  self.assertTrue(callable(gate),'Missing release 1.1.11 source-delta and fresh-native gate')
  gate(self.receipt if receipt is None else receipt,self.manifest if manifest is None else manifest)
 def test_complete_synthetic_gate_fixture_passes(self):self.check()
 def test_missing_failed_or_source_changed_current_evidence_blocks_release(self):
  for change in ('version','manifest_version','files','missing_device','extra_device','passed'):
   with self.subTest(change=change):
    r=copy.deepcopy(self.receipt);m=copy.deepcopy(self.manifest)
    if change=='version':r['controller']='0.1.81'
    elif change=='manifest_version':m['controller']='0.1.81'
    elif change=='files':r['files']['youtube_provider.py']='stale'
    elif change=='missing_device':del r['devices']['apple_tv']
    elif change=='extra_device':r['devices']['unverified']={}
    else:r['passed']=False
    with self.assertRaises(AssertionError):self.check(r,m)
 def test_each_device_requires_fresh_restart_preservation_refresh_and_new_subject_choices(self):
  failures={key:False for key in ('source_exact','ordinary_restart','authorization_grants_preserved','settings_preserved','youtube_history_preserved','refresh_recommendations_verified','continuation_preserves_existing_cards')}
  failures.update({'category_relevance.subject_rows_checked':0,'category_relevance.continued_new_choices':0,'category_relevance.row_mismatches':1})
  for name in ('mac','fire','apple_tv'):
   for key,value in failures.items():
    with self.subTest(device=name,change=key):
     r=copy.deepcopy(self.receipt);d=r['devices'][name];path=key.split('.')
     for part in path[:-1]:d=d[part]
     d[path[-1]]=value
     with self.assertRaises(AssertionError):self.check(r)
 def test_playback_inheritance_rejects_any_different_source_delta(self):
  for change in ('playback_changed','allowed_path_unchanged','added_path','deleted_path','deleted_allowed_path'):
   with self.subTest(change=change):
    m=copy.deepcopy(self.manifest)
    if change=='playback_changed':m['files']['live_review.py']='changed'
    elif change=='allowed_path_unchanged':m['files']['youtube_home.py']=self.baseline['files']['youtube_home.py']
    elif change=='added_path':m['files']['new.py']='added'
    elif change=='deleted_path':del m['files']['live_review.py']
    else:del m['files']['youtube_home.py']
    r=copy.deepcopy(self.receipt);r['files']=copy.deepcopy(m['files'])
    with self.assertRaises(AssertionError):self.check(r,m)
 def test_inherited_playback_requires_identified_unchanged_successful_prior_receipt(self):
  for change in ('basis_version','basis_source','basis_receipt','prior_failed','prior_source','prior_preview','prior_fire_cancellation'):
   with self.subTest(change=change):
    r=copy.deepcopy(self.receipt);prior=copy.deepcopy(self.prior)
    if change=='basis_version':r['prior_playback_basis']['controller']='0.1.82'
    elif change=='basis_source':r['prior_playback_basis']['files']['live_review.py']='stale'
    elif change=='basis_receipt':r['prior_playback_basis']['receipt']='other.json'
    elif change=='prior_failed':prior['passed']=False
    elif change=='prior_source':prior['files']['live_review.py']='stale'
    elif change=='prior_preview':prior['devices']['mac']['inline_preview']['codec']='vp9'
    else:prior['devices']['fire']['cancel_moments']=[]
    self.prior_path.write_text(json.dumps(prior))
    with self.assertRaises(AssertionError):self.check(r)
    self.prior_path.write_text(json.dumps(self.prior))

if __name__=='__main__':unittest.main()
