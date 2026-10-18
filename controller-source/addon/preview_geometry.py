"""Proportional cover fit for the decorative preview, independent of TV resolution."""
import math,json

class PreviewRendererGuard:
    """Use software decoding only while an Android preview is owned.

    Kodi 21's texture MediaCodec initialization waits on its UI thread. A Stop
    processed there during initialization waits on the decoder instead, so an
    immediately cancelled decorative preview can deadlock both threads. Software
    previews also support the cover crop/fades. Journal both original decoder
    preferences before changing either, and restore them before normal playback.
    """
    SETTINGS={'surface':'videoplayer.usemediacodecsurface','mediacodec':'videoplayer.usemediacodec'}
    def __init__(self,rpc,path,android):
        self.rpc=rpc;self.path=path;self.android=android;self.generation=0
    def _saved(self):
        saved=json.loads(self.path.read_text())
        legacy=isinstance(saved,dict) and set(saved)=={'surface'} and saved['surface'] is True
        if not legacy and (not isinstance(saved,dict) or set(saved)!=set(self.SETTINGS) or any(type(value) is not bool for value in saved.values())):
            raise ValueError('Invalid preview decoder recovery record')
        return saved
    def acquire(self):
        if not self.android:return True
        self.generation+=1;generation=self.generation
        try:
            exists=self.path.exists();saved=self._saved() if exists else {}
            for key,setting in self.SETTINGS.items():
                if key not in saved:saved[key]=self.rpc('Settings.GetSettingValue',{'setting':setting}).get('result',{}).get('value')
            if generation!=self.generation or any(type(value) is not bool for value in saved.values()):return False
            if not exists and not any(saved.values()):return True
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temporary=self.path.with_suffix('.tmp');temporary.write_text(json.dumps(saved));temporary.replace(self.path)
            for setting in self.SETTINGS.values():
                if generation!=self.generation:return False
                changed=self.rpc('Settings.SetSettingValue',{'setting':setting,'value':False}).get('result') is True
                # Native boundaries may reenter cancellation on this thread.
                # Never continue an acquisition invalidated by restore/new owner.
                if generation!=self.generation or not changed:return False
            return True
        except (OSError,ValueError,TypeError):return False
    def restore(self):
        self.generation+=1
        if not self.android or not self.path.exists():return True
        try:
            saved=self._saved()
            for key,value in saved.items():
                if self.rpc('Settings.SetSettingValue',{'setting':self.SETTINGS[key],'value':value}).get('result') is not True:return False
            self.path.unlink();return True
        except (OSError,ValueError,TypeError):return False

def preview_display_aspect(stream,aspect_label=''):
    def positive(value):
        try:
            value=float(value)
            return value if math.isfinite(value) and value>0 else None
        except (TypeError,ValueError):return None
    width=positive(stream.get('width'));height=positive(stream.get('height'))
    encoded=width/height if width and height else None
    displayed=positive(aspect_label)
    # Kodi rounds the display-aspect label; retain exact dimensions for square
    # pixels, but honor a materially different display ratio for anamorphic video.
    return encoded if encoded and (not displayed or abs(encoded-displayed)<0.01) else displayed

def preview_fill_viewmode(stream,aspect_label='',compact=True):
    aspect=preview_display_aspect(stream,aspect_label)
    if not aspect:return 'zoom'
    target=1530/689 if compact else 1800/810
    zoom=max(target/aspect,aspect/target)
    if not math.isfinite(zoom) or zoom>4:return 'zoom'
    return {'zoom':zoom,'pixelratio':1.0,'verticalshift':0.0,'nonlinearstretch':False}
