"""Release 1.1.10 requires fresh exact-source proof on all three devices."""
import copy,unittest
from tools import verify_release

class Release110Acceptance(unittest.TestCase):
 def setUp(self):
  self.manifest={'controller':'0.1.81','files':{'addon.xml':'source-digest','youtube_provider.py':'provider-digest'}}
  device={'source_exact':True,'continuation_rows':3,'continuation_batches':3,'inline_preview':{'media_seconds':45,'max_height':720,'codec':'h264','fade':True,'max_probe_gap_seconds':1,'same_hover_no_restart':True},'fullscreen':{'automatic':True,'ceiling':2160,'selected_height':1080},'category_relevance':{'music_rows_checked':1,'nonmusic_in_added_music_choices':0},'ordinary_restart':True,'authorization_grants_preserved':True,'settings_preserved':True,'youtube_history_preserved':True}
  self.receipt={'controller':'0.1.81','files':copy.deepcopy(self.manifest['files']),'passed':True,'devices':{name:copy.deepcopy(device) for name in ('mac','fire','apple_tv')}}
  self.receipt['devices']['fire'].update(cancel_moments=[{'moment':moment,'no_late_play':True,'normal_core_restored':True} for moment in ('queued','opening','playing')],normal_clip_decoder='amc-h264')
 def check(self,receipt=None,manifest=None):
  gate=getattr(verify_release,'verify_release110_acceptance',None)
  self.assertTrue(callable(gate),'Missing fresh three-device release 1.1.10 gate')
  gate(receipt or self.receipt,manifest or self.manifest)
 def test_complete_exact_source_device_proof_passes(self):self.check()
 def test_source_or_device_coverage_drift_blocks_release(self):
  for change in ('version','source','missing_device','failed','source_exact'):
   with self.subTest(change=change):
    r=copy.deepcopy(self.receipt)
    if change=='version':r['controller']='0.1.80'
    elif change=='source':r['files']['youtube_provider.py']='stale'
    elif change=='missing_device':del r['devices']['apple_tv']
    elif change=='failed':r['passed']=False
    else:r['devices']['mac']['source_exact']=False
    with self.assertRaises(AssertionError):self.check(r)
 def test_each_device_requires_current_playback_and_preservation_proof(self):
  failures={
   'continuation_rows':2,'continuation_batches':2,'inline_preview.media_seconds':30,
   'inline_preview.max_height':1080,'inline_preview.codec':'vp9','inline_preview.fade':False,
   'inline_preview.max_probe_gap_seconds':5,'inline_preview.same_hover_no_restart':False,
   'fullscreen.automatic':False,'fullscreen.ceiling':1080,'fullscreen.selected_height':720,
   'category_relevance.music_rows_checked':0,'category_relevance.nonmusic_in_added_music_choices':1,
   'ordinary_restart':False,'authorization_grants_preserved':False,'settings_preserved':False,'youtube_history_preserved':False}
  for name in ('mac','fire','apple_tv'):
   for key,value in failures.items():
    with self.subTest(device=name,change=key):
     r=copy.deepcopy(self.receipt);d=r['devices'][name];path=key.split('.')
     for part in path[:-1]:d=d[part]
     d[path[-1]]=value
     with self.assertRaises(AssertionError):self.check(r)
 def test_fire_cancellation_and_normal_hardware_decoder_are_required(self):
  for change in ('phase','late_play','restore','decoder'):
   with self.subTest(change=change):
    r=copy.deepcopy(self.receipt);f=r['devices']['fire']
    if change=='phase':f['cancel_moments']=f['cancel_moments'][:2]
    elif change=='late_play':f['cancel_moments'][0]['no_late_play']=False
    elif change=='restore':f['cancel_moments'][1]['normal_core_restored']=False
    else:f['normal_clip_decoder']='ff-h264'
    with self.assertRaises(AssertionError):self.check(r)

if __name__=='__main__':unittest.main()
