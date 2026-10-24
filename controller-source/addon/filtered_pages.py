"""Fill a discovery shelf after filtering, with a lossless provider-page cursor.

Raw provider results remain untouched. Work runs in the existing cancellable
list worker, with no per-title requests and no eager next-page prefetch.
"""
from urllib.parse import parse_qs,parse_qsl,urlsplit,urlencode
from browse_controls import is_next_page

class PageCancelled(RuntimeError):pass

def provider_path(path):
    if 'bl_start' not in parse_qs(urlsplit(path).query):return path
    u=urlsplit(path)
    return u._replace(query=urlencode([(k,v) for k,v in parse_qsl(u.query,keep_blank_values=True) if k!='bl_start'])).geturl()

def upstream_path(path):
    """JP animation is exactly the existing anime rule; mixed countries stay local."""
    u=urlsplit(path);q=parse_qs(u.query)
    if u.netloc!='plugin.video.themoviedb.helper' or q.get('info')!=['discover'] or q.get('with_origin_country')!=['JP']:return path
    original=q.get('without_genres',[''])[0]
    # Preserve compound exclusions rather than changing their boolean semantics.
    if original and not all(x.isdigit() for x in original.split(',')):return path
    genres=list(dict.fromkeys(([x for x in original.split(',') if x])+['16']))
    pairs=[(k,v) for k,v in parse_qsl(u.query,keep_blank_values=True) if k!='without_genres']
    return u._replace(query=urlencode(pairs+[('without_genres',','.join(genres))])).geturl()

def logical_files(files,actual,logical):
    if actual==logical:return files
    original=parse_qs(urlsplit(logical).query).get('without_genres');result=[]
    for item in files:
        if is_next_page(item,actual):
            u=urlsplit(item['file']);pairs=[(k,v) for k,v in parse_qsl(u.query,keep_blank_values=True) if k!='without_genres']
            if original:pairs.append(('without_genres',original[0]))
            item=dict(item,file=u._replace(query=urlencode(pairs)).geturl())
        result.append(item)
    return result

def _start(path):
    try:value=int(parse_qs(urlsplit(path).query).get('bl_start',['0'])[0])
    except (TypeError,ValueError):raise ValueError('Invalid page cursor')
    if not 0<=value<=10000:raise ValueError('Invalid page cursor')
    return value

def _cursor(path,index):
    return provider_path(path)+'&bl_start='+str(index)

def needs_fill(path,files,keep,size=20,positioned=False):
    if not positioned and _start(path):return True
    titles=[x for x in files if not is_next_page(x,path) and not x.get('_page_control')]
    return len(keep(titles))<size and any(is_next_page(x,path) for x in files)

def first_page_minimum(definition):
    path=definition.get('path','');u=urlsplit(path);q=parse_qs(u.query)
    quick=(definition.get('discovery_order') or {}).get('enabled') is True
    public=q.get('info',[''])[0] in ('discover','trending_day','trending_week','popular','top_rated','trakt_popular','trakt_trending','now_playing','upcoming','airing_today','on_the_air')
    first=q.get('page',['1'])==['1'] and q.get('bl_start',['0'])==['0']
    return 1 if quick and public and first and (u.scheme,u.netloc,u.path)==('plugin','plugin.video.themoviedb.helper','/') else 20

def path_minimum(window,path):
    for definition in getattr(window,'page_definitions',[]):
        if provider_path(definition.get('path',''))==provider_path(path):
            return first_page_minimum(dict(definition,path=path))
    return 20

def first_page_keep(window,path,keep,definition=None):
    """Count titles that survive both metadata and hard row eligibility.

    This does not rank titles or record selector exposure. Partial first pages
    may publish early only when at least one title can actually be displayed.
    """
    if definition is None:
        definition=next((d for d in getattr(window,'page_definitions',[]) if provider_path(d.get('path',''))==provider_path(path)),{})
    definition=dict(definition,path=path)
    if first_page_minimum(definition)!=1:return keep
    from discovery_order import hard_eligible
    policy=definition.get('discovery_order') or {}
    return lambda files:[item for item in keep(files) if hard_eligible(item,policy)]

def fill_page(path,files,fetch,keep,current=lambda:True,size=20,max_pages=40,minimum=20):
    raw_path=provider_path(path);start=_start(path);seen=set();result=[];identities=set()
    for _ in range(max_pages):
        if not current():raise PageCancelled('Page navigation changed')
        if raw_path in seen:raise ValueError('Provider repeated a page')
        seen.add(raw_path)
        if any(x.get('filetype')=='directory' and (x.get('file')==raw_path or is_next_page({'file':raw_path,'filetype':'directory'},x.get('file',''))) for x in files):
            raise ValueError('Provider page did not advance')
        next_item=next((x for x in files if is_next_page(x,raw_path)),None)
        titles=[x for x in files if not is_next_page(x,raw_path) and not x.get('_page_control')]
        allowed={x.get('file') for x in keep(titles)}
        for index,item in enumerate(titles[start:],start):
            identity=item.get('file')
            if identity not in allowed or identity in identities:continue
            identities.add(identity);result.append(item)
            if len(result)==size:
                target=_cursor(raw_path,index+1) if index+1<len(titles) else next_item.get('file') if next_item else None
                if target:result.append({'file':target,'filetype':'directory','label':'Next'})
                if not current():raise PageCancelled('Page navigation changed')
                return result
        if not next_item:
            if not current():raise PageCancelled('Page navigation changed')
            return result
        if not current():raise PageCancelled('Page navigation changed')
        if result and len(result)>=minimum:
            return result+[{'file':next_item['file'],'filetype':'directory','label':'Next'}]
        if len(seen)>=max_pages:raise RuntimeError('Provider page limit reached; retry the row')
        raw_path=provider_path(next_item['file']);start=0;files=fetch(raw_path)
    raise RuntimeError('Provider page limit reached; retry the row')
