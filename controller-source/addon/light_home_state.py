"""Bounded disposable display records and early input ownership; no Kodi imports."""
import hashlib,json,math,os,time
from pathlib import Path
MAX_BYTES=768*1024
MAX_AGE=24*3600

class EarlyIntent:
    def __init__(self):self.pending=None;self.retired=False
    def choose(self,kind,control_id,stable_item_key):
        if not self.retired:self.pending=(kind,control_id,stable_item_key)
    def take(self):
        value=self.pending;self.pending=None
        return None if self.retired else value
    def cancel(self):self.pending=None
    def retire(self):self.retired=True;self.pending=None

def extend_scope(provider_scope,row_layout_bytes,title_preferences_bytes):
    digest=hashlib.sha256(str(provider_scope).encode())
    for value in (row_layout_bytes,title_preferences_bytes):digest.update(b'\0');digest.update(value)
    return digest.hexdigest()

def policy_bytes(store):
    values=[]
    for name in ('row-layouts.json','title-preferences.json'):
        path=Path(store)/name
        try:
            if path.stat().st_size>256*1024:raise ValueError('Policy file too large')
            values.append(path.read_bytes())
        except FileNotFoundError:values.append(b'')
    return values

def read_record(path,scope,now=None):
    if not scope:return None
    try:
        path=Path(path)
        if path.stat().st_size>MAX_BYTES:return None
        value=json.loads(path.read_text(encoding='utf-8'));stamp=value.get('time')
        now=time.time() if now is None else now
        if type(stamp) not in (int,float) or not math.isfinite(stamp) or not 0<=now-stamp<=MAX_AGE:return None
        if value.get('version')!=1 or value.get('scope')!=scope:return None
        return value
    except (OSError,ValueError,TypeError,AttributeError):return None

def write_record(path,scope,fields):
    value=dict(fields,version=1,scope=scope,time=time.time())
    raw=json.dumps(value,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    if len(raw)>MAX_BYTES:return False
    path=Path(path);temporary=path.with_suffix('.pending')
    try:
        temporary.write_bytes(raw);os.replace(temporary,path);return True
    finally:
        try:temporary.unlink()
        except FileNotFoundError:pass
