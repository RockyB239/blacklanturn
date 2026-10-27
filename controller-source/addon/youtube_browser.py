"""YouTube account visibility and tabs using the skin's existing row browser."""
import json,time,threading,copy
from contextlib import nullcontext
from youtube_core import ConnectionState,TABS,tab_rows,account_options,connected_account
from youtube_provider import load_home_rows
from youtube_rows import YouTubeRows
from youtube_saved_runtime import SavedYouTube

def read_account_store():
    import xbmcvfs
    path=xbmcvfs.translatePath('special://profile/addon_data/plugin.video.youtube/access_manager.json')
    if not xbmcvfs.exists(path):return {}
    stream=xbmcvfs.File(path)
    try:
        if stream.size()>1024*1024:raise ValueError('YouTube account store exceeds limit')
        raw=bytes(stream.readBytes())
    finally:stream.close()
    if not raw:raise ValueError('YouTube account store temporarily unreadable')
    return json.loads(raw.decode('utf-8'))

class YouTubeBrowser(YouTubeRows,SavedYouTube):
    def refresh_youtube_connection(self,force=False):
        import xbmc
        if force:SavedYouTube.invalidate_saved_youtube_settings(self)
        lifetime=getattr(self,'window_lifetime',None)
        def current():return getattr(self,'alive',True) and lifetime is getattr(self,'window_lifetime',None)
        if not current():return
        self.apply_youtube_home_rows()
        if not force and time.monotonic()-getattr(self,'youtube_checked_at',0)<5:return
        self.youtube_checked_at=time.monotonic()
        result=json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'Addons.GetAddonDetails','params':{'addonid':'plugin.video.youtube','properties':['enabled']}})))
        if not current() or 'error' in result:return
        candidate=ConnectionState();previous=getattr(self,'youtube_connection',None)
        if previous:candidate.connected,candidate.identity=previous.connected,previous.identity
        changed=candidate.refresh(read_account_store,bool(result.get('result',{}).get('addon',{}).get('enabled')))
        if not current():return
        self.youtube_connection=candidate
        self.setProperty('youtubeConnected','true' if candidate.connected else 'false')
        if not current() or not changed:return
        saved=getattr(self,'youtube_saved_store',None)
        if saved is not None and previous and previous.connected:saved.clear()
        self.youtube_saved_store=None;self.youtube_saved_active=False;self.youtube_saved_due=float('inf')
        self.youtube_home_cache=None;self.youtube_home_request=object()
        self.youtube_pages={};self.youtube_content_revision=object();self.youtube_job=None;self.youtube_update=None;self.youtube_refreshing=False
        self.invalidate_row_results()
        if not current():return
        self.youtube_query='';self.refresh_navigation()
        if not current():return
        if self.section=='YouTube':
            if candidate.connected:self.load_youtube_section()
            else:self.section='Home';self.navigation_id='home';self.load_section()

    def load_youtube_section(self,tab='home',query=None):
        if not getattr(getattr(self,'youtube_connection',None),'connected',False):
            self.section='Home';self.navigation_id='home';self.load_section();return
        self.youtube_home_request=object()
        self.youtube_pages={};self.youtube_content_revision=object();self.youtube_job=None;self.youtube_update=None;self.youtube_refreshing=False
        self.setProperty('youtubeRowEnd','false')
        self.stop_preview();self.section='YouTube';self.mode='home';self.active_page=tab
        self.youtube_tab=tab;self.youtube_query=query if query is not None else getattr(self,'youtube_query','')
        self.search_state=None;self.search_origin=None;self.discovery_stack=[];self.person_context=None;self.episode_browser_context=None
        self.generation+=1
        for key,value in [('youtubeBrowser','true'),('captionRows','true'),('addonBrowser','false'),('genreChooser','false'),('episodeBrowser','false'),('searchBrowser','false'),('filmographyBrowser','false'),('page','home'),('scroll','top'),('browseFilters','true'),('allEpisodes','false'),('previewsReady','true'),('previewMode','auto' if self.config.get('YouTubePreviews',True) else 'manual'),('eyebrow','YOUTUBE / '+dict(TABS).get(tab,'Home').upper())]:self.setProperty(key,value)
        self.populate_youtube_tabs()
        options={}
        if tab=='library':
            try:options=account_options(read_account_store())
            except (OSError,ValueError,TypeError):pass
        self.set_rows(self.saved_youtube_home() if tab=='home' and hasattr(self,'saved_youtube_home') else tab_rows(tab,self.youtube_query,account=options))
        if tab=='home':self.start_youtube_home()

    def apply_youtube_home_rows(self):
        cache=getattr(self,'youtube_home_cache',None);connection=getattr(self,'youtube_connection',None)
        lifetime=getattr(self,'window_lifetime',None);request=getattr(self,'youtube_home_request',None)
        definitions=getattr(self,'page_definitions',None)
        def current():
            active=getattr(self,'youtube_connection',None)
            return (getattr(self,'alive',False) and lifetime is getattr(self,'window_lifetime',None)
                    and request is getattr(self,'youtube_home_request',None) and cache is getattr(self,'youtube_home_cache',None)
                    and cache and getattr(active,'connected',False) and cache['identity']==active.identity
                    and time.monotonic()-cache['time']<=300 and self.section=='YouTube' and getattr(self,'youtube_tab','')=='home'
                    and not getattr(self,'discovery_stack',[]) and definitions is getattr(self,'page_definitions',None) and len(definitions)==2)
        if not current():return
        try:
            if connected_account(read_account_store())[1]!=connection.identity:return
        except (OSError,ValueError,TypeError):return
        # The blended recommendation row is already first. Extra shelves retain
        # YouTube's own labels/order without moving the user's current selection.
        rows=copy.deepcopy(cache['rows'][1:])
        with getattr(self,'preview_dispatch_lock',nullcontext()):
            if current():
                definitions.extend(rows)
                if hasattr(self,'youtube_refresh_navigation'):self.youtube_refresh_navigation()

    def start_youtube_home(self):
        self.youtube_home_pending=False
        if getattr(self,'youtube_saved_active',False):return
        self.apply_youtube_home_rows()
        cache=getattr(self,'youtube_home_cache',None);identity=self.youtube_connection.identity
        if cache and cache['identity']==identity and time.monotonic()-cache['time']<300:return
        request=object();self.youtube_home_request=request;lifetime=self.window_lifetime
        self.youtube_home_pending=True
        def owns():
            if (not self.alive or self.window_lifetime is not lifetime or self.youtube_home_request is not request
                    or not self.youtube_connection.connected or self.youtube_connection.identity!=identity):return False
            return True
        def current():
            if not owns():return False
            try:identity_now=connected_account(read_account_store())[1]
            except (OSError,ValueError,TypeError):return False
            return owns() and identity_now==identity
        if hasattr(self,'youtube_saved_guard'):current=self.youtube_saved_guard(current)
        def work():
            try:
                rows=load_home_rows(current) if current() else []
                if rows and current():
                    if hasattr(self,'remember_youtube_shelves'):self.remember_youtube_shelves(rows,current)
                    self.youtube_home_cache={'identity':identity,'time':time.monotonic(),'rows':rows}
                    self.apply_youtube_home_rows()
            except Exception as exc:
                # A failed request never replaces live lists or becomes a cached
                # empty success. Reopening Home retries through the provider.
                if current():self.youtube_home_error=type(exc).__name__
            finally:
                if current():self.youtube_home_pending=False
        threading.Thread(target=work,name='BlackLanturnYouTubeHome',daemon=True).start()

    def populate_youtube_tabs(self):
        import xbmcgui
        self.browse_sources=[{'id':key,'label':label} for key,label in TABS]
        control=self.getControl(600);control.reset();items=[]
        selected=0
        for index,(key,label) in enumerate(TABS):
            item=xbmcgui.ListItem(label=label);active=key==getattr(self,'youtube_tab','home');item.setProperty('active','true' if active else 'false');items.append(item)
            if active:selected=index
        control.addItems(items);control.selectItem(selected)
        self.setProperty('browseFilters','true');self.setProperty('genreChooser','false')
        self.getControl(900).controlUp(control)
        for cid in (900,901):self.getControl(cid).setHeight(360)

    def select_youtube_tab(self,tab=None):
        import xbmcgui
        if tab is None:
            index=self.getControl(600).getSelectedPosition()
            if not 0<=index<len(TABS):return
            tab=TABS[index][0]
        query=None
        if tab=='search':
            self.stop_preview();self.actions_open=True
            try:query=xbmcgui.Dialog().input('Search YouTube',defaultt=getattr(self,'youtube_query','')).strip()
            finally:self.actions_open=False
            if not query:return
        self.load_youtube_section(tab,query)
        self.setFocusId(600)

    def remember_youtube_watch_items(self,files):
        from youtube_core import video_id
        fresh={video_id(item):item for item in files if video_id(item)}
        def update(items):
            for item in items:
                match=fresh.get(video_id(item))
                if match:
                    for key in ('playcount','resume'):
                        if key in match:item[key]=copy.deepcopy(match[key])
        for definition in getattr(self,'page_definitions',[]):update(definition.get('local_items',[]))
        for cached in getattr(self,'row_cache',{}).values():
            if isinstance(cached,dict):update(cached.get('files',[]))
        for page in getattr(self,'youtube_pages',{}).values():update(page.get('items',[]))
        cache=getattr(self,'youtube_home_cache',None)
        if cache:
            for definition in cache['rows']:update(definition.get('local_items',[]))

    def youtube_request_guard(self,generation=None):
        lifetime=self.window_lifetime;identity=self.youtube_connection.identity
        def owns():
            active=getattr(self,'youtube_connection',None)
            return (self.alive and self.window_lifetime is lifetime and (generation is None or self.generation==generation)
                    and getattr(active,'connected',False) and active.identity==identity)
        def current():
            if not owns():return False
            try:identity_now=connected_account(read_account_store())[1]
            except (OSError,ValueError,TypeError):return False
            return owns() and identity_now==identity
        return current
