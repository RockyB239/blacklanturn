"""Provider-backed season selectors and compact episode captions."""
from datetime import date
from urllib.parse import urlsplit,parse_qs

def season_entries(files):
    entries=[]
    for item in files:
        route=urlsplit(item.get('file',''));query=parse_qs(route.query)
        value=query.get('season',[''])[0]
        if route.netloc!='plugin.video.themoviedb.helper' or query.get('info')!=['episodes'] or query.get('tmdb_type')!=['tv'] or not value.isdigit():continue
        season=int(value);label='Specials' if season==0 else 'Season '+str(season)
        count=item.get('episode')
        if isinstance(count,int) and count>0:label+=' · '+str(count)+(' episode' if count==1 else ' episodes')
        entries.append({'season':season,'label':label,'path':item['file']})
    return entries

def episode_card(item):
    title=item.get('title') or item.get('label') or 'Untitled episode'
    season=item.get('season');episode=item.get('episode')
    caption=f'S{season:02d} · E{episode:02d} — {title}' if item.get('filetype')!='directory' and isinstance(season,int) and season>=0 and isinstance(episode,int) and episode>0 else title
    parts=[]
    try:
        runtime=float(item.get('runtime') or 0)
        if runtime>=60:parts.append(str(int(runtime/60))+' min')
    except (ValueError,TypeError,OverflowError):pass
    try:
        aired=date.fromisoformat(item.get('premiered') or item.get('firstaired') or '')
        parts.append(aired.strftime('%b')+f' {aired.day}, {aired.year}')
    except (ValueError,TypeError):pass
    return {'caption':caption,'meta':' · '.join(parts)}

def episode_item(item,show):
    result=dict(item)
    if not result.get('showtitle') and result.get('filetype')!='directory':result['showtitle']=show
    return result
