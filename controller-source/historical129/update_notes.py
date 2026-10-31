"""Local installed-version history. No network, settings or account access."""
import copy,json,os,re,tempfile,time,uuid
from pathlib import Path
SCHEMA=1
MAX_HISTORY=20

def clean(value,limit=160):
    value=re.sub(r'\[[^\]]*\]','',str(value or ''))
    return ''.join(c for c in value if c.isprintable())[:limit]

def inventory(items):
    if not isinstance(items,list) or not items:raise ValueError('Installed inventory unavailable')
    result={}
    for item in items:
        key=item.get('addonid','');version=clean(item.get('version'),80)
        if not re.fullmatch(r'[a-zA-Z0-9_-]+(?:\.[a-zA-Z0-9_-]+)+',key) or not version:
            raise ValueError('Incomplete installed inventory')
        if key in result:raise ValueError('Duplicate installed identity')
        result[key]={'name':clean(item.get('name') or key),'version':version}
    return result

def validate(state):
    required={'schema','inventory','history','enabled','seen','sequence'}
    if not isinstance(state,dict) or set(state)!=required or state.get('schema')!=SCHEMA:raise ValueError('Unsupported update history')
    if not isinstance(state['inventory'],dict) or len(state['inventory'])>2000 or not isinstance(state['history'],list):raise ValueError('Invalid update history')
    if type(state['enabled']) is not bool or any(type(state[k]) is not int or state[k]<0 for k in ('seen','sequence')):raise ValueError('Invalid notice preference')
    if state['seen']>state['sequence'] or len(state['history'])>MAX_HISTORY:raise ValueError('Invalid notice sequence')
    for key,item in state['inventory'].items():
        if not isinstance(item,dict) or set(item)!={'name','version'}:raise ValueError('Invalid installed identity')
        if inventory([dict(item,addonid=key)])[key]!=item:raise ValueError('Invalid installed text')
    previous=0
    for batch in state['history']:
        if not isinstance(batch,dict) or set(batch)!={'id','time','changes'}:raise ValueError('Invalid update batch')
        if type(batch['id']) is not int or not previous<batch['id']<=state['sequence']:raise ValueError('Invalid batch order')
        if type(batch['time']) is not int or not 0<=batch['time']<=4102444800:raise ValueError('Invalid update time')
        if not isinstance(batch['changes'],list) or not 1<=len(batch['changes'])<=2000:raise ValueError('Invalid update entries')
        previous=batch['id'];identities=set()
        for change in batch['changes']:
            if not isinstance(change,dict) or not {'id','name','before','after','kind'}<=set(change)<= {'id','name','before','after','kind','notes'}:raise ValueError('Invalid update entry')
            if not all(isinstance(change[k],str) for k in ('id','name','before','after','kind')):raise ValueError('Invalid update text')
            inventory([{'addonid':change['id'],'name':change['name'],'version':change['after']}])
            if change['id'] in identities or change['kind'] not in ('changed','installed'):raise ValueError('Invalid update identity')
            identities.add(change['id'])
            if len(change['before'])>80 or len(change['after'])>80 or len(change['name'])>160:raise ValueError('Oversized update text')
            if (change['kind']=='installed')!= (change['before']==''):raise ValueError('Invalid update kind')
            notes=change.get('notes',[])
            if not isinstance(notes,list) or len(notes)>6 or any(not isinstance(n,str) or len(n)>240 for n in notes):raise ValueError('Invalid release notes')
    if previous!=state['sequence']:raise ValueError('Incomplete update sequence')
    return state


def complete_inventory(response):
    if not isinstance(response,dict) or 'error' in response:raise ValueError('Installed inventory unavailable')
    result=response.get('result',{});items=result.get('addons');limits=result.get('limits',{})
    if not isinstance(items,list) or limits!={'start':0,'end':len(items),'total':len(items)}:raise ValueError('Incomplete installed response')
    inventory(items)
    return items

