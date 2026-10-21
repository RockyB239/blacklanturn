"""Owned YouTube natural-ending suggestions, using the existing native client."""
import json,math,threading,time
from pathlib import Path
import xbmc,xbmcgui,xbmcvfs,xbmcaddon
from youtube_core import video_id,caption,YouTubeEndState,show_end_screen,save_end_preference,connected_account,end_card_height
from youtube_browser import read_account_store
ROOT=Path(__file__).resolve().parent
STORE=Path(xbmcvfs.translatePath(xbmcaddon.Addon('script.blacklanturn.preview').getAddonInfo('profile')))

def config():return json.loads((STORE/'rows.json').read_text())
def identity():
    connected,value=connected_account(read_account_store())
    return value if connected else None

def event(name,**values):
    folder=STORE/'logs';folder.mkdir(parents=True,exist_ok=True)
    with (folder/'youtube-end.jsonl').open('a') as stream:stream.write(json.dumps(dict(event=name,time=time.time(),**values))+'\n')

class YouTubeEndSession:
    def __init__(self,target,owner_skin):
        self.target=target or {};self.ident=video_id(self.target);self.owner_skin=owner_skin
        self.alive=True;self.items=None;self.started=False;self.reason='';self.invalid=False;self.source=None
        try:self.account=identity() if self.ident else None;self.enabled=bool(self.ident and self.account and config().get('YouTubeEndSuggestions',True))
        except (OSError,ValueError,TypeError):self.account=None;self.enabled=False
    def current(self):
        try:return self.alive and not self.invalid and xbmc.getSkinDir()==self.owner_skin and identity()==self.account
        except (OSError,ValueError,TypeError):return False
    def observe(self,player,playing,source,window):
        if not self.enabled or not playing or not source:return
        if self.source and self.source!=source:self.invalid=True;return
        if window!=12005:return
        if self.source is None:self.source=source
        if self.started or not self.current():return
        try:position=player.getTime();total=player.getTotalTime()
        except RuntimeError:return
        if not total or position<.5 or total-position>35:return
        self.started=True
        def fetch():
            began=time.monotonic()
            try:
                from youtube_provider import load_end_suggestions
                items=load_end_suggestions(self.ident,self.current)
                if self.current():self.items=items;event('suggestions_ready',video_id=self.ident,count=len(items),seconds=round(time.monotonic()-began,3))
            except Exception as exc:event('suggestions_unavailable',error_type=type(exc).__name__)
        threading.Thread(target=fetch,name='BlackLanturnYouTubeEnd',daemon=True).start()
    def prompt(self):
        ready=bool(self.items)
        event('playback_finished',video_id=self.ident,reason=self.reason,ready=ready)
        try:enabled=show_end_screen(self.reason,config(),self.current() and self.source is not None,ready)
        except (OSError,ValueError,TypeError):return None
        if not enabled:return None
        dialog=YouTubeEndDialog('YouTubeEnd.xml',str(ROOT),'Default','1080i')
        dialog.items=self.items;dialog.target=self.target;dialog.session=self
        dialog.doModal();result=dialog.result;del dialog
        return result
    def close(self):self.alive=False

