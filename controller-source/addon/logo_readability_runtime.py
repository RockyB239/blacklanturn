"""Bounded local decisions; never downloads artwork or changes its original file."""
import hashlib,json,re,threading
from collections import OrderedDict
from pathlib import Path
from logo_readability import png_readable,MAX_PNG_BYTES

class LogoDecisions:
    def __init__(self,path):
        self.path=Path(path);self.entries=OrderedDict();self.inspected=set();self.lock=threading.RLock()
        try:
            with self.path.open('rb') as f:raw=f.read(32769)
            if len(raw)>32768:return
            document=json.loads(raw);entries=document['entries']
            if document.get('version')!=1 or not isinstance(entries,dict) or len(entries)>256:return
            if any(not re.fullmatch('[0-9a-f]{64}',key) or type(value) is not bool for key,value in entries.items()):return
            self.entries.update(entries)
        except (OSError,ValueError,KeyError,TypeError):pass
    @staticmethod
    def key(url):return hashlib.sha256(url.encode()).hexdigest()
    def visible(self,url):
        with self.lock:return '' if url and self.entries.get(self.key(url)) is False else url
    def inspect(self,url,find_cached):
        if not url:return None
        key=self.key(url)
        with self.lock:
            if key in self.entries:return self.entries[key]
            if key in self.inspected:return None
        try:
            path=find_cached(url)
            if path is None:return None
            with Path(path).open('rb') as f:raw=f.read(MAX_PNG_BYTES+1)
            value=png_readable(raw)
        except (OSError,ValueError,TypeError):return None
        with self.lock:
            self.inspected.add(key)
            if len(self.inspected)>256:self.inspected={key}
            if value is None:return None
            self.entries[key]=value
            while len(self.entries)>256:self.entries.popitem(last=False)
            try:
                self.path.parent.mkdir(parents=True,exist_ok=True)
                temp=self.path.with_suffix('.pending');temp.write_text(json.dumps({'version':1,'entries':self.entries}));temp.replace(self.path)
            except OSError:pass
        return value

def check_cached_logo(owner,rpc,store,thumbnails):
    """Run only in the existing background monitor, after artwork is visible."""
    if not getattr(owner,'alive',False):return
    url=getattr(owner,'logo_source','')
    if not url:return
    decisions=getattr(owner,'logo_decisions',None)
    if decisions is None:
        decisions=owner.logo_decisions=LogoDecisions(Path(store)/'logo-readability.json')
    pending=getattr(owner,'logo_check',('',0))
    attempts=pending[1] if pending[0]==url else 0
    if attempts>=5:return
    owner.logo_check=(url,attempts+1)
    def local_path(value):
        from urllib.parse import urlsplit,unquote
        parsed=urlsplit(value);original=unquote(parsed.netloc) if parsed.scheme=='image' else value
        result=rpc('Textures.GetTextures',{'properties':['cachedurl'],'filter':{'or':[{'field':'url','operator':'is','value':candidate} for candidate in set((value,original))]}})
        base=Path(thumbnails).resolve()
        for texture in result.get('result',{}).get('textures',[]):
            try:
                path=(base/texture['cachedurl']).resolve();path.relative_to(base)
                if path.is_file():return path
            except (KeyError,ValueError,OSError):continue
        return None
    try:value=decisions.inspect(url,local_path)
    except (OSError,ValueError,TypeError,RuntimeError):return
    if value is False:
        with owner.preview_dispatch_lock:
            if owner.alive and getattr(owner,'logo_source','')==url and owner.getProperty('titleLogo')==url:
                owner.setProperty('titleLogo','');owner.light_home_saved=False

# One short-lived decoder at a time; focus monitoring never waits for PNG work.
_decode_slot=threading.BoundedSemaphore(1)
def queue_cached_logo(owner,rpc,store,thumbnails):
    url=getattr(owner,'logo_source','')
    if not url or not getattr(owner,'alive',False):return
    decisions=getattr(owner,'logo_decisions',None)
    if decisions is not None:
        key=decisions.key(url)
        with decisions.lock:
            if key in decisions.entries or key in decisions.inspected:return
    pending=getattr(owner,'logo_check',('',0))
    if pending[0]==url and pending[1]>=5:return
    if not _decode_slot.acquire(False):return
    def work():
        try:check_cached_logo(owner,rpc,store,thumbnails)
        finally:_decode_slot.release()
    try:threading.Thread(target=work,name='BlackLanturnCachedLogo',daemon=True).start()
    except RuntimeError:_decode_slot.release()
