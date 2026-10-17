"""Source and paging contracts for the temporary live-integration probe."""
from urllib.parse import urlsplit,parse_qs
import math,re
from copy import deepcopy

def my_stuff_rows(saved,make_path):
    return [
        {'label':'Saved on this device','path':'','local_items':saved},
        {'label':'Trakt Watchlist · Movies','path':make_path('trakt_watchlist','movie')},
        {'label':'Trakt Watchlist · Shows','path':make_path('trakt_watchlist','tv')},
    ]

def row_items(definition,provider):
    if 'local_items' in definition:return deepcopy(definition['local_items'])
    return provider(definition['path'])

def show_identity(item):
    query=parse_qs(urlsplit(item.get('file','')).query)
    if query.get('tmdb_type',query.get('type',['']))[0]!='tv':return None
    identity=query.get('tmdb_id',[item.get('uniqueid',{}).get('tvshow.tmdb','')])[0]
    return str(identity) if str(identity).isdigit() else None

def episode_identity(item):
    identity=show_identity(item)
    if not identity:return None
    query=parse_qs(urlsplit(item.get('file','')).query)
    if item.get('filetype')=='directory' and 'episode' not in query:return None
    try:
        season=int(query.get('season',[item.get('season',-1)])[0])
        episode=int(query.get('episode',[item.get('episode',-1)])[0])
    except (TypeError,ValueError):return None
    return {'tmdb_id':identity,'season':season,'episode':episode} if season>=0 and episode>=0 else None

def title_details_params(item):
    episode=episode_identity(item)
    if episode:return dict(tmdb_type='tv',**episode)
    query=parse_qs(urlsplit(item.get('file','')).query)
    return {'tmdb_type':query.get('tmdb_type',query.get('type',['movie']))[0],
            'tmdb_id':query.get('tmdb_id',[item.get('uniqueid',{}).get('tmdb','')])[0]}

def merge_title_details(item,details):
    merged={**item,**details,'file':item.get('file',''),'filetype':item.get('filetype','file')}
    keep=['resume','playcount']
    if episode_identity(item):keep+=['title','label','showtitle','season','episode','plot','runtime']
    for key in keep:
        if key in item:merged[key]=item[key]
    return merged

def episode_heading(item):
    episode=episode_identity(item);title=item.get('title') or item.get('label','')
    if not episode:
        query=parse_qs(urlsplit(item.get('file','')).query)
        if item.get('filetype')=='directory' and query.get('info',[''])[0]=='episodes':
            season=query.get('season',[''])[0]
            return item.get('showtitle') or title, f'Season {season} · {title}'
        return title,''
    return item.get('showtitle') or item.get('tvshowtitle') or title, f"S{episode['season']:02d} · E{episode['episode']:02d} — {title}"

def is_browse_folder(item):
    if item.get('filetype')!='directory':return False
    query=parse_qs(urlsplit(item.get('file','')).query)
    return query.get('info',[''])[0] in ('seasons','episodes','flatseasons') or not (item.get('year') or item.get('plot'))

def card_artwork(item):
    """Choose provider art without pretending a poster is a landscape."""
    art=item.get('art') or {}
    if item.get('_page_control') and art.get('navigation'):return {'image':art['navigation'],'kind':'paging'}
    if item.get('type')=='addon':return {'image':art.get('square') or art.get('icon',''),'kind':'square'}
    query=parse_qs(urlsplit(item.get('file','')).query)
    if query.get('info')==['discover'] and query.get('with_companies',[''])[0].isdigit():
        logo=art.get('thumb') or art.get('icon') or item.get('thumbnail','')
        if logo:return {'image':logo,'kind':'square'}
    # Season directories expose episode counts; they are not episode thumbnails.
    season_folder=(item.get('filetype')=='directory' and
                   query.get('info',[''])[0]=='episodes' and
                   query.get('tmdb_type',query.get('type',['']))[0]=='tv' and
                   query.get('season',[''])[0].isdigit())
    if season_folder:
        for key in ('season.poster','poster'):
            value=art.get(key)
            if value and value!=art.get('tvshow.poster'):
                return {'image':value,'kind':'portrait'}
    posters={art.get(k) for k in ('poster','season.poster','tvshow.poster') if art.get(k)}
    episode=episode_identity(item) or item.get('episode',-1)>=0
    if episode:
        for value in (art.get('thumb'),item.get('thumbnail')):
            if value and value not in posters:return {'image':value,'kind':'landscape'}
    for key in ('landscape','season.landscape','tvshow.landscape','fanart','tvshow.fanart'):
        if art.get(key):return {'image':art[key],'kind':'landscape'}
    for key in ('poster','season.poster','tvshow.poster'):
        if art.get(key):return {'image':art[key],'kind':'portrait'}
    thumb=art.get('thumb') or item.get('thumbnail','')
    return {'image':thumb,'kind':'landscape'} if thumb else {'image':'','kind':'text'}

