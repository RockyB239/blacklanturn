"""A display-only Home record. Normal controller owns its production and refresh."""
import copy,threading,json,hashlib
from pathlib import Path
from light_home_state import extend_scope,policy_bytes,read_record,write_record
from home_rows import home_path,home_item_path
from public_rows import _items,_art
HERO_KEYS=frozenset(('hasSelection','sourceSession','hero','title','episodeLine','episodeMeta','allEpisodes','meta','technicalMeta','watchMeta','watchState','titleLogo','browsable','plot'))|frozenset('rating'+kind+str(n) for kind in ('Value','Icon') for n in range(5))
BASE_KEYS=frozenset(('captionRows','episodeBrowser','searchBrowser','heroCompact','addonBrowser','genreChooser','loading','loadingStatus','input','previewMode','genreLabel','page','notice','youtubeBrowser','filmographyBrowser','scroll','eyebrow','browseFilters','previewsReady','showClock','showDate','showWeather','sidebarCompact','startupIdle','captionFitStep'))
def display_scope(store,provider_scope):
    if not provider_scope:return None
    import xbmc,xbmcaddon
    store=Path(store)
    digest=hashlib.sha256((provider_scope+'\0'+str(store.resolve())).encode())
    account_path=store.parent/'plugin.video.youtube/access_manager.json'
    try:
        if account_path.stat().st_size>1024*1024:return None
        account=json.loads(account_path.read_text(encoding='utf-8'))
    except FileNotFoundError:account={}
    except (OSError,ValueError):return None
    # A temporary partial write is not a logged-out account. Routine access
    # token renewal, however, leaves the current refreshable identity intact.
    if not isinstance(account,dict):return None
    manager=account.get('access_manager',{})
    if not isinstance(manager,dict) or not isinstance(manager.get('users',{}),dict):return None
    current=manager.get('current_user');users=manager.get('users',{})
    if current is not None and type(current) not in (str,int):return None
    user=users.get(str(current),users.get(current))
    if user is not None and (not isinstance(user,dict) or not isinstance(user.get('refresh_token',''),str)):return None
    from youtube_core import connected_account
    digest.update(b'youtube-account-v1\0')
    digest.update(json.dumps(connected_account(account),separators=(',',':')).encode())
    path=store.parent/'plugin.video.youtube/api_keys.json'
    try:
        if path.stat().st_size>1024*1024:return None
        digest.update(path.read_bytes())
    except FileNotFoundError:digest.update(b'absent')
    addon=xbmcaddon.Addon('plugin.video.youtube')
    for key in ('youtube.api.key','youtube.api.id','youtube.api.secret'):digest.update(addon.getSetting(key).encode())
    result=json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'Addons.GetAddons','params':{'properties':['enabled','path']}})))
    if 'error' in result:return None
    relevant=sorted((a.get('addonid',''),a.get('enabled'),a.get('path','')) for a in result.get('result',{}).get('addons',[]) if a.get('addonid')=='plugin.video.youtube' or a.get('addonid','').startswith('resource.images.'))
    digest.update(json.dumps(relevant,sort_keys=True).encode())
    return extend_scope(digest.hexdigest(),*policy_bytes(store))

class CaptureControl:
    def __init__(self):self.label='';self.height=None
    def setLabel(self,value):self.label=value
    def setHeight(self,value):self.height=value
    def controlRight(self,*a):pass
    def reset(self):pass
class HeroProjection:
    def __init__(self,owner):
        self.props={};self.controls={};self.preview_dispatch_lock=threading.RLock();self.config=owner.config;self.mode='home';self.section='Home';self.episode_browser_context=None;self.preview_mode=owner.preview_mode;self.previews_ready=owner.previews_ready;self.adaptive_browsing=True;self.rating_cache={}
        # Only the ordinary Home renderer is projected. Personal native
        # subclasses may use super(), which cannot run on a display projection.
        from live_review import LiveReview
        self._home_behavior=LiveReview
        self.logo_decisions=getattr(owner,'logo_decisions',None)
        self.display_ratings=LiveReview.display_ratings.__get__(self)
        self.rating_identity=LiveReview.rating_identity.__get__(self)
    def setProperty(self,key,value):self.props[key]=value
    def getControl(self,key):
        if key not in self.controls:self.controls[key]=CaptureControl()
        return self.controls[key]
    def source_session_label(self,item):return ''
    def render(self,owner,item):
        self._home_behavior.update(self,item)
        return {'properties':{k:v for k,v in self.props.items() if k in HERO_KEYS},'play':self.controls[101].label,'saved':self.controls[103].label,'height':self.controls[251].height}

