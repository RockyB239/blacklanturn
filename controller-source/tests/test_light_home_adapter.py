import importlib,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
class Native:
    def __init__(self):self.props={'hero':'original'};self.calls=[]
    def setProperty(self,k,v):self.props[k]=v;self.calls.append(('property',k,v))
    def getProperty(self,k):return self.props.get(k,'')
    def setFocusId(self,v):self.calls.append(('focus',v))
    def getFocusId(self):return 901
    def getControl(self,k):raise AssertionError('Initialization touched native control')
    def close(self):self.calls.append(('close',))
class FakeBase:pass
class FakeReview(FakeBase):
    def onInit(self):
        self.alive=True;self.rows=[];self.setProperty('hero','reset');self.getControl(900).reset();self.setFocusId(5)
        self.read_back=self.getProperty('hero')
    def click(self,n):self.clicked=n;self.setProperty('action','handled');self.close()
class AdapterTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('light_home_adapter'),'Persistent adapter absent')
        return importlib.import_module('light_home_adapter')
    def test_initialization_is_buffered_then_state_adopts_without_native_reset(self):
        m=self.module();view=Native();c=m.ControllerAdapter(FakeReview,view,{'hero':'original'})
        c.onInit();self.assertEqual(view.calls,[]);self.assertEqual(c.read_back,'reset')
        c.adopt({'rows':[['kept']], 'selected':{'file':'stable'}})
        self.assertEqual(c.rows,[['kept']]);self.assertEqual(view.props['hero'],'original');self.assertEqual(view.calls,[])
        c.click(102);self.assertEqual(view.calls,[('property','action','handled'),('close',)])
    def test_retire_clears_native_reference_and_cancels_controller(self):
        m=self.module();view=Native();c=m.ControllerAdapter(FakeReview,view,{})
        c.onInit();c.adopt({});c.retire();self.assertFalse(c.alive);self.assertIsNone(c._native)
        with self.assertRaises(RuntimeError):c.setProperty('hero','late')
    def test_native_class_is_never_constructed_or_reassigned(self):
        m=self.module()
        class Review(FakeReview):
            def __new__(cls,*a,**k):raise AssertionError('Second native window allocated')
        c=m.ControllerAdapter(Review,Native(),{});c.onInit();self.assertTrue(c.alive)
