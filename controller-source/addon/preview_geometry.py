"""Proportional cover fit for the decorative preview, independent of TV resolution."""
import math,json

class PreviewRendererGuard:
    """Use MediaCodec texture rendering only while an Android preview is owned.

    Surface clips the destination rectangle without applying the matching source
    crop. Texture rendering supports the proportional cover crop and GUI fades.
    Record the original enabled Surface setting before changing it, so a later
    startup can recover after an interrupted preview.
    """
    def __init__(self,rpc,path,android):
        self.rpc=rpc;self.path=path;self.android=android
    def acquire(self):
        if not self.android:return True
        if self.path.exists():
            if json.loads(self.path.read_text())!={'surface':True}:return False
            return self.rpc('Settings.SetSettingValue',{'setting':'videoplayer.usemediacodecsurface','value':False}).get('result') is True
        value=self.rpc('Settings.GetSettingValue',{'setting':'videoplayer.usemediacodecsurface'}).get('result',{}).get('value')
        if value is False:return True
        if value is not True:return False
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temporary=self.path.with_suffix('.tmp');temporary.write_text(json.dumps({'surface':True}));temporary.replace(self.path)
        return self.rpc('Settings.SetSettingValue',{'setting':'videoplayer.usemediacodecsurface','value':False}).get('result') is True
    def restore(self):
        if not self.android or not self.path.exists():return True
        if json.loads(self.path.read_text())!={'surface':True}:return False
        if self.rpc('Settings.SetSettingValue',{'setting':'videoplayer.usemediacodecsurface','value':True}).get('result') is not True:return False
        self.path.unlink();return True

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
