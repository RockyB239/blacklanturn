"""Curated BlackLanturn releases: available before update, confirmed afterward."""
import json,threading,time
from pathlib import Path
import xbmc,xbmcgui,xbmcaddon,xbmcvfs
import release_updates as releases
from update_notes import notice_allowed,has_dialog
ROOT=Path(__file__).resolve().parent
LOCK=threading.RLock()
def profile_path():return Path(xbmcvfs.translatePath(xbmcaddon.Addon('script.blacklanturn.preview').getAddonInfo('profile')))
def state_path():return profile_path()/'release-notices.json'
def legacy_path():return profile_path()/'update-notes.json'
def home_path():return Path(xbmcvfs.translatePath('special://home/'))
def catalog_source():return releases.FEED

def save_preference(enabled):return releases.transact(state_path(),lambda s:dict(s,enabled=bool(enabled)),legacy_path())
def mark_seen(event):return releases.transact(state_path(),lambda s:releases.dismiss(s,event),legacy_path())
def request_update():
    if xbmc.Player().isPlaying():return False
    # Fixed native Installer destination: catalog text never supplies commands.
    xbmc.executebuiltin('RunPlugin(plugin://plugin.program.blacklanturninstaller/?mode=builds)')
    return True

class UpdateNotes(xbmcgui.WindowXMLDialog):
    def onInit(self):
        state=releases.read_state(state_path(),legacy_path())
        event=getattr(self,'event',None)
        self.entry=event['release'] if event else state['available'] or state['completed'] or (state['history'][-1] if state['history'] else None)
        self.setProperty('noticesEnabled','true' if state['enabled'] else 'false')
        self.setProperty('subtitle',self.entry['title'] if self.entry else 'BlackLanturn release notes')
        available=bool(self.entry and state['available'] and self.entry['id']==state['available']['id'])
        self.setProperty('updateAvailable','true' if available else 'false')
        listing=self.getControl(100);listing.reset()
        sections=self.entry['sections'] if self.entry else [{'heading':'BlackLanturn releases','bullets':['New BlackLanturn releases and our compatibility patches will be explained here.']}]
        for section in sections:
            item=xbmcgui.ListItem(section['heading']);item.setProperty('bullets','\n'.join('• '+s for s in section['bullets']));listing.addItem(item)
        self.setFocusId(102)
    def onClick(self,cid):
        if cid==101:
            enabled=self.getProperty('noticesEnabled')!='true';save_preference(enabled);self.setProperty('noticesEnabled','true' if enabled else 'false')
        elif cid==102:self.close()
        elif cid==103:self.close();request_update()
    def onAction(self,action):
        if action.getId() in (9,10,92):self.close()

def show_notes(event=None):
    try:
        releases.read_state(state_path(),legacy_path())
        dialog=UpdateNotes('UpdateNotes.xml',str(ROOT),'Default','1080i');dialog.event=event;dialog.doModal();del dialog
    except (ValueError,OSError):
        xbmcgui.Dialog().ok('BlackLanturn','Release notes are unavailable. Your accounts and playback settings have not been changed.')

class UpdateNotice(xbmcgui.WindowXMLDialog):
    def onInit(self):
        self.view=False;self.update=False;self.finished=False;self.opened=time.monotonic()
        available=self.event['kind']=='available'
        self.setProperty('available','true' if available else 'false')
        self.setProperty('heading','BlackLanturn update available' if available else 'BlackLanturn updated')
        self.setProperty('summary','Build '+self.event['release']['version']+' · '+self.event['release']['summary'])
        self.setProperty('dismissLabel','Later' if available else 'Dismiss');self.setFocusId(101)
        threading.Thread(target=self.timeout,name='BlackLanturnNoticeTimeout',daemon=True).start()
    def timeout(self):
        monitor=xbmc.Monitor()
        while not self.finished and not monitor.waitForAbort(.2):
            if xbmc.Player().isPlaying() or time.monotonic()-self.opened>=20:
                self.finished=True;self.close();return
    def onClick(self,cid):
        if cid in (101,102,103):self.view=cid==101;self.update=cid==103;self.finished=True;self.close()
    def onAction(self,action):
        if action.getId() in (9,10,92):self.finished=True;self.close()

