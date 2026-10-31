"""One native window, with ordinary Python controller state and explicit UI boundary."""
import types,time
class BufferedControl:
    """Initialization cannot reset, select, hide or focus the already visible controls."""
    def __init__(self,identity):self.identity=identity
    def __getattr__(self,name):
        if name.startswith(('set','control')) or name in ('reset','addItems','addItem','selectItem'):return lambda *a,**k:None
        if name=='getSelectedPosition':return lambda:0
        raise AttributeError(name)

class ControllerAdapter:
    def __init__(self,behavior,native,properties):
        self._behavior=behavior;self._native=native;self._buffered=True;self._properties=dict(properties);self._controls={};self.defer_startup_workers=True
    def __getattr__(self,name):
        # Only Python behavior is rebound. Kodi descriptors and constructors are
        # never borrowed, instantiated, or called with a non-native receiver.
        for base in self._behavior.__mro__:
            value=vars(base).get(name)
            if isinstance(value,types.FunctionType):
                bound=types.MethodType(value,self);setattr(self,name,bound);return bound
        raise AttributeError(name)
    def _view(self):
        if self._native is None:raise RuntimeError('Retired native view')
        return self._native
    def setProperty(self,key,value):
        if self._buffered:self._properties[key]=value
        else:self._view().setProperty(key,value)
    def getProperty(self,key):return self._properties.get(key,'') if self._buffered else self._view().getProperty(key)
    def clearProperty(self,key):self.setProperty(key,'')
    def getControl(self,identity):
        if not self._buffered:return self._view().getControl(identity)
        if identity not in self._controls:self._controls[identity]=BufferedControl(identity)
        return self._controls[identity]
    def setFocusId(self,identity):
        if not self._buffered:self._view().setFocusId(identity)
    def getFocusId(self):
        if getattr(self,'_dispatch_choice',None):return self._dispatch_choice[0]
        return 5 if self._buffered else self._view().getFocusId()
    def chosen(self,cid=None):
        forced=getattr(self,'_dispatch_choice',None)
        if forced and (cid is None or cid==forced[0]):return forced[1]
        return self._behavior.chosen(self,cid)
    def dispatch_choice(self,kind,cid,item):
        self._dispatch_choice=(cid,item)
        try:
            if kind=='context':return self.title_actions()
            return self.onClick(cid)
        finally:self._dispatch_choice=None
    def dispatch_navigation(self,entry):
        self.search_row_step=None;self.input_generation+=1;self.dwell=time.monotonic()
        if self.owned_preview and not self.preview_dispatched:self.stop_preview()
        self.startup_idle=False;self.setProperty('startupIdle','false')
        return self.activate_navigation(entry)
    def close(self):
        if not self._buffered:self._view().close()
        else:self.alive=False
    def adopt(self,state):
        for key,value in state.items():setattr(self,key,value)
        self._buffered=False;self._properties={};self._controls={}
    def retire(self):
        self.alive=False;self.window_lifetime=None;self._native=None;self._properties={};self._controls={}
