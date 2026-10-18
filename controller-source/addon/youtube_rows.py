"""Account-owned YouTube row continuation and explicit Home refresh.

Workers only stage data. The browser monitor publishes one coherent update,
restores native selection, and skips preview observation during that rebind.
"""
import copy,threading,time
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
from youtube_core import video_id,tab_rows
from youtube_home import split_page,merge_page
from youtube_provider import load_home_rows,load_shelf_page

MAX_ROW_ITEMS=150

def _fetch_feed(path):
    from live_review import get_list
    return get_list(path)

def _focus_id():
    from live_review import gui_labels
    return int(gui_labels(['System.CurrentControlId'])['System.CurrentControlId'] or '0')

def _token(cursor):
    return (cursor or {}).get('continuation') or (cursor or {}).get('path')

def _more_card(error=False):
    label='Retry' if error else 'Next'
    image=str(Path(__file__).parent/'resources/media/page-next.png')
    return {'file':'blacklanturn://youtube/more','filetype':'directory','label':label,'title':label,'plot':'',
            '_page_control':'next','_youtube_more':True,'art':{'navigation':image,'icon':image}}

def _fresh_path(path):
    route=urlsplit(path);params=[(k,v) for k,v in parse_qsl(route.query) if k!='refresh']+[('refresh','1')]
    return urlunsplit(route._replace(query=urlencode(params)))

