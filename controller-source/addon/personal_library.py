"""Local collections and named searches; copy-on-write, no provider/account calls."""
from copy import deepcopy
from uuid import uuid4
import json
from title_preferences import title_key
KINDS=('all','movie','tv','person','company','collection')
MAX_COLLECTIONS=60
MAX_ITEMS=200
MAX_SEARCHES=60

def _name(value):
    if not isinstance(value,str):raise ValueError('Enter a name')
    value=value.strip()
    if not value or len(value)>80 or any(ord(c)<32 for c in value):raise ValueError('Use a name of 1–80 characters without line breaks')
    return value

def _records(config,key):
    records=config.get(key,[])
    if not isinstance(records,list) or any(not isinstance(x,dict) or not isinstance(x.get('id'),str) or not isinstance(x.get('name'),str) for x in records):raise ValueError('Saved library data could not be read; it has been left unchanged')
    if len({x['id'] for x in records})!=len(records):raise ValueError('Saved library identities are invalid; original data was kept')
    if key=='PersonalCollections' and any(not isinstance(x.get('items'),list) for x in records):raise ValueError('Saved collection could not be read')
    if key=='SavedSearches' and any(not isinstance(x.get('query'),str) or x.get('kind') not in KINDS for x in records):raise ValueError('Saved search could not be read')
    return deepcopy(records)

def _updated(config,key,records):
    if len(json.dumps(records,ensure_ascii=False).encode())>2*1024*1024:raise ValueError('Saved library is full; remove some entries first')
    result=dict(config,**{key:records})
    if len(json.dumps(result,ensure_ascii=False,indent=2).encode())>3*1024*1024:raise ValueError('Saved preferences are full; remove some library entries first')
    return result

def snapshot(item):
    if not title_key(item):raise ValueError('Choose a movie or show')
    keys=('file','filetype','label','title','type','year','premiered','art','thumbnail','uniqueid','plot','showtitle','runtime','mpaa','genre','playcount','resume','set')
    value={k:deepcopy(item[k]) for k in keys if k in item}
    # No transient preview, source resolver, account or generated work fields.
    if len(json.dumps(value).encode())>32768:raise ValueError('This title contains too much saved metadata')
    return value

def create_collection(config,name):
    name=_name(name);records=_records(config,'PersonalCollections')
    if any(x['name'].casefold()==name.casefold() for x in records):raise ValueError('A collection with that name already exists')
    if len(records)>=MAX_COLLECTIONS:raise ValueError('Collection limit reached')
    records.append({'id':uuid4().hex,'name':name,'items':[]})
    return _updated(config,'PersonalCollections',records)

def membership(config,ident,item,add):
    records=_records(config,'PersonalCollections');record=next((x for x in records if x['id']==ident),None)
    if record is None:raise ValueError('Collection is no longer available')
    saved=snapshot(item);key=title_key(saved)
    items=[x for x in record['items'] if title_key(x)!=key]
    if add:items.append(saved)
    if len(items)>MAX_ITEMS:raise ValueError('This collection is full')
    record['items']=items;return _updated(config,'PersonalCollections',records)

def _edit(config,key,ident,action,name=None):
    records=_records(config,key);index=next((i for i,x in enumerate(records) if x['id']==ident),None)
    if index is None:raise ValueError('Saved entry is no longer available')
    if action=='delete':records.pop(index)
    elif action=='rename':
        name=_name(name)
        if any(i!=index and x['name'].casefold()==name.casefold() for i,x in enumerate(records)):raise ValueError('That name is already in use')
        records[index]['name']=name
    elif action in ('up','down'):
        dest=max(0,min(len(records)-1,index+(-1 if action=='up' else 1)));records[index],records[dest]=records[dest],records[index]
    else:raise ValueError('Unknown library action')
    return _updated(config,key,records)

def edit_collection(config,ident,action,name=None):return _edit(config,'PersonalCollections',ident,action,name)
def edit_search(config,ident,action,name=None):return _edit(config,'SavedSearches',ident,action,name)

def save_search(config,name,query,kind):
    name=_name(name)
    if not isinstance(query,str) or not query.strip() or len(query)>300 or any(ord(c)<32 for c in query) or kind not in KINDS:raise ValueError('Choose a supported search and category')
    records=_records(config,'SavedSearches');query=query.strip()
    if any(x['query']==query and x['kind']==kind for x in records):return dict(config)
    if any(x['name'].casefold()==name.casefold() for x in records):raise ValueError('A saved search with that name already exists')
    if len(records)>=MAX_SEARCHES:raise ValueError('Saved search limit reached')
    records.append({'id':uuid4().hex,'name':name,'query':query,'kind':kind});return _updated(config,'SavedSearches',records)

def collection_rows(config):
    return [{'id':'personal-'+c['id'],'label':c['name'],'path':'','local_items':c['items']} for c in _records(config,'PersonalCollections')]

def collections(config):return _records(config,'PersonalCollections')
def searches(config):return _records(config,'SavedSearches')

def refresh_watch(config,fresh):
    key=title_key(fresh)
    if not key:return config
    changes={k:deepcopy(fresh[k]) for k in ('playcount','resume') if k in fresh}
    if not changes:return config
    result=deepcopy(config)
    for item in result.get('Saved',[]):
        if title_key(item)==key:item.update(changes)
    _records(result,'PersonalCollections')
    for collection in result.get('PersonalCollections',[]):
        for item in collection['items']:
            if title_key(item)==key:item.update(changes)
    return result