def save_home_display(owner,store,root):
    """Called after usable Home rows; this writes only a bounded disposable file."""
    def ready():
        return (owner.alive and owner.section=='Home' and owner.mode=='home'
                and owner.row_offset==0 and len(owner.page_definitions)>=2 and all(owner.window_ready))
    try:
        with owner.preview_dispatch_lock:
            if not ready():return False
            cache=getattr(owner,'home_snapshot_cache',None)
            if cache is None or not cache.scope:return False
            provider_scope=cache.scope;generation=getattr(owner,'generation',None)
        # Kodi add-on enumeration and account files can take time. The
        # visible Home and remote input do not need to wait for this proof.
        policies=policy_bytes(store);scope=display_scope(store,provider_scope)
        if not scope:return False
        with owner.preview_dispatch_lock:
            if (not ready() or getattr(owner,'home_snapshot_cache',None) is not cache
                    or cache.scope!=provider_scope or getattr(owner,'generation',None)!=generation):return False
            rows=[];projection=HeroProjection(owner)
            for n,definition in enumerate(owner.page_definitions[:2]):
                if set(definition)-{'label','_canonical_label','path','enabled'} or not home_path(definition.get('path')):return False
                raw=_items(copy.deepcopy(owner.raw_title_row(n)),path_filter=home_item_path,max_items=40)
                if not raw:return False
                from browse_controls import is_next_page,page_card
                heroes=[projection.render(owner,page_card('next',item['file']) if is_next_page(item,definition['path']) else item) for item in raw]
                rows.append({'label':definition.get('_canonical_label',definition['label']),'path':definition['path'],'items':raw,'heroes':heroes})
            from icon_packs import icon_path,selected_pack
            from navigation_core import status_settings,sidebar_layout
            sidebar=[{'id':entry['id'],'label':entry['label'],'icon':icon_path(root,entry['icon'],selected_pack(owner.config))} for entry in owner.navigation_items]
            layout=sidebar_layout(len(sidebar)-2)
            properties=dict(captionRows='false',episodeBrowser='false',searchBrowser='false',heroCompact='true',addonBrowser='false',genreChooser='false',loading='false',loadingStatus='',input='remote',previewMode=owner.preview_mode,genreLabel='Genres: All',page='home',notice='Live add-on content  ·  Select a title for details',youtubeBrowser='false',filmographyBrowser='false',scroll='top',eyebrow='HOME',browseFilters='false',previewsReady='true' if owner.previews_ready else 'false',sidebarCompact='true' if layout['row_height']==80 else 'false',startupIdle='true')
            for key,value in status_settings(owner.config).items():properties['show'+key.title()]='true' if value else 'false'
            fields={'rows':rows,'sidebar':sidebar,'properties':properties}
        if policy_bytes(store)!=policies:return False
        return write_record(Path(store)/'home-display.json',scope,fields)
    except (OSError,ValueError,AttributeError,TypeError,KeyError):return False

def validated_record(path,scope):
    value=read_record(path,scope)
    if not value:return None
    try:
        if set(value)!={'version','scope','time','rows','sidebar','properties'}:return None
        rows=value['rows'];sidebar=value['sidebar'];props=value['properties']
        if not isinstance(rows,list) or len(rows)!=2 or not isinstance(sidebar,list) or not 3<=len(sidebar)<=30:return None
        if not isinstance(props,dict) or set(props)-BASE_KEYS or any(not isinstance(v,str) or len(v)>200 for v in props.values()):return None
        for entry in sidebar:
            if not isinstance(entry,dict) or set(entry)!={'id','label','icon'} or any(not isinstance(v,str) or len(v)>4096 for v in entry.values()):return None
            icon=Path(entry['icon'])
            if not icon.is_absolute() or icon.suffix.lower()!='.png' or '/addons/' not in str(icon) or not icon.is_file():return None
        if sidebar[0]['id']!='search' or sidebar[-1]['id']!='settings' or not any(x['id']=='home' for x in sidebar):return None
        for row in rows:
            if not isinstance(row,dict) or set(row)!={'label','path','items','heroes'} or not isinstance(row['label'],str) or len(row['label'])>200 or not home_path(row['path']):return None
            sanitized=_items(row['items'],path_filter=home_item_path,max_items=40)
            if not sanitized or sanitized!=row['items'] or len(row['heroes'])!=len(sanitized):return None
            for hero in row['heroes']:
                if not isinstance(hero,dict) or set(hero)!={'properties','play','saved','height'} or hero['height'] not in (105,155):return None
                if hero['play'] not in ('Play','Episodes','Resume','Next') or hero['saved'] not in ('Saved','+ My Stuff'):return None
                hp=hero['properties']
                if not isinstance(hp,dict) or set(hp)-HERO_KEYS or any(not isinstance(v,str) or len(v)>20000 for v in hp.values()):return None
                if any(hp.get(k) and not _art(hp[k]) for k in ('hero','titleLogo')):return None
                if any(v and (not v.startswith('rating-') or not v.endswith('.png') or '/' in v or '\\' in v) for k,v in hp.items() if k.startswith('ratingIcon')):return None
        return value
    except (ValueError,TypeError,KeyError,OSError,AttributeError):return None

def adoption_definitions(config,arrange,record):
    """Rebuild the complete live catalogue, matching only its visible saved pair."""
    from discovery_core import display_page_rows, page_rows
    definitions=list(arrange(page_rows(config,'Home')))
    visible=record['rows']
    if len(definitions)<2 or any((definition.get('label'),definition.get('path'))!=(row['label'],row['path']) for definition,row in zip(definitions[:2],visible)):return None
    return display_page_rows('Home',definitions)