class YouTubeRows:
    def youtube_home_visible(self):
        paths={d.get('path') for d in getattr(self,'page_definitions',[])}
        return (getattr(self,'section','')=='YouTube' and self.mode=='home' and getattr(self,'youtube_tab','')=='home'
                and not getattr(self,'discovery_stack',[]) and all(not path or path in paths for path in getattr(self,'paths',[])))

    def youtube_category_counts(self,path):
        counts=Counter()
        for definition in self.page_definitions:
            if not definition.get('youtube_category') or definition.get('path')==path:continue
            counts.update({ident for ident in (video_id(x) for x in definition.get('local_items',[])) if ident})
        return counts

    def prepare_youtube_row(self,n,files):
        if getattr(self,'section','')!='YouTube':return files
        path=self.paths[n]
        if not path.startswith('plugin://plugin.video.youtube/'):return files
        if not hasattr(self,'youtube_pages'):self.youtube_pages={}
        definition=next((d for d in self.page_definitions if d.get('path')==path),{})
        page=self.youtube_pages.get(path)
        if page is not None and any(x.get('_youtube_more') for x in files):
            return copy.deepcopy(page['items'])+([_more_card(page.get('error'))] if page['cursor'] else [])
        items,cursor=split_page(files,path)
        if 'youtube_cursor' in definition:cursor=copy.deepcopy(definition['youtube_cursor'])
        # Existing provider/saved cards are stable. Diversity is applied only
        # to incoming continuation batches, never again at a finite end/return.
        page={'items':items,'cursor':cursor,'seen':[],'error':False}
        self.youtube_pages[path]=page
        # Off-screen rows retain at most the bounded native row window. Home
        # category definitions also retain their current items/cursor for return.
        for key in list(self.youtube_pages):
            if len(self.youtube_pages)<=8:break
            if key not in self.paths:self.youtube_pages.pop(key)
        return copy.deepcopy(items)+([_more_card()] if cursor else [])

    def request_youtube_more(self,n,explicit=False):
        if (getattr(self,'section','')!='YouTube' or self.mode!='home' or getattr(self,'youtube_job',None)
                or getattr(self,'youtube_update',None) or getattr(self,'settings_open',False) or getattr(self,'actions_open',False)
                or getattr(self,'youtube_refreshing',False)):return
        if explicit:self.stop_preview()
        elif self.nav or self.owned_preview or self.player.isPlaying():return
        path=self.paths[n];page=getattr(self,'youtube_pages',{}).get(path)
        if not page or not page['cursor'] or (page.get('error') and not explicit):return
        replace=len(page['items'])>=MAX_ROW_ITEMS
        if replace and not explicit:return
        cursor=copy.deepcopy(page['cursor']);key=_token(cursor)
        if not key or key in page['seen']:return
        lifetime=self.window_lifetime;generation=self.generation;displayed=self.rows[n]
        account_current=self.youtube_request_guard(generation);revision=getattr(self,'youtube_content_revision',None)
        job=object();self.youtube_job=job
        def current():
            return (account_current() and self.window_lifetime is lifetime and self.section=='YouTube'
                    and self.paths[n]==path and self.rows[n] is displayed and self.youtube_pages.get(path) is page
                    and getattr(self,'youtube_content_revision',None) is revision and self.youtube_job is job)
        counts=self.youtube_category_counts(path) if 'bl_shelf=' in path else {}
        self.setProperty('rowMessage'+str(n),'Loading more…')
        def work():
            try:
                files=[];seen=list(page['seen']);more=cursor
                # Empty/duplicate-only batches may still have a real continuation.
                # Bound each focused request; never fan out across Home shelves.
                for _ in range(2):
                    if not current():return
                    key=_token(more)
                    if not key or key in seen:more=None;break
                    seen.append(key)
                    if 'path' in more:
                        incoming,following=split_page(_fetch_feed(more['path']),more['path'])
                    else:incoming,following=load_shelf_page(more,current)
                    if not current():return
                    files=merge_page(files,incoming,counts);more=following
                    if _token(more) in seen:more=None
                    if files or not more:break
                replacing=replace and bool(files)
                if current():self.youtube_update={'kind':'page','current':current,'job':job,'n':n,'path':path,'page':page,
                    'items':merge_page([] if replacing else page['items'],files,{}),'cursor':more,'seen':seen[-16:],'replace':replacing}
            except Exception:
                if current():self.youtube_update={'kind':'page_error','current':current,'job':job,'n':n,'path':path,'page':page}
            finally:
                if self.youtube_job is job and not getattr(self,'youtube_update',None):self.youtube_job=None
        threading.Thread(target=work,name='BlackLanturnYouTubeRow',daemon=True).start()

    def refresh_youtube_recommendations(self):
        if not self.youtube_home_visible() or getattr(self,'youtube_refreshing',False):return
        self.stop_preview();self.youtube_home_request=object();self.youtube_home_pending=False
        revision=object();self.youtube_content_revision=revision
        self.youtube_update=None;job=object();self.youtube_job=job;self.youtube_refreshing=True
        generation=self.generation;lifetime=self.window_lifetime;identity=self.youtube_connection.identity
        account_current=self.youtube_request_guard()
        home_paths={d.get('path') for d in self.page_definitions}
        def current():
            return (account_current() and self.window_lifetime is lifetime and self.section=='YouTube'
                    and self.youtube_tab=='home' and self.mode=='home' and not self.discovery_stack and self.youtube_content_revision is revision
                    and all(not path or path in home_paths for path in self.paths)
                    and self.youtube_job is job)
        self.setProperty('youtubeRefreshLabel','Refreshing…');self.setProperty('notice','Requesting fresh YouTube recommendations…')
        def work():
            try:
                rows=tab_rows('home')
                for row in rows:
                    if not current():return
                    raw=_fetch_feed(_fresh_path(row['path']))
                    row['local_items'],row['youtube_cursor']=split_page(raw,row['path'])
                if not rows[0]['local_items']:raise RuntimeError('Recommendations unavailable')
                shelves=load_home_rows(current,refresh=True) if current() else []
                if not shelves:raise RuntimeError('Personalized Home unavailable')
                if current():self.youtube_update={'kind':'refresh','current':current,'job':job,'rows':rows+copy.deepcopy(shelves[1:]),'shelves':shelves,'identity':identity}
            except Exception:
                if current():self.youtube_update={'kind':'refresh_error','current':current,'job':job}
            finally:
                if self.youtube_job is job and not getattr(self,'youtube_update',None):
                    self.youtube_job=None;self.youtube_refreshing=False
                    if self.window_lifetime is lifetime:self.setProperty('youtubeRefreshLabel','Refresh recommendations')
        threading.Thread(target=work,name='BlackLanturnYouTubeRefresh',daemon=True).start()

    def apply_youtube_updates(self):
        update=getattr(self,'youtube_update',None)
        if not update:return False
        with self.preview_dispatch_lock:
            if update is not getattr(self,'youtube_update',None):return False
            if not update['current']():
                self.youtube_update=None
                if getattr(self,'youtube_job',None) is update['job']:self.youtube_job=None;self.youtube_refreshing=False
                return False
            kind=update['kind'];self.youtube_update=None
            try:
                if kind.startswith('refresh'):
                    self.youtube_refreshing=False;self.setProperty('youtubeRefreshLabel','Refresh recommendations')
                    if kind=='refresh':
                        self.stop_preview();self.youtube_pages={};self.generation+=1
                        self.youtube_home_cache={'identity':update['identity'],'time':time.monotonic(),'rows':copy.deepcopy(update['shelves'])}
                        self.set_rows(update['rows']);self.setFocusId(900)
                        self.setProperty('notice','YouTube recommendations refreshed')
                    else:self.setProperty('notice','Could not refresh YouTube. Current recommendations remain available; try Refresh recommendations again.')
                else:
                    n=update['n'];page=update['page'];previous_count=len(page['items']);control=self.getControl(900+n);position=control.getSelectedPosition()
                    anchor=self.rows[n][position] if 0<=position<len(self.rows[n]) else None
                    prior_page=copy.deepcopy(page);prior_rows=self.rows[n]
                    if kind=='page_error':page['error']=True
                    else:
                        page.update(items=update['items'],cursor=update['cursor'],seen=update['seen'],error=False)
                    files=copy.deepcopy(page['items'])+([_more_card(page['error'])] if page['cursor'] else [])
                    if anchor and anchor.get('_page_control')=='previous':files.insert(0,copy.deepcopy(anchor))
                    if update.get('replace'):selected=0
                    elif kind=='page' and anchor and anchor.get('_youtube_more'):
                        # Enter the appended choices instead of following Next to
                        # its new trailing position and immediately paging again.
                        selected=min(previous_count,max(0,len(files)-1))
                    elif anchor:selected=next((i for i,x in enumerate(files) if x.get('file')==anchor.get('file')),min(position,max(0,len(files)-1)))
                    else:selected=min(position,max(0,len(files)-1))
                    # apply_row runs the same presentation pipeline as initial load.
                    # Preserve this page object/cursor while its native vector rebinds.
                    label=next((d['label'] for d in self.page_definitions if d.get('path')==update['path']),self.getProperty('row'+str(n)))
                    focus=self.getFocusId();lifetime=self.window_lifetime;generation=self.generation
                    definitions=[(d,'youtube_cursor' in d,copy.deepcopy(d.get('youtube_cursor'))) for d in self.page_definitions if d.get('path')==update['path']]
                    for definition,_,_ in definitions:definition['youtube_cursor']=copy.deepcopy(page['cursor'])
                    try:
                        self.apply_row(n,files,label,selected,update_selected=False)
                    except RuntimeError:
                        # Cursor consumption commits only after native publication.
                        # Keep the old window retryable even for a terminal response.
                        page.clear();page.update(prior_page);page['error']=True
                        for definition,present,cursor in definitions:
                            if present:definition['youtube_cursor']=cursor
                            else:definition.pop('youtube_cursor',None)
                        self.youtube_pages[update['path']]=page;self.rows[n]=prior_rows
                        retry=copy.deepcopy(page['items'])+([_more_card(True)] if page['cursor'] else [])
                        if anchor and anchor.get('_page_control')=='previous':retry.insert(0,copy.deepcopy(anchor))
                        try:self.apply_row(n,retry,label,min(position,max(0,len(retry)-1)),update_selected=False)
                        except RuntimeError:pass
                        self.youtube_pages[update['path']]=page
                        self.setProperty('rowMessage'+str(n),'Could not load more. Select Retry.')
                        raise
                    finally:
                        # Kodi queues reset/add/select. The dispatched read observes
                        # the finished rebind rather than the old native focus.
                        def focus_current():
                            return (self.alive and self.window_lifetime is lifetime and self.generation==generation
                                    and self.section=='YouTube' and self.mode=='home' and self.paths[n]==update['path'])
                        try:
                            if focus==900+n and focus_current() and _focus_id()==0 and focus_current():self.setFocusId(900+n)
                        except RuntimeError:pass # A closed native window must not discard a successful page.
                    self.youtube_pages[update['path']]=page
                    if kind=='page':
                        for definition in self.page_definitions:
                            if definition.get('path')==update['path']:
                                definition['local_items']=copy.deepcopy(page['items']);definition['youtube_cursor']=copy.deepcopy(page['cursor'])
                        self.row_cache.pop(self.row_offset+n,None)
                    self.setProperty('rowMessage'+str(n),'Could not load more. Select Retry.' if kind=='page_error' else '')
                    self.focus_key=None
            finally:
                if getattr(self,'youtube_job',None) is update['job']:self.youtube_job=None
        return True

    def prefetch_youtube_row(self):
        if getattr(self,'section','')!='YouTube' or self.mode!='home' or self.nav:return
        if getattr(self,'row_window_busy',False) or getattr(self,'loading_paths',{}):return
        focus=self.getFocusId()
        if focus not in (900,901):return
        n=focus-900;position=self.getControl(focus).getSelectedPosition()
        if position<max(0,len(self.rows[n])-6):return
        page=getattr(self,'youtube_pages',{}).get(self.paths[n])
        explicit=self.getProperty('youtubeRowEnd')=='true'
        if explicit:self.setProperty('youtubeRowEnd','false')
        if page and len(page['items'])>=MAX_ROW_ITEMS and not explicit:return # Automatic prefetch stays bounded.
        self.request_youtube_more(n,explicit=explicit)

    def youtube_refresh_navigation(self):
        home=self.youtube_home_visible()
        bottom=home and bool(self.page_definitions) and self.row_offset==len(self.page_definitions)-1
        self.setProperty('youtubeRefreshBottom','true' if bottom else 'false')
        if not getattr(self,'youtube_refreshing',False):self.setProperty('youtubeRefreshLabel','Refresh recommendations')
        if bottom:self.getControl(900).controlDown(self.getControl(610))
