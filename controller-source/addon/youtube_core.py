"""Account-scoped YouTube navigation; provider owns credentials and playback."""
import hashlib,re
from urllib.parse import urlsplit,parse_qs,urlencode

BASE='plugin://plugin.video.youtube'
TABS=(('home','Home'),('search','Search'),('subscriptions','Subscriptions'),('library','Library'),('channels','Channels'))

def connected_account(store,enabled=True):
    """A saved refreshable user is connected even while offline/access expires."""
    if not enabled or not isinstance(store,dict):return False,''
    manager=store.get('access_manager',{})
    if not isinstance(manager,dict):return False,''
    users=manager.get('users',{});current=manager.get('current_user')
    if not isinstance(users,dict):return False,''
    user=users.get(str(current),users.get(current))
    if not isinstance(user,dict):return False,''
    refresh=user.get('refresh_token','')
    if not isinstance(refresh,str) or not any(t.strip() for t in refresh.split('|')):return False,''
    identity=str(current)+'\0'+str(user.get('id',''))+'\0'+refresh
    return True,hashlib.sha256(identity.encode('utf-8')).hexdigest()

class ConnectionState:
    def __init__(self):self.connected=False;self.identity=''
    def refresh(self,read_store,enabled):
        before=(self.connected,self.identity)
        if not enabled:self.connected=False;self.identity=''
        else:
            try:self.connected,self.identity=connected_account(read_store(),enabled=True)
            except (OSError,ValueError,TypeError):return False
        return before!=(self.connected,self.identity)

def video_id(item):
    if not isinstance(item,dict) or item.get('filetype')=='directory' or item.get('_page_control'):return None
    route=urlsplit(item.get('file',''))
    if route.scheme!='plugin' or route.netloc!='plugin.video.youtube' or route.path.rstrip('/')!='/play':return None
    value=parse_qs(route.query).get('video_id',[''])[0]
    return value if re.fullmatch(r'[A-Za-z0-9_-]{11}',value) else None

def preview_path(item):
    value=video_id(item)
    if not value:return None
    # screensaver skips suggested-playlist enqueue as well as quality prompts;
    # incognito suppresses both local and remote watch/resume history writes.
    return BASE+'/play/?'+urlencode({'video_id':value,'incognito':'true','screensaver':'true','start':'0','end':'0'})

def is_youtube(item):
    source=urlsplit(item.get('file',''))
    return source.scheme=='plugin' and source.netloc=='plugin.video.youtube'

def tab_rows(tab,query='',account=None):
    account=account or {}
    def playlist(key,default):
        value=account.get(key,default)
        if value=='':return '/kodion/'+('watch_later' if key=='watch_later' else 'playback_history')+'/list/'
        if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,160}',value):value=default
        return ('/special/playlist/' if value.upper() in ('WL','HL','LL') else '/channel/mine/playlist/')+value+'/'
    definitions={
        'home':[('Recommended for you','/special/recommendations'),('Subscriptions','/special/my_subscriptions')],
        'subscriptions':[('Subscriptions','/special/my_subscriptions')],
        'library':[('Playlists','/channel/mine/playlists'),('Watch Later',playlist('watch_later','WL')),('History',playlist('watch_history','HL')),('Liked videos','/special/playlist/LL/')],
        'channels':[('Subscribed channels','/subscriptions/list/')],
        'search':[('Search results','/kodion/search/query/?'+urlencode({'q':query}))] if query else [('Search YouTube','/kodion/search/list/')],
    }
    return [{'label':label,'path':BASE+path} for label,path in definitions.get(tab,definitions['home'])]

def caption(item):
    parts=[]
    channels=item.get('studio') or item.get('artist') or []
    if isinstance(channels,str):channels=[channels]
    if channels:parts.append(str(channels[0]))
    try:
        seconds=int(item.get('runtime') or 0)
        if seconds>0:parts.append((str(seconds//3600)+':'+str(seconds%3600//60).zfill(2)+':'+str(seconds%60).zfill(2)) if seconds>=3600 else str(seconds//60)+':'+str(seconds%60).zfill(2))
    except (ValueError,TypeError,OverflowError):pass
    return ' · '.join(parts)

def automatic_preview(config,section,movie_mode):
    return bool(config.get('YouTubePreviews',True)) if section=='YouTube' else movie_mode=='auto'


def account_options(store):
    manager=store.get('access_manager',{}) if isinstance(store,dict) else {}
    users=manager.get('users',{}) if isinstance(manager,dict) else {}
    key=manager.get('current_user')
    user=users.get(str(key),users.get(key,{})) if isinstance(users,dict) else {}
    return {k:user[k] for k in ('watch_later','watch_history') if isinstance(user,dict) and k in user}

def resume_allowed(state,connected,identity):
    """Reject private rows captured under any other YouTube authorization."""
    if not isinstance(state,dict):return True
    if state.get('section')=='YouTube' and (not connected or not identity or state.get('youtube_identity')!=identity):return False
    return all(resume_allowed(s,connected,identity) for s in state.get('discovery_stack',[])) and resume_allowed(state.get('search_origin'),connected,identity)
