"""Conservative end-of-available-series decisions; no playback or account writes."""
import sqlite3,math,time
from datetime import date
from live_core import episode_identity
from title_preferences import title_key
from movie_series import helper_database

def should_offer(reason,enabled,owner,qualified,ready):return reason=='ended' and bool(enabled and owner and qualified and ready)

def current_episode(target,current):
    ident=episode_identity(target)
    if not ident or current.get('type')!='episode':return None
    expected=str(target.get('showtitle') or target.get('tvshowtitle') or '').strip().casefold()
    if not expected or str(current.get('showtitle') or '').strip().casefold()!=expected:return None
    s,e=current.get('season'),current.get('episode')
    if type(s) is not int or type(e) is not int or s<=0 or e<=0:return None
    return ident['tmdb_id'],s,e

def observed_episode(target,current,player):
    """Use the playing item's native tag when JSON omits unindexed video fields."""
    key=current_episode(target,current)
    if key is not None:return key
    if current.get('type') not in (None,'','unknown','episode'):return None
    try:
        tag=player.getVideoInfoTag()
        if tag.getMediaType()!='episode':return None
        native={'type':'episode','showtitle':tag.getTVShowTitle(),'season':tag.getSeason(),'episode':tag.getEpisode()}
    except (AttributeError,RuntimeError,TypeError,ValueError):return None
    # Missing JSON fields can be filled; contradictory observations cannot.
    if current.get('showtitle') and str(current['showtitle']).strip().casefold()!=str(native['showtitle']).strip().casefold():return None
    for field in ('season','episode'):
        value=current.get(field)
        if type(value) is int and value>=0 and value!=native[field]:return None
    return current_episode(target,native)

def latest_available(profile,key,now=None,today=None):
    db=helper_database(profile);now=time.time() if now is None else now;today=today or date.today()
    if not db or not key:return False
    try:
        with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True,timeout=.05) as c:
            row=c.execute('SELECT s.season,e.episode,e.premiered,n.premiered,b.expiry FROM tvshow t JOIN baseitem b ON b.id=t.id JOIN episode e ON e.id=t.last_episode_to_air_id JOIN season s ON s.id=e.season_id LEFT JOIN episode n ON n.id=t.next_episode_to_air_id WHERE t.tmdb_id=?', (key[0],)).fetchone()
        if not row or not math.isfinite(float(row[4])) or row[4]<now:return False
        last=date.fromisoformat(row[2]);nxt=date.fromisoformat(row[3]) if row[3] else None
        return (row[0],row[1])==key[1:] and last<=today and (nxt is None or nxt>today)
    except (OSError,sqlite3.Error,TypeError,ValueError,OverflowError):return False

def suggestions(items,completed,preferences):
    result=[];seen={'tv:'+str(completed)}
    for item in preferences.apply(items):
        key=title_key(item)
        if not key or not key.startswith('tv:') or key in seen or item.get('playcount'):continue
        seen.add(key);result.append(item)
        if len(result)==3:break
    return result

def completed_latest(data,key,today=None):
    today=today or date.today()
    try:
        if str(data['id'])!=key[0]:return False
        last=data['last_episode_to_air'];nxt=data.get('next_episode_to_air')
        if (last['season_number'],last['episode_number'])!=key[1:]:return False
        if date.fromisoformat(last['air_date'])>today:return False
        if nxt is not None and date.fromisoformat(nxt['air_date'])<=today:return False
        return True
    except (KeyError,TypeError,ValueError):return False

def map_recommendations(package):
    from urllib.parse import urlencode
    result=[]
    for group in ('recommendations','similar'):
        values=package.get(group,{}).get('results',[]) if isinstance(package.get(group),dict) else []
        for raw in values[:20]:
            if not isinstance(raw,dict) or type(raw.get('id')) is not int or raw['id']<=0 or not isinstance(raw.get('name'),str):continue
            def image(value):return 'https://image.tmdb.org/t/p/w780'+value if isinstance(value,str) and value.startswith('/') and '..' not in value else ''
            premiered=raw.get('first_air_date') or '';year=int(premiered[:4]) if premiered[:4].isdigit() else 0
            result.append({'file':'plugin://plugin.video.themoviedb.helper/?'+urlencode({'info':'seasons','tmdb_type':'tv','tmdb_id':raw['id']}),'label':raw['name'],'title':raw['name'],'filetype':'directory','type':'tvshow','year':year,'premiered':premiered,'plot':raw.get('overview') or '', 'art':{'landscape':image(raw.get('backdrop_path')),'fanart':image(raw.get('backdrop_path')),'poster':image(raw.get('poster_path'))},'playcount':0})
    return result