def empty_state():
    return {"schema":SCHEMA,"inventory":{},"history":[],"enabled":True,"seen":0,"sequence":0}

def observe(state,items,now,catalog=None,complete=False):
    current=inventory(items)
    if not state or not state.get('inventory'):
        result=copy.deepcopy(state) if state else empty_state();result['inventory']=current;return result
    validate(state);updated=copy.deepcopy(state);old=state['inventory']
    if not complete and set(old)-set(current):raise ValueError('Unconfirmed inventory removal')
    changes=[]
    for key,item in sorted(current.items()):
        prior=old.get(key)
        if prior and prior['version']==item['version']:continue
        changes.append({'id':key,'name':item['name'],'before':prior['version'] if prior else '',
                        'after':item['version'],'kind':'changed' if prior else 'installed'})
    for change in changes:
        entry=(catalog or {}).get(change['id'],{}).get(change['after'],{})
        change['notes']=[clean(x,240) for x in entry.get('summary',[])[:6] if isinstance(x,str)]
    updated['inventory']=current
    if changes:
        sequence=state.get('sequence',0)+1;updated['sequence']=sequence
        updated['history']=(state['history']+[{'id':sequence,'time':int(now),'changes':changes}])[-MAX_HISTORY:]
    return updated

def pending(state):
    if not state or not state.get('enabled',True):return []
    return [b for b in state.get('history',[]) if b['id']>state.get('seen',0)]

def acknowledge(state):
    result=copy.deepcopy(state);result['seen']=result.get('sequence',0);return result

def notes_text(state):
    if not state.get('history'):return 'Update notices are ready.\n\nFuture installed add-on changes will appear here. Playback settings and authorizations are not changed by this feature.'
    lines=[]
    for batch in reversed(state['history']):
        from datetime import datetime
        lines.append(datetime.fromtimestamp(batch['time']).strftime('%d %b %Y · %H:%M'))
        for item in batch['changes']:
            line=clean(item['name'])+'\n'
            line+=clean(item['before'])+' → '+clean(item['after']) if item['before'] else 'Installed '+clean(item['after'])
            notes=[clean(x,240) for x in item.get('notes',[])[:6]]
            if notes:line+='\n'+'\n'.join(notes)
            lines.append(line)
        lines.append('')
    return '\n\n'.join(lines)

def read_state(path):
    path=Path(path)
    if not path.exists():return {}
    if path.stat().st_size>1024*1024:raise ValueError('Oversized update history')
    return validate(json.loads(path.read_text(encoding='utf-8')))

def write_state(path,state):
    validate(state);path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=str(path.parent))
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as out:
            json.dump(state,out,ensure_ascii=False,indent=2);out.flush();os.fsync(out.fileno())
        os.replace(name,str(path))
    finally:
        if os.path.exists(name):os.unlink(name)

def notice_allowed(home,loading,playing,dialog,settings,idle):
    return bool(home and not (loading or playing or dialog or settings) and idle>=8)


def transact(path,transform,reader=None,writer=None):
    """Serialize separate Kodi script interpreters; atomically replace JSON."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    lock=path.with_suffix('.lock');token=uuid.uuid4().hex;deadline=time.monotonic()+2
    while True:
        try:
            fd=os.open(str(lock),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as out:out.write(token)
            break
        except FileExistsError:
            try:
                if time.time()-lock.stat().st_mtime>300:lock.unlink();continue
            except FileNotFoundError:continue
            if time.monotonic()>=deadline:raise OSError('Update history busy')
            time.sleep(.02)
    try:
        old=(reader or read_state)(path);new=transform(copy.deepcopy(old))
        if new!=old:(writer or write_state)(path,new)
        return new
    finally:
        try:
            if lock.read_text()==token:lock.unlink()
        except FileNotFoundError:pass



def has_dialog(window_id):
    # Kodi Omega returns WINDOW_INVALID (9999) when no dialog is active.
    return window_id not in (0,9999,-1)
