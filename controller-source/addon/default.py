"""Private BlackLanturn preview entry point for the current Kodi profile."""
import sys,time,json
from pathlib import Path
import xbmc,xbmcgui,xbmcvfs,xbmcaddon
# Kodi abort signals belong to existing Monitor instances, not future ones.
monitor=xbmc.Monitor()
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from live_runtime import validate_paths,SkinStartupGate
PROFILE=validate_paths(xbmcvfs.translatePath('special://home/'),xbmcvfs.translatePath('special://profile/'),ROOT)
STORE=Path(xbmcvfs.translatePath(xbmcaddon.Addon('script.blacklanturn.preview').getAddonInfo('profile')))
EVIDENCE=STORE/'logs';EVIDENCE.mkdir(parents=True,exist_ok=True)
def record(event,**values):
    with (EVIDENCE/'runtime.jsonl').open('a') as f:f.write(json.dumps(dict(event=event,time=time.time(),**values))+'\n')
def run_live_review(startup=None,early_home=None,monitor=None):
    if monitor is None:monitor=xbmc.Monitor()
    resume=None;playback_resume=None;owner_skin=xbmc.getSkinDir()
    while not monitor.abortRequested() and xbmc.getSkinDir()==owner_skin:
        lightweight=bool(early_home and not resume and not playback_resume)
        if lightweight:
            from light_home_view import LightweightHome
            w=LightweightHome('LiveReview.xml',str(ROOT),'Default','1080i');w.early_home=early_home
        else:
            from live_review import LiveReview
            w=LiveReview('LiveReview.xml',str(ROOT),'Default','1080i')
        w.resume_backend=resume;w.resume_playback=playback_resume;w.startup_home=startup
        try:
            w.doModal()
            if lightweight and getattr(w,'startup_error',None):raise RuntimeError('Home attachment failed: '+w.startup_error)
            controller=getattr(w,'controller',None) if lightweight else w
            request=getattr(controller,'core_settings_request',None);playback=getattr(controller,'playback_request',None);state=getattr(controller,'playback_return',None);options=getattr(controller,'playback_options',{})
        finally:
            if lightweight:w.dispose()
            else:w.alive=False
        # Return state is detached above; retire the native view before playback.
        controller=None
        del w
        if monitor.abortRequested():return
        if playback:
            from playback_runtime import play_and_wait
            from youtube_core import video_id
            target=(state or {}).get('selected') or {}
            while True:
                session=None;series_session=None
                if video_id({'file':playback}):
                    from youtube_end import YouTubeEndSession
                    session=YouTubeEndSession(target,owner_skin)
                else:
                    from live_core import episode_identity
                    if episode_identity(target):
                        from series_end import SeriesEndSession
                        series_session=SeriesEndSession(target,owner_skin)
                try:
                    if series_session is not None:
                        returned=play_and_wait(playback,owner_skin,options,target,series_end=series_session)
                    else:returned=play_and_wait(playback,owner_skin,options,target,youtube_end=session) if session is not None else play_and_wait(playback,owner_skin,options,target)
                    if not returned:return
                    choice=session.prompt() if session is not None else series_session.prompt() if series_session is not None else None
                finally:
                    if session is not None:session.close()
                    if series_session is not None:series_session.close()
                if not choice:break
                if choice['action']=='series':
                    state=dict(state or {},_series_end_open=choice['item']);break
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
        from backend_core import CoreSettingsReturn
        gate=CoreSettingsReturn(time.monotonic())
        if request.get('parameters'):
            xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':'GUI.ActivateWindow','params':{'window':request['target'],'parameters':request['parameters']}}))
        else:xbmc.executebuiltin('ActivateWindow('+request['target']+')')
        if request.get('script'):xbmc.executebuiltin('RunScript('+request['script']+')')
        while not monitor.abortRequested():
            outcome=gate.tick(xbmcgui.getCurrentWindowId(),time.monotonic())
            if outcome!='wait':break
            xbmc.sleep(100)
        if monitor.abortRequested():return
        if outcome=='failed':xbmcgui.Dialog().notification('BlackLanturn','This page could not open; returning to BlackLanturn.')
        record('core_settings_return',target=request['target'],outcome=outcome,category=request['category'],row=request['row'])
        resume=request
        playback_resume=None
home=xbmcgui.Window(10000)
owns_session=False
startup=None
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
        from home_startup import HomeStartup
        startup=HomeStartup(home)
        gate=SkinStartupGate(time.monotonic())
        # Preparation uses the existing settling interval; native windows still
        # wait for skin confirmation. Report an import failure only after that.
        preload_error=None
        early_home=None
        try:
            from light_home_bootstrap import prepare_home
            early_home=prepare_home(ROOT,STORE)
            if not early_home:
                from live_review import LiveReview
        except Exception as exc:
            preload_error=exc
        while not monitor.abortRequested():
            outcome=gate.tick(xbmc.getSkinDir(),xbmc.getCondVisibility('Window.IsVisible(yesnodialog)'),time.monotonic())
            if outcome!='wait':break
            xbmc.sleep(100)
        if not monitor.abortRequested() and outcome=='ready':
            if preload_error is not None:raise preload_error
            record('installed_profile',profile=str(PROFILE),addon=str(ROOT),skin=xbmc.getSkinDir())
            if early_home:run_live_review(startup,early_home,monitor)
            else:run_live_review(startup,monitor=monitor)
except Exception:
    if startup is not None:startup.release()
    home.setProperty('BlackLanturn.Recovery.Visible','true');home.clearProperty('BlackLanturn.Handoff.Status')
    record('startup_error',error_type=sys.exc_info()[0].__name__)
    xbmcgui.Dialog().ok('BlackLanturn','The preview could not open. Use Kodi Settings to switch to your previous skin.')
finally:
    if startup is not None:startup.release()
    if owns_session:home.clearProperty('BlackLanturn.Preview.Running')
