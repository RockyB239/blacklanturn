"""Exact title actions and in-memory return contracts; no account credentials."""
from urllib.parse import urlsplit,parse_qs,urlencode,urlunsplit
from live_core import title_details_params,episode_identity
import math

def resume_options(item):
    try:
        point=item.get('resume') or {};position=float(point.get('position',0));total=float(point.get('total',0))
        if math.isfinite(position) and math.isfinite(total) and 0<position<total:
            return {'resume':True}
    except (TypeError,ValueError):pass
    return {}

def watch_sync_command():
    # Current Helper routes watched progress under 'watched'; unknown routes open a chooser.
    # Helper Script parameters are strings: 'false' is truthy; an empty value becomes None.
    return 'RunScript(plugin.video.themoviedb.helper,invalidate_sync=watched,notification=,sync=)'

class ResumeHandoff:
    """One initial resume fallback when an integration loses Kodi's resume flag."""
    def __init__(self,item):
        self.item=item or {};self.started=None;self.done=not bool(resume_options(self.item))
    def tick(self,current,percentage,now):
        if self.done:return None
        if self.started is None:self.started=now;return None
        if now-self.started<3:return None
        self.done=True
        if current.get('type')=='episode':
            matches=all(current.get(k)==self.item.get(k) for k in ('season','episode')) and str(current.get('showtitle','')).casefold()==str(self.item.get('showtitle') or self.item.get('title','')).casefold()
        else:
            matches=current.get('type')=='movie' and str(current.get('title','')).casefold()==str(self.item.get('title','')).casefold()
            if current.get('year') and self.item.get('year'):matches=matches and current['year']==self.item['year']
        if not matches:return None
        point=self.item['resume'];requested=float(point['position'])/float(point['total'])*100
        return requested if abs(percentage-requested)>2 else None

def action_identity(item):
    params=title_details_params(item)
    if params.get('tmdb_type') not in ('movie','tv') or not str(params.get('tmdb_id','')).isdigit():return None
    query=parse_qs(urlsplit(item.get('file','')).query)
    if params['tmdb_type']=='tv' and 'episode' in query and not episode_identity(item):return None
    if params['tmdb_type']=='tv' and 'season' in query and 'episode' not in query:
        season=query['season'][0]
        if not season.isdigit():return None
        params['season']=int(season)
    return params

def trakt_command(item):
    identity=action_identity(item)
    if not identity:return None
    return 'RunScript(plugin.video.themoviedb.helper,sync_trakt,'+','.join(str(k)+'='+str(v) for k,v in identity.items())+')'

def choose_player_path(item):
    source=urlsplit(item.get('file',''));query=parse_qs(source.query)
    if source.netloc!='plugin.video.themoviedb.helper' or query.get('info')!=['play'] or item.get('filetype')=='directory':return None
    # Preserve provider identity and all arguments, replacing only this supported switch.
    pairs=[(k,v) for k,values in query.items() for v in values if k!='ignore_default']
    return urlunsplit((source.scheme,source.netloc,source.path,urlencode(pairs+[('ignore_default','true')]),source.fragment))

def item_key(item):
    identity=action_identity(item)
    return tuple(identity.items()) if identity else item.get('file','')

def restored_position(files,item,position=0):
    key=item_key(item or {})
    return next((n for n,value in enumerate(files) if item_key(value)==key),max(0,min(position,len(files)-1)))

def refreshed_watch_item(item,fresh):
    return {**item,**{k:fresh[k] for k in ('playcount','resume') if k in fresh}}

class PlaybackReturnGate:
    """Wait for video and provider dialogs, including the next-episode handoff."""
    def __init__(self,started):self.started=started;self.played=False;self.quiet_since=None
    def tick(self,playing,busy,home,now,owner=True):
        if not owner:return 'abandon'
        if playing:self.played=True
        if playing or busy or not home:self.quiet_since=None;return 'wait'
        if self.quiet_since is None:self.quiet_since=now
        if now-self.quiet_since<2 or (not self.played and now-self.started<15):return 'wait'
        return 'return'

class YouTubeExitGuard:
    """A Home return can stop only the fullscreen source owned by this handoff."""
    def __init__(self,enabled):
        self.enabled=bool(enabled);self.source=None;self.armed=False;self.finished=False
    def observe(self,playing,fullscreen,source,owner):
        if not self.enabled or not owner:
            self.armed=False;return
        if not playing:
            if self.source:self.finished=True
            self.armed=False;return
        if self.source and source!=self.source:
            self.finished=True;self.armed=False;return
        if not self.finished and fullscreen and source:
            if self.source is None:self.source=source
            self.armed=True
    def consume_back(self,requested,playing,source,owner):
        if not requested:return False
        stop=bool(self.enabled and self.armed and playing and owner and source and source==self.source)
        self.armed=False;self.finished=True
        return stop
