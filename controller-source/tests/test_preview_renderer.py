import sys,unittest,tempfile,importlib.util,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))

class PreviewRenderer(unittest.TestCase):
    def test_cancel_during_preview_start_never_uses_main_thread_dependent_android_decoder(self):
        # Kodi's texture MediaCodec startup synchronously calls its UI thread.
        # A Stop on that UI thread waits for startup, so this decoder cannot be
        # selected for a decorative preview that navigation may stop immediately.
        state={'videoplayer.usemediacodecsurface':True,'videoplayer.usemediacodec':True}
        original=dict(state)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'restore.json'
            def rpc(method,params):
                key=params['setting']
                if method=='Settings.GetSettingValue':return {'result':{'value':state[key]}}
                self.assertTrue(path.exists(),'Recovery must precede temporary decoder changes')
                state[key]=params['value'];return {'result':True}
            guard=self.guard(rpc,path)
            self.assertTrue(guard.acquire())
            self.assertFalse(any(state.values()),'Preview could enter the deadlocking Android codec startup')
            self.assertTrue(guard.restore());self.assertEqual(state,original)
            self.assertFalse(path.exists())

    def guard(self,rpc,path,android=True):
        import preview_geometry
        self.assertTrue(hasattr(preview_geometry,'PreviewRendererGuard'))
        return preview_geometry.PreviewRendererGuard(rpc,path,android)

    def test_every_original_decoder_combination_is_restored_after_repeated_acquire(self):
        from itertools import product
        for surface,codec in product([False,True],repeat=2):
            with self.subTest(surface=surface,codec=codec),tempfile.TemporaryDirectory() as tmp:
                state={'videoplayer.usemediacodecsurface':surface,'videoplayer.usemediacodec':codec};before=dict(state);calls=[]
                def rpc(method,params):
                    calls.append((method,dict(params)));key=params['setting']
                    if method=='Settings.GetSettingValue':return {'result':{'value':state[key]}}
                    state[key]=params['value'];return {'result':True}
                guard=self.guard(rpc,Path(tmp)/'restore.json')
                self.assertTrue(guard.acquire());self.assertTrue(guard.acquire())
                self.assertEqual(state,{'videoplayer.usemediacodecsurface':False,'videoplayer.usemediacodec':False})
                self.assertTrue(guard.restore());self.assertEqual(state,before)
                if not surface and not codec:self.assertFalse(any(m=='Settings.SetSettingValue' for m,_ in calls))

    def test_restart_recovers_both_original_settings_after_interrupted_preview(self):
        calls=[]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'restore.json';path.write_text(json.dumps({'surface':False,'mediacodec':True}))
            guard=self.guard(lambda m,p:calls.append((m,p)) or {'result':True},path)
            self.assertTrue(guard.restore());self.assertFalse(path.exists())
            self.assertCountEqual(calls,[('Settings.SetSettingValue',{'setting':'videoplayer.usemediacodecsurface','value':False}),('Settings.SetSettingValue',{'setting':'videoplayer.usemediacodec','value':True})])

    def test_legacy_restart_record_does_not_change_unrecorded_decoder_preference(self):
        calls=[]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'restore.json';path.write_text(json.dumps({'surface':True}))
            guard=self.guard(lambda m,p:calls.append((m,p)) or {'result':True},path)
            self.assertTrue(guard.restore());self.assertFalse(path.exists())
            self.assertEqual(calls,[('Settings.SetSettingValue',{'setting':'videoplayer.usemediacodecsurface','value':True})])

    def test_failed_second_decoder_change_blocks_preview_and_retains_full_recovery(self):
        state={'videoplayer.usemediacodecsurface':True,'videoplayer.usemediacodec':True}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'restore.json'
            def rpc(method,params):
                key=params['setting']
                if method=='Settings.GetSettingValue':return {'result':{'value':state[key]}}
                if key=='videoplayer.usemediacodec' and params['value'] is False:return {'error':{}}
                state[key]=params['value'];return {'result':True}
            guard=self.guard(rpc,path)
            self.assertFalse(guard.acquire());self.assertFalse(guard.acquire());self.assertTrue(path.exists())
            self.assertTrue(guard.restore());self.assertTrue(all(state.values()));self.assertFalse(path.exists())

    def test_reentrant_cancellation_during_first_decoder_write_stops_remaining_writes(self):
        state={'videoplayer.usemediacodecsurface':True,'videoplayer.usemediacodec':True};before=dict(state)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'restore.json';cancelled=False
            def rpc(method,params):
                nonlocal cancelled
                key=params['setting']
                if method=='Settings.GetSettingValue':return {'result':{'value':state[key]}}
                state[key]=params['value']
                if not cancelled and params['value'] is False:
                    cancelled=True;self.assertTrue(guard.restore())
                return {'result':True}
            guard=self.guard(rpc,path)
            self.assertFalse(guard.acquire(),'Cancelled acquisition must not resume after restoration')
            self.assertEqual(state,before);self.assertFalse(path.exists())

    def test_failed_restore_keeps_recovery_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'restore.json';path.write_text(json.dumps({'surface':True,'mediacodec':True}))
            guard=self.guard(lambda m,p:{'error':{}},path)
            self.assertFalse(guard.restore());self.assertTrue(path.exists())

    def test_invalid_recovery_or_unavailable_setting_never_allows_preview(self):
        for saved in [{'surface':1,'mediacodec':True},{'surface':True,'unexpected':True}]:
            with self.subTest(saved=saved),tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'restore.json';path.write_text(json.dumps(saved));calls=[]
                guard=self.guard(lambda *a:calls.append(a) or {'result':True},path)
                self.assertFalse(guard.acquire());self.assertFalse(guard.restore());self.assertEqual(calls,[])
        with tempfile.TemporaryDirectory() as tmp:
            guard=self.guard(lambda *a:{'error':{}},Path(tmp)/'restore.json')
            self.assertFalse(guard.acquire())

    def test_non_android_does_not_change_rendering(self):
        with tempfile.TemporaryDirectory() as tmp:
            guard=self.guard(lambda *a:self.fail('Mac renderer must not be changed'),Path(tmp)/'restore.json',False)
            self.assertTrue(guard.acquire());self.assertTrue(guard.restore())

if __name__=='__main__':unittest.main()
