"""Bounded preview-only detection of embedded letterboxing; no stored video frames."""
import json,math,hashlib

def top_border_fraction(pixels,width,height):
    if width<20 or height<20 or len(pixels)!=width*height*4:return None
    pixels=memoryview(pixels);left=int(width*.05);right=width-left
    def black_row(y):
        black=sum(max(pixels[(y*width+x)*4:(y*width+x)*4+3])<=24 for x in range(left,right))
        return black/(right-left)>=.99
    limit=int(height*.12);top=bottom=0
    while top<=limit and black_row(top):top+=1
    while bottom<=limit and black_row(height-1-bottom):bottom+=1
    if top>limit or bottom>limit:return None
    if bool(top)!=bool(bottom) or abs(top-bottom)>max(1,height*.02):return None
    # A dark frame cannot establish that a black edge is permanent padding.
    points=[max(pixels[(y*width+x)*4:(y*width+x)*4+3]) for y in range(top+2,height-bottom-2,2) for x in range(left,right,4)]
    if not points or sum(v>=48 for v in points)/len(points)<.25:return None
    if top<2 and bottom<2:return 0
    return top/height

def top_aligned_viewmode(fit,fraction,source_aspect,compact,flipped=False):
    if not isinstance(fit,dict) or not fraction:return fit
    if not (0<fraction<=.12 and source_aspect>0):return fit
    target=1530/689 if compact else 1800/810
    original_height=min(1,target/source_aspect)*fit['zoom']
    # Kodi shift values below -1 move an oversized rectangle upward. Convert
    # the observed visible-border fraction to that renderer's shift range.
    result=dict(fit);result['verticalshift']=(1 if flipped else -1)*(1+2*fraction/(original_height+1))
    return result

class PreviewBarScan:
    def __init__(self,factory,compact,now):
        self.factory=factory;self.width=240
        self.height=round(self.width/(1530/689 if compact else 1800/810))
        self.capture=None;self.next_at=now+.6;self.attempts=0
        self.samples=[];self.done=False;self.result=None;self.observations=[]
    def close(self):
        self.capture=None;self.done=True
    def tick(self,now):
        if self.done or now<self.next_at:return
        self.next_at=now+.35;self.attempts+=1
        try:
            if self.capture is None:
                self.capture=self.factory();self.capture.capture(self.width,self.height)
            pixels=self.capture.getImage(30)
            if len(pixels)==self.width*self.height*4:
                row_peaks=[max(pixels[y*self.width*4:(y+1)*self.width*4:4]) for y in (0,1,self.height//2,self.height-2,self.height-1)]
                self.observations.append({'bytes':len(pixels),'row_peaks':row_peaks})
            else:self.observations.append({'bytes':len(pixels)})
            measured=top_border_fraction(pixels,self.width,self.height)
        except Exception:
            self.close();return
        if measured is not None:
            self.samples.append(measured)
            recent=self.samples[-4:]
            if len(recent)==4 and max(recent)-min(recent)<=1.01/self.height:
                # Mixed zero/bordered observations are inconclusive.
                if all(v==0 for v in recent) or all(v>0 for v in recent):
                    self.result=min(recent);self.close();return
        else:self.samples=[]
        # Kodi can report playback while YouTube is still buffering. Allow
        # about twelve seconds for frames; each read still waits only 30ms.
        if self.attempts>=32:self.close()

def framing_key(url,compact,aspect):
    return hashlib.sha256(url.encode()).hexdigest()+(':compact:' if compact else ':details:')+format(aspect,'.4f')

class PreviewFramingCache:
    def __init__(self,path):
        self.path=path
        try:values=json.loads(path.read_text())
        except (OSError,ValueError):values={}
        if not isinstance(values,dict):values={}
        self.values={k:v for k,v in values.items() if isinstance(k,str) and type(v) in (int,float) and math.isfinite(v) and 0<=v<=.12}
    def get(self,key):return self.values.get(key)
    def put(self,key,value):
        self.values[key]=value
        self.values=dict(list(self.values.items())[-256:])
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temporary=self.path.with_suffix('.tmp');temporary.write_text(json.dumps(self.values));temporary.replace(self.path)