class YouTubeEndDialog(xbmcgui.WindowXMLDialog):
    def onInit(self):
        self.result=None;self.active=True;self.modal=False
        self.state=YouTubeEndState(self.items,config().get('YouTubeEndAutoplay',False),time.monotonic())
        self.setProperty('suggestions','true');self.setProperty('endedTitle',self.target.get('title') or self.target.get('label','YouTube'))
        art=self.target.get('art') or {};self.setProperty('backdrop',art.get('fanart') or art.get('thumb') or 'blacklanturn-splash.png')
        self.setProperty('suggestionSource','Suggestions from your YouTube account' if self.items[0].get('_youtube_suggestion_source')=='account' else 'Related videos from YouTube')
        self.setProperty('details','false');self.setProperty('autoplay','Autoplay: '+('On' if self.state.autoplay else 'Off'))
        self.selection=0;self.focused_control=7000
        labels=['System.ScreenWidth','System.ScreenHeight']
        screen=json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'XBMC.GetInfoLabels','params':{'labels':labels}}))).get('result',{})
        height=end_card_height(screen.get(labels[0]),screen.get(labels[1]))
        for n in range(3):
            exists=n<len(self.items)
            for cid in (7000,7100,7200,7300,7400):self.getControl(cid+n).setVisible(exists)
            if not exists:continue
            item=self.items[n];art=item.get('art') or {}
            self.setProperty('cardThumb'+str(n),art.get('thumb') or item.get('thumbnail',''))
            self.setProperty('cardTitle'+str(n),item.get('title') or item.get('label',''))
            self.setProperty('cardCaption'+str(n),caption(item))
            self.getControl(7100+n).setHeight(height);self.getControl(7200+n).setHeight(height+10)
            self.getControl(7300+n).setPosition(134+556*n,348+height+18)
            self.getControl(7400+n).setPosition(134+556*n,348+height+123)
            self.getControl(7000+n).setHeight(height+150)
            self.getControl(7000+n).controlRight(self.getControl(7000+min(n+1,len(self.items)-1)))
        self.setFocusId(7000)
        self.update_status();event('end_screen_opened',count=len(self.items),autoplay=self.state.autoplay)
        threading.Thread(target=self.monitor,name='BlackLanturnYouTubeEndClock',daemon=True).start()
    def update_status(self):
        remaining=max(0,math.ceil(self.state.deadline-time.monotonic())) if self.state.deadline is not None else None
        self.setProperty('status','Next video in '+str(remaining)+' seconds · Any navigation cancels' if remaining is not None else 'Choose a video · Back hides suggestions')
    def monitor(self):
        monitor=xbmc.Monitor()
        while self.active and not monitor.abortRequested():
            if not self.session.current() or xbmc.Player().isPlaying():
                event('end_screen_retired',owner=self.session.current(),playing=xbmc.Player().isPlaying());self.finish();return
            if not self.modal:
                chosen=self.state.tick(time.monotonic())
                if chosen:self.result={'action':'play','item':chosen};event('autoplay_selected',video_id=video_id(chosen));self.finish();return
                self.update_status()
            if monitor.waitForAbort(.2):return
    def finish(self):self.active=False;self.close()
    def dismiss(self):
        if self.state.back()=='exit':self.finish();return
        self.setProperty('suggestions','false');self.setProperty('details','false');self.setFocusId(7999)
        event('suggestions_dismissed',autoplay_cancelled=self.state.deadline is None)
    def show_suggestions(self):
        self.state.visible=True;self.state.interact();self.setProperty('suggestions','true');self.setFocusId(7000);self.update_status()
    def selected(self):
        n=self.selection
        return self.items[n] if 0<=n<len(self.items) else self.items[0]
    def options(self):
        self.state.interact();self.update_status()
        item=self.selected();saved=config().get('Saved',[]);is_saved=any(x.get('file')==item.get('file') for x in saved)
        entries=[('play','Play'),('details','Details'),('save','Remove from My Stuff on this device' if is_saved else 'Save to My Stuff on this device')]
        if item.get('_youtube_channel'):entries.append(('channel','More from this channel'))
        entries.append(('disable','Turn off next-video suggestions'))
        self.modal=True
        try:index=xbmcgui.Dialog().contextmenu([label for _,label in entries])
        finally:self.modal=False
        if index<0:return
        action=entries[index][0]
        if action=='details':
            self.setProperty('detailTitle',item.get('title') or item.get('label',''))
            self.setProperty('detailBody',caption(item)+'\n\n'+(item.get('plot') or 'No description available.'))
            self.setProperty('details','true');self.setFocusId(7020)
        elif action=='save':
            # Reload immediately before merge; preserve every unrelated preference.
            values=config();saved=values.setdefault('Saved',[])
            if is_saved:saved[:]=[x for x in saved if x.get('file')!=item.get('file')]
            else:saved.append(item)
            path=STORE/'rows.json';temp=path.with_suffix('.youtube-end.tmp');temp.write_text(json.dumps(values,indent=2));temp.replace(path)
            xbmcgui.Dialog().notification('My Stuff','Removed on this device' if is_saved else 'Saved on this device',time=2000)
        elif action=='disable':save_end_preference(STORE/'rows.json','YouTubeEndSuggestions',False);self.finish()
        elif action=='channel':self.result={'action':'channel','item':dict(item,file='plugin://plugin.video.youtube/channel/'+item['_youtube_channel']+'/',filetype='directory')};self.finish()
        else:self.result={'action':'play','item':item};self.finish()
    def onClick(self,cid):
        self.state.interact();self.update_status()
        if cid in (7000,7001,7002):
            selected=self.state.choose(cid-7000)
            if selected:self.result={'action':'play','item':selected};self.finish()
        elif cid==7010:self.result={'action':'replay','item':self.target};self.finish()
        elif cid==7011:self.dismiss()
        elif cid==7012:self.finish()
        elif cid==7013:
            enabled=not self.state.autoplay
            try:save_end_preference(STORE/'rows.json','YouTubeEndAutoplay',enabled)
            except (OSError,ValueError):xbmcgui.Dialog().notification('YouTube','Could not save autoplay preference');return
            self.state.set_autoplay(enabled,time.monotonic());self.setProperty('autoplay','Autoplay: '+('On' if enabled else 'Off'));self.update_status()
        elif cid==7014:self.options()
        elif cid==7020:self.setProperty('details','false');self.setFocusId(7000)
    def onFocus(self,cid):
        if cid!=getattr(self,'focused_control',7000):self.state.interact();self.update_status()
        self.focused_control=cid
        if cid in (7000,7001,7002):self.selection=cid-7000
    def onAction(self,action):
        cid=action.getId()
        if cid in (9,10,92):
            if self.getProperty('details')=='true':self.setProperty('details','false');self.setFocusId(7000)
            else:self.dismiss()
        elif cid in (117,101):
            if not self.state.visible:self.show_suggestions()
            else:self.options()
        elif cid in (1,2,3,4,104,105,106,107,100):self.state.interact();self.update_status()