def sample(rpc=None):
    """Background only: one bounded catalog fetch/hour; local marker each sample."""
    root=profile_path();cache=root/'release-catalog-cache.json';now=time.time();source=catalog_source();catalog={'schema':1,'releases':[]};fetched=0
    try:
        bundled=home_path()/'userdata/blacklanturn-releases.json'
        if bundled.stat().st_size<=releases.MAX_BYTES:catalog=releases.validate_catalog(json.loads(bundled.read_text()))
    except (OSError,ValueError):pass
    bundled_catalog=catalog
    try:
        if cache.stat().st_size<=releases.MAX_BYTES+2048:
            saved=json.loads(cache.read_text())
            if saved.get('source')==source:
                catalog=releases.validate_catalog(saved['catalog']);fetched=float(saved['fetched'])
    except (ValueError,OSError,KeyError,TypeError):pass
    if now-fetched>=3600:
        try:catalog=releases.fetch_catalog(source)
        except (OSError,ValueError):pass
        # Failures also back off; never hammer a missing feed or block rows.
        root.mkdir(parents=True,exist_ok=True)
        raw=json.dumps({'source':source,'fetched':now,'catalog':catalog})
        import os,tempfile
        fd,tmp=tempfile.mkstemp(prefix='release-catalog.',dir=str(root))
        try:
            with os.fdopen(fd,'w') as out:out.write(raw);out.flush();os.fsync(out.fileno())
            os.replace(tmp,cache)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
    merged={entry['id']:entry for entry in catalog['releases']+bundled_catalog['releases']}
    catalog=releases.validate_catalog({'schema':1,'releases':sorted(merged.values(),key=releases.order)[-30:]})
    marker=json.loads((home_path()/'userdata/blacklanturn-build.json').read_text())
    return releases.transact(state_path(),lambda old:releases.refresh(old,marker,catalog,now,home_path()),legacy_path())

class HomeUpdates:
    def __init__(self,owner,rpc):
        self.owner=owner;self.rpc=rpc;self.due=time.monotonic()+12;self.busy=False;self.state=None
        self.lifetime=owner.window_lifetime;self.failed=False
    def current(self):return self.owner.alive and self.owner.window_lifetime is self.lifetime
    def tick(self):
        try:self._tick()
        except (OSError,ValueError,KeyError,TypeError,RuntimeError):
            self.state=None;self.failed=True;self.due=time.monotonic()+120
            xbmc.log('BlackLanturn release notes unavailable; browsing continues.',xbmc.LOGWARNING)
    def _tick(self):
        if not self.current():return
        owner=self.owner
        loading=owner.getProperty('loading')=='true' or bool(getattr(owner,'loading_paths',{}))
        if time.monotonic()>=self.due and not self.busy and not loading and not xbmc.Player().isPlaying():
            self.due=time.monotonic()+120;self.busy=True
            threading.Thread(target=self.refresh,name='BlackLanturnReleaseCheck',daemon=True).start()
        if not self.state or not releases.pending(self.state):return
        if not notice_allowed(home=owner.mode=='home' and not owner.nav,loading=loading,
          playing=xbmc.Player().isPlaying(),dialog=has_dialog(xbmcgui.getCurrentWindowDialogId()),settings=owner.settings_open or owner.actions_open,idle=xbmc.getGlobalIdleTime()):return
        self.state=releases.read_state(state_path(),legacy_path());event=releases.pending(self.state)
        if not event:return
        dialog=UpdateNotice('UpdateNotice.xml',str(ROOT),'Default','1080i');dialog.event=event
        owner.actions_open=True
        try:
            dialog.doModal();view=dialog.view;update=dialog.update;dialog.finished=True;del dialog
            mark_seen(event)
            if update:request_update()
            elif view and not xbmc.Player().isPlaying():show_notes(event)
            self.state=releases.read_state(state_path(),legacy_path())
        finally:owner.actions_open=False
    def refresh(self):
        try:
            if self.current() and not xbmc.Player().isPlaying():
                state=sample(self.rpc)
                if self.current():self.state=state
        except (ValueError,OSError,RuntimeError):self.failed=True
        finally:self.busy=False