def title_presentation(item,logos=True):
    genres=item.get('genre') or []
    genres=' / '.join(str(g) for g in genres if g) if isinstance(genres,list) else str(genres)
    meta='  ·  '.join(str(x) for x in (item.get('year'),genres) if x)
    runtime=item.get('runtime') or 0
    try:duration=str(round(float(runtime)/60))+' min' if math.isfinite(float(runtime)) and float(runtime)>0 else ''
    except (TypeError,ValueError):duration=''
    technical='  ·  '.join(x for x in (duration,item.get('mpaa') or '') if x)
    state=watch_state(item);art=item.get('art') or {}
    return {'meta':meta,'technical':technical,'watch':state['label'],'watch_state':state['state'],
            'logo':(art.get('clearlogo') or art.get('tvshow.clearlogo') or '') if logos else ''}

def watch_state(item):
    resume=item.get('resume') or {}
    try:position,total=float(resume.get('position',0)),float(resume.get('total',0))
    except (ValueError,TypeError):position,total=0,0
    if math.isfinite(position) and math.isfinite(total) and 0<position<total:
        percent=max(1,min(99,round(100*position/total)))
        return {'state':'progress','label':f'In progress · {percent}%','percent':percent}
    count=item.get('playcount')
    if item.get('filetype')=='directory' and not item.get('year') and not item.get('plot') and item.get('episode',-1)<0:return {'state':'unknown','label':'','percent':0}
    if isinstance(count,(int,float)) and math.isfinite(count) and count>0:return {'state':'watched','label':'Watched','percent':100}
    query=parse_qs(urlsplit(item.get('file','')).query)
    is_show=item.get('filetype')=='directory' and query.get('tmdb_type',[''])[0]=='tv' and 'episode' not in query
    if count==0 and not is_show:return {'state':'unwatched','label':'Unwatched','percent':0}
    return {'state':'unknown','label':'','percent':0}

def clear_stale_preview(rpc):
    """Release only a positively identified, overrun YouTube trailer."""
    def seconds(value):return sum(float(value.get(k,0))*scale for k,scale in [('hours',3600),('minutes',60),('seconds',1),('milliseconds',.001)])
    for player in rpc('Player.GetActivePlayers').get('result',[]):
        if player.get('type')!='video':continue
        pid=player['playerid'];item=rpc('Player.GetItem',{'playerid':pid,'properties':['title','file']}).get('result',{}).get('item',{})
        source=urlsplit(item.get('file',''))
        if source.scheme!='plugin' or source.netloc!='plugin.video.youtube' or 'trailer' not in (item.get('title') or item.get('label','')).lower():continue
        props=rpc('Player.GetProperties',{'playerid':pid,'properties':['time','totaltime']}).get('result',{})
        try:elapsed,total=seconds(props.get('time',{})),seconds(props.get('totaltime',{}))
        except (TypeError,ValueError):continue
        if math.isfinite(elapsed) and 0<total<=1800 and elapsed>total+10:
            return rpc('Player.Stop',{'playerid':pid}).get('result')=='OK'
    return False

def person_identity(path):
    source=urlsplit(path)
    query=parse_qs(source.query)
    kind=query.get('tmdb_type',query.get('type',['']))[0]
    identity=query.get('tmdb_id',[''])[0]
    if source.netloc=='plugin.video.themoviedb.helper' and kind=='person' and identity.isdigit():return identity
    return None

def mdblist_line(data):
    scores={entry.get('source'):entry.get('value') for entry in data.get('ratings',[])}
    labels=[('tomatoes','RT critics','%'),('metacritic','Metacritic','/100'),('imdb','IMDb','/10'),('tomatoesaudience','RT audience','%'),('popcorn','RT audience','%')]
    result=[];shown=set()
    for source,label,scale in labels:
        value=scores.get(source)
        if value is None or label in shown:continue
        try:value=float(value)
        except (TypeError,ValueError):continue
        maximum=10 if scale=='/10' else 100
        if not 0<=value<=maximum:continue
        shown.add(label);number=f'{value:.1f}' if scale=='/10' else f'{value:g}'
        result.append(f'{label} {number}{scale}')
    return '   ·   '.join(result)

def rating_badges(item,data=None):
    icons=[('tomatoes','rottentomatoes','%','critic'),('metacritic','metacritic','/100','critic'),('imdb','imdb','/10','audience'),('tomatoesaudience','popcorn','%','audience'),('popcorn','popcorn','%','audience')]
    scores={entry.get('source'):entry.get('value') for entry in (data or {}).get('ratings',[])}
    badges=[];shown=set()
    for source,icon,scale,kind in icons:
        value=scores.get(source)
        if value is None or icon in shown:continue
        try:value=float(value)
        except (ValueError,TypeError):continue
        maximum=10 if scale=='/10' else 100
        if not 0<=value<=maximum:continue
        shown.add(icon);number=f'{value:.1f}' if scale=='/10' else f'{value:g}'
        badges.append({'icon':icon,'value':number+scale,'kind':kind})
    if not badges and item.get('rating',0)>0:
        badges.append({'icon':'themoviedatabase' if item.get('_rating_source','TMDb')=='TMDb' else 'star','value':f"{item['rating']:.1f}/10",'kind':'audience'})
    return badges

