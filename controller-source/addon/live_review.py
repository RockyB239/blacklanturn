"""Temporary live Kodi integration review. Uses provider directories, not a scraped catalogue."""
import json,time,threading,traceback,ssl,copy,hashlib
from urllib.request import urlopen,Request
from pathlib import Path
from urllib.parse import urlencode,urlsplit,parse_qs
import xbmc,xbmcgui,xbmcvfs,xbmcaddon
from live_core import directory_items,rating_line,PageHistory,valid_source,person_identity,mdblist_line,rating_badges,select_rating_badges,update_rating_sources,preview_candidates,PreviewAttempts,watch_state,clear_stale_preview,episode_identity,show_identity,title_details_params,merge_title_details,episode_heading,is_browse_folder
from probe_core import HoverScroll
from live_core import card_artwork,title_presentation
from playback_core import trakt_command,choose_player_path,restored_position,refreshed_watch_item,item_key,resume_options,watch_sync_command
from playback_runtime import wait_for_helper
from episode_ui import season_entries,episode_card,episode_item
from player_preferences import player_choices,player_path,default_setting
from search_ui import SEARCH_KINDS,search_sources,discovery_result,best_matches,load_best_matches,clear_search_selection,entity_kind,search_caption
from preview_setup import configured as preview_configured
from youtube_core import video_id as youtube_video_id,preview_path as youtube_preview_path,is_youtube,caption as youtube_caption,automatic_preview,resume_allowed as youtube_resume_allowed
from youtube_browser import YouTubeBrowser
from youtube_provider import resolve_preview
from watch_metadata import hydrate_watch_metadata
from page_ahead import PageAhead,eligible as page_ahead_eligible
from row_feedback import trim_row_cache,row_message,provider_page_label,RowResultCache
from public_rows import PublicRowSnapshots,snapshot_scope,public_path,helper_settings_identity
from backend_ui import BackendSettings,LoadingPreview
from icon_picker import choose_icon
from genre_picker import choose_genre
from browse_controls import AnimeMetadata,can_choose_genre,should_exclude_anime,page_cards
from filtered_pages import provider_path,upstream_path,logical_files,needs_fill,fill_page,PageCancelled
from preview_language import cached_video_metadata,cached_title_aliases
from preview_identity import TitleVerifier
from preview_geometry import preview_fill_viewmode,preview_display_aspect,PreviewRendererGuard
from preview_bars import PreviewBarScan,PreviewFramingCache,top_aligned_viewmode,framing_key
from live_core import caption_fit_step,my_stuff_rows,row_items
from discovery_core import migrate_pages,collection_pages,page_rows,window_shift
from addon_catalog import catalogue_items,catalogue_category
from navigation_core import migrate_navigation,visible_navigation,resolve_destination,edit_navigation,status_settings,default_icon,ICON_CHOICES,KODI_DESTINATIONS,SECTIONS,sidebar_items,sidebar_layout
ROOT=Path(__file__).resolve().parent
PROFILE=Path(xbmcvfs.translatePath('special://profile/'))
STORE=Path(xbmcvfs.translatePath(xbmcaddon.Addon('script.blacklanturn.preview').getAddonInfo('profile')))
EVIDENCE=STORE/'logs'
EVIDENCE.mkdir(parents=True,exist_ok=True)
TMDB='plugin://plugin.video.themoviedb.helper/'
RATING_OPTIONS=[('rottentomatoes','Rotten Tomatoes critics'),('metacritic','Metacritic'),('imdb','IMDb audience'),('popcorn','Rotten Tomatoes audience'),('themoviedatabase','TMDb audience')]
DEFAULT_RATINGS=[x[0] for x in RATING_OPTIONS[:4]]

def rpc(method,params=None):
    return json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params or {}})))

def gui_labels(labels):
    # Kodi's direct Python getter reads native GUI objects on the caller's
    # thread. JSON-RPC dispatches these reads through TMSG_GUI_INFOLABEL.
    response=rpc('XBMC.GetInfoLabels',{'labels':list(labels)})
    if 'error' in response:raise RuntimeError('GUI labels unavailable')
    result=response.get('result',{})
    return {label:result.get(label,'') for label in labels}

def event(name,**fields):
    with (EVIDENCE/'live-runtime.jsonl').open('a') as f:f.write(json.dumps({'event':name,'time':time.time(),**fields})+'\n')

def tmdb(info,kind='movie',**params):
    return TMDB+'?'+urlencode(dict(info=info,tmdb_type=kind,nextpage='true',widget='true',**params))

PROPERTIES=['title','plot','year','rating','votes','genre','country','runtime','mpaa','art','thumbnail','uniqueid','cast','director','studio','trailer','season','episode','showtitle','playcount','resume','premiered','writer','set','artist']
def get_list(path):
    if not valid_source(path):raise ValueError('Choose an add-on list')
    start=time.monotonic()
    query=parse_qs(urlsplit(path).query)
    if urlsplit(path).netloc=='plugin.video.themoviedb.helper' and query.get('info')==['blacklanturn_search_matches']:
        return load_best_matches(query.get('query',[''])[0],get_list,workers=2,batch_provider=get_list)
    category=catalogue_category(path)
    if category:
        content='video' if category=='video' else 'executable'
        result=rpc('Addons.GetAddons',{'type':'xbmc.addon.'+content,'content':content,'enabled':True,'installed':True,'properties':['name','enabled','thumbnail','fanart','description','summary']})
        if 'error' in result:raise ValueError(result['error'].get('message','Installed add-ons unavailable'))
        return catalogue_items(result.get('result',{}).get('addons',[]),category)
    result=rpc('Files.GetDirectory',{'directory':path,'media':'video','properties':PROPERTIES})
    if 'error' in result:event('directory_rpc_error',message=result['error'].get('message'))
    files=directory_items(result)
    if urlsplit(path).netloc=='plugin.video.youtube':
        from youtube_artwork import cached_fit_cards
        files=cached_fit_cards(files)
    if query.get('info')==['search'] and query.get('query') and query.get('blacklanturn_all')!=['1']:
        files=best_matches(query['query'][0],files,limit=80)+[x for x in files if not entity_kind(x)]
    if query.get('info')==['search']:
        for item in files:item['_search_kind']=entity_kind(item)
    for item in files:item['_rating_source']='TMDb' if urlsplit(path).netloc=='plugin.video.themoviedb.helper' else 'Rating'
    event('provider_list',addon=urlsplit(path).netloc,count=len(files),seconds=round(time.monotonic()-start,2),last_label=files[-1].get('label') if files else None,folder_count=sum(x.get('filetype')=='directory' for x in files))
    return files

def initialize_addons():
    from live_runtime import check_dependencies
    missing=check_dependencies(rpc,wait_for_abort=xbmc.Monitor().waitForAbort,timeout=10)
    if missing:raise RuntimeError('Required integrations are missing or disabled: '+', '.join(missing))
    flag=STORE/'enable-watch-indicators.pending'
    if flag.exists():
        helper=xbmcaddon.Addon('plugin.video.themoviedb.helper')
        helper.setSettingBool('trakt_watchedindicators',True)
        if not helper.getSettingBool('trakt_watchedindicators'):raise RuntimeError('Watched-indicator preference did not save')
        flag.unlink();event('watch_indicators_enabled')
    if clear_stale_preview(rpc):event('stale_trailer_released')
    event('existing_integrations_ready')

def media_item(data):
    headline,episode_line=episode_heading(data)
    li=xbmcgui.ListItem(label=episode_line or data.get('title') or data.get('label',''),path=data.get('file',''))
    art=dict(data.get('art',{}))
    selected_art=card_artwork(data)
    art['landscape']=selected_art['image'] if selected_art['kind']=='landscape' else ''
    art['poster']=selected_art['image'] if selected_art['kind']=='portrait' else art.get('poster','')
    if selected_art['kind']=='square':art['square']=selected_art['image']
    if data.get('_page_control') and selected_art['kind']=='text':selected_art['kind']='paging'
    li.setProperty('pageControl',data.get('_page_control',''))
    youtube_folder=is_youtube(data) and data.get('filetype')=='directory' and not data.get('_page_control')
    li.setProperty('youtubeFolder','true' if youtube_folder else 'false')
    if youtube_folder:art['youtubefolder']=selected_art['image'] or 'video-addons.png'
    li.setProperty('cardArtKind',selected_art['kind'])
    li.setArt(art)
    info={k:data[k] for k in ['title','plot','year','rating','genre','mpaa','director','studio','season','episode','tvshowtitle','playcount'] if k in data}
    if data.get('runtime'):info['duration']=data['runtime']
    if data.get('showtitle'):info['tvshowtitle']=data['showtitle']
    if info:li.setInfo('video',info)
    hydrate_watch_metadata(li,data)
    caption={'caption':data.get('title') or data.get('label',''),'meta':youtube_caption(data)} if is_youtube(data) else episode_card(data)
    li.setProperty('episodeCaption',caption['caption']);li.setProperty('episodeMeta',search_caption(data) if data.get('_search_kind') else caption['meta'])
    return li

class PreviewPlayer(xbmc.Player):
    def __init__(self):super().__init__();self.failed=False
    def onPlayBackError(self):self.failed=True

