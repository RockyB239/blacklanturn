"""BlackLanturn update history and quiet Home notices; local Kodi inventory only."""
import json,threading,time
from pathlib import Path
import xbmc,xbmcgui,xbmcaddon,xbmcvfs
from update_notes import observe,pending,acknowledge,read_state,write_state,notes_text,notice_allowed,transact,empty_state,complete_inventory,has_dialog
ROOT=Path(__file__).resolve().parent
def state_path():
    return Path(xbmcvfs.translatePath(xbmcaddon.Addon('script.blacklanturn.preview').getAddonInfo('profile')))/'update-notes.json'
LOCK=threading.RLock()

def save_preference(enabled):
    transact(state_path(),lambda state:dict(state or empty_state(),enabled=bool(enabled)))

def mark_seen(sequence):
    def mark(state):
        if state:state['seen']=max(state['seen'],min(sequence,state['sequence']))
        return state
    transact(state_path(),mark)

class UpdateNotes(xbmcgui.WindowXMLDialog):
    def onInit(self):
        with LOCK:self.state=read_state(state_path())
        self.setProperty('notes',notes_text(self.state))
        self.setProperty('noticesEnabled','true' if self.state.get('enabled',True) else 'false')
        self.setFocusId(102)
    def onClick(self,cid):
        if cid==101:
            enabled=self.getProperty('noticesEnabled')!='true';save_preference(enabled)
            self.setProperty('noticesEnabled','true' if enabled else 'false')
        elif cid==102:self.close()
    def onAction(self,action):
        if action.getId() in (9,10,92):self.close()

def show_notes():
    try:
        read_state(state_path())
        dialog=UpdateNotes('UpdateNotes.xml',str(ROOT),'Default','1080i');dialog.doModal();del dialog
    except (ValueError,OSError):
        xbmcgui.Dialog().ok('BlackLanturn','Saved update notes are unavailable. Your accounts and playback settings have not been changed.')

class UpdateNotice(xbmcgui.WindowXMLDialog):
    def onInit(self):
        self.view=False;self.finished=False;self.opened=time.monotonic()
        self.setProperty('summary',self.summary);self.setFocusId(101)
        threading.Thread(target=self.timeout,name='BlackLanturnNoticeTimeout',daemon=True).start()
    def timeout(self):
        monitor=xbmc.Monitor()
        while not self.finished and not monitor.waitForAbort(.2):
            # New playback always wins, including automatic inline previews.
            if xbmc.Player().isPlaying() or time.monotonic()-self.opened>=15:
                self.finished=True;self.close();return
    def onClick(self,cid):
        if cid in (101,102):self.view=cid==101;self.finished=True;self.close()
    def onAction(self,action):
        if action.getId() in (9,10,92):self.finished=True;self.close()

def sample(rpc):
    response=rpc('Addons.GetAddons',{'installed':True,'properties':['name','version','enabled']})
    items=complete_inventory(response)
    catalog=json.loads((ROOT/'update-releases.json').read_text(encoding='utf-8'))
    return transact(state_path(),lambda old:observe(old,items,time.time(),catalog,complete=True))

class HomeUpdates:
    def __init__(self,owner,rpc):
        self.owner=owner;self.rpc=rpc;self.due=time.monotonic()+12;self.busy=False;self.state=None
        self.lifetime=owner.window_lifetime;self.failed=False
    def current(self):
        return self.owner.alive and self.owner.window_lifetime is self.lifetime
    def tick(self):
        try:self._tick()
        except (OSError,ValueError,KeyError,TypeError,RuntimeError):
            self.state=None;self.failed=True;self.due=time.monotonic()+120
            xbmc.log('BlackLanturn update notes unavailable; browsing continues and saved history is retained.',xbmc.LOGWARNING)
    def _tick(self):
        if not self.current():return
        now=time.monotonic()
        if now>=self.due and not self.busy:
            self.due=now+120;self.busy=True
            threading.Thread(target=self.refresh,name='BlackLanturnUpdateInventory',daemon=True).start()
        if not self.state or not pending(self.state):return
        owner=self.owner
        if not notice_allowed(home=owner.mode=='home' and not owner.nav,
          loading=owner.getProperty('loading')=='true' or bool(getattr(owner,'loading_paths',{})),
          playing=xbmc.Player().isPlaying(),dialog=has_dialog(xbmcgui.getCurrentWindowDialogId()),
          settings=owner.settings_open or owner.actions_open,idle=xbmc.getGlobalIdleTime()):return
        with LOCK:self.state=read_state(state_path())
        batches=pending(self.state)
        if not batches:return
        sequence=batches[-1]['id']
        changes={c['id']:c for batch in batches for c in batch['changes']}
        summary=str(len(changes))+' add-on'+('s' if len(changes)!=1 else '')+' changed. View the installed versions and release notes.'
        dialog=UpdateNotice('UpdateNotice.xml',str(ROOT),'Default','1080i');dialog.summary=summary
        owner.actions_open=True
        try:
            dialog.doModal();view=dialog.view;dialog.finished=True;del dialog
            mark_seen(sequence)
            if view and not xbmc.Player().isPlaying():show_notes()
            with LOCK:self.state=read_state(state_path())
        finally:owner.actions_open=False
    def refresh(self):
        try:
            if self.current() and not xbmc.Player().isPlaying():
                state=sample(self.rpc)
                if self.current():self.state=state
        except (ValueError,OSError,RuntimeError):
            # Preserve old data; never turn failure into an update-success notice.
            self.failed=True
        finally:self.busy=False
