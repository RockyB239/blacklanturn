"""Run providers after releasing WindowXML, then return without stealing focus."""
import json,time,threading
import xbmc,xbmcgui
from playback_core import PlaybackReturnGate,ResumeHandoff,action_identity
from playback_info import playback_info_fields,playback_identity,name

def integration_busy():
    return any(xbmc.getCondVisibility(condition) for condition in (
        'System.HasActiveModalDialog','Window.IsActive(busydialog)','Window.IsActive(busydialognocancel)',
        'System.IsAddonRunning(plugin.video.themoviedb.helper)','System.IsAddonRunning(plugin.video.umbrella)'))

class PlaybackInfoSession:
    """Nonblocking enrichment, tied to the exact active episode or movie."""
    def __init__(self,target):
        self.target=target or {};self.home=xbmcgui.Window(10000)
        self.ready=None;self.requested=None;self.worker=None;self.last_poll=0;self.alive=True;self.published=None
        self.clear()
    def clear(self):
        self.home.clearProperty('BlackLanturn.Playback.title')
        for field in ('plot','cast','castLabel','showtitle','season','episode','year')+tuple('cast'+str(i)+'.'+part for i in range(1,7) for part in ('name','role','thumb','id','bio')):
            self.home.clearProperty('BlackLanturn.Playback.'+field)
        self.published=None
    def tick(self,current,now):
        key=playback_identity(current)
        if not key:self.clear();return
        details=self.ready[1] if self.ready and self.ready[0]==key else None
        fields=playback_info_fields(current,self.target,details)
        if fields!=self.published:
            # Title is the XML validity guard; clear it while swapping metadata.
            self.home.clearProperty('BlackLanturn.Playback.title')
            for field,value in fields.items():
                if field!='title':self.home.setProperty('BlackLanturn.Playback.'+field,value)
            self.home.setProperty('BlackLanturn.Playback.title',fields['title']);self.published=fields
        identity=action_identity(self.target)
        if not identity or key==self.requested or self.worker and self.worker.is_alive():return
        if key[0]=='episode':
            if name(current.get('showtitle'))!=name(self.target.get('showtitle') or self.target.get('title')):return
            params={'tmdb_id':identity['tmdb_id'],'season':current.get('season'),'episode':current.get('episode')};kind='tv'
        elif identity['tmdb_type']=='movie' and key==playback_identity(self.target):
            params={'tmdb_id':identity['tmdb_id']};kind='movie'
        else:return
        self.requested=key
        def enrich():
            try:
                from live_review import get_list,tmdb
                found=get_list(tmdb('details',kind,**params))
                if self.alive and found and playback_identity(found[0])==key:
                    self.ready=(key,found[0])
                    people=get_list(tmdb('cast',kind,**params))
                    if self.alive:self.ready=(key,dict(found[0],people=people))
            except Exception:pass # Native metadata continues to render.
        self.worker=threading.Thread(target=enrich,name='BlackLanturnPlaybackInfo',daemon=True);self.worker.start()
    def close(self):
        self.alive=False;self.clear()

def play_and_wait(path,owner_skin,options=None,target=None):
    monitor=xbmc.Monitor();player=xbmc.Player();gate=PlaybackReturnGate(time.monotonic())
    resume=ResumeHandoff(target if options else None);info=PlaybackInfoSession(target)
    home=xbmcgui.Window(10000);home.setProperty('BlackLanturn.Handoff.Status','Finding playback…')
    def rpc(method,params):return json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}))).get('result',{})
    try:
        params={'item':{'file':path}}
        if options:params['options']=options
        response=json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'Player.Open','params':params})))
        if 'error' in response:
            xbmcgui.Dialog().notification('BlackLanturn','Playback could not open; returning to your title.')
            return xbmc.getSkinDir()==owner_skin
        while not monitor.abortRequested():
            playing=player.isPlayingVideo();now=time.monotonic()
            if playing and xbmc.getSkinDir()==owner_skin and now-info.last_poll>=1:
                home.clearProperty('BlackLanturn.Handoff.Status');info.last_poll=now
                try:
                    active=next((p for p in rpc('Player.GetActivePlayers',{}) if p['type']=='video'),None)
                    if active:
                        pid=active['playerid']
                        current=rpc('Player.GetItem',{'playerid':pid,'properties':['title','showtitle','season','episode','year','plot','cast']}).get('item',{})
                        info.tick(current,now)
                        if not resume.done:
                            progress=rpc('Player.GetProperties',{'playerid':pid,'properties':['percentage']})
                            if current and 'percentage' in progress:
                                seek=resume.tick(current,progress['percentage'],now)
                                if seek is not None:rpc('Player.Seek',{'playerid':pid,'value':{'percentage':seek}})
                except (ValueError,TypeError,KeyError):
                    resume.done=True;info.clear()
            if not playing:
                info.clear()
                if gate.played:home.setProperty('BlackLanturn.Handoff.Status','Returning to your title…')
            result=gate.tick(player.isPlaying(),integration_busy(),xbmcgui.getCurrentWindowId()==10000,
                             now,owner=xbmc.getSkinDir()==owner_skin)
            if result!='wait':return result=='return'
            if monitor.waitForAbort(.2):return False
        return False
    finally:
        info.close();home.clearProperty('BlackLanturn.Handoff.Status')

def wait_for_helper(alive):
    """RunScript is asynchronous; allow launch then wait for actual completion."""
    monitor=xbmc.Monitor();started=time.monotonic();quiet=None
    while alive() and not monitor.abortRequested():
        now=time.monotonic()
        if integration_busy():quiet=None
        elif quiet is None:quiet=now
        elif now-started>=2 and now-quiet>=1:return True
        if now-started>=120:return False
        if monitor.waitForAbort(.2):return False
    return False
