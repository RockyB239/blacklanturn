"""Local arrangement overlay. Provider rows/content remain owned by their source."""
import copy,hashlib,json,os,tempfile,threading
from pathlib import Path
from urllib.parse import urlsplit,parse_qsl,urlencode
MAX_BYTES=256*1024
MAX_ROWS=256

def row_key(row):
    path=row.get('path','')
    if row.get('youtube_category'):
        identity='youtube-category\0'+str(row.get('label','')).strip().casefold()
    else:
        u=urlsplit(path);q=urlencode(sorted((k,v) for k,v in parse_qsl(u.query,keep_blank_values=True) if k not in ('cacheonly','reload','update_listing')))
        identity=u._replace(query=q).geturl()+'\0'+str(row.get('label',''))
    return hashlib.sha256(identity.encode()).hexdigest()

class RowLayouts:
    def __init__(self,path):
        self.path=Path(path);self.sections={};self.error='';self.lock=threading.RLock()
        try:
            if self.path.stat().st_size>MAX_BYTES:raise ValueError('Row arrangements exceed storage limit')
            value=json.loads(self.path.read_text())
            if not isinstance(value,dict) or value.get('version')!=1 or not isinstance(value.get('sections'),dict) or len(value['sections'])>128:raise ValueError('Invalid saved row arrangements')
            for scope,entry in value['sections'].items():
                if not isinstance(scope,str) or len(scope)>200 or not isinstance(entry,dict):raise ValueError('Invalid section')
                for name in ('order','hidden','pinned'):
                    keys=entry.get(name,[])
                    if not isinstance(keys,list) or len(keys)>MAX_ROWS or any(not isinstance(k,str) or len(k)!=64 or any(c not in '0123456789abcdef' for c in k) for k in keys):raise ValueError('Invalid row identity')
            self.sections=value['sections']
        except FileNotFoundError:pass
        except (OSError,ValueError,TypeError) as exc:self.error=str(exc)
    def entry(self,scope):return self.sections.get(scope,{})
    def rows(self,scope,definitions,include_hidden=False):
        with self.lock:
            state=self.entry(scope)
            if not state:return list(definitions)
            rank={k:i for i,k in enumerate(state.get('order',[]))};hidden=set(state.get('hidden',[]));pinned=set(state.get('pinned',[]))
            rows=[(row_key(r),i,r) for i,r in enumerate(definitions)]
            rows.sort(key=lambda x:(x[0] not in pinned,rank.get(x[0],MAX_ROWS+x[1])))
            visible=[r for key,_,r in rows if include_hidden or key not in hidden]
            # Upstream catalogs can temporarily lose the last visible category.
            # Keep a usable feed without erasing any hidden-row preference.
            return visible or ([rows[0][2]] if rows else [])
    def flags(self,scope,row):
        with self.lock:
            state=self.entry(scope);key=row_key(row)
            return key in state.get('hidden',[]),key in state.get('pinned',[])
    def change(self,scope,definitions,row,action):
        with self.lock:
            if action not in ('up','down','pin','unpin','hide','show'):raise ValueError('Unknown row action')
            key=row_key(row);available={row_key(r) for r in definitions}
            if key not in available:raise ValueError('This row is no longer available')
            updated=copy.deepcopy(self.sections);state=updated.setdefault(scope,{'order':[],'hidden':[],'pinned':[]})
            for name in ('order','hidden','pinned'):state.setdefault(name,[])
            # Establish upstream order once. Keep temporarily absent identities.
            state['order']+=list(dict.fromkeys(row_key(r) for r in definitions if row_key(r) not in state['order']))
            if action in ('up','down'):
                pinned=set(state['pinned']);group=[row_key(r) for r in self.rows(scope,definitions,include_hidden=True) if (row_key(r) in pinned)==(key in pinned)]
                at=group.index(key);target=at+(-1 if action=='up' else 1)
                if not 0<=target<len(group):return False
                a,b=state['order'].index(key),state['order'].index(group[target]);state['order'][a],state['order'][b]=state['order'][b],state['order'][a]
            else:
                field='hidden' if action in ('hide','show') else 'pinned';enable=action in ('hide','pin')
                if action=='hide' and key not in state['hidden'] and len(available-set(state['hidden']))<=1:raise ValueError('Keep at least one row visible in this section.')
                if enable and key not in state[field]:state[field].append(key)
                elif not enable:state[field]=[k for k in state[field] if k!=key]
            self._write(updated);return True
    def reset(self,scope):
        with self.lock:
            updated=copy.deepcopy(self.sections);updated.pop(scope,None);self._write(updated)
    def _write(self,updated):
        if self.error:raise ValueError('Saved arrangements could not be read. The original file has been left unchanged.')
        raw=json.dumps({'version':1,'sections':updated},sort_keys=True).encode()
        if len(raw)>MAX_BYTES or len(updated)>128 or any(len(e.get(k,[]))>MAX_ROWS for e in updated.values() for k in ('order','hidden','pinned')):raise ValueError('Row arrangement storage is full')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        fd,name=tempfile.mkstemp(prefix=self.path.name+'.',suffix='.pending',dir=str(self.path.parent))
        try:
            with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
            os.replace(name,self.path)
        finally:
            if os.path.exists(name):os.unlink(name)
        self.sections=updated
