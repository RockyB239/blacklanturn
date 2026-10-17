import sys,unittest,tempfile,importlib.util,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))

class PreviewRenderer(unittest.TestCase):
    def guard(self,rpc,path,android=True):
        import preview_geometry
        self.assertTrue(hasattr(preview_geometry,'PreviewRendererGuard'))
        return preview_geometry.PreviewRendererGuard(rpc,path,android)

    def test_preview_uses_texture_rendering_then_restores_surface(self):
        state={'surface':True};calls=[]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'restore.json'
            def rpc(method,params):
                calls.append((method,params))
                if method=='Settings.GetSettingValue':return {'result':{'value':state['surface']}}
                if params['value'] is False:self.assertTrue(path.exists())
                state['surface']=params['value'];return {'result':True}
            guard=self.guard(rpc,path)
            self.assertTrue(guard.acquire());self.assertFalse(state['surface'])
            self.assertTrue(guard.acquire());self.assertFalse(state['surface'])
            self.assertTrue(guard.restore());self.assertTrue(state['surface'])
            self.assertFalse(path.exists())
            self.assertTrue(all(params['setting']=='videoplayer.usemediacodecsurface' for _,params in calls))

    def test_existing_disabled_surface_is_left_disabled(self):
        calls=[]
        def rpc(method,params):calls.append(method);return {'result':{'value':False}}
        with tempfile.TemporaryDirectory() as tmp:
            guard=self.guard(rpc,Path(tmp)/'restore.json')
            self.assertTrue(guard.acquire());self.assertTrue(guard.restore())
            self.assertEqual(calls,['Settings.GetSettingValue'])

    def test_restart_recovers_interrupted_preview_before_another_video(self):
        calls=[]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'restore.json';path.write_text(json.dumps({'surface':True}))
            guard=self.guard(lambda m,p:calls.append((m,p)) or {'result':True},path)
            self.assertTrue(guard.restore());self.assertFalse(path.exists())
            self.assertEqual(calls,[('Settings.SetSettingValue',{'setting':'videoplayer.usemediacodecsurface','value':True})])

    def test_failed_restore_keeps_recovery_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'restore.json';path.write_text(json.dumps({'surface':True}))
            guard=self.guard(lambda m,p:{'error':{}},path)
            self.assertFalse(guard.restore());self.assertTrue(path.exists())

    def test_failed_acquire_cannot_allow_surface_playback_on_retry(self):
        calls=[]
        def rpc(method,params):
            calls.append(method)
            return {'result':{'value':True}} if method=='Settings.GetSettingValue' else {'error':{}}
        with tempfile.TemporaryDirectory() as tmp:
            guard=self.guard(rpc,Path(tmp)/'restore.json')
            self.assertFalse(guard.acquire());self.assertFalse(guard.acquire())

    def test_non_android_does_not_change_rendering(self):
        with tempfile.TemporaryDirectory() as tmp:
            guard=self.guard(lambda *a:self.fail('Mac renderer must not be changed'),Path(tmp)/'restore.json',False)
            self.assertTrue(guard.acquire());self.assertTrue(guard.restore())

if __name__=='__main__':unittest.main()