def valid_source(path):
    p=urlsplit(path)
    return p.scheme=='plugin' and bool(p.netloc) and p.netloc.startswith(('plugin.','script.'))

def select_rating_badges(item,badges,sources):
    """Respect configured sources without substituting a disabled rating."""
    available={b['icon']:b for b in badges}
    score=item.get('rating',0)
    if item.get('_rating_source')=='TMDb' and isinstance(score,(float,int)) and 0<score<=10:
        available['themoviedatabase']={'icon':'themoviedatabase','value':f'{score:.1f}/10','kind':'audience'}
    return [available[source] for source in dict.fromkeys(sources) if source in available]

def update_rating_sources(current,selected):
    """Keep existing display order and append newly enabled sources."""
    return list(dict.fromkeys([s for s in current if s in selected]+list(selected)))

def directory_items(response):
    if 'error' in response:raise ValueError(response['error'].get('message','List unavailable'))
    return response.get('result',{}).get('files',[])

def rating_line(item):
    names={'tmdb':'TMDb','themoviedb':'TMDb','imdb':'IMDb','trakt':'Trakt','metacritic':'Metacritic','rottentomatoes':'Rotten Tomatoes'}
    scores=[]
    for source,value in item.get('ratings',{}).items():
        score=value.get('rating') if isinstance(value,dict) else value
        if isinstance(score,(float,int)) and score>0:
            scale=100 if source.lower() in ('metacritic','rottentomatoes') else 10
            scores.append(f'{names.get(source.lower(),source)} {score:g}/{scale}')
    if not scores and item.get('rating',0)>0:scores.append(f"{item.get('_rating_source','TMDb')} {item['rating']:.1f}/10")
    return '   ·   '.join(scores)

class PageHistory:
    def __init__(self):self.pages=[]
    def push(self,path,position):self.pages.append((path,position))
    def pop(self):return self.pages.pop() if self.pages else None


def caption_fit_step(width,height):
    """Quantize fitted-art height correction; keep 16:9 TV geometry unchanged."""
    try:
        ratio=float(width)/float(height)/(1920/1080)
        if ratio<=0:return 0
        return max(0,min(8,round((1-min(1,ratio))*264/12)))
    except (TypeError,ValueError,ZeroDivisionError):return 0

def preview_candidates(primary, videos, metadata=None, preferred_language='en'):
    """Prefer labelled English/dubbed trailers; retain all distinct fallbacks.

    Language metadata may describe subtitles rather than spoken audio. Explicit
    subtitled labels are ranked below known English/dubbed candidates.
    """
    records={};metadata=metadata or {}
    for video in [{'file':primary}]+list(videos):
        url=video.get('file','');p=urlsplit(url);key=parse_qs(p.query).get('video_id',[''])[0]
        if p.scheme!='plugin' or p.netloc!='plugin.video.youtube' or not key:continue
        if key not in records:records[key]={'url':url,'index':len(records),**metadata.get(key,{})}
        record=records[key]
        for target,keys in [('name',('label','title','name')),('language',('language','iso_language','iso_639_1')),('type',('video_type','content'))]:
            value=next((video.get(k) for k in keys if video.get(k)),None)
            if value:record[target]=value
    def rank(record):
        if not preferred_language:return (0,0,record['index'])
        language=str(record.get('language','')).lower().replace('_','-').split('-')[0]
        if language in ('eng','english'):language='en'
        name=str(record.get('name','')).lower()
        explicit_english=bool(re.search(r'\benglish\b',name))
        dubbed=bool(re.search(r'\bdub(?:bed)?\b',name))
        subtitles=bool(re.search(r'\bsub(?:titled|titles|bed)?\b',name))
        preferred=language==preferred_language or preferred_language=='en' and explicit_english
        score=0 if preferred and dubbed else 1 if preferred and not subtitles else 3 if preferred else 4 if language else 2
        extra=str(record.get('type','')).lower() not in ('','trailer','teaser') or bool(re.search(r'\b(?:opening credits|date announcement)\b',name))
        return (int(extra),score,record['index'])
    return [record['url'] for record in sorted(records.values(),key=rank)]

class PreviewAttempts:
    def __init__(self,candidates,timeout=12):
        self.candidates=candidates;self.timeout=timeout;self.index=-1
        self.requested=0;self.started=False;self.finished=False
    def start(self,now):
        self.index+=1;self.requested=now;self.started=False
        if self.index>=len(self.candidates):self.finished=True;return None
        return self.candidates[self.index]
    def tick(self,now,playing,error=False):
        if self.finished or self.index<0:return None
        if error:return self.start(now)
        if playing:self.started=True;return None
        if self.started:self.finished=True;return None
        if now-self.requested>=self.timeout:return self.start(now)
        return None
    def cancel(self):self.finished=True