class LiveReview(YouTubeBrowser,xbmcgui.WindowXML):
    def onInit(self):
        # Kodi may initialize this object again with recreated native controls.
        # Retire its old setup/monitor before any native initialization can wait.
        lifetime=object();self.window_lifetime=lifetime
        self.generation=getattr(self,'generation',-1)+1
        self.input_generation=getattr(self,'input_generation',-1)+1
        self.preview_generation=getattr(self,'preview_generation',-1)+1
        skin=xbmc.getSkinDir()
        if getattr(self,'owner_skin',skin)!=skin:
            self.alive=False
            if getattr(self,'owned_preview',False):self.stop_preview()
            self.close();return
        self.owner_skin=skin
        self.batch_search_enabled=True
        self.page_ahead=PageAhead()
        self.preview_renderer=PreviewRendererGuard(rpc,STORE/'preview-renderer-recovery.json',xbmc.getCondVisibility('System.Platform.Android'))
        self.restore_preview_renderer()
        self.setProperty('captionRows','false')
        self.setProperty('episodeBrowser','false')
        self.alive=True;self.mode='home';self.section='Home';self.nav=False;self.mouse=False
        self.nav_state_lock=threading.RLock();self.nav_focus_intent=None;self.nav_revision=0;self.nav_width_requested=82;self.nav_width_applied=None
        self.preview_input_generation=self.input_generation
        self.preview_dispatch_lock=threading.RLock();self.preview_dispatched=False
        self.player=PreviewPlayer();self.preview_attempts=None;self.preview_cache={};self.preview_title_verifier=TitleVerifier();self.browse_sources=[];self.owned_preview=False;self.preview_mode='manual';self.dwell=time.monotonic();self.preview_key=None
        self.hover=HoverScroll();self.focus_key=None;self.selected=None;self.last_row=0;self.rows=[[],[]];self.paths=['',''];self.histories=[PageHistory(),PageHistory()];self.return_focus=900
        self.anime_metadata=AnimeMetadata(PROFILE/'addon_data/plugin.video.themoviedb.helper')
        self.cast_people=[];self.person_context=None;self.episode_browser_context=None;self.preview_requested_at=0;self.preview_playing=False
        self.season_sources=[];self.season_title='';self.season_position=0
        self.search_state=None;self.search_origin=None;self.discovery_stack=[];self.row_states={};self.failed_paths={};self.path_tokens={}
        self.setProperty('searchBrowser','false');self.setProperty('browsable','false');self.setProperty('hasSelection','false')
        self.refresh_preview_setup()
        self.rating_cache={};self.rating_busy=False;self.rating_key=None
        self.preview_viewmode=None
        self.preview_bar_scan=None;self.preview_framing_cache=PreviewFramingCache(STORE/'preview-framing-cache.json')
        resume=getattr(self,'resume_backend',None)
        if resume:self.section=resume['section']
        self.core_settings_request=None;self.playback_request=None;self.playback_return=None;self.actions_open=False;self.settings_open=False;self.backend_position=(resume['category'],resume['row']) if resume else (0,0);self.backend_focus=200 if resume else 100;self.loading_started=time.monotonic()
        self.navigation_id=resume.get('navigation_id','home') if resume else 'home';self.navigation_items=[];self.pending_sidebar_return=False
        self.active_page=None;self.page_definitions=[];self.row_offset=0;self.row_cache={};self.window_ready=[False,False];self.list_lock=threading.Lock()
        self.result_cache=RowResultCache()
        self.adaptive_browsing=True;self.fixed_hero=True
        self.setProperty('heroCompact','true');self.setProperty('addonBrowser','false');self.setProperty('genreChooser','false')
        self.setProperty('loading','true');self.setProperty('loadingStatus','Starting BlackLanturn…')
        self.setProperty('input','remote');self.setProperty('previewMode','manual');self.setProperty('genreLabel','Genres: All');self.setProperty('page','home');self.setProperty('notice','Loading live add-on lists…')
        STORE.mkdir(parents=True,exist_ok=True)
        try:self.config=json.loads((STORE/'rows.json').read_text())
        except (FileNotFoundError,ValueError):
            self.config={'Home':[{'label':'Movies this week','path':tmdb('trending_week')},{'label':'Shows this week','path':tmdb('trending_week','tv')}],
                         'Movies':[{'label':'Trending movies','path':tmdb('trending_week')},{'label':'Popular movies','path':tmdb('popular')}],
                         'Shows':[{'label':'Trending shows','path':tmdb('trending_week','tv')},{'label':'Popular shows','path':tmdb('popular','tv')}],
                         'Categories':[],'Saved':[]}
        self.config.setdefault('Genres',[])
        migrated=migrate_navigation(migrate_pages(self.config))
        if migrated!=self.config:self.config=migrated;self.save()
        self.snapshot_cache=None;self.configure_row_snapshots()
        # Explicit private A/B trial only; serialized provider calls are not cancellable.
        self.prefetch_trial=False;self.prefetch_attempted=set();self.prefetch_busy=False
        self.preview_mode=self.config.get('PreviewMode','manual');self.setProperty('previewMode',self.preview_mode)
        self.refresh_youtube_connection(force=True)
        self.refresh_navigation();self.apply_status()
        self.initialize_startup_focus()
        threading.Thread(target=lambda:self.start(lifetime),name='BlackLanturnLiveSetup',daemon=True).start()
        threading.Thread(target=lambda:self.monitor(lifetime),name='BlackLanturnLiveFocus',daemon=True).start()
        if resume and resume.get('origin')!='sidebar':threading.Thread(target=lambda:self.resume_settings(lifetime),name='BlackLanturnSettingsReturn',daemon=True).start()
        event('live_opened')
    def initialize_startup_focus(self):
        # Only a new browsing session starts neutral. Settings and playback
        # returns keep their existing position/focus restoration.
        self.startup_idle=not (getattr(self,'resume_backend',None) or getattr(self,'resume_playback',None))
        self.setProperty('startupIdle','true' if self.startup_idle else 'false')
        self.setFocusId(5 if self.startup_idle else 900)
    def resume_settings(self,lifetime=None):
        if lifetime is None:lifetime=getattr(self,'window_lifetime',None)
        def current():return self.alive and lifetime is getattr(self,'window_lifetime',None)
        if not current():return
        self.settings(lifetime)
        if current():self.set_nav(False,pending_focus=True);self.setFocusId(900 if self.rows[0] else 101)
    def save(self,invalidate=True):
        temp=STORE/'rows.tmp';temp.write_text(json.dumps(self.config,indent=2));temp.replace(STORE/'rows.json')
        if invalidate:
            self.invalidate_row_results()
            if getattr(self,'alive',False):self.restart_pending_rows()
    def start(self,lifetime=None):
        if lifetime is None:lifetime=getattr(self,'window_lifetime',None)
        def current():return getattr(self,'alive',True) and lifetime is getattr(self,'window_lifetime',None)
        if not current():return
        try:
            if getattr(self,'resume_backend',None) and self.resume_backend.get('browse_state'):
                self.restore_browse(self.resume_backend['browse_state']);return
            playback_resume=getattr(self,'resume_playback',None)
            if playback_resume:
                restored=self.restore_browse(playback_resume)
                if restored is not False and current():self.refresh_watch_status(sync=getattr(self,'section','')!='YouTube',browse_state=playback_resume)
                return
            self.setProperty('loadingStatus','Preparing your integrations…')
            if not getattr(self,'resume_backend',None):initialize_addons()
            if not current():return
            self.setProperty('loadingStatus','Loading your home…');self.load_section()
            if not current():return
            resume=getattr(self,'resume_backend',None)
            if resume and resume.get('origin')=='sidebar' and resume.get('active_page'):
                route=resolve_destination({'kind':'page','page_id':resume['active_page']},self.config,self.section)
                if route:self.load_navigation_page(route)
            if not current():return
            if resume and resume.get('origin')=='sidebar':self.pending_sidebar_return=True;self.restore_sidebar_focus()
        except Exception as exc:
            if not current():return
            self.finish_loading('setup_failed')
            self.setProperty('notice','Integration setup failed. Open Home to retry, or check integrations in Settings.')
            event('setup_error',error=str(exc))
    def finish_loading(self,reason):
        if self.getProperty('loading')=='true':
            self.setProperty('loading','false');event('branded_loading_complete',reason=reason,seconds=round(time.monotonic()-self.loading_started,2))
    def stop_preview(self):
        with self.preview_dispatch_lock:
            self.preview_generation+=1
            self.cancel_preview_bar_scan()
            if self.preview_attempts:self.preview_attempts.cancel()
            self.preview_attempts=None
            # Player.stop waits for Kodi while holding Python's GIL. A resolving
            # YouTube script may need that GIL to stop, so post the owned stop.
            if self.owned_preview and (self.preview_dispatched or self.player.isPlaying()):
                xbmc.executebuiltin('PlayerControl(Stop)',False)
                # Drain the main-thread message after Stop through JSON-RPC,
                # which releases Python's GIL while waiting. Reflected skin
                # controls can otherwise hold the GIL in setWidth while Kodi
                # waits for a Python YouTube proxy response during CloseFile.
                rpc('XBMC.GetInfoLabels',{'labels':['System.CurrentControlId']})
            self.preview_dispatched=False;self.owned_preview=False;self.preview_key=None
            # Cleanup belongs to this cancellation. Keep a new owner from
            # dispatching until restoration has completed; these JSON-RPC calls
            # release the GIL, unlike the legacy Player.stop call above.
            self.restore_preview_viewmode()
            self.restore_preview_renderer()
            self.setProperty('preview','idle')
    def cancel_preview_bar_scan(self):
        scan=getattr(self,'preview_bar_scan',None)
        if scan:scan.close()
        self.preview_bar_scan=None
    def start_preview_bar_scan(self,stream,aspect,fit):
        self.cancel_preview_bar_scan()
        compact=self.getProperty('heroCompact')=='true' and self.mode=='home'
        source_aspect=preview_display_aspect(stream,aspect)
        if not source_aspect or not isinstance(fit,dict):return
        self.preview_bar_context=(self.preview_generation,compact,source_aspect,fit,framing_key(self.preview_url,compact,source_aspect))
        cached=self.preview_framing_cache.get(self.preview_bar_context[-1])
        if cached is not None:self.apply_preview_bar_alignment(cached,True)
        else:self.preview_bar_scan=PreviewBarScan(xbmc.RenderCapture,compact,time.monotonic())
    def apply_preview_bar_alignment(self,fraction,cached=False):
        with self.preview_dispatch_lock:
            token,compact,aspect,fit,key=self.preview_bar_context
            if token!=self.preview_generation or not self.owned_preview or not self.player.isPlayingVideo():return
            decoder=gui_labels(['Player.Process(videodecoder)'])['Player.Process(videodecoder)'].lower()
            if token!=self.preview_generation or not self.owned_preview or not self.player.isPlayingVideo():return
            adjusted=top_aligned_viewmode(fit,fraction,aspect,compact,flipped=decoder.startswith('amc-') and '(s)' not in decoder)
            if fraction:
                result=rpc('Player.SetViewMode',{'viewmode':adjusted})
                if result.get('result')!='OK':return
            if not cached:
                try:self.preview_framing_cache.put(key,fraction)
                except OSError:event('preview_framing_cache_unavailable')
            event('preview_top_alignment',fraction=round(fraction,5),adjusted=bool(fraction),cached=cached,viewmode=adjusted)
    def sample_preview_bar_scan(self):
        scan=self.preview_bar_scan
        if not scan:return
        scan.tick(time.monotonic())
        if scan.done:
            if scan.result is not None:self.apply_preview_bar_alignment(scan.result)
            else:event('preview_border_inconclusive',samples=scan.attempts,observations=scan.observations)
            self.preview_bar_scan=None
    def restore_preview_renderer(self):
        guard=getattr(self,'preview_renderer',None)
        if guard and not guard.restore():
            event('preview_renderer_restore_failed')
            xbmcgui.Dialog().ok('BlackLanturn','The normal video renderer could not be restored. Restart Kodi before starting playback.')
            raise RuntimeError('Preview renderer restoration failed')
    def restore_preview_viewmode(self):
        if self.preview_viewmode is not None:
            previous=self.preview_viewmode;self.preview_viewmode=None
            mode=previous.get('viewmode','normal')
            value={k:previous[k] for k in ('zoom','pixelratio','verticalshift','nonlinearstretch') if k in previous} if mode=='custom' else mode
            result=rpc('Player.SetViewMode',{'viewmode':value})
            event('preview_viewmode_restored',ok=result.get('result')=='OK')
    def display_ratings(self,badges):
        badges=[] if discovery_result(self.selected or {}) else select_rating_badges(self.selected or {},badges,self.config.get('RatingSources',DEFAULT_RATINGS))
        for i in range(5):
            badge=badges[i] if i<len(badges) else None
            self.setProperty('ratingValue'+str(i),badge['value'] if badge else '')
            self.setProperty('ratingIcon'+str(i),'rating-'+badge['icon']+'.png' if badge else '')
    def set_nav(self,opened,pending_focus=False):
        # Callbacks submit intent. Only the focus monitor changes geometry.
        with self.nav_state_lock:
            self.nav=opened;self.nav_width_requested=350 if opened else 82
            self.nav_focus_intent=opened if pending_focus else None;self.nav_revision+=1
        if opened:self.stop_preview()
    def apply_nav_width(self):
        with self.preview_dispatch_lock:
            with self.nav_state_lock:width=self.nav_width_requested
            if self.nav_width_applied==width:return
            self.setProperty('nav','open' if width==350 else 'closed')
            for cid in (10,50,15):self.getControl(cid).setWidth(width)
            # A newer intent may arrive while the native setter yields. Leave that
            # request queued for the next monitor pass instead of dropping it.
            self.nav_width_applied=width
    def sync_nav_focus(self,focus):
        opened=focus in (10,50,15)
        with self.nav_state_lock:
            pending=self.nav_focus_intent
            change=False
            if pending is None or pending==opened:
                self.nav_focus_intent=None;change=self.nav!=opened;revision=self.nav_revision
        if change:
            if opened:self.stop_preview()
            with self.nav_state_lock:
                if self.nav_revision==revision:
                    self.nav=opened;self.nav_width_requested=350 if opened else 82;self.nav_revision+=1
        self.apply_nav_width()
    def refresh_navigation(self):
        connected=getattr(getattr(self,'youtube_connection',None),'connected',False)
        visible=visible_navigation(self.config,connected);self.navigation_items=sidebar_items(self.config,connected);control=self.getControl(50);control.reset();items=[]
        layout=sidebar_layout(len(visible));control.setHeight(layout['height'])
        self.setProperty('sidebarCompact','true' if layout['row_height']==80 else 'false')
        for entry in self.navigation_items:
            li=xbmcgui.ListItem(label=entry['label']);li.setArt({'icon':str(ROOT/'resources/media'/(entry['icon']+'.png'))})
            li.setProperty('active','true' if entry['id']==self.navigation_id else 'false');items.append(li)
        control.addItems(items);control.setVisible(bool(items))
        if items:control.selectItem(next((i for i,e in enumerate(self.navigation_items) if e['id']==self.navigation_id),0))
        control.controlUp(control);control.controlDown(control)
        for cid in (101,600,900,901,3000,3100):self.getControl(cid).controlLeft(self.getControl(50 if items else 10))
    def restore_sidebar_focus(self):
        if getattr(self,'pending_sidebar_return',False) and all(self.window_ready):
            self.pending_sidebar_return=False;self.set_nav(True,pending_focus=True);self.setFocusId(50 if self.navigation_items else 10)
    def apply_status(self):
        for key,value in status_settings(self.config).items():self.setProperty('show'+key.title(),'true' if value else 'false')
    def status_options(self):
        while self.alive:
            values=status_settings(self.config);keys=['clock','date','weather']
            chosen=xbmcgui.Dialog().select('Status display',[key.title()+'  ·  '+('On' if values[key] else 'Off') for key in keys])
            if chosen<0:return
            values[keys[chosen]]=not values[keys[chosen]];self.config['StatusDisplay']=values;self.save();self.apply_status()
    def sidebar_settings(self):
        while self.alive:
            entries=self.config['Sidebar']
            chosen=xbmcgui.Dialog().select('Sidebar — Search and Settings stay pinned',[e['label']+('  ·  Hidden' if not e.get('enabled',True) else '') for e in entries]+['Add item'])
            event('sidebar_editor_selection',position=chosen,count=len(entries))
            if chosen<0:return
            if chosen==len(entries):
                picked=self.choose_destination()
                if not picked:continue
                from uuid import uuid4
                name=xbmcgui.Dialog().input('Sidebar name',defaultt=picked['label'])
                if not name:continue
                entry={'id':uuid4().hex,'label':name,'icon':picked['icon'],'enabled':True,'destination':picked['destination']}
                self.config['Sidebar']=edit_navigation(self.config,'','add',entry)['Sidebar']
            else:
                entry=entries[chosen];action=xbmcgui.Dialog().select(entry['label'],['Change destination','Rename','Choose icon','Move up','Move down','Hide item' if entry.get('enabled',True) else 'Show item','Remove item'])
                if action<0:continue
                value=None
                if action==0:
                    picked=self.choose_destination()
                    if not picked:continue
                    value=picked['destination']
                elif action==1:value=xbmcgui.Dialog().input('Sidebar name',defaultt=entry['label'])
                elif action==2:
                    value=choose_icon(entry.get('icon'))
                    if value is None:continue
                self.config['Sidebar']=edit_navigation(self.config,entry['id'],['destination','rename','icon','up','down','toggle','remove'][action],value)['Sidebar']
            self.save();self.refresh_navigation()
            event('sidebar_editor_saved',count=len(self.config['Sidebar']))
    def choose_destination(self):
        group=xbmcgui.Dialog().select('Sidebar destination',['BlackLanturn page','Genre or category page','Video add-on or folder','Kodi section'])
        if group<0:return None
        if group==0:
            chosen=xbmcgui.Dialog().select('Page',list(SECTIONS))
            if chosen>=0:return {'label':SECTIONS[chosen],'icon':default_icon(SECTIONS[chosen],{'kind':'section','section':SECTIONS[chosen]}),'destination':{'kind':'section','section':SECTIONS[chosen]}}
        elif group==1:
            pages=[p for g in ('Genres','Categories') for p in self.config.get(g,[])]
            if not pages:xbmcgui.Dialog().ok('No pages yet','Create a genre or category page first.');return None
            chosen=xbmcgui.Dialog().select('Page',[p['label']+'  ·  '+p.get('section','Both') for p in pages])
            if chosen>=0:
                destination={'kind':'page','page_id':pages[chosen]['id']};label=pages[chosen]['label']
                return {'label':label,'icon':default_icon(label,destination),'destination':destination}
        elif group==2:
            addons=rpc('Addons.GetAddons',{'properties':['name','enabled']}).get('result',{}).get('addons',[])
            addons=sorted([a for a in addons if a.get('enabled') and a['addonid'].startswith('plugin.video.')],key=lambda a:a.get('name',a['addonid']).lower())
            if not addons:xbmcgui.Dialog().ok('No video add-ons','Enable the add-on in Kodi settings first.');return None
            chosen=xbmcgui.Dialog().select('Installed video add-ons',[a.get('name',a['addonid']) for a in addons])
            if chosen<0:return None
            addon=addons[chosen];mode=xbmcgui.Dialog().select(addon.get('name',addon['addonid']),['Open add-on','Choose a folder'])
            if mode<0:return None
            source=self.choose_source(addon) if mode==1 else {'label':addon.get('name',addon['addonid']),'path':'plugin://'+addon['addonid']+'/'}
            if source:
                destination={'kind':'addon','path':source['path']}
                return {'label':source['label'],'icon':default_icon(source['label'],destination),'destination':destination}
        elif group==3:
            chosen=xbmcgui.Dialog().select('Kodi section',[x[1] for x in KODI_DESTINATIONS])
            if chosen>=0:
                window,label=KODI_DESTINATIONS[chosen]
                destination={'kind':'kodi','window':window}
                return {'label':label,'icon':default_icon(label,destination),'destination':destination}
        return None
    def load_navigation_page(self,route):
        self.setProperty('filmographyBrowser','false')
        self.search_state=None;self.search_origin=None;self.discovery_stack=[];self.setProperty('searchBrowser','false')
        self.episode_browser_context=None
        self.setProperty('episodeBrowser','false')
        self.setProperty('captionRows','false')
        self.section=route['section'];self.person_context=None;self.mode='home';self.active_page=route['page_id']
        self.setProperty('page','home');self.setProperty('scroll','top');self.setProperty('eyebrow',self.section.upper()+' / '+route['label'].upper());self.load_browse_sources()
        self.set_rows(route['rows'])
    def activate_navigation(self,entry):
        if entry.get('fixed_action'):
            self.onClick(10 if entry['fixed_action']=='search' else 15);return
        route=resolve_destination(entry.get('destination'),self.config,self.section)
        if not route:xbmcgui.Dialog().ok('Destination unavailable','This page was removed or its destination is unsupported. Change it in Sidebar settings.');return
        if route['kind']=='addon' and not xbmc.getCondVisibility('System.HasAddon('+route['addon']+')'):
            xbmcgui.Dialog().ok('Add-on unavailable','Enable this add-on in Kodi settings. Your sidebar item has been retained.');return
        if route['kind']=='kodi':
            window=route['window'];required='PVR.HasTVChannels' if window in ('tvchannels','tvguide') else 'PVR.HasRadioChannels' if window=='radiochannels' else None
            if required and not xbmc.getCondVisibility(required):xbmcgui.Dialog().ok('Live TV setup','Configure a PVR client and channels in Kodi settings first. Your sidebar item has been retained.');return
            if window=='weather' and not rpc('Settings.GetSettingValue',{'setting':'weather.addon'}).get('result',{}).get('value'):
                xbmcgui.Dialog().ok('Weather setup','Choose a weather service and location under Kodi settings → Services → Weather first.');return
        self.stop_preview();self.navigation_id=entry['id'];self.refresh_navigation();self.set_nav(False,pending_focus=True)
        if route['kind']=='section':self.section=route['section'];self.load_section();self.setFocusId(900)
        elif route['kind']=='page':self.load_navigation_page(route);self.setFocusId(900)
        else:
            self.core_settings_request={'target':route.get('window','videos'),'category':self.backend_position[0],'row':self.backend_position[1],'section':self.section,'origin':'sidebar','navigation_id':self.navigation_id,'active_page':self.active_page}
            if route['kind']=='addon':self.core_settings_request['parameters']=[route['path'],'return']
            self.finish()
    def load_section(self):
        if self.section=='YouTube':self.load_youtube_section();return
        self.setProperty('youtubeBrowser','false');self.setProperty('previewMode',getattr(self,'preview_mode','manual'));self.setProperty('previewsReady','true' if getattr(self,'previews_ready',True) else 'false')
        self.setProperty('filmographyBrowser','false')
        self.search_state=None;self.search_origin=None;self.discovery_stack=[];self.setProperty('searchBrowser','false')
        self.episode_browser_context=None
        self.setProperty('episodeBrowser','false')
        self.setProperty('captionRows','true' if self.section=='Add-ons' else 'false')
        self.setProperty('addonBrowser','true' if self.section=='Add-ons' else 'false')
        for cid in (900,901):self.getControl(cid).setHeight(344 if self.section=='Add-ons' else 276)
        self.person_context=None
        self.active_page=None;self.mode='home';self.setProperty('page','home');self.setProperty('scroll','top');self.generation+=1
        self.histories=[PageHistory(),PageHistory()]
        self.setProperty('eyebrow',self.section.upper());self.setProperty('genreLabel','Genres: All');self.load_browse_sources()
        if self.section=='My Stuff':
            self.set_rows(my_stuff_rows(self.config['Saved'],tmdb));return
        self.set_rows(page_rows(self.config,self.section))
    def set_rows(self,definitions):
        self.page_definitions=list(definitions);self.row_offset=0;self.row_cache={};self.window_ready=[False,False]
        self.show_row_window(0,0)
    def publish_cache_stats(self):
        for key,value in self.result_cache.stats().items():self.setProperty('rowCache'+key.title(),str(value))
    def configure_row_snapshots(self):
        if not hasattr(self,'snapshot_cache'):return False
        try:
            helper=xbmcaddon.Addon('plugin.video.themoviedb.helper')
            schema=xbmcvfs.File(helper.getAddonInfo('path')+'/resources/settings.xml')
            try:identity=helper_settings_identity(schema.read(),helper.getSetting)
            finally:schema.close()
        except Exception:
            # No account/config identity proof means no disk reuse on this platform.
            if self.snapshot_cache is not None:self.invalidate_row_results();self.snapshot_cache=None;return True
            return False
        scope=snapshot_scope(self.config,identity);previous=self.snapshot_cache
        if previous is not None and previous.scope==scope:return False
        if previous is not None:self.invalidate_row_results()
        self.snapshot_cache=PublicRowSnapshots(STORE/'public-row-snapshots.json',scope)
        return previous is not None
    def invalidate_row_results(self):
        cache=getattr(self,'result_cache',None)
        if cache is not None:cache.clear();self.publish_cache_stats()
        snapshots=getattr(self,'snapshot_cache',None)
        if snapshots is not None:snapshots.clear()
        self.row_cache={}
    def retained_row_items(self,definition):
        path=definition.get('path','')
        if 'local_items' in definition or not path.startswith(TMDB):return None,False
        metadata=getattr(self,'anime_metadata',None)
        filtered=metadata is not None and should_exclude_anime(self,path)
        if filtered:
            files=self.result_cache.get('filtered-v1:'+path)
            if files is not None and not needs_fill(path,files,metadata.without_anime,positioned=True):return files,False
        files=self.result_cache.get(path)
        if files is not None:
            return (None,False) if filtered and needs_fill(path,files,metadata.without_anime) else (files,False)
        snapshots=getattr(self,'snapshot_cache',None)
        files=snapshots.get(path) if snapshots is not None else None
        if files is not None and filtered and needs_fill(path,files,metadata.without_anime):return None,False
        return files,files is not None
    def fill_discovery_page(self,path,files,current,refresh=False,publish=True):
        metadata=getattr(self,'anime_metadata',None)
        if metadata is None or not path.startswith(TMDB) or not should_exclude_anime(self,path):return files
        cache=self.result_cache;revision=cache.revision;key='filtered-v1:'+path
        cached=None if refresh else cache.get(key)
        if cached is not None and not needs_fill(path,cached,metadata.without_anime,positioned=True):return cached
        if not current():raise PageCancelled('Page navigation changed')
        def fetch(raw_path):
            if not current():raise PageCancelled('Page navigation changed')
            actual=upstream_path(raw_path);raw=cache.get(actual)
            if raw is None:
                raw=get_list(actual)
                if current():cache.put(actual,raw,revision=revision)
            return logical_files(raw,actual,raw_path)
        if upstream_path(provider_path(path))!=provider_path(path):files=fetch(provider_path(path))
        filled=fill_page(path,files,fetch,metadata.without_anime,current=current)
        if current():cache.put(key,filled,revision=revision)
        if publish:self.publish_cache_stats()
        return filled
    def cached_provider_list(self,path,revision,current):
        """Reuse successful exact search subroutes within the existing cache budget."""
        if not current():raise PageCancelled('Search navigation changed')
        cache=self.result_cache;files=cache.get(path)
        if files is None:
            files=get_list(path)
            if not current() or cache.revision!=revision:raise PageCancelled('Search navigation changed')
            cache.put(path,files,revision=revision,ttl=30 if parse_qs(urlsplit(path).query).get('info',[''])[0].startswith('trakt') else 120)
        return files
    def cached_row_items(self,definition,expected_revision=None,owner_current=lambda:True):
        path=definition.get('path','')
        if 'local_items' in definition or not path.startswith(TMDB):return row_items(definition,get_list)
        cache=self.result_cache;revision=cache.revision if expected_revision is None else expected_revision
        if revision!=cache.revision:return []
        generation=self.generation
        def current():return self.alive and self.generation==generation and cache.revision==revision and owner_current()
        if not definition.get('_snapshot_refresh') and getattr(self,'anime_metadata',None) is not None and should_exclude_anime(self,path):
            filled=cache.get('filtered-v1:'+path)
            if filled is not None and not needs_fill(path,filled,self.anime_metadata.without_anime,positioned=True):self.publish_cache_stats();return filled
        if getattr(self,'anime_metadata',None) is not None and should_exclude_anime(self,path) and upstream_path(provider_path(path))!=provider_path(path):
            return self.fill_discovery_page(path,[],current,refresh=definition.get('_snapshot_refresh',False))
        snapshots=getattr(self,'snapshot_cache',None);snapshot_revision=snapshots.revision if snapshots is not None else None
        files=None if definition.get('_snapshot_refresh') else cache.get(path)
        if files is None:
            params=parse_qs(urlsplit(path).query)
            if params.get('info')==['blacklanturn_search_matches']:
                files=load_best_matches(params.get('query',[''])[0],lambda part:self.cached_provider_list(part,revision,current),current,workers=2,batch_provider=get_list if getattr(self,'batch_search_enabled',False) else None,cache=cache,revision=revision)
            else:files=get_list(provider_path(path))
            with self.preview_dispatch_lock:
                if not current():raise PageCancelled('Row navigation changed')
                if self.configure_row_snapshots():self.restart_pending_rows()
                if not current():raise PageCancelled('Row configuration changed')
                # Personal rows stay session-only; late work cannot repopulate either cache.
                info=parse_qs(urlsplit(path).query).get('info',[''])[0]
                cache.put(path,files,revision=revision,ttl=30 if info.startswith('trakt') else 120)
                if revision==cache.revision and snapshots is not None and snapshots is getattr(self,'snapshot_cache',None):snapshots.put(path,files,revision=snapshot_revision)
        self.publish_cache_stats()
        return self.fill_discovery_page(path,files,current,refresh=definition.get('_snapshot_refresh',False))
    def apply_refreshed_row(self,n,files,label):
        # ControlList reset/add/select enqueue separate native GUI messages. A
        # background result must never replace that vector while input uses it.
        displayed=self.rows[n];path=self.paths[n];snapshots=self.snapshot_rows
        owner=(self.generation,self.result_cache.revision,getattr(self,'row_request_serial',0),getattr(self,'path_tokens',{}).get(n))
        def current():
            return (self.alive and self.rows[n] is displayed and self.paths[n]==path and self.snapshot_rows is snapshots
                    and owner==(self.generation,self.result_cache.revision,getattr(self,'row_request_serial',0),getattr(self,'path_tokens',{}).get(n)))
        control=self.getControl(900+n);fresh={item_key(item):item for item in files};matched=0
        for position,item in enumerate(displayed):
            if not current():return
            replacement=fresh.get(item_key(item))
            if replacement is None:continue
            native=control.getListItem(position)
            # Navigation may have replaced vecItems before getListItem returned.
            # After capture this reference owns the old item, so later resets
            # cannot redirect our property writes to a different card.
            if native.getPath()!=item.get('file','') or not current():return
            hydrated={key:value for key,value in item.items() if key not in ('playcount','resume')}
            hydrated.update({key:replacement[key] for key in ('playcount','resume') if key in replacement})
            hydrate_watch_metadata(native,hydrated)
            if not current():return
            displayed[position]=hydrated;matched+=1
        if not current():return
        position=control.getSelectedPosition()
        if not current():return
        anchor=displayed[position] if 0<=position<len(displayed) else None
        # This deferred row belongs to the current window, not the expiring
        # provider cache. Retain even [] until navigation consumes the result.
        deferred={'files':copy.deepcopy(files),'path':path,'history':self.histories[n],'label':label,'position':restored_position(files,anchor,position),'state':'ready' if files else 'empty','failed':None,'message':row_message(label,'ready' if files else 'empty'),'snapshot':False,'deferred':True,'revision':owner[1]}
        if not current():return
        self.row_cache[self.row_offset+n]=deferred
        trim_row_cache(self.row_cache,self.row_offset)
        if not current():return
        snapshots[n]=False
        event('row_snapshot_hydrated',row=n,matched=matched,visible=len(displayed),deferred_order=[item_key(item) for item in displayed]!=[item_key(item) for item in files])
        focus=self.getFocusId();position=control.getSelectedPosition()
        selected=getattr(self,'selected',None) or {}
        target=None
        if focus==900+n and 0<=position<len(displayed):target=displayed[position]
        elif focus in (101,102,103,105,106) and selected:
            target=next((item for item in displayed if item_key(item)==item_key(selected)),None)
        if target is not None and item_key(target) in fresh and current():
            self.update(target);self.focus_key=None
    def show_row_window(self,offset,focus_slot=None):
        scope_changed=self.configure_row_snapshots()
        revision=self.result_cache.revision
        if offset!=self.row_offset and not scope_changed:
            for n in range(2):
                if self.window_ready[n]:
                    index=self.row_offset+n;previous=self.row_cache.get(index);position=self.getControl(900+n).getSelectedPosition()
                    entry={'files':self.rows[n],'path':self.paths[n],'history':self.histories[n],'label':getattr(self,'row_labels',{}).get(n,self.getProperty('row'+str(n))),'position':position,'state':self.row_states.get(n),'failed':copy.deepcopy(self.failed_paths.get(n)),'message':self.getProperty('rowMessage'+str(n)),'snapshot':getattr(self,'snapshot_rows',{}).get(n,False)}
                    if previous and previous.get('deferred') and previous.get('revision')==revision and previous['path']==self.paths[n] and previous.get('files') is not None:
                        anchor=self.rows[n][position] if 0<=position<len(self.rows[n]) else None
                        entry=dict(previous,history=self.histories[n],position=restored_position(previous['files'],anchor,position))
                    self.row_cache[index]=entry
        trim_row_cache(self.row_cache,offset)
        self.row_states={};self.failed_paths={};self.path_tokens={};self.loading_paths={};self.snapshot_rows={}
        for n in range(2):self.setProperty('rowState'+str(n),'');self.setProperty('rowMessage'+str(n),'')
        self.stop_preview();self.selected=None;self.generation+=1;generation=self.generation
        if getattr(self,'search_state',None):clear_search_selection(self)
        self.row_offset=offset;self.focus_key=None;self.window_ready=[False,False];definitions=self.page_definitions[offset:offset+2]
        addon_browser=getattr(self,'section','')=='Add-ons' and not (getattr(self,'search_state',None) or getattr(self,'episode_browser_context',None) or getattr(self,'discovery_stack',[]))
        self.setProperty('addonBrowser','true' if addon_browser else 'false')
        self.setProperty('heroCompact','true' if getattr(self,'adaptive_browsing',False) and (getattr(self,'fixed_hero',False) or offset>0 or addon_browser or self.getProperty('captionRows')=='true') else 'false')
        self.setProperty('notice','Loading live add-on lists…')
        pending=[]
        for n in range(2):
            if generation!=self.generation:return
            index=offset+n;cached=self.row_cache.get(index)
            if cached and cached.get('deferred') and cached.get('revision')!=revision:
                cached=dict(cached,files=None,deferred=False);self.row_cache[index]=cached
            metadata=getattr(self,'anime_metadata',None)
            if cached and cached.get('files') is not None and metadata is not None and should_exclude_anime(self,cached['path']) and needs_fill(cached['path'],cached['files'],metadata.without_anime,positioned=True):
                cached=dict(cached,files=None,deferred=False);self.row_cache[index]=cached
            if n>=len(definitions):
                self.paths[n]='';self.histories[n]=PageHistory();self.apply_row(n,[],'');continue
            if cached and cached.get('files') is not None:
                self.paths[n]=cached['path'];self.histories[n]=cached['history']
                # A visible snapshot keeps its layout until navigation. On
                # return consume its deferred response. Only an unhydrated disk
                # snapshot may use session data; explicit rows are already newer.
                fresh=cached['files'] if cached.get('deferred') else self.result_cache.get(cached['path']) if cached.get('snapshot') and 'local_items' not in definitions[n] and cached['path'].startswith(TMDB) else None
                files=fresh if fresh is not None else cached['files']
                anchor=cached['files'][cached['position']] if 0<=cached['position']<len(cached['files']) else None
                position=restored_position(files,anchor,cached['position']) if fresh is not None and not cached.get('deferred') else cached['position']
                self.apply_row(n,files,cached['label'],position)
                cached['deferred']=False
                if cached.get('state')=='error':
                    self.row_states[n]='error';self.setProperty('rowState'+str(n),'ready' if cached['files'] else 'error');self.setProperty('rowMessage'+str(n),cached.get('message',''))
                    self.setProperty('row'+str(n),cached['label'])
                    if cached.get('failed'):self.failed_paths[n]=copy.deepcopy(cached['failed'])
                if cached.get('snapshot') and fresh is None:
                    self.snapshot_rows[n]=True
                    pending.append((n,dict(definitions[n],path=cached['path'],label=cached['label'],position=cached['position'],_snapshot_refresh=True)))
            else:
                definition=dict(definitions[n])
                if cached:
                    definition.update(path=cached['path'],label=cached['label'],position=cached['position'],_display_position=True)
                    failed=cached.get('failed')
                    if cached.get('state')=='error' and failed:
                        if failed['path']==cached['path']:definition['label']=failed.get('label') or definitions[n]['label']
                        else:definition['_failed_page']={'request':copy.deepcopy(failed),'message':cached.get('message','')}
                self.paths[n]=definition['path'];self.histories[n]=cached['history'] if cached else PageHistory()
                retained,refresh=self.retained_row_items(definition)
                if retained is not None:
                    self.apply_row(n,retained,definition['label'],definition.get('position',0),**({'display_position':True} if definition.get('_display_position') else {}))
                    if refresh:
                        self.snapshot_rows[n]=True;definition['_snapshot_refresh']=True;pending.append((n,definition))
                    continue
                self.rows[n]=[]
                self.getControl(900+n).reset();self.getControl(900+n).setVisible(False)
                self.setProperty('row'+str(n),definition['label']);self.setProperty('rowState'+str(n),'loading');self.setProperty('rowMessage'+str(n),row_message(definition['label'],'loading'));pending.append((n,definition))
        if generation!=self.generation:return
        self.row_navigation()
        if focus_slot is not None and not getattr(self,'startup_idle',False):self.setFocusId(600 if getattr(self,'search_state',None) and not self.rows[focus_slot] else 900+focus_slot)
        if not definitions:
            self.finish_loading('home_empty_or_unavailable');self.setProperty('notice','No visible rows configured. Open Settings to add a row.')
            if not getattr(self,'startup_idle',False):self.getControl(50).selectItem(len(self.navigation_items)-1);self.set_nav(True,pending_focus=True);self.setFocusId(50)
        self.request_row_loads(pending,focus_slot)
        event('row_window',offset=offset,total=len(self.page_definitions),page=self.active_page,focus_slot=focus_slot)
    def request_row_loads(self,pending,focus_slot=None):
        generation=self.generation;revision=self.result_cache.revision
        serial=getattr(self,'row_request_serial',0)+1;self.row_request_serial=serial
        tokens={n:getattr(self,'path_tokens',{}).get(n,0) for n,definition in pending}
        self.row_window_busy=bool(pending)
        def current(n,definition):
            return (self.alive and generation==self.generation and revision==self.result_cache.revision
                    and serial==self.row_request_serial and self.paths[n]==definition['path']
                    and getattr(self,'path_tokens',{}).get(n,0)==tokens[n])
        def work():
            try:
                for n,definition in pending:
                    try:
                        with self.list_lock:
                            if not current(n,definition):continue
                            files=self.cached_row_items(definition,expected_revision=revision,owner_current=lambda n=n,definition=definition:current(n,definition))
                        with self.preview_dispatch_lock:
                            if current(n,definition):
                                if definition.get('_snapshot_refresh'):self.apply_refreshed_row(n,files,definition['label'])
                                else:self.apply_row(n,files,definition['label'],definition.get('position',0),**({'display_position':True} if definition.get('_display_position') else {}))
                                if definition.get('_failed_page'):
                                    retained=definition['_failed_page'];self.failed_paths[n]=retained['request'];self.row_states[n]='error'
                                    self.setProperty('rowState'+str(n),'ready' if files else 'error');self.setProperty('rowMessage'+str(n),retained['message'])
                                if not definition.get('_snapshot_refresh') and focus_slot==n and files and not getattr(self,'startup_idle',False) and int(gui_labels(['System.CurrentControlId'])['System.CurrentControlId'] or '0') in (0,900,901) and current(n,definition):self.setFocusId(900+n)
                    except Exception as exc:
                        with self.preview_dispatch_lock:
                            if current(n,definition):
                                retained=bool(self.rows[n]) if definition.get('_snapshot_refresh') else False
                                if not retained:self.apply_row(n,[],definition['label'])
                                self.failed_paths[n]={'path':definition['path'],'label':definition['label'],'back':True,'position':definition.get('position',0)}
                                self.row_states[n]='error';self.setProperty('row'+str(n),definition['label']+(' · Search unavailable' if getattr(self,'search_state',None) else ' · Unavailable'));self.setProperty('rowState'+str(n),'ready' if retained else 'error');self.setProperty('rowMessage'+str(n),row_message(definition['label'],'error',search=bool(getattr(self,'search_state',None))))
                                self.setProperty('notice','List unavailable · Open title actions to retry or check its integration in Settings.')
                        event('row_error',row=n,error=str(exc))
                if self.alive and generation==self.generation and serial==self.row_request_serial and revision==self.result_cache.revision and getattr(self,'pending_sidebar_return',False):self.restore_sidebar_focus()
            finally:
                if generation==self.generation and serial==self.row_request_serial:self.row_window_busy=False
        threading.Thread(target=work,name='BlackLanturnLiveLists',daemon=True).start()
    def restart_pending_rows(self):
        if not hasattr(self,'window_ready') or not hasattr(self,'paths'):return
        if getattr(self,'watch_refresh_generation',None)==self.generation:return
        pending=[]
        for n,path in enumerate(self.paths):
            if self.window_ready[n] and not getattr(self,'snapshot_rows',{}).get(n):continue
            index=self.row_offset+n
            definition=dict(self.page_definitions[index]) if index<len(self.page_definitions) else {}
            if not path and 'local_items' not in definition:continue
            label=definition.get('label',self.getProperty('row'+str(n))) if not self.window_ready[n] else getattr(self,'row_labels',{}).get(n,self.getProperty('row'+str(n)))
            definition.update(path=path,label=label,position=self.getControl(900+n).getSelectedPosition())
            if self.rows[n]:definition['_snapshot_refresh']=True
            pending.append((n,definition))
        if pending:self.request_row_loads(pending)
    def prefetch_next_row(self):
        """Optional one-row A/B trial. Cache hits never wait on this provider work."""
        if not getattr(self,'prefetch_trial',False) or self.prefetch_busy:return
        def idle():
            return (self.alive and self.mode=='home' and all(self.window_ready)
                    and not getattr(self,'row_window_busy',False) and not self.settings_open and not self.actions_open
                    and not self.owned_preview and self.preview_mode!='auto' and not self.player.isPlaying()
                    and not self.search_state and not self.episode_browser_context and not self.discovery_stack
                    and self.getProperty('loading')!='true' and not getattr(self,'loading_paths',{})
                    and xbmcgui.getCurrentWindowDialogId() in (0,9999)
                    and self.getFocusId() in (900,901) and time.monotonic()-self.dwell>=3)
        if not idle():return
        index=self.row_offset+2
        if index>=len(self.page_definitions):return
        definition=dict(self.page_definitions[index]);path=definition.get('path','')
        if 'local_items' in definition or not public_path(path):return
        key=(self.generation,index,path)
        if key in self.prefetch_attempted or self.result_cache.get(path) is not None:return
        self.prefetch_attempted.clear();self.prefetch_attempted.add(key);self.prefetch_busy=True
        generation=self.generation;revision=self.result_cache.revision
        def work():
            acquired=False
            try:
                acquired=self.list_lock.acquire(blocking=False)
                if not acquired or generation!=self.generation or revision!=self.result_cache.revision or not idle():return
                self.cached_row_items(definition,expected_revision=revision)
                event('row_prefetch_complete',index=index)
            except Exception as exc:event('row_prefetch_error',error_type=type(exc).__name__)
            finally:
                if acquired:self.list_lock.release()
                self.prefetch_busy=False
        threading.Thread(target=work,name='BlackLanturnPublicRowTrial',daemon=True).start()
    def page_files(self,path,current,revision):
        """Shared foreground/lookahead path, including logical filtered pages."""
        if not current():raise PageCancelled('Page navigation changed')
        cache=self.result_cache;metadata=getattr(self,'anime_metadata',None)
        filtered=metadata is not None and path.startswith(TMDB) and should_exclude_anime(self,path)
        files=cache.get(('filtered-v1:' if filtered else '')+path)
        if files is not None and filtered and needs_fill(path,files,metadata.without_anime,positioned=True):files=None
        if files is None:
            if filtered and upstream_path(provider_path(path))!=provider_path(path):files=[]
            else:files=self.cached_provider_list(provider_path(path),revision,current)
            if filtered:files=self.fill_discovery_page(path,files,current,publish=False)
        if not current():raise PageCancelled('Page navigation changed')
        return files
    def prefetch_next_page(self):
        ahead=getattr(self,'page_ahead',None)
        if ahead is None or not self.alive or self.mode!='home' or not all(self.window_ready):return
        if self.nav or self.settings_open or self.actions_open or self.owned_preview or self.player.isPlaying():return
        if getattr(self,'row_window_busy',False) or getattr(self,'loading_paths',{}) or self.getProperty('loading')=='true':return
        if xbmcgui.getCurrentWindowDialogId() not in (0,9999) or self.getFocusId() not in (900,901):return
        if time.monotonic()-self.dwell<.4:return
        n=self.getFocusId()-900;rows=self.rows[n];origin=self.paths[n]
        position=self.getControl(900+n).getSelectedPosition()
        if position<max(0,len(rows)-9):return
        target=next((x.get('file','') for x in rows if x.get('_page_control')=='next'),None)
        if not target or not page_ahead_eligible(target):return
        generation=self.generation;revision=self.result_cache.revision
        key=(generation,revision,target)
        def current():
            return (self.alive and self.generation==generation and self.result_cache.revision==revision
                    and self.rows[n] is rows and self.paths[n]==origin and not self.player.isPlaying())
        def fetch():
            start=time.monotonic();self.page_files(target,current,revision)
            if current():event('next_page_prepared',seconds=round(time.monotonic()-start,3),generation=generation,revision=revision,target_sha256=hashlib.sha256(target.encode()).hexdigest())
        ahead.start(key,fetch,current)
    def row_navigation(self):
        with self.preview_dispatch_lock:
            self.getControl(900).controlUp(self.getControl(900 if self.row_offset>0 else (600 if self.browse_sources or self.episode_browser_context or getattr(self,'search_state',None) else 101)))
            self.getControl(900).controlDown(self.getControl(901 if self.rows[1] else 900))
            self.getControl(901).controlUp(self.getControl(900 if self.rows[0] else (901 if self.row_offset>0 else (600 if self.browse_sources or getattr(self,'search_state',None) else 101))));self.getControl(901).controlDown(self.getControl(901))
            if getattr(self,'adaptive_browsing',False) and self.mode=='home':
                self.getControl(900).controlDown(self.getControl(900))
            if hasattr(self,'youtube_refresh_navigation'):self.youtube_refresh_navigation()
            if getattr(self,'search_state',None) and getattr(self,'adaptive_browsing',False):
                for cid in (900,901):
                    self.getControl(cid).controlUp(self.getControl(cid));self.getControl(cid).controlDown(self.getControl(cid))
            first=900 if self.rows[0] or not self.window_ready[0] else 901 if self.rows[1] else 101
            if getattr(self,'search_state',None) and not any(self.rows):first=600
            self.getControl(600).controlUp(self.getControl(101 if self.selected else 600))
            has_episodes=bool(show_identity(self.selected or {}) and not self.episode_browser_context)
            manual_preview=self.preview_mode!='auto' and getattr(self,'previews_ready',True)
            if getattr(self,'startup_idle',False):
                idle=self.getControl(5);idle.controlRight(self.getControl(first));idle.controlDown(self.getControl(first))
            if self.mode=='home':
                self.getControl(101).controlRight(self.getControl(101 if discovery_result(getattr(self,'selected',None) or {}) else 102))
                self.getControl(103).controlLeft(self.getControl(102))
                self.getControl(103).controlRight(self.getControl(105 if manual_preview else 106 if has_episodes else 103))
                self.getControl(105).controlLeft(self.getControl(103));self.getControl(105).controlRight(self.getControl(106 if has_episodes else 105))
                self.getControl(106).controlLeft(self.getControl(105 if manual_preview else 103))
                self.getControl(600).controlDown(self.getControl(600 if getattr(self,'search_state',None) and getattr(self,'adaptive_browsing',False) else first))
                for cid in (101,102,103,105,106):self.getControl(cid).controlDown(self.getControl(first))
                if getattr(self,'search_state',None) and getattr(self,'adaptive_browsing',False):
                    for cid in (101,102,103,105,106):self.getControl(cid).controlDown(self.getControl(cid))

    def step_search_rows(self,direction,slot=0,focus_target=None):
        """Resolve the next usable row before replacing the current viewport."""
        generation=self.generation;revision=self.result_cache.revision
        epoch=getattr(self,'input_generation',0)
        pending=getattr(self,'search_row_step',None)
        if pending and pending['generation']==generation and pending['direction']==direction:
            pending['epoch']=epoch
            return True
        origin=self.getFocusId()
        request={'generation':generation,'direction':direction,'epoch':epoch,'focus':focus_target or origin,'origin':origin}
        self.search_row_step=request
        start=self.row_offset if origin==600 and focus_target is None else self.row_offset+(slot if origin==901 else 0)+direction
        known=dict(self.row_cache)
        for n in range(2):
            if self.window_ready[n] and self.row_offset+n<len(self.page_definitions):
                known[self.row_offset+n]={'files':self.rows[n],'path':self.paths[n],'history':self.histories[n],
                    'label':getattr(self,'row_labels',{}).get(n,self.getProperty('row'+str(n))),
                    'position':self.getControl(900+n).getSelectedPosition(),'state':self.row_states.get(n),
                    'message':self.getProperty('rowMessage'+str(n)),'failed':self.failed_paths.get(n)}
        definitions=list(self.page_definitions)
        def current():
            return (self.alive and self.generation==generation and self.result_cache.revision==revision
                    and getattr(self,'search_row_step',None) is request
                    and getattr(self,'input_generation',0)==request['epoch'])
        self.stop_preview()
        def work():
            found=None;loaded={}
            try:
                index=start
                while 0<=index<len(definitions) and current():
                    entry=known.get(index)
                    if entry is None:
                        definition=definitions[index];error=False
                        try:
                            with self.list_lock:
                                if not current():return
                                files=self.cached_row_items(definition,expected_revision=revision)
                        except Exception as exc:
                            files=[];error=True;event('search_row_skipped',row=index,error_type=type(exc).__name__)
                        entry={'files':files,'path':definition['path'],'history':PageHistory(),'label':definition['label'],
                            'position':0,'state':'error' if error else 'ready' if files else 'empty',
                            'message':row_message(definition['label'],'error' if error else 'empty',search=True),'failed':None}
                        loaded[index]=entry
                    if entry.get('files'):
                        found=index;break
                    index+=direction
                with self.preview_dispatch_lock:
                    if not current() or self.getFocusId() not in (request['focus'],request['origin']) or request['focus'] not in (600,900,901,700,701):return
                    self.row_cache.update(loaded)
                    self.search_row_step=None
                    if found is not None:
                        self.show_row_window(found,0 if request['focus'] in (600,900,901) else None)
                        if request['focus'] in (700,701):self.setFocusId(request['focus'])
                    elif direction<0 and request['focus'] in (900,901):self.setFocusId(600)
                    else:self.setProperty('notice','End of results' if direction>0 else 'Start of results')
            except Exception as exc:event('search_row_step_error',error_type=type(exc).__name__)
            finally:
                if getattr(self,'search_row_step',None) is request:self.search_row_step=None
        threading.Thread(target=work,name='BlackLanturnSearchRows',daemon=True).start()
        return True

    def shift_rows(self,direction,slot):
        if getattr(self,'search_state',None) and getattr(self,'adaptive_browsing',False):return self.step_search_rows(direction,slot)
        if getattr(self,'adaptive_browsing',False):
            offset=self.row_offset+direction
            if not 0<=offset<len(self.page_definitions):return False
            self.show_row_window(offset,0);return True
        if direction>0 and slot==0 and self.window_ready[1] and not self.rows[1]:slot=1
        elif direction<0 and slot==1 and self.window_ready[0] and not self.rows[0]:slot=0
        offset=window_shift(self.row_offset,slot,direction,len(self.page_definitions))
        if offset is None:return False
        self.show_row_window(offset,slot);return True
    def apply_row(self,n,files,label,position=0,update_selected=True,display_position=False):
        with self.preview_dispatch_lock:
            original=files[position] if 0<=position<len(files) else None
            if getattr(self,'section','')=='YouTube' and hasattr(self,'prepare_youtube_row'):files=self.prepare_youtube_row(n,files)
            metadata=getattr(self,'anime_metadata',None)
            if metadata and should_exclude_anime(self,self.paths[n]):files=metadata.without_anime(files)
            files,position=page_cards(files,self.histories[n],self.paths[n],position,display_position=display_position)
            if original and not display_position:position=restored_position(files,original,position)
            if hasattr(self,'snapshot_rows'):self.snapshot_rows[n]=False
            if not hasattr(self,'row_labels'):self.row_labels={}
            self.row_labels[n]=label
            if self.episode_browser_context and self.mode=='home':files=[episode_item(x,self.season_title) for x in files]
            if n==0:self.finish_loading('home_ready' if files else 'home_empty_or_unavailable')
            if not hasattr(self,'row_states'):self.row_states={}
            state='ready' if files else 'empty' if label else ''
            self.row_states[n]=state;self.setProperty('rowState'+str(n),state);self.setProperty('rowMessage'+str(n),row_message(label,state,search=bool(getattr(self,'search_state',None))))
            self.window_ready[n]=True;self.rows[n]=files;c=self.getControl(900+n);c.reset();c.addItems([media_item(d) for d in files]);c.setVisible(bool(files))
            self.setProperty('row'+str(n),label if files else label+'  ·  No titles' if label else '')
            if files:
                c.selectItem(min(position,len(files)-1));self.setProperty('notice','Live add-on content  ·  Select a title for details')
                if n==0 and update_selected:self.update(files[min(position,len(files)-1)])
            self.row_navigation()
            if getattr(self,'search_state',None):
                focus=self.getFocusId()
                if focus in (900,901) and not self.rows[focus-900]:self.setFocusId(600)
                return
            if update_selected and all(self.window_ready) and not getattr(self,'startup_idle',False):
                if not self.rows[0] and not self.rows[1]:
                    if getattr(self,'section','')!='My Stuff' and self.row_offset+2<len(self.page_definitions):
                        self.show_row_window(min(self.row_offset+2,len(self.page_definitions)-2),0);return
                    if getattr(self,'search_state',None) or self.episode_browser_context:self.setFocusId(600)
                    else:self.getControl(50).selectItem(len(self.navigation_items)-1);self.set_nav(True,pending_focus=True);self.setFocusId(50)
                elif not self.rows[0] and self.rows[1]:
                    if getattr(self,'section','')!='My Stuff' and getattr(self,'adaptive_browsing',False) and self.row_offset+1<len(self.page_definitions):self.show_row_window(self.row_offset+1,0)
                    else:self.setFocusId(901)

    def update(self,item):
        with self.preview_dispatch_lock:
            self.selected=item;self.setProperty('hasSelection','true');self.dwell=time.monotonic();art=item.get('art',{})
            self.setProperty('hero',art.get('fanart') or art.get('landscape') or art.get('poster',''))
            headline,episode_line=episode_heading(item)
            self.setProperty('title',headline);self.setProperty('episodeLine',episode_line)
            self.setProperty('episodeMeta',episode_card(item)['meta'] if self.episode_browser_context else '')
            self.getControl(251).setHeight(105 if episode_line else 155)
            self.setProperty('allEpisodes','true' if show_identity(item) and not self.episode_browser_context else 'false')
            presentation=title_presentation(item,self.config.get('TitleLogos',True))
            for key,prop in [('meta','meta'),('technical','technicalMeta'),('watch','watchMeta'),('watch_state','watchState'),('logo','titleLogo')]:
                self.setProperty(prop,presentation[key])
            discovery=discovery_result(item)
            self.setProperty('browsable','true' if discovery or item.get('type')=='addon' or item.get('_page_control') else 'false')
            self.getControl(101).setLabel(item['label'] if item.get('_page_control') else 'Open add-on' if item.get('type')=='addon' else discovery['button'] if discovery else 'Episodes' if item.get('filetype')=='directory' and item.get('year') else 'Resume' if episode_line and watch_state(item)['state']=='progress' else 'Play')
            self.getControl(103).controlRight(self.getControl(105 if self.mode=='home' and self.preview_mode!='auto' and getattr(self,'previews_ready',True) else 106 if show_identity(item) and not self.episode_browser_context else 103))
            self.getControl(105).controlRight(self.getControl(103 if self.mode=='details' else 106 if show_identity(item) and not self.episode_browser_context else 105))
            self.display_ratings([] if discovery or is_youtube(item) else rating_badges(item));self.setProperty('plot',item.get('plot') or ('Browse movies and shows from this studio.' if entity_kind(item)=='company' else 'Browse the titles in this collection.' if entity_kind(item)=='collection' else ''))
            if is_youtube(item):
                self.setProperty('hero','' if item.get('filetype')=='directory' else art.get('thumb') or item.get('thumbnail') or art.get('fanart',''))
                self.setProperty('meta',youtube_caption(item));self.setProperty('technicalMeta','');self.setProperty('titleLogo','');self.setProperty('browsable','true' if item.get('filetype')=='directory' else 'false')
                self.getControl(101).setLabel('Open' if item.get('filetype')=='directory' else 'Resume' if watch_state(item)['state']=='progress' else 'Play')
                self.getControl(1250).reset();self.getControl(1251).reset();self.getControl(1252).reset();self.getControl(1254).reset()
            if discovery:
                self.setProperty('meta',search_caption(item));self.setProperty('technicalMeta','');self.setProperty('watchMeta','');self.setProperty('watchState','')
            self.getControl(250).reset()
            if getattr(self,'adaptive_browsing',False):self.getControl(254).reset()
            self.getControl(103).setLabel('Saved' if any(x.get('file')==item.get('file') for x in self.config['Saved']) else '+ My Stuff')
            identity=self.rating_identity(item)
            if identity in self.rating_cache:self.display_ratings(self.rating_cache[identity] or rating_badges(item))

    def rating_identity(self,item):
        if is_youtube(item):return None
        if item.get('_page_control') or discovery_result(item):return None
        query=parse_qs(urlsplit(item.get('file','')).query)
        kind=query.get('tmdb_type',query.get('type',['']))[0]
        identity=query.get('tmdb_id',[item.get('uniqueid',{}).get('tmdb','')])[0]
        if kind in ('movie','tv') and str(identity).isdigit() and 'episode' not in query:return kind,str(identity)
        return None
    def selected_ratings(self):
        item=self.selected or {};identity=self.rating_identity(item)
        if not identity or self.rating_busy or identity in self.rating_cache:return
        key=xbmcaddon.Addon('plugin.video.themoviedb.helper').getSetting('mdblist_apikey')
        if not key:return
        self.rating_busy=True
        def work():
            try:
                kind,media_id=identity;media_type='movie' if kind=='movie' else 'show'
                context=ssl.create_default_context(cafile=str(PROFILE.parent/'addons/script.module.certifi/lib/certifi/cacert.pem'))
                endpoint='https://api.mdblist.com/tmdb/'+media_type+'/'+media_id+'?'+urlencode({'apikey':key})
                request=Request(endpoint,headers={'User-Agent':'Kodi/21.3 BlackLanturnReview','Accept':'application/json'})
                with urlopen(request,timeout=8,context=context) as response:data=json.load(response)
                badges=rating_badges(item,data);self.rating_cache[identity]=badges
                if self.alive and self.rating_identity(self.selected or {})==identity:self.display_ratings(badges)
                event('critic_ratings_loaded',available=bool(badges),sources=[b['icon'] for b in badges],media_type=kind,media_id=media_id)
            except Exception as exc:
                # Exception strings can contain authenticated URLs: never record them.
                self.rating_cache[identity]=[]
                reason=None
                if hasattr(exc,'read'):
                    try:
                        body=json.loads(exc.read(2048));message=body.get('error') or body.get('message')
                        if isinstance(message,str):reason=message.replace(key,'[redacted]')[:180]
                    except (ValueError,TypeError):pass
                event('critic_ratings_unavailable',error_type=type(exc).__name__,status=getattr(exc,'code',None),reason=reason)
            finally:self.rating_busy=False
        threading.Thread(target=work,name='BlackLanturnSelectedRatings',daemon=True).start()
    def load_path(self,n,path,label=None,back=False,position=0):
        if not valid_source(path):return
        if getattr(self,'section','')=='YouTube':
            self.youtube_content_revision=object();self.youtube_job=None;self.youtube_update=None;self.youtube_refreshing=False
        label=provider_page_label(self.paths[n],path,self.getProperty('row'+str(n)),label)
        generation=self.generation
        if not hasattr(self,'path_tokens'):self.path_tokens={}
        if not hasattr(self,'failed_paths'):self.failed_paths={}
        token=self.path_tokens.get(n,0)+1;self.path_tokens[n]=token
        if not hasattr(self,'loading_paths'):self.loading_paths={}
        self.loading_paths[n]=(generation,token);self.stop_preview()
        previous=self.paths[n];previous_position=self.getControl(900+n).getSelectedPosition()
        if not self.rows[n]:self.setProperty('rowState'+str(n),'loading');self.setProperty('rowMessage'+str(n),'Loading provider page…')
        self.setProperty('notice','Loading provider page…')
        cache=getattr(self,'result_cache',None);revision=cache.revision if cache is not None else None
        def current():return self.alive and generation==self.generation and self.path_tokens.get(n)==token and (cache is None or cache.revision==revision)
        def work():
            try:
                if not current():return
                ahead=getattr(self,'page_ahead',None)
                if ahead is not None and page_ahead_eligible(path):
                    ahead.wait((generation,revision,path),current)
                    files=self.page_files(path,current,revision)
                else:
                    params=parse_qs(urlsplit(path).query)
                    metadata=getattr(self,'anime_metadata',None)
                    filtered=metadata is not None and path.startswith(TMDB) and should_exclude_anime(self,path)
                    files=self.result_cache.get('filtered-v1:'+path) if filtered else None
                    if files is not None and needs_fill(path,files,metadata.without_anime,positioned=True):files=None
                    if files is None:
                        files=[] if filtered and upstream_path(provider_path(path))!=provider_path(path) else load_best_matches(params.get('query',[''])[0],lambda part:self.cached_provider_list(part,revision,current),current,workers=2,batch_provider=get_list if getattr(self,'batch_search_enabled',False) else None,cache=cache,revision=revision) if params.get('info')==['blacklanturn_search_matches'] else get_list(provider_path(path))
                        if filtered:files=self.fill_discovery_page(path,files,current)
                with self.preview_dispatch_lock:
                    if current():
                        if not back:self.histories[n].push(previous,previous_position)
                        self.paths[n]=path;self.failed_paths.pop(n,None)
                        # Explicit navigation replaces the old visible owner and its
                        # deferred automatic result, including same-path back/retry.
                        self.row_cache.pop(self.row_offset+n,None)
                        self.apply_row(n,files,label or self.getProperty('row'+str(n)),position,display_position=back)
                        if not getattr(self,'search_state',None) or self.getFocusId() in (0,900,901):self.setFocusId(900+n if self.rows[n] else 600 if self.search_state or self.episode_browser_context else 50)
                        event('page_loaded',row=n,count=len(files),back=back)
            except Exception as exc:
                with self.preview_dispatch_lock:
                    if current():
                        if back and path!=previous:self.histories[n].push(path,position)
                        self.failed_paths[n]={'path':path,'label':label,'back':back,'position':position}
                        self.row_states[n]='error';self.setProperty('rowState'+str(n),'error' if not self.rows[n] else 'ready');self.setProperty('rowMessage'+str(n),row_message(label or self.getProperty('row'+str(n)),'error'))
                        self.setProperty('notice','Page unavailable; current titles remain visible. Open title actions to retry.')
                event('page_error',error_type=type(exc).__name__)
            finally:
                if self.loading_paths.get(n)==(generation,token):self.loading_paths.pop(n,None)
        threading.Thread(target=work,name='BlackLanturnLivePage',daemon=True).start()
    def chosen(self,cid=None):
        cid=cid or self.getFocusId()
        if cid in (900,901):
            n=cid-900;pos=self.getControl(cid).getSelectedPosition()
            if 0<=pos<len(self.rows[n]):return self.rows[n][pos]
        if cid==3100:
            pos=self.getControl(3100).getSelectedPosition()
            return self.related[pos] if 0<=pos<len(self.related) else None
        return self.selected
    def capture_browse(self,include_stack=True):
        fields=('section','mode','navigation_id','active_page','page_definitions','row_offset','row_cache','rows','paths','histories','last_row','return_focus','selected','person_context','episode_browser_context','season_sources','season_title','season_position')
        state={key:getattr(self,key) for key in fields}
        state.update(youtube_identity=getattr(getattr(self,'youtube_connection',None),'identity',''),youtube_tab=getattr(self,'youtube_tab','home'),youtube_query=getattr(self,'youtube_query',''),youtube_pages=copy.deepcopy(getattr(self,'youtube_pages',{})),snapshot_rows=copy.deepcopy(getattr(self,'snapshot_rows',{})),window_ready=list(getattr(self,'window_ready',[True,True])),search_state=copy.deepcopy(getattr(self,'search_state',None)),search_origin=copy.deepcopy(getattr(self,'search_origin',None)),row_states=copy.deepcopy(getattr(self,'row_states',{})),failed_paths=copy.deepcopy(getattr(self,'failed_paths',{})),row_labels=copy.deepcopy(getattr(self,'row_labels',{})))
        if include_stack:state['discovery_stack']=copy.deepcopy(getattr(self,'discovery_stack',[]))
        if self.mode=='details':state['cast_position']=self.getControl(3000).getSelectedPosition()
        state['positions']=[self.getControl(900+n).getSelectedPosition() for n in range(2)]
        state['focus']=self.getFocusId()
        state['properties']={key:self.getProperty(key) for key in ('eyebrow','captionRows','scroll','browseFilters','row0','row1','episodeBrowser','searchBrowser','page','rowState0','rowState1','rowMessage0','rowMessage1','heroCompact','addonBrowser','genreChooser','filmographyBrowser','youtubeBrowser','previewMode','previewsReady')}
        return copy.deepcopy(state)
    def restore_browse(self,state):
        lifetime=getattr(self,'window_lifetime',None)
        def current():return self.alive and lifetime is getattr(self,'window_lifetime',None)
        if not current():return
        connection=getattr(self,'youtube_connection',None)
        if not youtube_resume_allowed(state,getattr(connection,'connected',False),getattr(connection,'identity','')):
            self.generation+=1;self.invalidate_row_results();self.youtube_query=''
            self.section='YouTube' if state.get('section')=='YouTube' and getattr(connection,'connected',False) else 'Home'
            self.navigation_id='youtube' if self.section=='YouTube' else 'home';self.load_section();return False
        self.generation+=1;self.path_tokens={};self.row_window_busy=False
        self.loading_paths={}
        for key,value in state.items():
            if key not in ('positions','focus','properties','snapshot_rows','window_ready'):setattr(self,key,copy.deepcopy(value))
        self.refresh_navigation()
        if not current():return
        if self.episode_browser_context:self.populate_seasons()
        elif getattr(self,'search_state',None):self.populate_search()
        else:self.load_browse_sources()
        if not current():return
        if self.active_page and self.section not in ('Movies','Shows','YouTube') and not self.episode_browser_context and not getattr(self,'search_state',None):
            for n,source in enumerate(self.browse_sources,1):
                if source['id']==self.active_page:self.getControl(600).selectItem(n);break
        for key,value in state['properties'].items():self.setProperty(key,value)
        for n in range(2):
            if not current():return
            self.getControl(900+n).setHeight(360 if self.section=='YouTube' else 344 if state['properties']['captionRows']=='true' else 276)
            if not current():return
            self.apply_row(n,state['rows'][n],state.get('row_labels',{}).get(n,state['properties']['row'+str(n)]),state['positions'][n],update_selected=False)
        if not current():return
        self.row_states=copy.deepcopy(state.get('row_states',{}))
        self.snapshot_rows=copy.deepcopy(state.get('snapshot_rows',{}));self.window_ready=list(state.get('window_ready',[True,True]))
        for key,value in state['properties'].items():self.setProperty(key,value)
        if state['mode']=='details':
            self.details(state['selected'],cast_position=state.get('cast_position'));self.return_focus=state['return_focus']
        elif state['selected']:self.update(state['selected'])
        if not current():return
        focus=state['focus'] if state['focus'] in (101,102,103,105,106,600,610,900,901) else 101 if self.mode=='details' else 900+self.last_row
        self.setFocusId(focus);self.focus_key=None
        if not current():return
        self.restart_pending_rows()
        event('browse_restored',section=self.section,page=self.active_page,mode=self.mode,offset=self.row_offset,positions=state['positions'])
    def refresh_watch_status(self,sync=False,browse_state=None):
        if self.actions_open:return
        self.invalidate_row_results()
        self.generation+=1
        self.row_window_busy=False
        self.actions_open=True;self.stop_preview();generation=self.generation;self.watch_refresh_generation=generation
        # Native selection/focus messages may still be queued after restore_browse.
        focus=browse_state['focus'] if browse_state is not None else self.getFocusId()
        selected=dict(self.selected or {});paths=list(self.paths);rows=[list(r) for r in self.rows]
        positions=list(browse_state['positions']) if browse_state is not None else [self.getControl(900+n).getSelectedPosition() for n in range(2)]
        labels=[getattr(self,'failed_paths',{}).get(n,{}).get('label') or getattr(self,'row_labels',{}).get(n,self.getProperty('row'+str(n))) for n in range(2)]
        youtube_current=self.youtube_request_guard(generation) if self.section=='YouTube' else None
        self.row_cache={};self.setProperty('notice','Refreshing watched status…')
        def work():
            unavailable=False;fresh_selected=None
            try:
                if sync and self.section!='YouTube':
                    xbmc.executebuiltin(watch_sync_command())
                    if not wait_for_helper(lambda:self.alive):unavailable=True
                for n,path in enumerate(paths):
                    if not self.alive or generation!=self.generation:return
                    if not path:continue
                    try:
                        with self.list_lock:
                            if self.section=='YouTube':
                                from youtube_provider import refresh_watch_items
                                files=refresh_watch_items(rows[n],youtube_current)
                                if not youtube_current():return
                            else:
                                filtered=getattr(self,'anime_metadata',None) is not None and should_exclude_anime(self,path)
                                files=[] if filtered and upstream_path(provider_path(path))!=provider_path(path) else get_list(provider_path(path))
                                files=self.fill_discovery_page(path,files,lambda:self.alive and generation==self.generation,refresh=True)
                    except Exception:unavailable=True;continue
                    anchor=rows[n][positions[n]] if 0<=positions[n]<len(rows[n]) else None
                    position=restored_position(files,anchor,positions[n])
                    if self.alive and generation==self.generation:
                        if self.section=='YouTube':self.remember_youtube_watch_items(files)
                        self.apply_row(n,files,labels[n],position,update_selected=False)
                        getattr(self,'failed_paths',{}).pop(n,None)
                        match=next((x for x in files if item_key(x)==item_key(selected)),None)
                        if match:fresh_selected=refreshed_watch_item(selected,match)
                if fresh_selected is None and selected and trakt_command(selected) and not unavailable:
                    params=title_details_params(selected);kind=params.pop('tmdb_type')
                    try:
                        found=get_list(tmdb('details',kind,**params))
                        if found:fresh_selected=refreshed_watch_item(selected,found[0])
                    except Exception:unavailable=True
                if not self.alive or generation!=self.generation:return
                self.update(fresh_selected or selected)
                self.setProperty('notice','Some status data could not refresh; previous information retained' if unavailable else 'Watched status refreshed')
                event('watch_status_refreshed',available=not unavailable,matched=bool(fresh_selected),section=self.section)
            except Exception as exc:
                event('watch_refresh_error',error_type=type(exc).__name__)
            finally:
                if getattr(self,'watch_refresh_generation',None)==generation:self.watch_refresh_generation=None
                self.actions_open=False;self.focus_key=None;self.dwell=time.monotonic()
                if self.alive and generation==self.generation and focus in (101,102,103,105,106,600,900,901,3000,3100):self.setFocusId(focus)
        threading.Thread(target=work,name='BlackLanturnWatchRefresh',daemon=True).start()
    def choose_playback_player(self,item,save_default=False):
        self.stop_preview();self.actions_open=True
        try:
            kind='episode' if episode_identity(item) else 'movie'
            addon=rpc('Addons.GetAddonDetails',{'addonid':'plugin.video.umbrella','properties':['enabled']}).get('result',{}).get('addon',{})
            definitions={}
            for base in ('special://profile/addon_data/plugin.video.themoviedb.helper/players/',
                         'special://home/addons/plugin.video.themoviedb.helper/resources/players/',
                         'special://profile/addon_data/plugin.video.themoviedb.helper/reconfigured_players/'):
                folder=Path(xbmcvfs.translatePath(base))
                for filename in ('umbrella.select.json','umbrella.autoplay.json','umbrella.rescrape.json'):
                    try:definitions[filename]=json.loads((folder/filename).read_text())
                    except (OSError,ValueError):pass
            choices=player_choices(definitions,addon.get('enabled',False),kind)
            if not choices:
                xbmcgui.Dialog().ok('Playback','Umbrella playback choices are unavailable. Check the integration settings.');return
            helper=xbmcaddon.Addon('plugin.video.themoviedb.helper');key=default_setting(kind)
            current=helper.getSetting(key)
            labels=[choice['label']+(' · Current default' if choice['setting']==current else '') for choice in choices]
            selected=xbmcgui.Dialog().select(('Default player for episodes' if kind=='episode' else 'Default player for movies') if save_default else 'Play this title using',labels)
            if selected<0:return
            choice=choices[selected]
            if save_default:
                helper.setSetting(key,choice['setting'])
                if helper.getSetting(key)!=choice['setting']:raise RuntimeError('Default player did not save')
                xbmcgui.Dialog().notification('Default player',choice['label'],time=3000)
            else:
                request=player_path(item,choice['file'])
                if request:
                    self.update(item);self.playback_return=self.capture_browse();self.playback_options=resume_options(item);self.playback_request=request;self.finish()
        finally:self.actions_open=False
    def title_actions(self):
        focus=self.getFocusId()
        failed=any(value=='error' for value in getattr(self,'row_states',{}).values())
        n=focus-900 if focus in (900,901) else getattr(self,'last_row',0)
        histories=getattr(self,'histories',[])
        options=[]
        if getattr(self,'youtube_home_visible',lambda:False)():options.append(('youtube_refresh','Refresh recommendations'))
        if can_choose_genre(self):options.append(('genre','Choose genre…'))
        if n<len(histories) and histories[n].pages:options.append(('previous','Previous page'))
        item=self.chosen(focus) if focus in (101,102,103,105,106,900,901,3100) else None
        if focus in (900,901) and not self.rows[focus-900]:item=None
        if item and item.get('_page_control'):item=None
        discovery=discovery_result(item) if item else None
        command=trakt_command(item) if item and not discovery else None
        player_path=choose_player_path(item) if item and not discovery else None
        if discovery:options.append(('open_discovery',discovery['button']))
        elif item:
            saved=any(x.get('file')==item.get('file') for x in self.config['Saved'])
            options.extend([('details','Details'),('local','Remove from My Stuff on this device' if saved else 'Save to My Stuff on this device')])
            if self.rating_identity(item):options.append(('discover','Discover collections & creator credits'))
            if command:options.append(('trakt','Trakt · Watched, progress & lists'))
            if player_path:options.extend([('player','Play using…'),('default_player','Set default player…')])
            options.append(('refresh','Refresh watched status'))
        if failed:
            options.append(('retry','Retry unavailable lists'))
            if not item:options.append(('settings','Open integration settings'))
        if not options:return
        self.stop_preview();self.actions_open=True
        try:chosen=xbmcgui.Dialog().contextmenu([label for _,label in options])
        finally:self.actions_open=False
        event('title_action_selected',choice=chosen)
        if chosen<0:return
        action=options[chosen][0]
        if action=='youtube_refresh':self.refresh_youtube_recommendations()
        elif action=='genre':
            generation=getattr(self,'generation',0)
            self.browse_source()
            if getattr(self,'generation',0)==generation:self.setFocusId(focus)
        elif action=='previous':
            prior=self.histories[n].pop()
            if prior:self.load_path(n,prior[0],back=True,position=prior[1])
        elif action=='settings':self.settings()
        elif action=='open_discovery':self.open_discovery(discovery)
        elif action=='details':self.details(item)
        elif action=='discover':self.discover_more(item)
        elif action=='local':self.update(item);self.onClick(103)
        elif action=='player':self.choose_playback_player(item)
        elif action=='default_player':self.choose_playback_player(item,save_default=True)
        elif action=='refresh':self.refresh_watch_status(sync=True)
        elif action=='retry':self.retry_lists()
        elif action=='trakt':
            self.actions_open=True;self.set_browse_enabled(False);xbmc.executebuiltin(command)
            def after():
                complete=wait_for_helper(lambda:self.alive)
                self.actions_open=False
                if self.alive:
                    self.set_browse_enabled(True);self.setFocusId(focus)
                    if complete:self.refresh_watch_status()
            threading.Thread(target=after,name='BlackLanturnTraktActions',daemon=True).start()
    def set_browse_enabled(self,enabled):
        for cid in (10,50,15,101,102,103,105,106,600,900,901,3000,3100,700,701,710,711,712,713,720,721):
            self.getControl(cid).setEnabled(enabled)
    def details(self,item,cast_position=None):
        if not item:return
        lifetime=getattr(self,'window_lifetime',None)
        discovery=discovery_result(item)
        if discovery:self.open_discovery(discovery);return
        self.setProperty('captionRows','false')
        self.stop_preview();self.return_focus=self.getFocusId();self.mode='details';self.setProperty('page','details');self.setProperty('scroll','top');self.update(item)
        self.getControl(101).controlDown(self.getControl(3000));self.getControl(103).controlDown(self.getControl(3000));self.getControl(105).controlDown(self.getControl(3000))
        self.getControl(101).controlRight(self.getControl(105 if getattr(self,'previews_ready',True) else 103))
        self.getControl(105).controlLeft(self.getControl(101));self.getControl(105).controlRight(self.getControl(103))
        self.getControl(103).controlLeft(self.getControl(105 if getattr(self,'previews_ready',True) else 101));self.getControl(103).controlRight(self.getControl(106 if show_identity(item) and not self.episode_browser_context else 103))
        self.getControl(106).controlDown(self.getControl(3000));self.getControl(106).controlLeft(self.getControl(103))
        self.getControl(3000).reset();self.getControl(3100).reset();self.related=[];self.setFocusId(101)
        source_key=item.get('file');self.setProperty('notice','Loading details…')
        def current():return self.alive and lifetime is getattr(self,'window_lifetime',None) and self.mode=='details' and (self.selected or {}).get('file')==source_key
        def work():
            try:
                if not current():return
                params=title_details_params(item);kind=params.pop('tmdb_type');identity=params.get('tmdb_id')
                detail=item
                if identity:
                    found=get_list(tmdb('details',kind,**params))
                    if found:detail=merge_title_details(item,found[0])
                if not current():return
                self.update(detail)
                if not current():return
                cast=[];self.cast_people=[]
                people=get_list(tmdb('cast',kind,tmdb_id=identity)) if identity else []
                if not current():return
                roles={p.get('name',''):p.get('role','') for p in detail.get('cast',[])}
                for person in people:
                    if not current():return
                    name=person.get('title') or person.get('label','')
                    if not person_identity(person.get('file','')):continue
                    art=person.get('art',{})
                    li=xbmcgui.ListItem(label=name,label2=roles.get(name,''));li.setArt({'poster':art.get('poster') or art.get('thumb') or person.get('thumbnail','')});cast.append(li);self.cast_people.append(person)
                if not current():return
                self.getControl(3000).addItems(cast)
                if cast_position is not None and cast:
                    self.getControl(3000).selectItem(min(cast_position,len(cast)-1));self.setFocusId(3000)
                self.setProperty('notice','Director: '+', '.join(detail.get('director',[])) if detail.get('director') else 'Live title details')
                event('details_loaded',cast=len(cast),rating=bool(rating_line(detail)))
                if identity:
                    related=get_list(tmdb('similar',kind,tmdb_id=identity))
                    if current():
                        self.related=related;self.getControl(3100).addItems([media_item(d) for d in related])
            except Exception as exc:
                if current():event('details_error',error=str(exc));self.setProperty('notice','Available title details shown; additional metadata unavailable')
        threading.Thread(target=work,name='BlackLanturnLiveDetails',daemon=True).start()
    def browse_all_episodes(self):
        item=self.selected or {};identity=show_identity(item)
        if not identity:return
        self.stop_preview()
        self.episode_browser_context={'item':dict(item),'mode':self.mode,'last_row':self.last_row,'rows':[list(r) for r in self.rows],'paths':list(self.paths),'histories':self.histories,'labels':[self.getProperty('row'+str(n)) for n in range(2)],'positions':[self.getControl(900+n).getSelectedPosition() for n in range(2)],'page_definitions':self.page_definitions,'row_offset':self.row_offset,'row_cache':self.row_cache,'active_page':self.active_page,'eyebrow':self.getProperty('eyebrow'),'captionRows':self.getProperty('captionRows'),'snapshot_rows':dict(getattr(self,'snapshot_rows',{})),'window_ready':list(getattr(self,'window_ready',[True,True]))}
        self.mode='home';self.setProperty('page','home');self.setProperty('scroll','top');self.setProperty('captionRows','true');self.setProperty('browseFilters','false');self.setProperty('allEpisodes','false');self.setProperty('episodeBrowser','true')
        for cid in (900,901):self.getControl(cid).setHeight(344)
        title=item.get('showtitle') or item.get('tvshowtitle') or item.get('title','Show')
        self.season_title=title;self.season_sources=[];self.season_position=0
        self.selected=None
        self.setProperty('eyebrow',title+' / ALL EPISODES')
        self.generation+=1;generation=self.generation;self.setProperty('notice','Loading seasons…')
        self.getControl(600).reset()
        for n in range(2):self.rows[n]=[];self.getControl(900+n).reset();self.setProperty('row'+str(n),'')
        def work():
            try:
                with self.list_lock:files=get_list(tmdb('seasons','tv',tmdb_id=identity))
                if not self.alive or generation!=self.generation:return
                self.season_sources=season_entries(files)
                if not self.season_sources:self.setProperty('notice','No seasons available from this integration. Back returns to your title.');self.setFocusId(101);return
                self.season_position=next((n for n,s in enumerate(self.season_sources) if s['season']==item.get('season')),0)
                self.populate_seasons();self.select_episode_season(self.season_position)
            except Exception as exc:
                if self.alive and generation==self.generation:self.setProperty('notice','Seasons could not load. Back returns to your title.')
                event('seasons_unavailable',error_type=type(exc).__name__)
        threading.Thread(target=work,name='BlackLanturnSeasons',daemon=True).start()
        event('all_episodes_opened',tmdb_id=identity)
    def populate_seasons(self):
        self.setProperty('genreChooser','false')
        control=self.getControl(600);control.reset()
        for n,source in enumerate(self.season_sources):
            li=xbmcgui.ListItem(label=source['label']);li.setProperty('active','true' if n==self.season_position else 'false');control.addItem(li)
        if self.season_sources:control.selectItem(min(self.season_position,len(self.season_sources)-1))
    def select_episode_season(self,position=None):
        if not self.episode_browser_context:return
        control=self.getControl(600);position=control.getSelectedPosition() if position is None else position
        if not 0<=position<len(self.season_sources):return
        self.stop_preview();self.selected=None;self.season_position=position
        for n in range(len(self.season_sources)):control.getListItem(n).setProperty('active','true' if n==position else 'false')
        control.selectItem(position)
        self.mode='home';self.setProperty('page','home');self.setProperty('episodeBrowser','true');self.setProperty('captionRows','true')
        source=self.season_sources[position]
        self.set_rows([{'label':'Episodes · '+source['label'],'path':source['path']}])
    def restore_episode_browser(self):
        context=self.episode_browser_context;self.episode_browser_context=None;self.generation+=1
        self.setProperty('episodeBrowser','false');self.season_sources=[];self.season_title='';self.season_position=0
        if self.search_state:self.populate_search()
        else:self.load_browse_sources()
        for key in ('paths','histories','page_definitions','row_offset','row_cache','active_page','last_row'):setattr(self,key,context[key])
        self.setProperty('captionRows',context['captionRows']);self.setProperty('eyebrow',context['eyebrow']);self.setProperty('browseFilters','true' if self.section in ('Movies','Shows') and not self.search_state and not self.discovery_stack else 'false')
        for n in range(2):
            self.getControl(900+n).setHeight(344 if context['captionRows']=='true' else 276)
            self.apply_row(n,context['rows'][n],context['labels'][n],context['positions'][n])
        if context['mode']=='details':
            self.details(context['item']);self.return_focus=900+context['last_row']
        else:self.update(context['item']);self.setFocusId(900+context['last_row'])
        self.snapshot_rows=copy.deepcopy(context.get('snapshot_rows',{}));self.window_ready=list(context.get('window_ready',[True,True]));self.path_tokens={};self.row_window_busy=False
        self.restart_pending_rows()
        event('all_episodes_returned')
    def filmography(self):
        position=self.getControl(3000).getSelectedPosition()
        if not 0<=position<len(self.cast_people):return
        discovery=discovery_result(self.cast_people[position])
        if discovery:self.open_discovery(discovery)
    def refresh_preview_setup(self):
        ready=False
        try:
            addon=xbmcaddon.Addon('plugin.video.youtube')
            enabled=rpc('Addons.GetAddonDetails',{'addonid':'plugin.video.youtube','properties':['enabled']}).get('result',{}).get('addon',{}).get('enabled',False)
            fields={key:addon.getSetting(key) for key in ('youtube.api.key','youtube.api.id','youtube.api.secret')}
            path=PROFILE/'addon_data/plugin.video.youtube/api_keys.json'
            try:store=json.loads(path.read_text()) if path.is_file() else {}
            except (OSError,ValueError):store={}
            ready=preview_configured(fields,store,enabled=enabled)
        except Exception:pass
        self.previews_ready=ready;self.setProperty('previewsReady','true' if ready else 'false')
    def preview(self,automatic=False):
        input_generation=getattr(self,'input_generation',0)
        if automatic and time.monotonic()-self.dwell<self.config.get('PreviewDelay',5):return
        if not getattr(self,'previews_ready',True) and not youtube_video_id(self.selected or {}):return
        item=dict(self.selected or {})
        if not item:return
        selection_generation=self.preview_generation
        if self.player.isPlaying() and not self.owned_preview:
            now=time.monotonic()
            if now-getattr(self,'preview_foreign_checked',0)<1:return
            self.preview_foreign_checked=now
            cleared=clear_stale_preview(rpc)
            if cleared:event('stale_trailer_released')
            if not cleared or self.player.isPlaying():self.setProperty('notice','Preview paused while another video is playing');return
        event('preview_lookup_started',dwell_seconds=round(time.monotonic()-self.dwell,2),configured_delay=self.config.get('PreviewDelay',5))
        self.stop_preview()
        with self.preview_dispatch_lock:
            if not self.alive or self.nav or getattr(self,'input_generation',0)!=input_generation or automatic and time.monotonic()-self.dwell<self.config.get('PreviewDelay',5) or self.preview_generation!=selection_generation+1 or (self.selected or {}).get('file')!=item.get('file'):return
            self.owned_preview=True;self.preview_input_generation=input_generation;self.preview_key=item.get('file');token=self.preview_generation
        self.preview_requested_at=time.monotonic();self.preview_playing=False
        self.setProperty('preview','loading');self.setProperty('notice','Finding previews…')
        def work():
            direct=youtube_preview_path(item)
            if direct:
                with self.preview_dispatch_lock:
                    if not self.alive or self.nav or token!=self.preview_generation or getattr(self,'input_generation',0)!=input_generation or (self.selected or {}).get('file')!=item.get('file'):return
                    attempts=PreviewAttempts([direct]);url=attempts.start(time.monotonic());self.preview_attempts=attempts
                self.play_preview_candidate(url,token,attempts);return
            identity=self.rating_identity(item);key=item.get('file')
            names=('showtitle',) if item.get('showtitle') else ('title','originaltitle')
            aliases=tuple(dict.fromkeys(str(item[k]) for k in names if item.get(k))) or (item.get('label',''),)
            helper_profile=Path(xbmcvfs.translatePath('special://profile/'))/'addon_data/plugin.video.themoviedb.helper'
            if identity:aliases=tuple(dict.fromkeys(aliases+tuple(cached_title_aliases(helper_profile,identity))))
            language=self.config.get('PreviewLanguage','en');cache_key=(key,identity,language,aliases,'verified-title-1')
            def current():return self.alive and not self.nav and token==self.preview_generation and self.owned_preview and getattr(self,'input_generation',0)==input_generation and (self.selected or {}).get('file')==key
            if not current():return
            cached=self.preview_cache.get(cache_key)
            candidates=cached[1] if cached and time.monotonic()-cached[0]<300 else None
            if candidates is None:
                videos=[]
                if identity:
                    try:videos=get_list(tmdb('videos',identity[0],tmdb_id=identity[1]))
                    except Exception:event('preview_candidates_unavailable')
                if not current():return
                metadata=cached_video_metadata(helper_profile,identity) if identity else {}
                ranked=preview_candidates(item.get('trailer',''),videos,metadata=metadata,preferred_language=language)
                candidates=self.preview_title_verifier.filter(ranked,aliases,valid=current)
                if not current():return
                if candidates:
                    self.preview_cache[cache_key]=(time.monotonic(),candidates)
                    while len(self.preview_cache)>128:self.preview_cache.pop(next(iter(self.preview_cache)))
                else:self.preview_cache.pop(cache_key,None)
                event('preview_identity_screened',candidates=len(ranked),approved=len(candidates))
            with self.preview_dispatch_lock:
                if not current():return
                attempts=PreviewAttempts(candidates);url=attempts.start(time.monotonic());self.preview_attempts=attempts
            event('preview_candidates_loaded',count=len(candidates))
            self.play_preview_candidate(url,token,attempts)
        threading.Thread(target=work,name='BlackLanturnPreviewCandidates',daemon=True).start()
    def play_preview_candidate(self,url,token=None,attempts=None):
        token=self.preview_generation if token is None else token
        attempts=self.preview_attempts if attempts is None else attempts
        request=None
        def current():
            return self.alive and self.owned_preview and token==self.preview_generation and getattr(self,'input_generation',0)==getattr(self,'preview_input_generation',0) and attempts is self.preview_attempts and attempts is not None and (request is None or getattr(self,'preview_resolution',None) is request)
        with self.preview_dispatch_lock:
            if not current():return
            request=object();self.preview_resolution=request
            if self.preview_dispatched:
                self.preview_dispatched=False
                xbmc.executebuiltin('PlayerControl(Stop)',False)
                # Drain the main-thread message after Stop through JSON-RPC,
                # which releases Python's GIL while waiting. Reflected skin
                # controls can otherwise hold the GIL in setWidth while Kodi
                # waits for a Python YouTube proxy response during CloseFile.
                rpc('XBMC.GetInfoLabels',{'labels':['System.CurrentControlId']})
            self.cancel_preview_bar_scan();self.preview_url=url
        if not url:
            with self.preview_dispatch_lock:
                if not current():return
                self.restore_preview_viewmode();self.restore_preview_renderer();self.owned_preview=False;self.preview_dispatched=False;self.setProperty('preview','idle')
                self.setProperty('notice','No working preview available; artwork retained');event('preview_exhausted')
            return
        def work():
            try:
                prepared=resolve_preview(url,current)
                with self.preview_dispatch_lock:
                    if not current():return
                    if prepared is None:
                        self.player.failed=True;return
                    self.restore_preview_viewmode()
                    if not current():return
                    self.player.failed=False;self.preview_playing=False
                    self.preview_requested_at=time.monotonic();self.setProperty('preview','loading');self.setProperty('notice','Loading preview…')
                    # Decoder preparation and cancellation/restoration are one
                    # ownership transition; neither may overtake the other.
                    acquired=self.preview_renderer.acquire()
                    if not current():
                        if not self.owned_preview:self.restore_preview_renderer()
                        return
                    if not acquired:
                        self.player.failed=True;event('preview_renderer_unavailable');return
                    if not prepared.publish():return
                    # Only a resolved stream enters Kodi's playback queue. A
                    # cancelled network lookup cannot open a late plug-in job.
                    self.preview_dispatched=True;self.player.play(prepared.path,listitem=prepared.listitem,windowed=True)
                    event('trailer_requested',attempt=attempts.index+1,video_id=parse_qs(urlsplit(url).query).get('video_id',[''])[0])
            except Exception as exc:
                with self.preview_dispatch_lock:
                    if current():self.player.failed=True
                event('preview_resolution_failed',error_type=type(exc).__name__)
        threading.Thread(target=work,name='BlackLanturnPreviewResolve',daemon=True).start()
    def choose_source(self,addon=None):
        names=['TMDbHelper','Umbrella'];ids=['plugin.video.themoviedb.helper','plugin.video.umbrella']
        if addon:path='plugin://'+addon['addonid']+'/';label=addon.get('name',addon['addonid'])
        else:
            selected=xbmcgui.Dialog().select('Choose an integrated add-on',names)
            if selected<0:return None
            path='plugin://'+ids[selected]+'/';label=names[selected]
        stack=[]
        while self.alive:
            try:files=get_list(path)
            except Exception:
                xbmcgui.Dialog().ok('List unavailable','Open this add-on’s settings to complete its setup.');return None
            folders=[f for f in files if f.get('filetype')=='directory']
            options=['Use this list as the source']+(['Back'] if stack else [])+[f.get('label','Folder') for f in folders]
            choice=xbmcgui.Dialog().select('List source: '+label,options)
            if choice<0:return None
            if choice==0:return {'label':label,'path':path}
            if stack and choice==1:path,label=stack.pop();continue
            item=folders[choice-1-(1 if stack else 0)];stack.append((path,label));path=item['file'];label=item.get('label','List')
    def manage_rows(self):
        sections=['Home','Movies','Shows','Add-ons']
        choice=xbmcgui.Dialog().select('Configure rows for',sections)
        if choice<0:return
        section=sections[choice]
        rows=self.config[section]
        self.edit_rows(rows,section);self.load_section()
    def edit_rows(self,rows,title):
        while self.alive:
            choice=xbmcgui.Dialog().select(title+' rows',[r['label']+('  ·  Hidden' if not r.get('enabled',True) else '') for r in rows]+['Add row'])
            if choice<0:return
            if choice==len(rows):
                source=self.choose_source()
                if not source:continue
                name=xbmcgui.Dialog().input('Row name',defaultt=source['label'])
                if name:source['label']=name;source['enabled']=True;rows.append(source)
            else:
                action=xbmcgui.Dialog().select(rows[choice]['label'],['Change source','Rename','Move up','Move down','Hide row' if rows[choice].get('enabled',True) else 'Show row','Remove row'])
                if action==0:
                    source=self.choose_source()
                    if source:source['label']=rows[choice]['label'];source['enabled']=rows[choice].get('enabled',True);rows[choice]=source
                elif action==1:
                    name=xbmcgui.Dialog().input('Row name',defaultt=rows[choice]['label'])
                    if name:rows[choice]['label']=name
                elif action in (2,3):
                    target=choice+(-1 if action==2 else 1)
                    if 0<=target<len(rows):rows[choice],rows[target]=rows[target],rows[choice]
                elif action==4:rows[choice]['enabled']=not rows[choice].get('enabled',True)
                elif action==5:rows.pop(choice)
            self.save()
    def categories(self,edit=False,collection='Categories'):
        cats=self.config[collection]
        while self.alive:
            choice=xbmcgui.Dialog().select('Configure '+collection,[c['label']+'  ·  '+c.get('section','Both')+('  ·  Hidden' if not c.get('enabled',True) else '') for c in cats]+['Add page'])
            if choice<0:break
            if choice==len(cats):
                name=xbmcgui.Dialog().input('Page name')
                if not name:continue
                section=xbmcgui.Dialog().select('Show page under',['Movies','Shows','Both'])
                if section<0:continue
                from uuid import uuid4
                page={'id':uuid4().hex,'label':name,'section':['Movies','Shows','Both'][section],'enabled':True,'rows':[]};cats.append(page);self.save();self.edit_rows(page['rows'],name)
            else:
                page=cats[choice]
                action=xbmcgui.Dialog().select(page['label'],['Manage rows','Rename','Show page under','Move up','Move down','Hide page' if page.get('enabled',True) else 'Show page','Remove page'])
                if action==0:self.edit_rows(page['rows'],page['label'])
                elif action==1:
                    name=xbmcgui.Dialog().input('Page name',defaultt=page['label'])
                    if name:page['label']=name
                elif action==2:
                    section=xbmcgui.Dialog().select('Show page under',['Movies','Shows','Both'],preselect=['Movies','Shows','Both'].index(page.get('section','Both')))
                    if section>=0:page['section']=['Movies','Shows','Both'][section]
                elif action in (3,4):
                    target=choice+(-1 if action==3 else 1)
                    if 0<=target<len(cats):cats[choice],cats[target]=cats[target],cats[choice]
                elif action==5:page['enabled']=not page.get('enabled',True)
                elif action==6:cats.pop(choice)
                self.save()
        self.load_section()
    def load_browse_sources(self):
        if self.section=='YouTube':self.populate_youtube_tabs();return
        self.browse_sources=collection_pages(self.config,self.section) if self.section in ('Movies','Shows') else [{'id':'addons-'+str(n),'label':row['label'],'rows':[row]} for n,row in enumerate(self.config.get('Add-ons',[])) if row.get('enabled',True)] if self.section=='Add-ons' else []
        c=self.getControl(600);c.reset()
        self.setProperty('genreChooser','true' if self.section in ('Movies','Shows') else 'false')
        if self.section in ('Movies','Shows'):
            current=next((p['label'] for p in self.browse_sources if p['id']==self.active_page),'All')
            item=xbmcgui.ListItem(label='Choose genre · '+current)
            item.setProperty('genreChooser','true');item.setProperty('active','true');c.addItems([item])
        else:
            c.addItems([xbmcgui.ListItem(label='All')]+[xbmcgui.ListItem(label=x['label']) for x in self.browse_sources])
            c.getListItem(0).setProperty('active','true')
        self.setProperty('browseFilters','true' if self.browse_sources else 'false')
        self.getControl(900).controlUp(self.getControl(600 if self.browse_sources or getattr(self,'search_state',None) else 101))
    def browse_source(self):
        if self.section=='YouTube':self.select_youtube_tab();return
        if self.section in ('Movies','Shows'):
            self.actions_open=True;self.stop_preview()
            try:selected=choose_genre(self.section,self.browse_sources,self.active_page)
            finally:self.actions_open=False
            if selected is None:return
            index=0 if selected=='' else next((n for n,p in enumerate(self.browse_sources,1) if p['id']==selected),-1)
        else:index=self.getControl(600).getSelectedPosition()
        if index==0:self.load_section();self.setFocusId(600);return
        if not 0<index<=len(self.browse_sources):return
        source=self.browse_sources[index-1];self.active_page=source['id'];self.stop_preview();self.mode='home';self.setProperty('page','home');self.setProperty('scroll','top')
        if self.section in ('Movies','Shows'):self.load_browse_sources()
        else:
            for n in range(len(self.browse_sources)+1):self.getControl(600).getListItem(n).setProperty('active','true' if n==index else 'false')
        self.setProperty('eyebrow',self.section.upper()+' / '+source['label'].upper());self.set_rows(source['rows'] if self.section=='Add-ons' else page_rows(self.config,self.section,self.active_page));self.setFocusId(600)
        event('browse_source_selected',section=self.section,label=source['label'],rows=len(self.page_definitions))
    def genres(self):
        kind='tv' if self.section=='Shows' else 'movie'
        try:items=get_list(tmdb('genres',kind))
        except Exception:xbmcgui.Dialog().notification('Genres','Provider genres could not load');return
        choice=xbmcgui.Dialog().select('Choose genre',['All']+[x.get('label','') for x in items])
        if choice<0:return
        if choice==0:self.load_section();return
        item=items[choice-1];self.setProperty('genreLabel',item['label']);self.load_path(0,item['file'],item['label'])
    def rating_order(self):
        sources=list(self.config.get('RatingSources',DEFAULT_RATINGS));names=dict(RATING_OPTIONS)
        if not sources:
            xbmcgui.Dialog().ok('Rating order','Enable at least one source under Rating sources first.');return
        position=0
        while self.alive:
            choice=xbmcgui.Dialog().select('Rating order: left to right',[names.get(s,s) for s in sources],preselect=position)
            if choice<0:break
            action=xbmcgui.Dialog().select(names.get(sources[choice],sources[choice]),['Move left','Move right'])
            if action<0:position=choice;continue
            target=choice+(-1 if action==0 else 1)
            if 0<=target<len(sources):
                sources[choice],sources[target]=sources[target],sources[choice]
                self.config['RatingSources']=list(sources);self.save();position=target
            else:position=choice
        if self.selected:self.update(self.selected)
    def settings(self,lifetime=None):
        if lifetime is None:lifetime=getattr(self,'window_lifetime',None)
        def current():return self.alive and lifetime is getattr(self,'window_lifetime',None)
        if not current():return
        self.settings_open=True;category,row=self.backend_position
        try:
            while current():
                dialog=BackendSettings('BackendSettings.xml',str(ROOT),'Default','1080i')
                dialog.config=self.config;dialog.preview_mode=self.preview_mode;dialog.category=category;dialog.row=row
                dialog.initial_focus=self.backend_focus
                dialog.handler=lambda action:self.run_setting(action) if current() else None
                dialog.doModal()
                if not current():return
                action=dialog.result;category,row=dialog.category,dialog.row
                self.backend_position=(category,row);del dialog
                if action is None:return
                event('backend_action',action=action)
                if action.startswith('kodi:'):
                    self.core_settings_request={'target':action[5:],'category':category,'row':row,'section':self.section}
                    self.finish();return
                if action.startswith('addon:'):
                    self.run_setting(action);continue
                self.backend_focus=200
                self.run_setting(action)
        finally:
            if lifetime is getattr(self,'window_lifetime',None):self.settings_open=False
    def run_setting(self,action):
        event('backend_action',action=action)
        if action.startswith('addon:'):
            xbmcaddon.Addon(action[6:]).openSettings()
            if action=='addon:plugin.video.youtube':
                self.refresh_preview_setup();self.refresh_youtube_connection(force=True);self.row_navigation()
        elif action=='sidebar':self.sidebar_settings()
        elif action=='status_display':self.status_options()
        elif action=='title_logos':
            self.config['TitleLogos']=not self.config.get('TitleLogos',True);self.save()
            if self.selected:self.update(self.selected)
        elif action=='rows':self.manage_rows()
        elif action in ('genres','categories'):self.categories(edit=True,collection='Genres' if action=='genres' else 'Categories')
        elif action=='rating_order':self.rating_order()
        elif action=='ratings':
            current=self.config.get('RatingSources',DEFAULT_RATINGS)
            chosen=xbmcgui.Dialog().multiselect('Show these rating sources',[x[1] for x in RATING_OPTIONS],preselect=[n for n,x in enumerate(RATING_OPTIONS) if x[0] in current])
            if chosen is not None:
                self.config['RatingSources']=update_rating_sources(current,[RATING_OPTIONS[n][0] for n in chosen]);self.save()
                if self.selected:self.update(self.selected)
        elif action=='youtube_previews':
            self.stop_preview();self.config['YouTubePreviews']=not self.config.get('YouTubePreviews',True);self.save()
            if self.section=='YouTube':self.setProperty('previewMode','auto' if self.config['YouTubePreviews'] else 'manual')
        elif action=='preview_language':
            chosen=xbmcgui.Dialog().select('Preferred preview language',['English first, other languages as fallback','Provider order'],preselect=0 if self.config.get('PreviewLanguage','en')=='en' else 1)
            if chosen>=0:
                self.stop_preview();self.config['PreviewLanguage']='en' if chosen==0 else '';self.preview_cache={};self.save()
        elif action=='preview_delay':
            delays=[3,5,8,10];current=self.config.get('PreviewDelay',5)
            chosen=xbmcgui.Dialog().select('Preview starts after staying on a title',[str(x)+' seconds' for x in delays],preselect=delays.index(current) if current in delays else 1)
            if chosen>=0:self.config['PreviewDelay']=delays[chosen];self.save();self.dwell=time.monotonic()
        elif action=='preview_mode':
            self.stop_preview();self.preview_mode='auto' if self.preview_mode=='manual' else 'manual'
            self.setProperty('previewMode',self.preview_mode);self.config['PreviewMode']=self.preview_mode;self.save()
        elif action=='integration_status':self.integration_status()
        elif action=='help':
            xbmcgui.Dialog().textviewer('BlackLanturn · Help',(ROOT/'HELP.txt').read_text(encoding='utf-8'))
        elif action=='clear_search':
            self.config.pop('SearchQuery',None);self.save()
            self.setProperty('notice','Saved search cleared on this device')
        elif action=='startup_preview':
            dialog=LoadingPreview('LoadingPreview.xml',str(ROOT),'Default','1080i');dialog.doModal();del dialog
        elif action=='recovery':
            from live_recovery import return_to_previous_skin
            self.finish();return_to_previous_skin()
    def monitor(self,lifetime=None):
        if lifetime is None:lifetime=getattr(self,'window_lifetime',None)
        def current():return self.alive and lifetime is getattr(self,'window_lifetime',None)
        caption_checked=0
        while current() and not xbmc.Monitor().abortRequested():
            try:
                if not current():return
                skin=xbmc.getSkinDir()
                if not current():return
                if skin!=self.owner_skin:self.alive=False;return
                if self.settings_open or self.actions_open:
                    time.sleep(.08);continue
                self.refresh_youtube_connection()
                if not current():return
                if hasattr(self,'apply_youtube_updates') and self.apply_youtube_updates():
                    # Native list binding/select are queued GUI messages. Do not
                    # observe the temporary selection-zero state as preview intent.
                    time.sleep(.08);continue
                self.apply_nav_width()
                if not current():return
                pending=getattr(self,'search_row_step',None)
                if pending and (pending['generation']!=self.generation or pending['epoch']!=getattr(self,'input_generation',0)):self.search_row_step=None
                if getattr(self,'loading_paths',{}) or getattr(self,'search_row_step',None) or self.getProperty('loading')=='true':
                    time.sleep(.08);continue
                if time.monotonic()-caption_checked>=1:
                    screen=gui_labels(['System.ScreenWidth','System.ScreenHeight'])
                    width=screen['System.ScreenWidth'];height=screen['System.ScreenHeight']
                    if not current():return
                    fit=str(caption_fit_step(width,height))
                    if self.getProperty('captionFitStep')!=fit:
                        self.setProperty('captionFitStep',fit)
                        event('caption_fit',width=width,height=height,step=fit)
                    caption_checked=time.monotonic()
                focus=self.getFocusId();key=(focus,self.getControl(focus).getSelectedPosition()) if focus in (900,901,3100) else (focus,0)
                if not current():return
                if getattr(self,'startup_idle',False) and focus!=5:
                    self.startup_idle=False;self.setProperty('startupIdle','false')
                    event('startup_browsing_entered',focus=focus)
                compact='true' if self.mode=='home' and (getattr(self,'fixed_hero',False) or self.row_offset>0 or self.getProperty('captionRows')=='true') else 'false'
                if self.getProperty('heroCompact')!=compact:self.setProperty('heroCompact',compact)
                self.sync_nav_focus(focus)
                if not current():return
                if key!=self.focus_key:
                    self.focus_key=key
                    if focus in (900,901):
                        self.last_row=focus-900;self.return_focus=focus;self.setProperty('scroll',('creditShows' if focus==901 else 'credits') if self.getProperty('captionRows')=='true' else ('down' if focus==901 else 'top'));item=self.chosen(focus)
                        if item:
                            self.stop_preview()
                            if not current():return
                            self.update(item)
                    elif focus in (3000,3100):self.setProperty('scroll','down' if focus==3000 else 'related')
                    # Hovering a visible button must not move it away before the
                    # click arrives. Directional navigation still reveals the hero.
                    elif focus in (101,102,103,105,106,600) and not self.mouse:self.setProperty('scroll','top')
                arrow=self.hover.tick(time.monotonic(),focus,self.mouse)
                if arrow is not None:self.arrow(arrow)
                if not current():return
                if (getattr(self,'previews_ready',True) or youtube_video_id(self.selected or {})) and not getattr(self,'startup_idle',False) and automatic_preview(getattr(self,'config',{}),getattr(self,'section',''),self.preview_mode) and self.mode=='home' and not self.episode_browser_context and not self.nav and focus in (900,901) and self.selected and (youtube_video_id(self.selected) or self.rating_identity(self.selected)) and time.monotonic()-self.dwell>=self.config.get('PreviewDelay',5) and self.preview_key!=self.selected.get('file'):self.preview(automatic=True)
                if getattr(self,'page_ahead',None) is not None:self.prefetch_next_page()
                if getattr(self,'section','')=='YouTube':self.prefetch_youtube_row()
                if getattr(self,'prefetch_trial',False):self.prefetch_next_row()
                if not self.nav and time.monotonic()-self.dwell>=1.2:self.selected_ratings()
                attempts=self.preview_attempts;preview_token=self.preview_generation
                if self.owned_preview and attempts:
                    playing=self.player.isPlayingVideo();failed=self.player.failed
                    self.player.failed=False
                    next_url=attempts.tick(time.monotonic(),playing,error=failed)
                    if preview_token!=self.preview_generation or attempts is not self.preview_attempts:continue
                    if next_url:
                        event('preview_fallback',attempt=attempts.index+1,reason='playback_error' if failed else 'start_timeout')
                        self.play_preview_candidate(next_url,preview_token,attempts)
                    elif playing and not self.preview_playing:
                        viewmode=rpc('Player.GetViewMode').get('result',{'viewmode':'normal'})
                        if not current():return
                        self.preview_viewmode=viewmode
                        stream=rpc('Player.GetProperties',{'playerid':1,'properties':['currentvideostream']}).get('result',{}).get('currentvideostream',{})
                        if not current():return
                        aspect=rpc('XBMC.GetInfoLabels',{'labels':['VideoPlayer.VideoAspect']}).get('result',{}).get('VideoPlayer.VideoAspect','')
                        if not current():return
                        fit=preview_fill_viewmode(stream,aspect,self.getProperty('heroCompact')=='true' and self.mode=='home')
                        result=rpc('Player.SetViewMode',{'viewmode':fit})
                        if not current():return
                        self.preview_playing=True;self.setProperty('preview','playing');self.setProperty('notice','')
                        self.start_preview_bar_scan(stream,aspect,fit)
                        event('trailer_playing',total=self.player.getTotalTime(),hero_fill=result.get('result')=='OK',preview_fit=fit,attempt=attempts.index+1)
                    elif attempts.finished:
                        self.cancel_preview_bar_scan()
                        self.restore_preview_viewmode();self.restore_preview_renderer();self.owned_preview=False;self.setProperty('preview','idle')
                        self.setProperty('notice','Preview ended' if self.preview_playing else 'No working preview available; artwork retained')
                        event('trailer_finished',played=self.preview_playing)
                    elif playing and self.preview_playing:self.sample_preview_bar_scan()
            except RuntimeError:
                if not current():return
            time.sleep(.08)
    def arrow(self,cid):
        if cid in (700,701):
            if self.mode=='home' and getattr(self,'adaptive_browsing',False):
                if getattr(self,'search_state',None) and self.mouse:
                    self.step_search_rows(1 if cid==701 else -1,focus_target=cid);self.setFocusId(cid);return
                if self.shift_rows(1 if cid==701 else -1,0):
                    if self.mouse:self.setFocusId(cid)
                    return
                self.setProperty('scroll','top');return
            stops=('top','down','related') if self.mode=='details' else ('top','credits','creditShows') if self.getProperty('captionRows')=='true' else ('top','down')
            current=self.getProperty('scroll')
            if self.mode=='home' and ((cid==701 and current=='down') or (cid==700 and current=='top')):
                if self.shift_rows(1 if cid==701 else -1,1 if cid==701 else 0):return
            index=stops.index(current) if current in stops else 0
            self.setProperty('scroll',stops[max(0,min(len(stops)-1,index+(-1 if cid==700 else 1)))])
            event('mouse_page_scroll',page=self.mode,anchor=self.getProperty('scroll'))
            return
        if self.mode=='details':
            control=3000 if cid in (720,721) else 3100
            items=self.cast_people if control==3000 else self.related
        else:
            control=900+self.last_row;items=self.rows[self.last_row]
        if not items:return
        ctrl=self.getControl(control);pos=ctrl.getSelectedPosition()
        pos=max(0,min(len(items)-1,pos+(-1 if cid in (710,712,720) else 1)))
        ctrl.selectItem(pos)
        if self.mode=='home':self.update(items[pos])
        event('mouse_row_scroll',page=self.mode,control=control,position=pos)
    def retry_lists(self):
        for n,path in enumerate(list(self.paths)):
            if path and self.row_states.get(n)=='error':
                self.setProperty('rowState'+str(n),'loading');self.setProperty('rowMessage'+str(n),'Retrying this list…')
                failed=self.failed_paths.get(n)
                if failed:
                    if failed['back'] and failed['path']!=self.paths[n]:self.histories[n].pop()
                    self.load_path(n,**failed)
                else:self.load_path(n,path,back=True,position=self.getControl(900+n).getSelectedPosition())
    def discover_more(self,item):
        self.actions_open=True
        try:
            event('discovery_selector_opened')
            choice=xbmcgui.Dialog().select('Discover more',['Franchise collections','Director & writer credits'])
            event('discovery_selector_selected',choice=choice)
            if choice<0:return
            if choice==0:
                query=xbmcgui.Dialog().input('Find a collection',defaultt=item.get('set') or item.get('title') or item.get('label','')).strip()
                if query:self.open_search(query=query,position=next(n for n,(kind,label) in enumerate(SEARCH_KINDS) if kind=='collection'))
                return
            identity=self.rating_identity(item)
            if not identity:return
            self.setProperty('notice','Loading creator credits…')
            people=get_list(tmdb('crew',identity[0],tmdb_id=identity[1]))
            creators=set(item.get('director',[])+item.get('writer',[]))
            matches=[p for p in people if (p.get('title') or p.get('label','')) in creators]
            people=matches or [p for p in people if person_identity(p.get('file',''))]
            if not people:xbmcgui.Dialog().ok('Creator credits','This integration returned no creator credits for this title.');return
            selected=xbmcgui.Dialog().select('Creators' if matches else 'Crew credits',[p.get('title') or p.get('label','') for p in people])
            if selected>=0:
                discovery=discovery_result(people[selected],crew=True)
                if discovery:self.open_discovery(discovery)
        except Exception as exc:
            event('creator_credits_unavailable',error_type=type(exc).__name__);self.setProperty('notice','Creator credits could not load. Available title information is retained.')
        finally:self.actions_open=False
    def integration_status(self):
        lines=[]
        for addon,label in [('plugin.video.themoviedb.helper','Discovery / Trakt'),('plugin.video.umbrella','Playback'),('plugin.video.youtube','Previews')]:
            result=rpc('Addons.GetAddonDetails',{'addonid':addon,'properties':['enabled','version']})
            details=result.get('result',{}).get('addon',{})
            state='Enabled' if details.get('enabled') else 'Disabled' if details else 'Not installed'
            lines.append(label+': '+state+(' · '+details['version'] if details.get('version') else ''))
        lines.append('Account authorization is managed by each integration. Enabled does not confirm an account is linked.')
        for n,state in getattr(self,'row_states',{}).items():
            if state=='error':lines.append('List unavailable: '+self.getProperty('row'+str(n)))
        xbmcgui.Dialog().textviewer('BlackLanturn · Integration status','\n\n'.join(lines))
    def open_search(self,query=None,position=0):
        if query is None:query=xbmcgui.Dialog().input('Search BlackLanturn',defaultt=(self.search_state or {}).get('query',self.config.get('SearchQuery','')))
        query=query.strip()
        if not query:return
        if not self.search_state:self.search_origin=self.capture_browse()
        # Retire old row workers without discarding otherwise valid browse results.
        self.generation=getattr(self,'generation',0)+1;self.row_window_busy=False
        self.stop_preview();self.setProperty('filmographyBrowser','false');self.search_state={'query':query,'kind':'all'}
        self.config['SearchQuery']=query;self.save(invalidate=False)
        self.person_context=None;self.episode_browser_context=None
        self.mode='home';self.active_page=None;self.setProperty('page','home');self.setProperty('scroll','top')
        self.setProperty('episodeBrowser','false');self.setProperty('captionRows','true');self.setProperty('browseFilters','false')
        for cid in (900,901):self.getControl(cid).setHeight(344)
        self.select_search(position)
    def populate_search(self):
        self.setProperty('genreChooser','false')
        control=self.getControl(600);control.reset()
        for kind,label in SEARCH_KINDS:
            li=xbmcgui.ListItem(label=label);li.setProperty('active','true' if kind==self.search_state['kind'] else 'false');control.addItem(li)
        control.selectItem(next((n for n,x in enumerate(SEARCH_KINDS) if x[0]==self.search_state['kind']),0))
    def select_search(self,position):
        if not self.search_state:return
        sources=search_sources(self.search_state['query'])
        if not 0<=position<len(sources):return
        source=sources[position];self.stop_preview();clear_search_selection(self);self.return_focus=600
        self.search_state['kind']=source['kind'];self.mode='home';self.active_page=None
        self.setProperty('page','home');self.setProperty('scroll','top');self.setProperty('searchBrowser','true');self.setProperty('captionRows','true')
        self.setProperty('eyebrow','SEARCH · '+self.search_state['query']);self.populate_search()
        self.set_rows([{'label':row['label']+' · '+self.search_state['query'],'path':row['path']} for row in source.get('rows',[source])])
    def open_discovery(self,discovery):
        self.discovery_stack.append(self.capture_browse(include_stack=False))
        self.stop_preview();self.search_state=None;self.search_origin=None;self.person_context=None;self.episode_browser_context=None
        self.mode='home';self.active_page=None;self.selected=None
        captions=not discovery.get('hide_captions',False)
        for key,value in [('page','home'),('scroll','top'),('filmographyBrowser','false' if captions else 'true'),('captionRows','true' if captions else 'false'),('searchBrowser','false'),('episodeBrowser','false'),('browseFilters','false'),('allEpisodes','false'),('eyebrow',discovery['heading'])]:self.setProperty(key,value)
        for cid in (900,901):self.getControl(cid).setHeight(360 if self.section=='YouTube' else 344 if captions else 276)
        self.set_rows(discovery['rows'])
    def open_installed_addon(self,item):
        from addon_catalog import launch_destination
        destination=launch_destination(item)
        if destination is None:return
        enabled=rpc('Addons.GetAddonDetails',{'addonid':item['addonid'],'properties':['enabled']}).get('result',{}).get('addon',{}).get('enabled')
        if not enabled:
            xbmcgui.Dialog().notification('BlackLanturn','This add-on is no longer enabled.');return
        self.stop_preview()
        self.core_settings_request={'target':destination['window'],'parameters':destination['parameters'],
            'category':self.backend_position[0],'row':self.backend_position[1],'section':self.section,
            'origin':'sidebar','navigation_id':self.navigation_id,'active_page':self.active_page,'browse_state':self.capture_browse()}
        if destination.get('script'):self.core_settings_request['script']=destination['script']
        self.finish()
    def onClick(self,cid):
        if getattr(self,'actions_open',False):return
        self.search_row_step=None
        self.input_generation=getattr(self,'input_generation',0)+1;self.dwell=time.monotonic()
        if getattr(self,'owned_preview',False) and not getattr(self,'preview_dispatched',False):self.stop_preview()
        if cid==5:
            if self.rows[0] or self.rows[1]:self.setFocusId(900 if self.rows[0] else 901)
        elif cid in (700,701,710,711,712,713,720,721):self.arrow(cid)
        elif cid==610:self.refresh_youtube_recommendations()
        elif cid==600:
            if self.episode_browser_context:self.select_episode_season()
            elif self.search_state:self.select_search(self.getControl(600).getSelectedPosition())
            else:self.browse_source()
        elif cid==3000:self.filmography()
        elif cid in (900,901,3100):
            item=self.chosen(cid)
            if not item:return
            if item.get('_youtube_more'):
                self.request_youtube_more(cid-900 if cid in (900,901) else 0,explicit=True);return
            if item.get('_page_control'):
                n=cid-900 if cid in (900,901) else 0
                if item['_page_control']=='previous':
                    prior=self.histories[n].pop()
                    if prior:self.load_path(n,prior[0],back=True,position=prior[1])
                else:self.load_path(n,item['file'],item.get('label'))
                return
            if item.get('type')=='addon':self.open_installed_addon(item);return
            if getattr(self,'section','')=='YouTube' and is_youtube(item):
                if item.get('filetype')=='directory':self.load_path(cid-900 if cid in (900,901) else 0,item['file'],item.get('label'))
                elif youtube_video_id(item):self.update(item);self.onClick(101)
                return
            discovery=discovery_result(item)
            if discovery:self.open_discovery(discovery)
            elif is_browse_folder(item):
                self.load_path(cid-900 if cid in (900,901) else 0,item['file'],item.get('label'))
            elif episode_identity(item) and item.get('filetype')!='directory':
                self.update(item);self.onClick(101)
            else:self.details(item)
        elif cid==102:self.details(self.selected)
        elif cid==101:
            item=self.selected
            if not item:return
            if item.get('_youtube_more'):
                self.request_youtube_more(getattr(self,'last_row',0),explicit=True);return
            if item.get('_page_control'):
                n=getattr(self,'last_row',0)
                if item['_page_control']=='previous':
                    prior=self.histories[n].pop()
                    if prior:self.load_path(n,prior[0],back=True,position=prior[1])
                else:self.load_path(n,item['file'],item.get('label'))
                return
            if item.get('type')=='addon':self.open_installed_addon(item);return
            discovery=discovery_result(item)
            if discovery:self.open_discovery(discovery);return
            self.stop_preview()
            if item.get('filetype')=='directory':
                self.mode='home';self.setProperty('page','home');self.load_path(0,item['file'],item.get('title') or item.get('label'))
            else:self.playback_return=self.capture_browse();self.playback_options=resume_options(item);self.playback_request=item['file'];self.finish()
        elif cid==105:self.preview()
        elif cid==106:self.browse_all_episodes()
        elif cid==103 and self.selected:
            saved=self.config['Saved'];match=next((i for i,x in enumerate(saved) if x.get('file')==self.selected.get('file')),None)
            if match is None:saved.append(self.selected)
            else:saved.pop(match)
            self.save();self.update(self.selected)
        elif cid==10:
            if getattr(self,'section','')=='YouTube':self.select_youtube_tab('search')
            else:self.open_search()
        elif cid==50:
            index=self.getControl(50).getSelectedPosition()
            if 0<=index<len(self.navigation_items):
                self.startup_idle=False;self.setProperty('startupIdle','false')
                self.activate_navigation(self.navigation_items[index])
        elif cid==15:
            self.stop_preview();self.settings()
            if self.alive:self.set_nav(False,pending_focus=True);self.setFocusId(101 if self.mode=='details' else 600 if getattr(self,'search_state',None) and not any(self.rows) else 900)
    def onAction(self,action):
        if getattr(self,'actions_open',False):return
        cid=action.getId()
        # Invalidate intent before any Kodi call can yield to the monitor.
        if cid in (1,2,3,4,9,10,92,104,105):
            self.input_generation=getattr(self,'input_generation',0)+1;self.dwell=time.monotonic()
            if cid not in (3,4):self.search_row_step=None
            if getattr(self,'owned_preview',False) and not getattr(self,'preview_dispatched',False):self.stop_preview()
        if cid in (117,101):self.title_actions();return
        if 100<=cid<=109:self.mouse=True;self.setProperty('input','mouse')
        elif cid in (1,2,3,4,7,9,10,92):self.mouse=False;self.setProperty('input','remote')
        if cid in (3,4) and self.mode=='home':
            focus=self.getFocusId()
            if getattr(self,'search_state',None) and getattr(self,'adaptive_browsing',False):
                if focus in (101,102,103,105,106) and cid==4:
                    self.search_row_step=None;self.setFocusId(600);return
                if focus==600 and cid==4:
                    self.search_row_step=None
                    if any(self.rows):self.setFocusId(900 if self.rows[0] else 901)
                    else:self.step_search_rows(1)
                    return
                if focus in (900,901):
                    if cid==3 and self.row_offset==0 and focus==900:self.search_row_step=None;self.stop_preview();self.setFocusId(600)
                    else:self.shift_rows(-1 if cid==3 else 1,focus-900)
                    return
            previous=self.focus_key[0] if self.focus_key else focus
            if getattr(self,'adaptive_browsing',False) and focus in (900,901) and previous in (900,901):
                if self.shift_rows(-1 if cid==3 else 1,0):return
            if focus in (900,901) and previous==focus and self.shift_rows(-1 if cid==3 else 1,focus-900):return
        if cid in (104,105):
            focus=self.getFocusId()
            if focus in (900,901,3000,3100):
                items=self.rows[focus-900] if focus in (900,901) else (self.cast_people if focus==3000 else self.related)
                if items:
                    ctrl=self.getControl(focus);ctrl.selectItem(max(0,min(len(items)-1,ctrl.getSelectedPosition()+(1 if cid==105 else -1))))
            elif focus==50:pass
            else:self.arrow(701 if cid==105 else 700)
        elif cid in (9,10,92):
            self.stop_preview()
            if self.nav:self.set_nav(False,pending_focus=True);self.setFocusId(101 if self.mode=='details' else 600 if getattr(self,'search_state',None) and not any(self.rows) else self.return_focus)
            elif self.mode=='details':
                self.mode='home';self.setProperty('page','home');self.setProperty('scroll','top');self.setFocusId(self.return_focus if self.return_focus in (900,901) else 900)
                captions=bool(self.person_context or self.episode_browser_context or self.search_state or self.discovery_stack and self.getProperty('filmographyBrowser')!='true')
                self.setProperty('captionRows','true' if captions else 'false')
                for control in (900,901):self.getControl(control).setHeight(360 if self.section=='YouTube' else 344 if captions else 276)
                for control in (101,103,105,106):self.getControl(control).controlDown(self.getControl(900))
                self.row_navigation()
            else:
                prior=self.histories[self.last_row].pop()
                if prior:self.load_path(self.last_row,prior[0],back=True,position=prior[1])
                elif self.episode_browser_context:self.restore_episode_browser()
                elif self.person_context:
                    context=self.person_context;self.person_context=None;self.generation+=1;self.paths=context['paths']
                    self.episode_browser_context=context.get('episode_context');self.season_sources=context.get('season_sources',[]);self.season_title=context.get('season_title','');self.season_position=context.get('season_position',0)
                    self.setProperty('episodeBrowser','true' if self.episode_browser_context else 'false')
                    if self.episode_browser_context:self.populate_seasons()
                    self.page_definitions=context['page_definitions'];self.row_offset=context['row_offset'];self.row_cache=context['row_cache'];self.active_page=context['active_page']
                    for n in range(2):self.apply_row(n,context['rows'][n],context['labels'][n],context['positions'][n])
                    self.setProperty('eyebrow',context['eyebrow']);self.details(context['item'],cast_position=context['cast_position'])
                    event('filmography_returned_to_title')
                elif self.discovery_stack:self.generation+=1;self.restore_browse(self.discovery_stack.pop())
                elif self.search_state and self.search_origin:
                    self.generation+=1;self.restore_browse(self.search_origin)
                elif getattr(self,'section','')=='YouTube':
                    if getattr(self,'youtube_tab','home')!='home':self.load_youtube_section('home');self.setFocusId(600)
                    else:self.set_nav(True,pending_focus=True);self.setFocusId(50)
                elif self.active_page:self.load_section();self.setFocusId(600)
                else:self.set_nav(True,pending_focus=True);self.setFocusId(50)
        elif cid==2 and self.nav:self.set_nav(False,pending_focus=True);self.setFocusId(101 if self.mode=='details' else 600 if getattr(self,'search_state',None) and not any(self.rows) else self.return_focus)
    def finish(self):
        self.alive=False;self.generation+=1;self.stop_preview();self.close();event('live_closed')
