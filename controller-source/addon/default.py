"""Private BlackLanturn preview entry point for the current Kodi profile."""
import sys,time,json,traceback
from pathlib import Path
import xbmc,xbmcgui,xbmcvfs,xbmcaddon
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from live_runtime import validate_paths,SkinStartupGate
PROFILE=validate_paths(xbmcvfs.translatePath('special://home/'),xbmcvfs.translatePath('special://profile/'),ROOT)
STORE=Path(xbmcvfs.translatePath(xbmcaddon.Addon('script.blacklanturn.preview').getAddonInfo('profile')))
EVIDENCE=STORE/'logs';EVIDENCE.mkdir(parents=True,exist_ok=True)
def record(event,**values):
    with (EVIDENCE/'runtime.jsonl').open('a') as f:f.write(json.dumps(dict(event=event,time=time.time(),**values))+'\n')
def run_live_review():
    from live_review import LiveReview
    from backend_core import CoreSettingsReturn
    resume=None;playback_resume=None;owner_skin=xbmc.getSkinDir()
    while not xbmc.Monitor().abortRequested() and xbmc.getSkinDir()==owner_skin:
        w=LiveReview('LiveReview.xml',str(ROOT),'Default','1080i');w.resume_backend=resume;w.resume_playback=playback_resume
        w.doModal();request=getattr(w,'core_settings_request',None);playback=getattr(w,'playback_request',None);state=getattr(w,'playback_return',None);options=getattr(w,'playback_options',{});w.alive=False;del w
        if playback:
            from playback_runtime import play_and_wait
            from youtube_core import video_id
            target=(state or {}).get('selected') or {}
            while True:
                session=None
                if video_id({'file':playback}):
                    from youtube_end import YouTubeEndSession
                    session=YouTubeEndSession(target,owner_skin)
                try:
                    returned=play_and_wait(playback,owner_skin,options,target,youtube_end=session) if session is not None else play_and_wait(playback,owner_skin,options,target)
                    if not returned:return
                    choice=session.prompt() if session is not None else None
                finally:
                    if session is not None:session.close()
                if not choice:break
                if choice['action']=='channel':
                    state=dict(state or {},_youtube_end_channel=choice['item']);break
                target=choice['item'];playback=target['file'];options={}
            record('playback_return_ready');resume=None;playback_resume=state;continue
        if not request:return
        if request.get('inline_extension'):
            from extensions import run_inline
            resolver=lambda aid:xbmcaddon.Addon(aid).getAddonInfo('path') if xbmc.getCondVisibility('System.HasAddon('+aid+')') else None
            if not run_inline(request['inline_extension'],resolver):
                xbmcgui.Dialog().notification('BlackLanturn','This personal page is unavailable. Its sidebar entry has been kept.')
                continue
            return
        gate=CoreSettingsReturn(time.monotonic())
        if request.get('parameters'):
            xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'GUI.ActivateWindow','params':{'window':request['target'],'parameters':request['parameters']}}))
        else:xbmc.executebuiltin('ActivateWindow('+request['target']+')')
        if request.get('script'):xbmc.executebuiltin('RunScript('+request['script']+')')
        while not xbmc.Monitor().abortRequested():
            outcome=gate.tick(xbmcgui.getCurrentWindowId(),time.monotonic())
            if outcome!='wait':break
            xbmc.sleep(100)
        if xbmc.Monitor().abortRequested():return
        if outcome=='failed':xbmcgui.Dialog().notification('BlackLanturn','This page could not open; returning to BlackLanturn.')
        record('core_settings_return',target=request['target'],outcome=outcome,category=request['category'],row=request['row'])
        resume=request
        playback_resume=None
home=xbmcgui.Window(10000)
owns_session=False
try:
    from installer_recovery import recover_installer,RecoveryError
    try:
        recovered=recover_installer(xbmcvfs.translatePath('special://home/'),xbmc,xbmcaddon.Addon)
    except RecoveryError:
        xbmcgui.Dialog().ok('BlackLanturn update recovery','An interrupted update could not be recovered. Keep the recovery data and retry. Your saved accounts and settings have not been replaced.')
        raise SystemExit
    if recovered:
        xbmcgui.Dialog().ok('BlackLanturn update recovered','The interrupted update was recovered. Close and reopen Kodi before continuing. Your settings and authorizations were kept.')
        raise SystemExit
    if 'updates' in sys.argv:
        from update_notes_ui import show_notes
        show_notes()
    elif 'recover' in sys.argv:
        from live_recovery import return_to_previous_skin
        return_to_previous_skin()
    elif xbmc.getSkinDir()!='skin.blacklanturn.preview':
        xbmcgui.Dialog().ok('BlackLanturn','Select BlackLanturn Preview in Kodi Settings → Interface → Skin.')
    elif home.getProperty('BlackLanturn.Preview.Running')!='1':
        home.setProperty('BlackLanturn.Preview.Running','1');home.setProperty('BlackLanturn.Preview.Launched','1')
        home.clearProperty('BlackLanturn.Recovery.Visible');home.setProperty('BlackLanturn.Handoff.Status','Loading BlackLanturn…')
        owns_session=True
        gate=SkinStartupGate(time.monotonic())
        while not xbmc.Monitor().abortRequested():
            outcome=gate.tick(xbmc.getSkinDir(),xbmc.getCondVisibility('Window.IsVisible(yesnodialog)'),time.monotonic())
            if outcome!='wait':break
            xbmc.sleep(100)
        if not xbmc.Monitor().abortRequested() and outcome=='ready':
            record('installed_profile',profile=str(PROFILE),addon=str(ROOT),skin=xbmc.getSkinDir())
            run_live_review()
except Exception:
    home.setProperty('BlackLanturn.Recovery.Visible','true');home.clearProperty('BlackLanturn.Handoff.Status')
    record('startup_error',error_type=sys.exc_info()[0].__name__)
    xbmcgui.Dialog().ok('BlackLanturn','The preview could not open. Use Kodi Settings to switch to your previous skin.')
finally:
    if owns_session:home.clearProperty('BlackLanturn.Preview.Running')
